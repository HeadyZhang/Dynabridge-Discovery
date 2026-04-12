"""Website scraping module using Playwright.

Crawls a brand's website comprehensively — extracts text, screenshots,
brand claims, product info, and visual tone for the Brand Discovery PPT.
"""
import asyncio
import re
from pathlib import Path
from urllib.parse import urlparse, urljoin
from config import OUTPUT_DIR


# Keywords for identifying key pages to crawl
KEY_PAGE_KEYWORDS = [
    "about", "story", "mission", "values", "our-story",
    "product", "collection", "shop", "catalog",
    "faq", "reviews", "testimonials",
    "blog", "news", "press",
    "sustainability", "impact", "responsibility",
    "team", "founders", "leadership",
]

# Patterns for extracting brand claims
CLAIM_PATTERNS = [
    r'(?:we (?:are|believe|create|make|deliver|provide|offer))[^.!?]*[.!?]',
    r'(?:our (?:mission|vision|purpose|goal|commitment))[^.!?]*[.!?]',
    r'(?:dedicated to|committed to|passionate about|designed for)[^.!?]*[.!?]',
    r'(?:100%|#1|award|patent|certified|organic|sustainable|premium|innovative)[^.!?]*[.!?]',
]


async def scrape_brand_website(url: str, max_pages: int = 15) -> dict:
    """Scrape a brand website comprehensively.

    Returns:
        {
            "url": str,
            "pages": [{"url", "title", "text", "screenshot_path", "page_type"}],
            "brand_claims": [str],
            "product_info": [{"name", "price", "description"}],
            "brand_voice": {"tone_words": [...], "messaging_themes": [...]},
            "social_links": {"instagram": ..., "facebook": ..., ...},
            "navigation_structure": [str],
        }
    """
    if not url:
        return _empty_result("")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return _empty_result(url)

    result = {
        "url": url,
        "pages": [],
        "brand_claims": [],
        "product_info": [],
        "brand_voice": {"tone_words": [], "messaging_themes": []},
        "social_links": {},
        "navigation_structure": [],
    }

    screenshots_dir = OUTPUT_DIR / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    parsed_base = urlparse(url)
    base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )
            page = await context.new_page()

            # ── Homepage ──────────────────────────────────────
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    await browser.close()
                    return _empty_result(url)

            # Screenshot homepage
            screenshot_path = screenshots_dir / "homepage.png"
            await page.screenshot(path=str(screenshot_path), full_page=False)

            # Extract homepage content
            homepage_data = await _extract_page_data(page)
            result["pages"].append({
                "url": url,
                "title": homepage_data["title"],
                "text": homepage_data["text"][:8000],
                "screenshot_path": str(screenshot_path),
                "page_type": "homepage",
            })

            # Extract navigation structure
            result["navigation_structure"] = await _extract_navigation(page)

            # Extract social media links
            result["social_links"] = await _extract_social_links(page)

            # ── Discover internal links ───────────────────────
            all_links = await page.evaluate("""
                () => {
                    const base = new URL(window.location.href).origin;
                    return [...new Set(
                        Array.from(document.querySelectorAll('a[href]'))
                            .map(a => {
                                try { return new URL(a.href, base).href; }
                                catch { return null; }
                            })
                            .filter(h => h && h.startsWith(base) && !h.includes('#'))
                    )];
                }
            """)

            # Prioritize key pages, then take remaining up to max
            key_pages = []
            other_pages = []
            for link in all_links:
                path = urlparse(link).path.lower()
                if path in ("", "/", parsed_base.path):
                    continue
                if any(kw in path for kw in KEY_PAGE_KEYWORDS):
                    key_pages.append(link)
                else:
                    other_pages.append(link)

            pages_to_crawl = key_pages[:10] + other_pages[:max_pages - len(key_pages[:10])]

            # ── Crawl pages ───────────────────────────────────
            crawled = {url}
            for i, link in enumerate(pages_to_crawl):
                if link in crawled:
                    continue
                crawled.add(link)

                try:
                    await page.goto(link, wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(0.5)

                    pg_screenshot = screenshots_dir / f"page_{i}.png"
                    await page.screenshot(path=str(pg_screenshot), full_page=False)

                    pg_data = await _extract_page_data(page)

                    # Classify page type
                    path = urlparse(link).path.lower()
                    page_type = _classify_page(path, pg_data["title"])

                    result["pages"].append({
                        "url": link,
                        "title": pg_data["title"],
                        "text": pg_data["text"][:5000],
                        "screenshot_path": str(pg_screenshot),
                        "page_type": page_type,
                    })

                    # Extract product info from product pages
                    if page_type == "product":
                        products = await _extract_product_info(page)
                        result["product_info"].extend(products)

                except Exception:
                    continue

            await browser.close()

        # ── Post-processing ───────────────────────────────────
        all_text = " ".join(p["text"] for p in result["pages"])
        result["brand_claims"] = _extract_brand_claims(all_text)
        result["brand_voice"] = _analyze_brand_voice(all_text)

    except Exception:
        if not result["pages"]:
            return _empty_result(url)

    return result


async def _extract_page_data(page) -> dict:
    """Extract text and metadata from current page."""
    title = await page.title()
    text = await page.evaluate("""
        () => {
            // Remove script, style, nav, footer noise
            const clone = document.body.cloneNode(true);
            clone.querySelectorAll('script, style, noscript, iframe').forEach(el => el.remove());
            return clone.innerText;
        }
    """)
    return {"title": title, "text": text}


async def _extract_navigation(page) -> list[str]:
    """Extract the site navigation structure."""
    try:
        nav_items = await page.evaluate("""
            () => {
                const items = [];
                document.querySelectorAll('nav a, header a, [role="navigation"] a').forEach(a => {
                    const text = a.textContent.trim();
                    if (text && text.length < 50 && !text.includes('\\n')) {
                        items.push(text);
                    }
                });
                return [...new Set(items)].slice(0, 30);
            }
        """)
        return nav_items
    except Exception:
        return []


async def _extract_social_links(page) -> dict:
    """Extract social media profile links."""
    try:
        links = await page.evaluate("""
            () => {
                const social = {};
                const platforms = {
                    'instagram.com': 'instagram',
                    'facebook.com': 'facebook',
                    'twitter.com': 'twitter',
                    'x.com': 'twitter',
                    'tiktok.com': 'tiktok',
                    'youtube.com': 'youtube',
                    'linkedin.com': 'linkedin',
                    'pinterest.com': 'pinterest',
                };
                document.querySelectorAll('a[href]').forEach(a => {
                    for (const [domain, name] of Object.entries(platforms)) {
                        if (a.href.includes(domain)) {
                            social[name] = a.href;
                        }
                    }
                });
                return social;
            }
        """)
        return links
    except Exception:
        return {}


async def _extract_product_info(page) -> list[dict]:
    """Extract product details from a product page."""
    try:
        products = await page.evaluate("""
            () => {
                const products = [];
                // Try common product selectors
                const selectors = [
                    '[data-product]', '.product-card', '.product-item',
                    '[itemtype*="Product"]', '.grid-product',
                ];
                for (const sel of selectors) {
                    document.querySelectorAll(sel).forEach(el => {
                        const name = el.querySelector('h1, h2, h3, .product-title, [itemprop="name"]');
                        const price = el.querySelector('.price, [itemprop="price"], .product-price');
                        const desc = el.querySelector('.description, [itemprop="description"], .product-description');
                        if (name) {
                            products.push({
                                name: name.textContent.trim().slice(0, 200),
                                price: price ? price.textContent.trim().slice(0, 50) : '',
                                description: desc ? desc.textContent.trim().slice(0, 500) : '',
                            });
                        }
                    });
                    if (products.length > 0) break;
                }
                // Fallback: try structured data
                if (products.length === 0) {
                    document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                        try {
                            const data = JSON.parse(s.textContent);
                            const items = Array.isArray(data) ? data : [data];
                            items.forEach(item => {
                                if (item['@type'] === 'Product') {
                                    products.push({
                                        name: item.name || '',
                                        price: item.offers?.price ? `$${item.offers.price}` : '',
                                        description: (item.description || '').slice(0, 500),
                                    });
                                }
                            });
                        } catch {}
                    });
                }
                return products.slice(0, 20);
            }
        """)
        return products
    except Exception:
        return []


def _classify_page(path: str, title: str) -> str:
    """Classify a page by its URL path and title."""
    combined = (path + " " + title).lower()
    if any(kw in combined for kw in ["product", "shop", "collection", "catalog", "item"]):
        return "product"
    if any(kw in combined for kw in ["about", "story", "mission", "values", "team", "founder"]):
        return "about"
    if any(kw in combined for kw in ["blog", "news", "press", "article"]):
        return "blog"
    if any(kw in combined for kw in ["faq", "help", "support", "contact"]):
        return "support"
    if any(kw in combined for kw in ["review", "testimonial"]):
        return "reviews"
    return "other"


def _extract_brand_claims(text: str) -> list[str]:
    """Extract brand positioning claims from combined page text."""
    claims = []
    text_lower = text.lower()
    for pattern in CLAIM_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for m in matches:
            claim = m.strip()
            if 20 < len(claim) < 300:
                claims.append(claim)

    # Deduplicate similar claims
    unique = []
    for c in claims:
        if not any(c[:30] in existing for existing in unique):
            unique.append(c)
    return unique[:15]


def _analyze_brand_voice(text: str) -> dict:
    """Analyze the brand's communication tone and themes."""
    text_lower = text.lower()

    # Tone analysis
    tone_markers = {
        "professional": ["expertise", "industry", "solution", "performance", "quality"],
        "friendly": ["love", "enjoy", "fun", "happy", "smile", "welcome"],
        "premium": ["luxury", "exclusive", "premium", "finest", "exceptional", "curated"],
        "innovative": ["innovative", "cutting-edge", "revolutionary", "breakthrough", "technology"],
        "authentic": ["authentic", "genuine", "real", "honest", "transparent", "handmade"],
        "sustainable": ["sustainable", "eco", "organic", "green", "responsible", "ethical"],
        "aspirational": ["dream", "inspire", "empower", "transform", "elevate", "achieve"],
        "value-driven": ["affordable", "value", "savings", "deal", "budget", "price"],
    }

    tone_scores = {}
    for tone, words in tone_markers.items():
        score = sum(text_lower.count(w) for w in words)
        if score > 0:
            tone_scores[tone] = score

    top_tones = sorted(tone_scores, key=tone_scores.get, reverse=True)[:4]

    # Theme extraction
    theme_keywords = {
        "comfort": ["comfort", "cozy", "soft", "relaxed", "ease"],
        "durability": ["durable", "lasting", "tough", "resistant", "strong"],
        "style": ["style", "fashion", "design", "aesthetic", "look"],
        "health": ["health", "wellness", "care", "medical", "clinical"],
        "community": ["community", "together", "team", "family", "belong"],
        "craftsmanship": ["craft", "handmade", "artisan", "detail", "precision"],
        "performance": ["performance", "function", "feature", "technology", "engineered"],
    }

    theme_scores = {}
    for theme, words in theme_keywords.items():
        score = sum(text_lower.count(w) for w in words)
        if score > 0:
            theme_scores[theme] = score

    top_themes = sorted(theme_scores, key=theme_scores.get, reverse=True)[:5]

    return {"tone_words": top_tones, "messaging_themes": top_themes}


def _empty_result(url: str) -> dict:
    """Return minimal result when scraping fails."""
    return {
        "url": url,
        "pages": [{"url": url, "title": url, "text": "", "screenshot_path": "", "page_type": "homepage"}] if url else [],
        "brand_claims": [],
        "product_info": [],
        "brand_voice": {"tone_words": [], "messaging_themes": []},
        "social_links": {},
        "navigation_structure": [],
    }
