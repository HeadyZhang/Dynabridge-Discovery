"""Automatic competitor discovery module.

Combines multiple strategies (in priority order):
1. Claude Managed Agent — autonomous web research via web_search tool (preferred)
2. E-commerce scraping — search Amazon for the same category, extract brand names
3. AI inference — ask Claude to identify competitors based on brand/category context

Returns a deduplicated list of competitor names with confidence and source.
"""
import asyncio
import json
import re
from collections import Counter


async def discover_competitors(
    brand_name: str,
    brand_url: str = "",
    scrape_data: dict = None,
    ecommerce_data: dict = None,
    max_competitors: int = 8,
) -> list[dict]:
    """Discover competitors automatically.

    Tries Claude Managed Agent first (web_search-based research).
    Falls back to Amazon scraping + AI inference if Managed Agent is unavailable.

    Returns:
        [{"name": str, "source": "managed_agent"|"amazon"|"ai"|"both", "confidence": float, "url": str|None}]
    """
    # Strategy 1: Try Managed Agent (preferred — uses web_search, no Playwright needed)
    try:
        from pipeline.managed_agent import discover_competitors_managed

        category_context = _infer_category(ecommerce_data, brand_name)
        managed_results = await discover_competitors_managed(
            brand_name=brand_name,
            brand_url=brand_url,
            category_context=category_context,
            max_competitors=max_competitors,
        )
        if managed_results and len(managed_results) >= 3:
            return managed_results
        else:
            print(f"[competitor_discovery] Managed agent returned {len(managed_results) if managed_results else 0} results, falling through")
    except Exception as e:
        print(f"[competitor_discovery] Managed agent failed: {e}")
        pass  # Fall through to legacy methods

    # Strategy 2: Legacy — Amazon scraping + AI inference in parallel
    amazon_task = _discover_from_amazon(brand_name, ecommerce_data)
    ai_task = _discover_from_ai(brand_name, brand_url, scrape_data)

    amazon_competitors, ai_competitors = await asyncio.gather(
        amazon_task, ai_task, return_exceptions=True
    )

    if isinstance(amazon_competitors, Exception):
        amazon_competitors = []
    if isinstance(ai_competitors, Exception):
        ai_competitors = []

    # Merge and deduplicate
    return _merge_competitors(
        brand_name, amazon_competitors, ai_competitors, max_competitors
    )


