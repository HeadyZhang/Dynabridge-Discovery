"""AI-powered metadata extraction for case files.

Uses Claude API to analyze extracted content and produce
structured tags: brand info, industry, challenges, insights, segments.
"""
import json
from config import ANTHROPIC_API_KEY

SYSTEM_PROMPT = """You are a brand strategy analyst at DynaBridge. You analyze brand consulting
deliverables and extract structured metadata.

You MUST return ONLY valid JSON — no markdown, no commentary."""

TAG_PROMPT = """Analyze this brand consulting document and extract structured metadata.

## Document Info
- File: {filename}
- Type: {file_type}
- Language: {language_hint}

## Content (first 8000 chars)
{content_preview}

## Extract this JSON structure:

{{
  "brand_name_en": "English brand name",
  "brand_name_zh": "Chinese brand name or empty string",
  "industry": "Primary industry/category (e.g., Medical Apparel, Consumer Electronics)",
  "sub_category": "Specific sub-category (e.g., Scrubs, Phone Cases)",
  "project_types": ["discovery", "strategy", "design", "naming"],
  "core_challenges": [
    "Challenge 1 — one sentence",
    "Challenge 2 — one sentence"
  ],
  "key_insights": [
    "Insight 1 — one sentence strategic finding",
    "Insight 2 — one sentence strategic finding"
  ],
  "consumer_segments": [
    {{"name": "Segment Name", "description": "Brief description"}}
  ],
  "competitors_mentioned": ["Competitor 1", "Competitor 2"],
  "positioning_summary": "One paragraph summarizing brand positioning",
  "tags": ["tag1", "tag2", "tag3"]
}}

If information is not available in the document, use empty strings or empty arrays.
Extract ONLY what is present — do not fabricate."""


def tag_case_file(extracted: dict) -> dict:
    """Generate AI tags for an extracted file.

    Args:
        extracted: Output from extractor.extract_file()

    Returns:
        Structured tag dict, or minimal fallback if API unavailable.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_tags(extracted)

    content_preview = extracted.get("content", {}).get("raw_text", "")[:8000]
    if not content_preview.strip():
        return _fallback_tags(extracted)

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=ANTHROPIC_API_KEY)

        prompt = TAG_PROMPT.format(
            filename=extracted.get("source_file", "unknown"),
            file_type=extracted.get("file_type", "unknown"),
            language_hint=extracted.get("metadata", {}).get("language_hint", "en"),
            content_preview=content_preview,
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass

    return _fallback_tags(extracted)


def tag_case_batch(extracted_files: list[dict]) -> list[dict]:
    """Tag multiple extracted files.

    Returns:
        List of tag dicts, one per file.
    """
    return [tag_case_file(e) for e in extracted_files]


def _fallback_tags(extracted: dict) -> dict:
    """Generate minimal tags without AI when API is unavailable."""
    raw = extracted.get("content", {}).get("raw_text", "")
    filename = extracted.get("source_file", "")

    # Try to extract brand name from filename
    brand_name = ""
    for part in filename.replace("/", " ").replace("_", " ").replace("-", " ").split():
        if part[0:1].isupper() and len(part) > 2 and part.lower() not in {
            "brand", "discovery", "strategy", "eng", "chinese", "english",
            "pptx", "pdf", "docx", "final", "updated", "review",
        }:
            brand_name = part
            break

    return {
        "brand_name_en": brand_name,
        "brand_name_zh": "",
        "industry": "",
        "sub_category": "",
        "project_types": [],
        "core_challenges": [],
        "key_insights": [],
        "consumer_segments": [],
        "competitors_mentioned": [],
        "positioning_summary": "",
        "tags": [],
    }
