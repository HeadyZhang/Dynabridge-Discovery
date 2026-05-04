"""Auto image collection for PPT slides.

Collects brand-relevant images from three sources:
1. Brand website — product shots, lifestyle imagery, logos
2. E-commerce listings — Amazon product images
3. Unsplash — free stock photos matched by category keywords

Images are saved to output/project_{id}/images/ and returned as a
categorized dict for the PPT generator to use.
"""
import asyncio
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from config import OUTPUT_DIR


async def collect_images(
    project_id: int,
    brand_name: str,
    brand_url: str = "",
    scrape_data: dict = None,
    ecommerce_data: dict = None,
    category_keywords: list[str] = None,
) -> dict:
    """Collect images from all sources.

    Returns:
        {
            "brand": [Path, ...],       # Brand website images
            "product": [Path, ...],     # E-commerce product images
            "lifestyle": [Path, ...],   # Stock/lifestyle images
            "all": [Path, ...],         # All images combined
        }
    """
    img_dir = OUTPUT_DIR / f"project_{project_id}" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    tasks = [
        _collect_from_website(img_dir, brand_url, scrape_data),
        _collect_from_ecommerce(img_dir, ecommerce_data),
        _collect_from_website_httpx(img_dir, brand_url, brand_name),
        _collect_via_web_search(img_dir, brand_name, category_keywords),
        _collect_amazon_screenshots(img_dir, brand_name),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    brand_imgs = results[0] if not isinstance(results[0], Exception) else []
    product_imgs = results[1] if not isinstance(results[1], Exception) else []
    httpx_imgs = results[2] if not isinstance(results[2], Exception) else []
    search_imgs = results[3] if not isinstance(results[3], Exception) else []
    amazon_imgs = results[4] if not isinstance(results[4], Exception) else []

    # Merge httpx brand images with Playwright brand images (deduplicate by path)
    seen = {p.name for p in brand_imgs}
    for p in httpx_imgs:
        if p.name not in seen:
            brand_imgs.append(p)
            seen.add(p.name)

    # Merge Amazon images into product images
    seen_product = {p.name for p in product_imgs}
    for p in amazon_imgs:
        if p.name not in seen_product:
            product_imgs.append(p)
            seen_product.add(p.name)

    lifestyle_imgs = search_imgs

    # Vision-based relevance filter: remove images unrelated to the brand/product
    all_before = brand_imgs + product_imgs + lifestyle_imgs
    relevant = await _filter_relevant_images(all_before, brand_name, category_keywords)
    if relevant is not None:
        relevant_set = set(relevant)
        brand_imgs = [p for p in brand_imgs if p in relevant_set]
        product_imgs = [p for p in product_imgs if p in relevant_set]
        lifestyle_imgs = [p for p in lifestyle_imgs if p in relevant_set]

    # Sort each list: landscape-first (wider images get priority)
    brand_imgs = _sort_by_aspect(brand_imgs)
    product_imgs = _sort_by_aspect(product_imgs)
    lifestyle_imgs = _sort_by_aspect(lifestyle_imgs)

    total = len(brand_imgs) + len(product_imgs) + len(lifestyle_imgs)
    print(f"[image_collector] Collected {total} images: brand={len(brand_imgs)}, product={len(product_imgs)}, lifestyle={len(lifestyle_imgs)}")

    return {
        "brand": brand_imgs,
        "product": product_imgs,
        "lifestyle": lifestyle_imgs,
        "all": brand_imgs + product_imgs + lifestyle_imgs,
    }


async def _filter_relevant_images(
    image_paths: list[Path],
    brand_name: str,
    category_keywords: list[str] = None,
) -> list[Path] | None:
    """Use Claude Vision to filter out images unrelated to the brand/product.

    Sends batches of thumbnails to Claude and asks which ones are relevant
    to the brand and its product category. Returns only the relevant paths,
    or None if Vision is unavailable (caller keeps all images).
    """
    import base64
    import io

    if not image_paths:
        return None

    # Skip tiny/broken images, skip already-filtered prefixes
    # Auto-keep brand_ images (explicitly collected brand assets) and
    # images with brand name in filename — these are always relevant
    brand_lower = brand_name.lower().replace(" ", "")
    auto_keep = []
    candidates = []
    for p in image_paths:
        name = p.name.lower()
        if any(name.startswith(pfx) for pfx in ("_cropped", "segment_bg", "persona_", "hero_", "topic_")):
            continue
        try:
            from PIL import Image
            w, h = Image.open(p).size
            if w < 200 or h < 200:
                continue
        except Exception:
            continue
        # brand_ prefixed files go through Vision filter too (may be wrong site screenshots)
        candidates.append(p)

    if not candidates:
        return auto_keep or None  # auto_keep is now always empty but kept for safety

    try:
        from config import ANTHROPIC_API_KEY, MODEL_SONNET
        import anthropic
        if not ANTHROPIC_API_KEY:
            return None
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except Exception as e:
        print(f"[image_collector] Vision filter init failed: {e}")
        return None

    category_hint = ", ".join(category_keywords[:3]) if category_keywords else "consumer products"
    relevant = []

    # Process in batches of 20 (Vision token budget)
    batch_size = 20
    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]

        content = [{"type": "text", "text": (
            f"I collected these {len(batch)} images for a brand presentation about \"{brand_name}\" "
            f"(category: {category_hint}).\n\n"
            f"For EACH image, reply YES or NO:\n"
            f"- YES: product photos of {brand_name}'s actual products ({category_hint}), "
            f"brand packaging, lifestyle shots WITH the product visible, "
            f"retail/e-commerce listings showing {brand_name} products, brand campaigns, "
            f"product collections, website screenshots that SHOW {brand_name}'s products, "
            f"store displays, logo/branding assets.\n"
            f"- NO: images from a DIFFERENT company/brand that happens to share the name, "
            f"certificates/awards from unrelated organizations, "
            f"random people WITHOUT any {category_hint} product visible, "
            f"stock photos of scenery/nature, generic clip art, abstract art, "
            f"tiny icons/buttons, blurry/broken images, "
            f"images from a completely different industry (e.g., edtech, education, "
            f"astronomy if the brand sells {category_hint}), "
            f"or images where the product is NOT {category_hint}.\n\n"
            f"BE STRICT: If an image is not clearly related to {brand_name}'s {category_hint} "
            f"products, mark NO. When in doubt, mark NO — it's better to have fewer good images "
            f"than many irrelevant ones.\n"
            f"Format: one line per image, just the number and YES/NO.\nExample:\n1 YES\n2 NO\n3 YES"
        )}]

        for i, img_path in enumerate(batch):
            try:
                from PIL import Image
                img = Image.open(img_path).convert("RGB")
                w, h = img.size
                if w > 300 or h > 300:
                    ratio = min(300 / w, 300 / h)
                    img = img.resize((int(w * ratio), int(h * ratio)))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img.close()
                b64 = base64.b64encode(buf.getvalue()).decode()
                content.append({"type": "text", "text": f"\nImage {i+1} ({img_path.name[:40]}):"})
                content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}})
            except Exception:
                content.append({"type": "text", "text": f"\nImage {i+1}: [failed to load]"})

        try:
            response = client.messages.create(
                model=MODEL_SONNET,
                max_tokens=512,
                messages=[{"role": "user", "content": content}],
            )
            answer = response.content[0].text.strip()
            for line in answer.splitlines():
                line = line.strip().upper()
                # Parse "1 YES", "2. YES", "3: NO" etc.
                parts = re.split(r'[\s.:)\-]+', line, maxsplit=1)
                if len(parts) >= 2:
                    try:
                        idx = int(parts[0]) - 1
                        if 0 <= idx < len(batch) and "YES" in parts[1]:
                            relevant.append(batch[idx])
                            print(f"[image_filter] KEEP: {batch[idx].name[:50]}")
                        elif 0 <= idx < len(batch):
                            print(f"[image_filter] DROP: {batch[idx].name[:50]}")
                    except ValueError:
                        continue
        except Exception as e:
            print(f"[image_filter] Vision batch failed ({e}), keeping only product/ecom images")
            # On Vision failure, only keep images with product/ecom/brand prefixes
            for bp in batch:
                bn = bp.name.lower()
                if any(bn.startswith(pfx) for pfx in ("ecom_", "product_", "amazon_", "brand_")):
                    relevant.append(bp)

    kept = len(relevant)
    dropped = len(candidates) - kept
    print(f"[image_filter] Result: {kept} kept, {dropped} dropped out of {len(candidates)} screened")
    return relevant