async def _discover_from_amazon(
    brand_name: str, ecommerce_data: dict = None
) -> list[dict]:
    """Extract competitor brand names from Amazon search results.

    Searches the same category and extracts brand names from listings
    that are NOT the target brand.
    """
    competitors = []

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return competitors

    # Infer search query from brand name + common category keywords
    category_keywords = _infer_category(ecommerce_data, brand_name)
    search_query = f"{category_keywords}" if category_keywords else brand_name

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )
            page = await context.new_page()

            # Search Amazon for the category
            search_url = f"https://www.amazon.com/s?k={search_query.replace(' ', '+')}"
            await page.goto(search_url, timeout=15000)
            await page.wait_for_timeout(2000)

            # Extract brand names from search results
            brands = await page.evaluate(r"""
                () => {
                    const results = [];
                    // Try multiple selectors for brand names
                    const items = document.querySelectorAll('[data-component-type="s-search-result"]');
                    items.forEach(item => {
                        // Brand name from "by Brand" text
                        const byLine = item.querySelector('.a-row .a-size-base, .a-row .a-color-secondary');
                        if (byLine) {
                            const text = byLine.textContent.trim();
                            const brandMatch = text.match(/^(?:by\s+)?(.+?)(?:\s+Visit.*)?$/i);
                            if (brandMatch) {
                                results.push(brandMatch[1].trim());
                            }
                        }
                        // Brand from sponsored label area
                        const sponsored = item.querySelector('.puis-label-popover-default .a-size-base');
                        if (sponsored) {
                            results.push(sponsored.textContent.trim());
                        }
                    });

                    // Also check brand filter sidebar
                    const brandFilters = document.querySelectorAll('#brandsRefinements .a-list-item a span');
                    brandFilters.forEach(el => {
                        const text = el.textContent.trim();
                        if (text && !text.match(/^\d/) && text.length > 1 && text.length < 50) {
                            results.push(text);
                        }
                    });

                    return results;
                }
            """)

            await browser.close()

            # Clean and count brand mentions
            brand_name_lower = brand_name.lower()
            junk_patterns = {
                "sponsored", "list:", "typical:", "save ", "climate pledge",
                "bought in past", "featured offers", "no featured",
                "amazon's choice", "best seller", "limited time",
                "deal of the day", "pack of", "count (pack",
                "subscribe", "free delivery", "prime", "coupon",
                "editorial", "results", "price:", "stars",
                "premium brands", "top brands", "top rated",
                "our brands", "related brands", "popular brands",
                "more results", "see more", "shop now",
                "customers also", "frequently bought",
                "from the manufacturer", "highly rated", "featured from",
                "amazon brands", "amazon brand",
                "new arrivals", "new releases",
                "left in stock", "order soon", "only ",
                "add to cart", "add to list", "save for later",
                "in stock", "out of stock", "ships from",
                "fulfilled by", "sold by",
                # Material / attribute fragments
                "stainless steel", "stainless", "recycled",
                "contains at least", "temperature", "retention",
                "top reviewed", "more buying", "buying choices",
                "/count", "per count", "plastic", "aluminum",
                "ceramic", "glass", "silicone", "tritan",
                # Measurement / specs
                "ounce", "oz", "ml", "liter", "inch",
                "bpa free", "bpa-free", "leak proof", "leak-proof",
                "insulated", "vacuum", "double wall",
                # Price fragments
                "$", "¢", "price", "cost",
            }
            brand_counts = Counter()
            for b in brands:
                clean = b.strip()
                lower = clean.lower()
                # Brand name structural validation
                word_count = len(clean.split())
                has_alpha = any(c.isalpha() for c in clean)
                starts_with_paren = clean.startswith("(") or clean.startswith("[")
                is_too_long_phrase = word_count > 5
                has_special = any(c in clean for c in "$¢%@#")
                if (
                    clean
                    and len(clean) > 1
                    and len(clean) < 40
                    and has_alpha
                    and not starts_with_paren
                    and not is_too_long_phrase
                    and not has_special
                    and clean.lower() != brand_name_lower
                    and not clean.startswith("Visit")
                    and not clean.isdigit()
                    and not any(j in lower for j in junk_patterns)
                    and not lower[0].isdigit()
                ):
                    brand_counts[clean] += 1

            # Convert to competitor dicts
            for name, count in brand_counts.most_common(15):
                competitors.append({
                    "name": name,
                    "source": "amazon",
                    "confidence": min(1.0, count / 3),
                    "url": None,
                    "mention_count": count,
                })

    except Exception as e:
        print(f"[competitor_discovery] Extraction from scrape data failed: {e}")

    return competitors


