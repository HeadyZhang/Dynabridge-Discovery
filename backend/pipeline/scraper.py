"""Website scraping module using Playwright.

Crawls a brand's website, extracts text content, and takes screenshots
for inclusion in the Brand Discovery PPT.
"""
import asyncio
from pathlib import Path
from config import OUTPUT_DIR


async def scrape_brand_website(url: str) -> dict:
    """Scrape a brand website and return structured data.

    Returns:
        {
            "url": str,
            "pages": [
                {
                    "url": str,
                    "title": str,
                    "text": str,
                    "screenshot_path": str,
                }
            ],
            "brand_claims": [str],
            "product_info": [str],
        }
    """
    if not url:
        return {"url": "", "pages": [], "brand_claims": [], "product_info": []}

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"url": url, "pages": [{"url": url, "title": url, "text": "", "screenshot_path": ""}],
                "brand_claims": [], "product_info": []}

    result = {
        "url": url,
        "pages": [],
        "brand_claims": [],
        "product_info": [],
    }

    screenshots_dir = OUTPUT_DIR / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    try:
      async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # Crawl main page
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Screenshot homepage
        screenshot_path = screenshots_dir / "homepage.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)

        # Extract text
        text = await page.evaluate("document.body.innerText")
        title = await page.title()

        result["pages"].append({
            "url": url,
            "title": title,
            "text": text[:5000],
            "screenshot_path": str(screenshot_path),
        })

        # Find internal links and crawl key pages
        links = await page.evaluate("""
            () => {
                const base = new URL(window.location.href).origin;
                return [...new Set(
                    Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter(h => h.startsWith(base))
                )].slice(0, 10);
            }
        """)

        key_pages = [l for l in links if any(kw in l.lower() for kw in
                     ["about", "product", "story", "mission", "collection", "shop"])][:5]

        for i, link in enumerate(key_pages):
            try:
                await page.goto(link, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1)

                pg_screenshot = screenshots_dir / f"page_{i}.png"
                await page.screenshot(path=str(pg_screenshot), full_page=False)

                pg_text = await page.evaluate("document.body.innerText")
                pg_title = await page.title()

                result["pages"].append({
                    "url": link,
                    "title": pg_title,
                    "text": pg_text[:3000],
                    "screenshot_path": str(pg_screenshot),
                })
            except Exception:
                continue

        await browser.close()
    except Exception:
        # Playwright/Chromium not available — return minimal result
        if not result["pages"]:
            result["pages"].append({"url": url, "title": url, "text": "", "screenshot_path": ""})

    return result