def _sort_by_aspect(paths: list[Path]) -> list[Path]:
    """Sort images by area (largest first), then landscape-preference."""
    def _score(p):
        try:
            from PIL import Image
            with Image.open(str(p)) as img:
                area = img.width * img.height
                landscape_bonus = 1.2 if img.width > img.height else 1.0
                return area * landscape_bonus
        except Exception:
            return 0
    return sorted(paths, key=_score, reverse=True)


def _img_filename(url: str, prefix: str) -> str:
    """Generate a stable filename from URL."""
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    ext = Path(urlparse(url).path).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    return f"{prefix}_{h}{ext}"


MIN_WIDTH = 500
MIN_HEIGHT = 300
MAX_ASPECT = 4.0   # reject very wide banners
MIN_ASPECT_DEFAULT = 0.3  # reject very tall/narrow


async def _download_image(
    client: httpx.AsyncClient, url: str, save_path: Path, min_aspect: float = 0.0
) -> Path | None:
    """Download an image if it meets quality criteria.

    Rejects images that are too small (< 500x300), have extreme aspect
    ratios, or are below the byte-size threshold.
    """
    if save_path.exists() and save_path.stat().st_size > 5000:
        try:
            from PIL import Image
            with Image.open(str(save_path)) as img:
                ratio = img.width / img.height
                if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
                    return None
                if ratio < (min_aspect or MIN_ASPECT_DEFAULT) or ratio > MAX_ASPECT:
                    return None
            return save_path
        except Exception:
            pass
        return save_path
    try:
        resp = await client.get(url, follow_redirects=True, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 8000:
            content_type = resp.headers.get("content-type", "")
            if "image" in content_type or save_path.suffix in (".jpg", ".jpeg", ".png", ".webp"):
                from PIL import Image
                import io
                try:
                    with Image.open(io.BytesIO(resp.content)) as img:
                        ratio = img.width / img.height
                        if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
                            return None
                        if ratio < (min_aspect or MIN_ASPECT_DEFAULT) or ratio > MAX_ASPECT:
                            return None
                except Exception:
                    return None

                # Convert WEBP to PNG (python-pptx doesn't support WEBP)
                if save_path.suffix.lower() == ".webp" or "webp" in content_type:
                    try:
                        with Image.open(io.BytesIO(resp.content)) as img:
                            save_path = save_path.with_suffix(".png")
                            img.convert("RGB").save(str(save_path), format="PNG")
                    except Exception:
                        save_path.write_bytes(resp.content)
                else:
                    save_path.write_bytes(resp.content)
                return save_path
    except Exception as e:
        print(f"[image_collector] Download failed for {url[:80]}: {e}")
    return None


# ── Source 1: Brand Website ──────────────────────────────────

async def _collect_from_website(
    img_dir: Path, brand_url: str, scrape_data: dict
) -> list[Path]:
    """Extract and download key images from the brand's website."""
    if not brand_url or not scrape_data:
        return []

    images = []
    image_urls = set()

    # Collect image URLs from scrape data pages
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )
            page = await context.new_page()

            # Visit up to 3 key pages to extract images
            pages_to_visit = []
            for pg in scrape_data.get("pages", [])[:5]:
                if pg.get("page_type") in ("homepage", "product", "about"):
                    pages_to_visit.append(pg["url"])

            for page_url in pages_to_visit[:3]:
                try:
                    await page.goto(page_url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(1000)

                    # Extract large images (likely product/hero images)
                    urls = await page.evaluate("""
                        () => {
                            const imgs = [];
                            document.querySelectorAll('img').forEach(img => {
                                const src = img.src || img.dataset.src || img.dataset.lazySrc || '';
                                const w = img.naturalWidth || img.width || 0;
                                const h = img.naturalHeight || img.height || 0;
                                // Only keep images that are reasonably large
                                if (src && (w >= 200 || h >= 200 || (!w && !h))) {
                                    // Skip tiny icons, tracking pixels
                                    if (!src.includes('pixel') && !src.includes('track') &&
                                        !src.includes('analytics') && !src.includes('.svg') &&
                                        !src.includes('data:image')) {
                                        imgs.push(src);
                                    }
                                }
                            });
                            // Also check CSS background images on hero sections
                            document.querySelectorAll('.hero, .banner, [class*="hero"], [class*="banner"]').forEach(el => {
                                const bg = getComputedStyle(el).backgroundImage;
                                const match = bg.match(/url\\(['"]?(.*?)['"]?\\)/);
                                if (match) imgs.push(match[1]);
                            });
                            return imgs.slice(0, 15);
                        }
                    """)

                    for u in urls:
                        abs_url = urljoin(page_url, u)
                        if abs_url not in image_urls:
                            image_urls.add(abs_url)
                except Exception:
                    continue

            await browser.close()

    except ImportError:
        return []

    # Download collected images — filter out very narrow/tall images (aspect >= 0.5)
    async with httpx.AsyncClient() as client:
        for url in list(image_urls)[:20]:
            fname = _img_filename(url, "brand")
            path = await _download_image(client, url, img_dir / fname, min_aspect=0.5)
            if path:
                images.append(path)
            if len(images) >= 10:
                break

    return images


# ── Source 2: E-commerce Product Images ──────────────────────

async def _collect_from_ecommerce(
    img_dir: Path, ecommerce_data: dict
) -> list[Path]:
    """Download product images from e-commerce data."""
    if not ecommerce_data:
        return []

    images = []
    image_urls = []

    for product in ecommerce_data.get("products", [])[:10]:
        # Try various image fields
        img_url = (
            product.get("image_url")
            or product.get("image")
            or product.get("thumbnail")
            or ""
        )
        if img_url and img_url.startswith("http"):
            image_urls.append(img_url)

    async with httpx.AsyncClient() as client:
        for url in image_urls[:8]:
            fname = _img_filename(url, "product")
            path = await _download_image(client, url, img_dir / fname)
            if path:
                images.append(path)

    return images


# ── Source 3: httpx-based website image extraction ─────────

async def _collect_from_website_httpx(
    img_dir: Path, brand_url: str, brand_name: str,
) -> list[Path]:
    """Extract images from the brand website using plain httpx + regex.

    Fallback when Playwright is unavailable. Fetches the homepage HTML
    and extracts img src attributes, og:image meta tags, and other
    common image patterns.
    """
    if not brand_url:
        return []

    images = []
    image_urls = set()

    pages_to_try = [brand_url]
    if not brand_url.endswith("/"):
        pages_to_try.append(brand_url + "/")
    for suffix in ("/collections", "/products", "/pages/about"):
        pages_to_try.append(brand_url.rstrip("/") + suffix)

    async with httpx.AsyncClient(
        follow_redirects=True, timeout=12,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    ) as client:
        for page_url in pages_to_try[:4]:
            try:
                resp = await client.get(page_url)
                if resp.status_code != 200:
                    continue
                html = resp.text

                # og:image
                for m in re.finditer(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html):
                    image_urls.add(urljoin(page_url, m.group(1)))

                # img src (skip tiny icons and data URIs)
                for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)', html):
                    src = m.group(1)
                    if src.startswith("data:") or ".svg" in src:
                        continue
                    if any(skip in src for skip in ("pixel", "track", "analytics", "icon", "logo", "favicon")):
                        continue
                    image_urls.add(urljoin(page_url, src))

                # srcset (pick largest)
                for m in re.finditer(r'srcset=["\']([^"\']+)', html):
                    parts = m.group(1).split(",")
                    best_url = ""
                    best_w = 0
                    for part in parts:
                        tokens = part.strip().split()
                        if len(tokens) >= 2:
                            w_match = re.match(r'(\d+)w', tokens[-1])
                            if w_match and int(w_match.group(1)) > best_w:
                                best_w = int(w_match.group(1))
                                best_url = tokens[0]
                    if best_url and best_w >= 400:
                        image_urls.add(urljoin(page_url, best_url))

            except Exception:
                continue

        # Download (limit to 15 candidates, keep 10 max)
        for url in list(image_urls)[:15]:
            fname = _img_filename(url, "httpx")
            path = await _download_image(client, url, img_dir / fname, min_aspect=0.5)
            if path:
                images.append(path)
            if len(images) >= 10:
                break

    print(f"[image_collector] httpx website: found {len(image_urls)} URLs, downloaded {len(images)}")
    return images