async def _discover_from_ai(
    brand_name: str, brand_url: str, scrape_data: dict = None
) -> list[dict]:
    """Discover competitors using Claude + web_search tool.

    Uses real-time web search to find competitors dynamically for ANY brand
    in ANY category, rather than relying on a static brand list.
    Falls back to non-search Claude inference if web_search fails.
    """
    from config import ANTHROPIC_API_KEY, MODEL_OPUS

    if not ANTHROPIC_API_KEY:
        return _fallback_ai_competitors(brand_name, scrape_data)

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Build context from scrape data
        context = ""
        if scrape_data and scrape_data.get("pages"):
            for page in scrape_data["pages"][:3]:
                context += f"\n{page.get('title', '')}: {page.get('text', '')[:500]}\n"

        prompt = f"""Research and identify 8-10 competitors for this brand using web search.

Brand: {brand_name}
Website: {brand_url or "Unknown"}
{f"Website content excerpt:{context}" if context else ""}

## Search Strategy
1. Search "{brand_name} competitors" and "{brand_name} alternatives"
2. Search the product category + "best brands" or "top brands"
3. Search "{brand_name} vs" to find head-to-head comparisons
4. Check Amazon and review sites for brands in the same category

## Output
Return a JSON array of 8-10 competitor objects. Each object must have:
- "name": competitor brand name (official capitalization)
- "category_role": one of "direct" | "aspirational" | "adjacent"
  - direct = same category, same price tier, competing for same customers
  - aspirational = where the brand wants to be (higher-end, more established)
  - adjacent = different approach to same customer need
- "reason": one sentence explaining competitive relationship with evidence from your search
- "url": brand website URL if found

Sort by relevance: direct competitors first, then aspirational, then adjacent.
Return ONLY the JSON array, no other text."""

        print(f"[competitor_discovery] AI discovery with web_search for '{brand_name}'...")
        response = client.messages.create(
            model=MODEL_OPUS,
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 10}],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response (may have tool_use blocks interspersed)
        text_parts = []
        search_count = 0
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
            if hasattr(block, "type") and block.type == "tool_use":
                search_count += 1
        text = "".join(text_parts)
        print(f"[competitor_discovery] AI used {search_count} web searches")

        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            items = json.loads(text[start:end])
            results = [
                {
                    "name": item["name"],
                    "source": "ai_websearch",
                    "confidence": 0.95 if item.get("category_role") == "direct" else 0.8,
                    "url": item.get("url"),
                    "category_role": item.get("category_role", "direct"),
                    "reason": item.get("reason", ""),
                }
                for item in items
                if item.get("name")
            ]
            if results:
                print(f"[competitor_discovery] Found {len(results)} competitors via web search")
                return results

    except Exception as e:
        print(f"[competitor_discovery] AI web_search failed ({e}), trying without search...")

    # Fallback: Claude without web_search (uses its training knowledge)
    return _discover_from_ai_nosearch(brand_name, brand_url, scrape_data)


