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
import requests
from pathlib import Path
from config import OPENAI_API_KEY, REPLICATE_API_TOKEN

ASSETS_DIR = Path(__file__).parent.parent / "templates" / "assets"


def generate_image(
    prompt: str,
    output_path: str | Path | None = None,
    backend: str = "auto",
    size: str = "1024x1024",
    quality: str = "standard",
) -> Path | None:
    """Generate an image and save to disk.

    Args:
        prompt: Text description of the image to generate.
        output_path: Where to save. If relative, saves under ASSETS_DIR.
                     If None, derives filename from prompt.
        backend: "dalle", "flux", or "auto" (tries DALL-E first, then FLUX).
        size: Image dimensions — "1024x1024", "1792x1024", "1024x1792" (DALL-E)
              or WxH for FLUX.
        quality: "standard" or "hd" (DALL-E only).

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

    if backend == "dalle":
        return _generate_dalle(prompt, output_path, size, quality)
    elif backend == "flux":
        return _generate_flux(prompt, output_path, size)
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
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size=size,
            quality=quality,
            response_format="url",
        )
        image_url = response.data[0].url
        out = _resolve_output_path(output_path, prompt, ".png")
        _download(image_url, out)
        print(f"[image_gen] DALL-E 3 → {out}")
        return out
    except Exception as e:
        print(f"[image_gen] DALL-E 3 error: {e}")
        return None


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

    try:
        output = replicate.run(
            "black-forest-labs/flux-pro",
            input={
                "prompt": prompt,
                "width": w,
                "height": h,
                "steps": 25,
            },
        )
        image_url = str(output)
        out = _resolve_output_path(output_path, prompt, ".png")
        _download(image_url, out)
        print(f"[image_gen] FLUX Pro → {out}")
        return out
    except Exception as e:
        print(f"[image_gen] FLUX Pro error: {e}")
        return None


def _download(url: str, dest: Path):
    """Download a file from URL to local path."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)


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