# ── Source 4: Web search → scrape discovered pages ────────

async def _collect_via_web_search(
    img_dir: Path, brand_name: str, category_keywords: list[str] = None,
) -> list[Path]:
    """Use Anthropic web_search to find product/lifestyle pages, then scrape images.

    Two-step process:
      1. Ask Claude to search for the brand and return PAGE URLs
         (Amazon listings, brand product pages, blog features)
      2. Fetch those pages via httpx and extract <img> src attributes
    """
    try:
        from config import ANTHROPIC_API_KEY, MODEL_SONNET as _MODEL_SONNET
        if not ANTHROPIC_API_KEY:
            return []
    except ImportError:
        return []

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        category_hint = " ".join((category_keywords or [])[:3])
        prompt = f"""Search the web for "{brand_name}" {f'({category_hint})' if category_hint else ''} products and find the best pages that contain product images.

I need PAGE URLs (not direct image URLs) where I can find high-quality product and lifestyle photos of {brand_name} products{f' in the {category_hint} category' if category_hint else ''}:
1. {brand_name} official website product/collection pages
2. {brand_name} Amazon product listing pages
3. Blog reviews or lifestyle features of {brand_name} products

IMPORTANT: Only return pages specifically about {brand_name} products. Do NOT include pages about unrelated brands or categories.

Return a JSON array of page URLs: ["https://...", "https://..."]
Return 5-8 URLs. Return ONLY the JSON array."""

        response = client.messages.create(
            model=_MODEL_SONNET,
            max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            messages=[{"role": "user", "content": prompt}],
        )

        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        page_urls = []
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                items = json.loads(text[start:end])
                for item in items:
                    url = item if isinstance(item, str) else (item.get("url", "") if isinstance(item, dict) else "")
                    if url.startswith("http"):
                        page_urls.append(url)
            except Exception:
                pass

        # Also extract raw URLs from the text
        for m in re.finditer(r'https?://[^\s"\'<>\]]+', text):
            url = m.group(0).rstrip(".,;)")
            if url.startswith("http") and url not in page_urls:
                page_urls.append(url)

        print(f"[image_collector] web_search: found {len(page_urls)} page URLs to scrape")

        # Step 2: scrape images from discovered pages
        images = []
        image_urls = set()
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=12,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        ) as dl_client:
            for page_url in page_urls[:6]:
                try:
                    resp = await dl_client.get(page_url)
                    if resp.status_code != 200:
                        continue
                    html = resp.text

                    # og:image
                    for m in re.finditer(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html):
                        image_urls.add(urljoin(page_url, m.group(1)))

                    # img src — prefer large/product images
                    for m in re.finditer(r'<img[^>]+src=["\']([^"\']+)', html):
                        src = m.group(1)
                        if src.startswith("data:") or ".svg" in src:
                            continue
                        if any(skip in src.lower() for skip in ("pixel", "track", "icon", "logo", "favicon", "sprite")):
                            continue
                        image_urls.add(urljoin(page_url, src))

                    # srcset largest
                    for m in re.finditer(r'srcset=["\']([^"\']+)', html):
                        parts = m.group(1).split(",")
                        best_url, best_w = "", 0
                        for part in parts:
                            tokens = part.strip().split()
                            if len(tokens) >= 2:
                                w_match = re.match(r'(\d+)w', tokens[-1])
                                if w_match and int(w_match.group(1)) > best_w:
                                    best_w = int(w_match.group(1))
                                    best_url = tokens[0]
                        if best_url and best_w >= 400:
                            image_urls.add(urljoin(page_url, best_url))

                except Exception:
                    continue

            # Download discovered images
            for url in list(image_urls)[:20]:
                fname = _img_filename(url, "search")
                path = await _download_image(dl_client, url, img_dir / fname, min_aspect=0.4)
                if path:
                    images.append(path)
                if len(images) >= 10:
                    break

        print(f"[image_collector] web_search: scraped {len(image_urls)} image URLs, downloaded {len(images)}")
        return images

    except Exception as e:
        print(f"[image_collector] web_search failed: {e}")
        return []


