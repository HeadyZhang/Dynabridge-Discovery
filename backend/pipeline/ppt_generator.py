"""PPT Generation module — uses build_template slide builders.

Reads analysis data from Claude and generates a full Brand Discovery
PPTX deck matching the CozyFit reference style.
"""
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches

# Allow importing from parent dir
sys.path.insert(0, str(Path(__file__).parent.parent))

from build_template import (
    SLIDE_W, SLIDE_H,
    build_cover, build_agenda, build_approach, build_step_divider,
    build_section_header, build_insight_slide, build_competitor_slide,
    build_summary_slide, build_research_approach, build_subsection_divider,
    build_bar_chart_slide, build_donut_chart_slide, build_dual_chart_slide,
    build_next_steps, build_thank_you,
)
from config import OUTPUT_DIR, PREVIEW_DIR


async def generate_pptx(
    project_id: int,
    analysis: dict,
    brand_name: str,
) -> tuple[Path, list[dict]]:
    """Generate a Brand Discovery PPTX from analysis data.

    Returns:
        (pptx_path, slide_previews)
    """
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_meta = []

    # 1. Cover
    build_cover(prs, brand_name, "Brand Discovery",
                analysis.get("date", "2026"))
    slide_meta.append({"type": "cover", "content": {"brand_name": brand_name}})

    # 2. Agenda
    build_agenda(prs)
    slide_meta.append({"type": "agenda", "content": {}})

    # 3. Approach
    build_approach(prs)
    slide_meta.append({"type": "approach", "content": {}})

    # 4. Step 1 – Discovery
    build_step_divider(prs, 1, "DISCOVERY")
    slide_meta.append({"type": "step", "content": {"step": 1}})

    # ── Capabilities ──────────────────────────────────────────

    build_section_header(prs, "A closer look at the\nbrand capabilities", "capabilities")
    slide_meta.append({"type": "section", "content": {"section": "capabilities"}})

    cap = analysis.get("capabilities", {})

    # Insight slides for each capabilities section
    for key in ["execution_summary", "product_offer", "pricing_position", "channel_analysis"]:
        section = cap.get(key)
        if section:
            build_insight_slide(prs,
                title=section.get("title", key.replace("_", " ").upper()),
                bullets=section.get("bullets", []),
                insight_text=section.get("insight", ""),
                has_image=section.get("has_image", False),
            )
            slide_meta.append({"type": "insight", "content": section})

    # Brand challenges
    for challenge in cap.get("brand_challenges", []):
        build_insight_slide(prs,
            title=challenge.get("title", "BRAND CHALLENGES"),
            bullets=challenge.get("bullets", []),
            insight_text=challenge.get("insight", ""),
        )
        slide_meta.append({"type": "insight", "content": challenge})

    # Capabilities summary
    cap_summary = cap.get("capabilities_summary", "")
    if cap_summary:
        build_summary_slide(prs, "CAPABILITIES SUMMARY", cap_summary)
        slide_meta.append({"type": "summary", "content": {"text": cap_summary}})

    # ── Competition ───────────────────────────────────────────

    build_section_header(prs, "A closer look at the\ncompetition", "competition")
    slide_meta.append({"type": "section", "content": {"section": "competition"}})

    comp = analysis.get("competition", {})

    # Market overview
    overview = comp.get("market_overview", {})
    if overview:
        build_insight_slide(prs,
            title=overview.get("title", "COMPETITIVE LANDSCAPE"),
            bullets=overview.get("bullets", []),
            insight_text=overview.get("insight", ""),
        )
        slide_meta.append({"type": "insight", "content": overview})

    # Competitor analysis slides
    for competitor in comp.get("competitor_analyses", []):
        build_competitor_slide(prs,
            name=competitor.get("name", "Competitor"),
            positioning=[(p["label"], p["detail"]) for p in competitor.get("positioning", [])],
            key_learnings=[(k["label"], k["detail"]) for k in competitor.get("key_learnings", [])],
        )
        slide_meta.append({"type": "competitor", "content": competitor})

    # Competition summary
    comp_summary = comp.get("competition_summary", "")
    if comp_summary:
        build_summary_slide(prs, "COMPETITION SUMMARY", comp_summary)
        slide_meta.append({"type": "summary", "content": {"text": comp_summary}})

    # ── Consumer ──────────────────────────────────────────────

    build_section_header(prs, "A closer look at the\nconsumer", "consumer")
    slide_meta.append({"type": "section", "content": {"section": "consumer"}})

    consumer = analysis.get("consumer", {})

    # Research approach
    research = consumer.get("research_approach")
    if research:
        build_research_approach(prs,
            [(r["label"], r["detail"]) for r in research])
        slide_meta.append({"type": "research", "content": {"rows": research}})

    # Demographics sub-section
    demographics = consumer.get("demographics", {})
    if demographics:
        build_subsection_divider(prs, "Demographics &\nBackground")
        slide_meta.append({"type": "subsection", "content": {"title": "Demographics"}})

    # Chart slides
    for chart in consumer.get("charts", []):
        chart_type = chart.get("chart_type", "hbar")
        if chart_type == "dual":
            build_dual_chart_slide(prs,
                title=chart.get("title", ""),
                subtitle_text=chart.get("subtitle", None),
                left_title=chart.get("left_title", ""),
                left_categories=chart.get("left_categories"),
                left_values=chart.get("left_values"),
                right_title=chart.get("right_title", ""),
                right_categories=chart.get("right_categories"),
                right_values=chart.get("right_values"),
                left_type=chart.get("left_type", "donut"),
                right_type=chart.get("right_type", "hbar"),
            )
        elif chart_type in ("bar", "hbar"):
            build_bar_chart_slide(prs,
                title=chart.get("title", ""),
                subtitle_text=chart.get("subtitle", None),
                question=chart.get("question", ""),
                categories=chart.get("categories"),
                values=chart.get("values"),
                is_horizontal=(chart_type == "hbar"),
            )
        slide_meta.append({"type": "chart", "content": chart})

    # Consumer insights
    for insight in consumer.get("key_insights", []):
        build_insight_slide(prs,
            title=insight.get("title", "KEY CONSUMER INSIGHTS"),
            bullets=insight.get("bullets", []),
            insight_text=insight.get("insight", ""),
        )
        slide_meta.append({"type": "insight", "content": insight})

    # ── Next Steps ────────────────────────────────────────────

    next_steps = analysis.get("next_steps", [])
    if next_steps:
        build_next_steps(prs, next_steps)
        slide_meta.append({"type": "next_steps", "content": {"steps": next_steps}})

    # ── Thank You ─────────────────────────────────────────────

    build_thank_you(prs,
                    phone="13736758116",
                    email="contact@dynabridge.com",
                    website="https://www.dynabridge.cn/")
    slide_meta.append({"type": "thank_you", "content": {}})

    # ── Save ──────────────────────────────────────────────────

    output_path = OUTPUT_DIR / f"project_{project_id}" / f"{brand_name}_Brand_Discovery.pptx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))

    # Generate previews
    preview_paths = _generate_previews(output_path, project_id)
    for i, pp in enumerate(preview_paths):
        if i < len(slide_meta):
            slide_meta[i]["preview_path"] = str(pp)

    return output_path, slide_meta


def _generate_previews(pptx_path: Path, project_id: int) -> list[Path]:
    """Convert PPTX slides to PNG previews via LibreOffice, PIL fallback."""
    import subprocess

    preview_dir = PREVIEW_DIR / f"project_{project_id}"
    preview_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run([
            "soffice", "--headless", "--convert-to", "png",
            "--outdir", str(preview_dir), str(pptx_path)
        ], capture_output=True, timeout=60)
        return sorted(preview_dir.glob("*.png"))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return _generate_placeholder_previews(pptx_path, preview_dir)


def _generate_placeholder_previews(pptx_path: Path, preview_dir: Path) -> list[Path]:
    """Simple placeholder previews when LibreOffice unavailable."""
    from PIL import Image, ImageDraw

    prs = Presentation(str(pptx_path))
    paths = []

    for i, slide in enumerate(prs.slides):
        img = Image.new("RGB", (1280, 720), "#FAFAF9")
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), f"Slide {i + 1}", fill="#E8652D")

        y = 80
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text[:100]
                if text.strip():
                    draw.text((40, y), text, fill="#292524")
                    y += 30
                    if y > 650:
                        break

        path = preview_dir / f"slide_{i:03d}.png"
        img.save(str(path))
        paths.append(path)

    return paths
