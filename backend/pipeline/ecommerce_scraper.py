"""E-commerce scraping module.

Scrapes Amazon and Shopify product listings to extract pricing,
product details, ratings, and competitive positioning data.
"""
import asyncio
import re
import json
from urllib.parse import urlparse, urlencode
from config import OUTPUT_DIR


async def scrape_ecommerce(brand_name: str, urls: list[str] = None) -> dict:
    """Scrape e-commerce data for a brand.

    Args:
        brand_name: Brand name to search for
        urls: Optional list of specific product/store URLs

    Returns:
        {
            "brand_name": str,
            "store_info": str,
            "products": [{"name", "price", "rating", "review_count", "description", "features", "url"}],
            "price_range": {"min": float, "max": float, "avg": float},
            "rating_summary": {"average": float, "total_reviews": int},
            "category_position": str,
        }
    """
    result = {
        "brand_name": brand_name,
        "store_info": "",
        "products": [],
        "price_range": {"min": 0, "max": 0, "avg": 0},
        "rating_summary": {"average": 0, "total_reviews": 0},
        "category_position": "",
    }

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return result

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )
            page = await context.new_page()

            if urls:
                for url in urls:
                    domain = urlparse(url).netloc.lower()
                    if "amazon" in domain:
                        products = await _scrape_amazon_page(page, url)
                        result["products"].extend(products)
                    elif "shopify" in domain or _is_shopify_store(url):
                        products = await _scrape_shopify_store(page, url)
                        result["products"].extend(products)
                    else:
                        products = await _scrape_generic_store(page, url)
                        result["products"].extend(products)
            else:
                # Search Amazon for the brand
                products = await _search_amazon(page, brand_name)
                result["products"].extend(products)

            await browser.close()

    except Exception:
        pass

    # Calculate summary stats
    if result["products"]:
        prices = [p["price"] for p in result["products"] if p.get("price") and p["price"] > 0]
        if prices:
            result["price_range"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": round(sum(prices) / len(prices), 2),
            }

        ratings = [p["rating"] for p in result["products"] if p.get("rating") and p["rating"] > 0]
        total_reviews = sum(p.get("review_count", 0) for p in result["products"])
        if ratings:
            result["rating_summary"] = {
                "average": round(sum(ratings) / len(ratings), 2),
                "total_reviews": total_reviews,
            }

    return result


async def _search_amazon(page, brand_name: str) -> list[dict]:
    """Search Amazon for a brand and extract product listings."""
    search_url = f"https://www.amazon.com/s?k={brand_name.replace(' ', '+')}"
    products = []

    try:
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        products = await page.evaluate(r"""
            () => {
                const items = [];
                document.querySelectorAll('[data-component-type="s-search-result"]').forEach(el => {
                    const titleEl = el.querySelector('h2 a span, .a-text-normal');
                    const priceWhole = el.querySelector('.a-price-whole');
                    const priceFraction = el.querySelector('.a-price-fraction');
                    const ratingEl = el.querySelector('.a-icon-star-small .a-icon-alt, .a-icon-star .a-icon-alt');
                    const reviewCountEl = el.querySelector('.a-size-small .a-link-normal .a-size-base, [aria-label*="stars"] + span');
                    const linkEl = el.querySelector('h2 a');

                    if (titleEl) {
                        const price = priceWhole ?
                            parseFloat(priceWhole.textContent.replace(',', '') + '.' + (priceFraction?.textContent || '00')) : 0;
                        const ratingText = ratingEl ? ratingEl.textContent : '';
                        const ratingMatch = ratingText.match(/([\d.]+)/);
                        const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 0;
                        const reviewText = reviewCountEl ? reviewCountEl.textContent.replace(/,/g, '') : '0';
                        const reviewMatch = reviewText.match(/(\d+)/);
                        const reviewCount = reviewMatch ? parseInt(reviewMatch[1]) : 0;

                        items.push({
                            name: titleEl.textContent.trim().slice(0, 200),
                            price: price,
                            rating: rating,
                            review_count: reviewCount,
                            description: '',
                            features: [],
                            url: linkEl ? 'https://www.amazon.com' + linkEl.getAttribute('href') : '',
                        });
                    }
                });
                return items.slice(0, 20);
            }
        """)
    except Exception:
        pass

    return products