async def _collect_amazon_screenshots(
    img_dir: Path, brand_name: str,
) -> list[Path]:
    """Scrape Amazon product listing images for the brand.

    Searches Amazon for the brand name and extracts high-res product images
    from the search results and individual listing pages.
    """
    images = []
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            # Search Amazon for the brand
            search_url = f"https://www.amazon.com/s?k={brand_name.replace(' ', '+')}"
            resp = await client.get(search_url)
            if resp.status_code != 200:
                return images

            html = resp.text

            # Extract high-res Amazon product images (m.media-amazon.com)
            img_urls = set()

            # Main product images from search results
            for m in re.finditer(r'https://m\.media-amazon\.com/images/I/[A-Za-z0-9._%-]+', html):
                url = m.group(0)
                # Upgrade to high-res version
                url = re.sub(r'\._[A-Z]+_[A-Z0-9,_]+_\.', '.', url)
                img_urls.add(url)

            # Also try to find ASIN links for individual product pages
            asins = re.findall(r'/dp/([A-Z0-9]{10})', html)
            for asin in asins[:3]:  # Check top 3 products
                try:
                    prod_resp = await client.get(f"https://www.amazon.com/dp/{asin}")
                    if prod_resp.status_code == 200:
                        prod_html = prod_resp.text
                        for m in re.finditer(r'https://m\.media-amazon\.com/images/I/[A-Za-z0-9._%-]+', prod_html):
                            url = m.group(0)
                            url = re.sub(r'\._[A-Z]+_[A-Z0-9,_]+_\.', '.', url)
                            img_urls.add(url)
                except Exception:
                    continue

            print(f"[image_collector] Amazon: found {len(img_urls)} product image URLs")

            # Download top images
            for url in list(img_urls)[:15]:
                fname = _img_filename(url, "amazon")
                path = await _download_image(client, url, img_dir / fname, min_aspect=0.4)
                if path:
                    images.append(path)
                if len(images) >= 8:
                    break

            print(f"[image_collector] Amazon: downloaded {len(images)} images")

    except Exception as e:
        print(f"[image_collector] Amazon scraping failed: {e}")

    return images


