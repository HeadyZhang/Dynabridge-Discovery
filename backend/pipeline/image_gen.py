"""Image generation via DALL-E 3 and FLUX Pro.

Provides two backends for generating images:
- DALL-E 3 (OpenAI): Best for icons, simple graphics, prompt adherence
- FLUX Pro (Replicate): Best for photorealistic, high-detail imagery

Usage:
    from pipeline.image_gen import generate_image

    # Auto-selects backend based on availability (prefers DALL-E 3)
    path = generate_image("a flat orange shopping cart icon", output_path="cart.png")

    # Force a specific backend
    path = generate_image("lifestyle photo", output_path="photo.png", backend="flux")
"""
import os
import time
import requests
from pathlib import Path
from config import OPENAI_API_KEY, REPLICATE_API_TOKEN


def _retry(fn, max_retries=3, base_delay=2.0):
    """Retry a function with exponential backoff."""
    last_err = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"[image_gen] Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
    print(f"[image_gen] All {max_retries} attempts failed: {last_err}")
    return None

ASSETS_DIR = Path(__file__).parent.parent / "templates" / "assets"


def generate_image(
    prompt: str,
    output_path: str | Path | None = None,
    backend: str = "auto",
    size: str = "1024x1024",
    quality: str = "standard",
    source_image: str | Path | None = None,
    strength: float = 0.65,
) -> Path | None:
    """Generate an image and save to disk.

    Args:
        prompt: Text description of the image to generate.
        output_path: Where to save. If relative, saves under ASSETS_DIR.
                     If None, derives filename from prompt.
        backend: "dalle", "flux", "flux-img2img", or "auto".
        size: Image dimensions — "1024x1024", "1792x1024", "1024x1792" (DALL-E)
              or WxH for FLUX.
        quality: "standard" or "hd" (DALL-E only).
        source_image: Path to source image for img2img mode.
        strength: How much to change source (0.0=keep, 1.0=ignore). img2img only.

    Returns:
        Path to the saved image, or None on failure.
    """
    if backend == "auto":
        if OPENAI_API_KEY:
            backend = "dalle"
        elif REPLICATE_API_TOKEN:
            backend = "flux"
        else:
            print("[image_gen] No API keys configured for image generation")
            return None

    if backend == "gpt-image":
        return _generate_gpt_image(prompt, output_path, size, quality)
    elif backend == "dalle":
        return _generate_dalle(prompt, output_path, size, quality)
    elif backend == "flux":
        return _generate_flux(prompt, output_path, size)
    elif backend == "flux-img2img":
        if not source_image:
            print("[image_gen] flux-img2img requires source_image")
            return _generate_flux(prompt, output_path, size)
        return _generate_flux_img2img(prompt, source_image, output_path, strength, size)
    else:
        print(f"[image_gen] Unknown backend: {backend}")
        return None


def _resolve_output_path(output_path: str | Path | None, prompt: str, ext: str = ".png") -> Path:
    """Resolve output path, defaulting to ASSETS_DIR."""
    if output_path is None:
        # Derive filename from first few words of prompt
        safe = "_".join(prompt.split()[:5]).lower()
        safe = "".join(c if c.isalnum() or c == "_" else "" for c in safe)
        output_path = ASSETS_DIR / f"{safe}{ext}"
    else:
        output_path = Path(output_path)
        if not output_path.is_absolute():
            output_path = ASSETS_DIR / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def _generate_gpt_image(prompt: str, output_path, size: str, quality: str) -> Path | None:
    """Generate image via gpt-image-1 (OpenAI's most photorealistic model)."""
    try:
        from openai import OpenAI
    except ImportError:
        print("[image_gen] openai package not installed — run: pip install openai")
        return None

    if not OPENAI_API_KEY:
        print("[image_gen] OPENAI_API_KEY not set")
        return None

    import base64
    client = OpenAI(api_key=OPENAI_API_KEY)
    q = {"standard": "medium", "hd": "high"}.get(quality, "medium")
    out = _resolve_output_path(output_path, prompt, ".png")

    def _call():
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            n=1,
            size=size,
            quality=q,
        )
        image_bytes = base64.b64decode(response.data[0].b64_json)
        out.write_bytes(image_bytes)
        print(f"[image_gen] gpt-image-1 → {out}")
        return out

    result = _retry(_call)
    return result


def _generate_dalle(prompt: str, output_path, size: str, quality: str) -> Path | None:
    """Generate image via DALL-E 3 (OpenAI API)."""
    try:
        from openai import OpenAI
    except ImportError:
        print("[image_gen] openai package not installed — run: pip install openai")
        return None

    if not OPENAI_API_KEY:
        print("[image_gen] OPENAI_API_KEY not set")
        return None

    client = OpenAI(api_key=OPENAI_API_KEY)
    out = _resolve_output_path(output_path, prompt, ".png")

    def _call():
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size=size,
            quality=quality,
            response_format="url",
        )
        image_url = response.data[0].url
        _download(image_url, out)
        print(f"[image_gen] DALL-E 3 → {out}")
        return out

    result = _retry(_call)
    return result


def _generate_flux(prompt: str, output_path, size: str) -> Path | None:
    """Generate image via FLUX Pro (Replicate API)."""
    try:
        import replicate
    except ImportError:
        print("[image_gen] replicate package not installed — run: pip install replicate")
        return None

    if not REPLICATE_API_TOKEN:
        print("[image_gen] REPLICATE_API_TOKEN not set")
        return None

    # Set token for replicate client
    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

    # Parse size
    parts = size.split("x")
    w, h = int(parts[0]), int(parts[1]) if len(parts) > 1 else (1024, 1024)

    out = _resolve_output_path(output_path, prompt, ".png")

    def _call():
        output = replicate.run(
            "black-forest-labs/flux-1.1-pro",
            input={
                "prompt": prompt,
                "width": w,
                "height": h,
                "prompt_upsampling": True,
            },
        )
        image_url = str(output)
        _download(image_url, out)
        print(f"[image_gen] FLUX Pro → {out}")
        return out

    result = _retry(_call)
    return result