async def _scrape_amazon_page(page, url: str) -> list[dict]:
    """Scrape a specific Amazon product or brand page."""
    products = []
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)

        # Check if it's a single product page
        is_product = await page.evaluate("() => !!document.querySelector('#productTitle')")

        if is_product:
            product = await page.evaluate(r"""
                () => {
                    const title = document.querySelector('#productTitle');
                    const price = document.querySelector('.a-price .a-offscreen, #priceblock_ourprice, #priceblock_dealprice');
                    const rating = document.querySelector('#acrPopover .a-icon-alt');
                    const reviewCount = document.querySelector('#acrCustomerReviewText');
                    const features = [];
                    document.querySelectorAll('#feature-bullets li span.a-list-item').forEach(li => {
                        const text = li.textContent.trim();
                        if (text && text.length > 5) features.push(text.slice(0, 200));
                    });
                    const desc = document.querySelector('#productDescription');

                    const priceText = price ? price.textContent.trim() : '';
                    const priceMatch = priceText.match(/[\d,.]+/);

                    return {
                        name: title ? title.textContent.trim() : '',
                        price: priceMatch ? parseFloat(priceMatch[0].replace(',', '')) : 0,
                        rating: rating ? parseFloat(rating.textContent) || 0 : 0,
                        review_count: reviewCount ? parseInt(reviewCount.textContent.replace(/\D/g, '')) || 0 : 0,
                        description: desc ? desc.textContent.trim().slice(0, 500) : '',
                        features: features.slice(0, 8),
                        url: window.location.href,
                    };
                }
            """)
            if product.get("name"):
                products.append(product)
        else:
            # Brand/search results page
            products = await _search_amazon(page, "")

    except Exception:
        pass

    return products


async def _scrape_shopify_store(page, url: str) -> list[dict]:
    """Scrape a Shopify store's products via /products.json."""
    products = []
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    try:
        # Shopify exposes /products.json
        await page.goto(f"{base_url}/products.json?limit=50", wait_until="domcontentloaded", timeout=15000)
        content = await page.evaluate("() => document.body.innerText")

        data = json.loads(content)
        for item in data.get("products", [])[:30]:
            price = 0
            if item.get("variants"):
                price_str = item["variants"][0].get("price", "0")
                try:
                    price = float(price_str)
                except (ValueError, TypeError):
                    pass

            products.append({
                "name": item.get("title", ""),
                "price": price,
                "rating": 0,
                "review_count": 0,
                "description": _strip_html(item.get("body_html", ""))[:500],
                "features": [tag for tag in item.get("tags", [])[:8]],
                "url": f"{base_url}/products/{item.get('handle', '')}",
            })
    except Exception:
        # Fallback to scraping the HTML
        products = await _scrape_generic_store(page, url)

    return products


async def _scrape_generic_store(page, url: str) -> list[dict]:
    """Scrape a generic e-commerce page for products."""
    products = []
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(1)

        # Try JSON-LD structured data first
        products = await page.evaluate(r"""
            () => {
                const products = [];
                document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
                    try {
                        const data = JSON.parse(s.textContent);
                        const items = Array.isArray(data) ? data : [data];
                        items.forEach(item => {
                            if (item['@type'] === 'Product') {
                                products.push({
                                    name: item.name || '',
                                    price: item.offers?.price ? parseFloat(item.offers.price) : 0,
                                    rating: item.aggregateRating?.ratingValue ? parseFloat(item.aggregateRating.ratingValue) : 0,
                                    review_count: item.aggregateRating?.reviewCount ? parseInt(item.aggregateRating.reviewCount) : 0,
                                    description: (item.description || '').slice(0, 500),
                                    features: [],
                                    url: item.url || window.location.href,
                                });
                            }
                        });
                    } catch {}
                });
                return products.slice(0, 20);
            }
        """)
    except Exception:
        pass

    return products


def _is_shopify_store(url: str) -> bool:
    """Check if a URL is likely a Shopify store."""
    return "myshopify.com" in url


def _strip_html(html: str) -> str:
    """Remove HTML tags from a string."""
    if not html:
        return ""
    return re.sub(r'<[^>]+>', ' ', html).strip()