def infer_category_keywords(
    brand_name: str,
    category: str = "",
    brand_context: dict = None,
) -> list[str]:
    """Generate semantically-aligned image search keywords for brand/category.

    Strategy:
    1. Use Claude to dynamically generate precise search terms for THIS brand (best quality)
    2. Fall back to static keyword map if Claude unavailable
    3. Generic fallback as last resort
    """
    # Build context for Claude
    cat_name = category or ""
    target_audience = ""
    hero_products = ""
    if brand_context:
        cat_land = brand_context.get("category_landscape", {})
        cat_name = cat_land.get("category_name", cat_name)
        pos = brand_context.get("brand_positioning", {})
        target_audience = pos.get("target_audience", "")
        heroes = brand_context.get("hero_products", [])
        if heroes:
            hero_names = [h.get("name", h) if isinstance(h, dict) else str(h) for h in heroes[:3]]
            hero_products = ", ".join(hero_names)

    # Strategy 1: Claude dynamic generation (produces precise, brand-specific search terms)
    try:
        from config import ANTHROPIC_API_KEY, MODEL_HAIKU
        if ANTHROPIC_API_KEY:
            from anthropic import Anthropic
            client = Anthropic(api_key=ANTHROPIC_API_KEY)

            context_parts = [f"Brand: {brand_name}"]
            if cat_name:
                context_parts.append(f"Category: {cat_name}")
            if target_audience:
                context_parts.append(f"Target audience: {target_audience}")
            if hero_products:
                context_parts.append(f"Hero products: {hero_products}")

            response = client.messages.create(
                model=MODEL_HAIKU,
                max_tokens=200,
                messages=[{"role": "user", "content": f"""Generate 5 Bing Image Search queries to find high-quality lifestyle and product photos for a brand discovery presentation.

{chr(10).join(context_parts)}

Requirements:
- Mix of: product shots (clean, white background), lifestyle shots (people using the product), and brand environment shots
- Each query should be 4-7 words, optimized for image search
- Be specific to THIS brand's category — not generic

Return ONLY a JSON array of 5 strings, nothing else.
Example for a fitness brand: ["premium gym equipment modern studio", "woman training dumbbell workout", "athletic gear flat lay", "active lifestyle fitness outdoor", "modern gym interior design"]"""}],
            )
            text = response.content[0].text
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                keywords = json.loads(text[start:end])
                if isinstance(keywords, list) and len(keywords) >= 3:
                    print(f"[image_collector] Claude generated {len(keywords)} search terms for '{brand_name}'")
                    return [str(k) for k in keywords[:5]]
    except Exception as e:
        print(f"[image_collector] AI keyword generation failed: {e}")

    # Strategy 2: Static keyword map fallback
    cat_lower = (cat_name or "").lower()
    # Generic category → image search terms (no brand-specific entries)
    _category_image_map = {
        "candle": ["candle cozy home ambiance", "home fragrance lifestyle", "candle relaxation self care"],
        "cookware": ["kitchen cookware modern", "cooking lifestyle gourmet", "kitchen product premium"],
        "furniture": ["modern home interior", "furniture lifestyle living room", "home decor minimal"],
        "skincare": ["skincare routine woman", "beauty product lifestyle", "woman glowing skin"],
        "makeup": ["makeup beauty lifestyle", "cosmetics product flat lay", "beauty routine morning"],
        "headphone": ["headphone music lifestyle", "wireless earbuds commute", "audio tech modern"],
        "apparel": ["fashion lifestyle model", "casual wear street style", "modern clothing brand"],
        "shoe": ["sneaker lifestyle urban", "athletic shoe running", "shoe fashion street"],
        "fitness": ["fitness gym workout", "exercise lifestyle active", "gym equipment modern"],
    }

    for key, searches in _category_image_map.items():
        if key in cat_lower:
            return searches[:5]

    # Strategy 3: Generic fallback
    return [
        f"{brand_name} product lifestyle",
        f"{brand_name} brand product photo",
        f"{cat_name or 'consumer product'} lifestyle premium",
        "modern product design minimal",
        "active lifestyle product photography",
    ]