def _generate_flux_img2img(
    prompt: str,
    source_image_path: str | Path,
    output_path,
    strength: float = 0.65,
    size: str = "1024x1024",
) -> Path | None:
    """Generate image via Flux img2img — modify an existing image with a prompt.

    Args:
        prompt: What to change/add to the image.
        source_image_path: Path to the source image to modify.
        strength: How much to change (0.0 = keep original, 1.0 = ignore original).
        size: Output dimensions.
    """
    try:
        import replicate
    except ImportError:
        print("[image_gen] replicate package not installed")
        return None

    if not REPLICATE_API_TOKEN:
        print("[image_gen] REPLICATE_API_TOKEN not set")
        return None

    os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN
    source = Path(source_image_path)
    if not source.exists():
        print(f"[image_gen] Source image not found: {source}")
        return None

    parts = size.split("x")
    w, h = int(parts[0]), int(parts[1]) if len(parts) > 1 else (1024, 1024)

    try:
        with open(source, "rb") as f:
            output = replicate.run(
                "black-forest-labs/flux-1.1-pro",
                input={
                    "prompt": prompt,
                    "image": f,
                    "prompt_upsampling": True,
                    "width": w,
                    "height": h,
                    "image_prompt_strength": 1.0 - strength,  # API uses inverted scale
                },
            )
        image_url = str(output)
        out = _resolve_output_path(output_path, prompt, ".png")
        _download(image_url, out)
        print(f"[image_gen] Flux img2img → {out}")
        return out
    except Exception as e:
        print(f"[image_gen] Flux img2img error: {e}")
        return None


def _download(url: str, dest: Path):
    """Download a file from URL to local path, converting WEBP to PNG."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    # If dest expects .png but content is WEBP, convert for PPTX compatibility
    if str(dest).lower().endswith(".png"):
        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(resp.content))
            if img.format == "WEBP":
                img.save(dest, "PNG")
                print(f"[image_gen] Converted WEBP → PNG: {dest.name}")
                return
        except Exception:
            pass
    dest.write_bytes(resp.content)


def generate_composite(
    scene_prompt: str,
    product_image_path: str | Path,
    output_path: str | Path,
    backend: str = "auto",
    scene_size: tuple[int, int] = (1344, 768),
    product_scale: float = 0.45,
    product_position: str = "center",
) -> Path | None:
    """Generate a scene background with AI, then composite the real product on top.

    1. Generate a pure scene/background image (no product) via AI
    2. Remove background from the real product photo (rembg)
    3. Composite the cutout product onto the scene

    Args:
        scene_prompt: Prompt for the background scene (should NOT mention any product).
        product_image_path: Path to the real product photo.
        output_path: Where to save the final composite.
        backend: "dalle", "flux", or "auto" for scene generation.
        scene_size: (width, height) of the scene.
        product_scale: Product height as fraction of scene height (0.0-1.0).
        product_position: "center", "right", "left" — where to place product.
    """
    from PIL import Image
    import io

    product_path = Path(product_image_path)
    if not product_path.exists():
        print(f"[image_gen] Product image not found: {product_path}")
        return None

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate scene background
    scene_file = out.parent / f"_scene_{out.stem}.png"
    size_str = f"{scene_size[0]}x{scene_size[1]}"
    scene = generate_image(
        scene_prompt, output_path=scene_file, backend=backend,
        size=size_str, quality="hd",
    )
    if not scene or not scene.exists():
        print("[image_gen] Scene generation failed")
        return None

    # Step 2: Remove background from product photo
    try:
        from rembg import remove as rembg_remove
        product_img = Image.open(product_path).convert("RGBA")
        product_cutout = rembg_remove(product_img)
    except Exception as e:
        print(f"[image_gen] Background removal failed: {e}")
        # Fallback: use product image as-is (works if already on white bg)
        product_cutout = Image.open(product_path).convert("RGBA")

    # Step 3: Composite
    scene_img = Image.open(scene).convert("RGBA")
    sw, sh = scene_img.size

    # Scale product
    pw, ph = product_cutout.size
    target_h = int(sh * product_scale)
    ratio = target_h / ph
    target_w = int(pw * ratio)
    product_resized = product_cutout.resize((target_w, target_h), Image.LANCZOS)

    # Position
    if product_position == "right":
        x = sw - target_w - int(sw * 0.05)
    elif product_position == "left":
        x = int(sw * 0.05)
    else:  # center
        x = (sw - target_w) // 2
    y = (sh - target_h) // 2

    scene_img.paste(product_resized, (x, y), product_resized)
    scene_img = scene_img.convert("RGB")
    scene_img.save(out, "PNG")

    # Cleanup temp scene
    if scene_file.exists():
        scene_file.unlink()

    print(f"[image_gen] Composite → {out}")
    return out


def generate_batch(prompts: dict[str, str], backend: str = "auto", size: str = "1024x1024") -> dict[str, Path]:
    """Generate multiple images. prompts = {filename: prompt_text}.

    Returns dict of {filename: saved_path} for successful generations.
    """
    results = {}
    for filename, prompt in prompts.items():
        path = generate_image(prompt, output_path=filename, backend=backend, size=size)
        if path:
            results[filename] = path
    return results
