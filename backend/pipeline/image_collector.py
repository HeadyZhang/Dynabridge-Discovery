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
        _collect_from_unsplash(img_dir, brand_name, category_keywords),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    brand_imgs = results[0] if not isinstance(results[0], Exception) else []
    product_imgs = results[1] if not isinstance(results[1], Exception) else []
    lifestyle_imgs = results[2] if not isinstance(results[2], Exception) else []

    # Sort each list: landscape-first (wider images get priority)
    brand_imgs = _sort_by_aspect(brand_imgs)
    product_imgs = _sort_by_aspect(product_imgs)
    lifestyle_imgs = _sort_by_aspect(lifestyle_imgs)

    return {
        "brand": brand_imgs,
        "product": product_imgs,
        "lifestyle": lifestyle_imgs,
        "all": brand_imgs + product_imgs + lifestyle_imgs,
    }


def _sort_by_aspect(paths: list[Path]) -> list[Path]:
    """Sort images by aspect ratio, landscape-first."""
    def _ratio(p):
        try:
            from PIL import Image
            with Image.open(str(p)) as img:
                return img.width / img.height
        except Exception:
            return 1.0
    return sorted(paths, key=_ratio, reverse=True)


def _img_filename(url: str, prefix: str) -> str:
    """Generate a stable filename from URL."""
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    ext = Path(urlparse(url).path).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    return f"{prefix}_{h}{ext}"


async def _download_image(
    client: httpx.AsyncClient, url: str, save_path: Path, min_aspect: float = 0.0
) -> Path | None:
    """Download an image if it doesn't already exist.

    Args:
        min_aspect: Minimum width/height ratio. Set >1.0 to require landscape.
                    0.6 filters out very tall/narrow images.
    """
    if save_path.exists() and save_path.stat().st_size > 1000:
        # Check aspect ratio of existing file
        if min_aspect > 0:
            try:
                from PIL import Image
                with Image.open(str(save_path)) as img:
                    if img.width / img.height < min_aspect:
                        return None
            except Exception:
                pass
        return save_path
    try:
        resp = await client.get(url, follow_redirects=True, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 5000:
            content_type = resp.headers.get("content-type", "")
            if "image" in content_type or save_path.suffix in (".jpg", ".jpeg", ".png", ".webp"):
                # Check aspect ratio before saving
                if min_aspect > 0:
                    try:
                        from PIL import Image
                        import io
                        with Image.open(io.BytesIO(resp.content)) as img:
                            if img.width / img.height < min_aspect:
                                return None
                    except Exception:
                        pass
                save_path.write_bytes(resp.content)
                return save_path
    except Exception:
        pass
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


# ── Source 3: Unsplash Stock Photos ──────────────────────────

UNSPLASH_API = "https://api.unsplash.com/search/photos"

async def _collect_from_unsplash(
    img_dir: Path,
    brand_name: str,
    category_keywords: list[str] = None,
) -> list[Path]:
    """Fetch relevant stock photos from Unsplash.

    Uses the free tier (50 req/hour) — no API key needed for demo.
    Falls back to direct URL pattern if API fails.
    """
    if not category_keywords:
        category_keywords = _infer_keywords(brand_name)

    queries = category_keywords[:3]  # Max 3 searches
    images = []

    async with httpx.AsyncClient() as client:
        for query in queries:
            try:
                # Unsplash source URL (no API key needed, direct redirect)
                for i in range(2):
                    url = f"https://source.unsplash.com/1200x800/?{query.replace(' ', ',')}&sig={hash(query + str(i))}"
                    fname = _img_filename(f"{query}_{i}", "stock")
                    path = img_dir / fname
                    if path.exists() and path.stat().st_size > 5000:
                        images.append(path)
                        continue

                    try:
                        resp = await client.get(url, follow_redirects=True, timeout=10)
                        if resp.status_code == 200 and len(resp.content) > 5000:
                            path.write_bytes(resp.content)
                            images.append(path)
                    except Exception:
                        continue
            except Exception:
                continue

    return images


def _infer_keywords(brand_name: str) -> list[str]:
    """Infer useful stock photo search keywords from brand name."""
    # Generic fallbacks — will be overridden by category_keywords if available
    return [
        "business professional",
        "modern office teamwork",
        "product lifestyle",
    ]