async def _discover_from_ai_nosearch(
    brand_name: str, brand_url: str, scrape_data: dict = None
) -> list[dict]:
    """Fallback: ask Claude to identify competitors from training knowledge (no web search)."""
    from config import ANTHROPIC_API_KEY, MODEL_OPUS

    if not ANTHROPIC_API_KEY:
        return _fallback_ai_competitors(brand_name, scrape_data)

    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        context = ""
        if scrape_data and scrape_data.get("pages"):
            for page in scrape_data["pages"][:3]:
                context += f"\n{page.get('title', '')}: {page.get('text', '')[:500]}\n"

        prompt = f"""Identify 6-8 competitors for this brand based on your knowledge.

Brand: {brand_name}
Website: {brand_url or "Unknown"}
{f"Website content:{context}" if context else ""}

Return ONLY a JSON array. Each object: {{"name": "Brand", "category_role": "direct|aspirational|adjacent", "reason": "why"}}"""

        response = client.messages.create(
            model=MODEL_OPUS,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            items = json.loads(text[start:end])
            return [
                {
                    "name": item["name"],
                    "source": "ai",
                    "confidence": 0.9 if item.get("category_role") == "direct" else 0.7,
                    "url": None,
                    "category_role": item.get("category_role", "direct"),
                    "reason": item.get("reason", ""),
                }
                for item in items
                if item.get("name")
            ]
    except Exception as e:
        print(f"[competitor_discovery] AI competitor discovery failed: {e}")

    return _fallback_ai_competitors(brand_name, scrape_data)


def _fallback_ai_competitors(brand_name: str, scrape_data: dict = None) -> list[dict]:
    """Fallback competitor list when AI is unavailable — infer from scrape data."""
    competitors = []

    if scrape_data:
        # Look for competitor mentions in scraped content
        all_text = ""
        for page in scrape_data.get("pages", []):
            all_text += " " + page.get("text", "")

        # Common global brand names as a broad fallback
        known_brands = [
            # General consumer / athletic
            "Nike", "Adidas", "Under Armour", "Lululemon", "Gymshark",
            "Patagonia", "The North Face", "Columbia", "REI",
            # Beverage / water bottles
            "Hydro Flask", "Stanley", "Yeti", "CamelBak", "Nalgene",
            "S'well", "Takeya", "Contigo", "Thermos", "Zojirushi",
            "Simple Modern", "Iron Flask", "Klean Kanteen", "Corkcicle",
            # Home / lifestyle / furniture
            "IKEA", "Crate & Barrel", "West Elm", "CB2", "Wayfair",
            "Article", "Pottery Barn", "Restoration Hardware",
            # Beauty / personal care / skincare
            "Glossier", "The Ordinary", "CeraVe", "Drunk Elephant",
            "La Roche-Posay", "Clinique", "Fenty Beauty", "Tatcha",
            "Olaplex", "Moroccanoil", "Kiehl's",
            # Medical / scrubs
            "FIGS", "Cherokee", "Dickies", "Carhartt", "Med Couture",
            "Healing Hands", "Jaanuu", "Barco",
            # Electronics / tech
            "Apple", "Samsung", "Sony", "Bose", "JBL", "Anker",
            "Logitech", "Dyson", "iRobot", "Ring",
            # Pet / food
            "Chewy", "Blue Buffalo", "Purina", "Hill's", "Royal Canin",
            "BarkBox", "Kong", "Wellness",
            # Kitchen / cookware
            "Le Creuset", "All-Clad", "Lodge", "Instant Pot", "KitchenAid",
            "Our Place", "Ninja", "Vitamix", "Breville",
            # Outdoor / camping
            "Osprey", "Deuter", "Gregory", "MSR", "Big Agnes",
            "Coleman", "REI Co-op",
        ]

        for brand in known_brands:
            if brand.lower() != brand_name.lower() and brand.lower() in all_text.lower():
                competitors.append({
                    "name": brand,
                    "source": "ai",
                    "confidence": 0.5,
                    "url": None,
                })

    return competitors


def _infer_category(ecommerce_data: dict = None, brand_name: str = "") -> str:
    """Infer product category from e-commerce data.

    Strategy:
    1. Fast keyword match against known categories (instant, no API call)
    2. If no match, ask Claude to identify the category from product names (dynamic)
    3. Last resort: return first product name as-is
    """
    if not ecommerce_data:
        return ""

    # Extract common words from product names
    product_names = [
        p.get("name", "").lower()
        for p in ecommerce_data.get("products", [])
    ]
    all_words = " ".join(product_names)

    # Strategy 1: Fast keyword match (no API call needed)
    category_map = {
        # Beverage / drinkware
        "water bottle": "water bottles insulated",
        "tumbler": "insulated tumblers",
        "bottle": "water bottles drinkware",
        "flask": "insulated water flask",
        # Apparel
        "scrubs": "medical scrubs",
        "nursing": "nursing scrubs uniforms",
        "medical": "medical uniforms scrubs",
        "jogger": "jogger pants",
        "lab coat": "lab coats medical",
        "yoga": "yoga pants leggings",
        "athletic": "athletic wear",
        "sneaker": "sneakers shoes",
        "shirt": "shirts apparel",
        "jacket": "jackets outerwear",
        "hoodie": "hoodies sweatshirts",
        "legging": "leggings activewear",
        "dress": "dresses women apparel",
        # Home / kitchen
        "candle": "candles home fragrance",
        "cookware": "cookware kitchen",
        "mattress": "mattresses beds",
        "pillow": "pillows bedding",
        "blanket": "blankets throws",
        "furniture": "home furniture",
        "lamp": "lamps lighting",
        "rug": "rugs home decor",
        "pan": "pans cookware",
        "knife": "kitchen knives",
        "blender": "blenders kitchen",
        # Beauty / personal care
        "serum": "skincare serum",
        "moisturizer": "skincare moisturizer",
        "shampoo": "hair care shampoo",
        "conditioner": "hair conditioner",
        "sunscreen": "sunscreen skincare",
        "cleanser": "face cleanser skincare",
        "foundation": "foundation makeup",
        "mascara": "mascara makeup",
        "lipstick": "lipstick makeup cosmetics",
        "perfume": "perfume fragrance",
        # Tech / electronics
        "headphone": "headphones earbuds",
        "earbud": "earbuds wireless",
        "speaker": "bluetooth speakers",
        "charger": "phone chargers",
        "laptop": "laptops computers",
        "tablet": "tablets iPad",
        "watch": "smartwatch watches",
        "camera": "cameras photography",
        "keyboard": "keyboards computer accessories",
        "mouse": "mouse computer accessories",
        # Pet
        "dog food": "dog food pet",
        "cat food": "cat food pet",
        "pet toy": "pet toys",
        "dog treat": "dog treats",
        "pet bed": "pet beds",
        # Outdoor / sports
        "tent": "camping tents outdoor",
        "backpack": "backpacks outdoor",
        "sleeping bag": "sleeping bags camping",
        "bicycle": "bicycles cycling",
        "golf": "golf equipment",
    }

    for keyword, search_term in category_map.items():
        if keyword in all_words:
            return search_term

    # Strategy 2: Ask Claude to identify category from product names (dynamic)
    if product_names:
        try:
            from config import ANTHROPIC_API_KEY, MODEL_HAIKU
            if ANTHROPIC_API_KEY:
                from anthropic import Anthropic
                client = Anthropic(api_key=ANTHROPIC_API_KEY)
                sample = "; ".join(product_names[:10])
                response = client.messages.create(
                    model=MODEL_HAIKU,
                    max_tokens=100,
                    messages=[{"role": "user", "content": f"What product category are these products? Return ONLY a 2-4 word category search term (e.g., 'wireless earbuds', 'face moisturizer skincare', 'camping tents outdoor'). Products: {sample}"}],
                )
                cat = response.content[0].text.strip().strip('"').strip("'").lower()
                if 2 < len(cat) < 50 and not cat.startswith("i ") and not cat.startswith("the "):
                    print(f"[competitor_discovery] Claude inferred category: '{cat}'")
                    return cat
        except Exception as e:
            print(f"[competitor_discovery] Category inference failed: {e}")

    # Strategy 3: Use first product name as-is
    if product_names:
        first = product_names[0][:50]
        return first

    return ""


def _merge_competitors(
    brand_name: str,
    amazon_list: list[dict],
    ai_list: list[dict],
    max_count: int,
) -> list[dict]:
    """Merge and deduplicate competitors from both sources."""
    # Build a name → entry map (case-insensitive)
    merged = {}

    for item in amazon_list:
        key = item["name"].lower().strip()
        if key == brand_name.lower():
            continue
        merged[key] = {
            "name": item["name"],
            "source": "amazon",
            "confidence": item.get("confidence", 0.5),
            "url": item.get("url"),
            "category_role": item.get("category_role", ""),
            "reason": item.get("reason", "Found in Amazon category search results"),
        }

    for item in ai_list:
        key = item["name"].lower().strip()
        if key == brand_name.lower():
            continue
        if key in merged:
            # Exists in both — boost confidence and mark as "both"
            merged[key]["source"] = "both"
            merged[key]["confidence"] = min(1.0, merged[key]["confidence"] + 0.3)
            if item.get("category_role"):
                merged[key]["category_role"] = item["category_role"]
            if item.get("reason"):
                merged[key]["reason"] = item["reason"]
        else:
            merged[key] = {
                "name": item["name"],
                "source": item.get("source", "ai"),
                "confidence": item.get("confidence", 0.7),
                "url": item.get("url"),
                "category_role": item.get("category_role", ""),
                "reason": item.get("reason", ""),
            }

    # Sort by confidence (both > single source), then take top N
    sorted_competitors = sorted(
        merged.values(),
        key=lambda x: (
            {"both": 3, "amazon": 2, "ai": 1}.get(x["source"], 0),
            x["confidence"],
        ),
        reverse=True,
    )

    return sorted_competitors[:max_count]
