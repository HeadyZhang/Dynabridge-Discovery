"""PPT Generation module — clones slides from the CozyFit reference PPTX.

Instead of building slides from scratch with python-pptx shapes,
this module copies slides from the original template and replaces
text content with new analysis data. This preserves all formatting,
backgrounds, images, fonts, and layout exactly.

Images are replaced with brand-specific images collected by image_collector.py.
When no collected image is available, the template's original image is kept as-is.

Template slide index map (0-based):
  0  = Cover (Title_Slide)
  1  = Agenda (Blank)
  2  = Approach / Brand Building Process (Text Slide)
  3  = Step 1 Divider (Text Slide)
  4  = Section Header - Capabilities (Overview Slide)
  5  = Content slide - title + 3 bullets + insight + image (Blank)
  13 = Summary slide - title + paragraph + half-image (Text Slide)
  14 = Section Header - Competition (Overview Slide)
  17 = Competitor deep dive - two-column positioning + learnings (Blank)
  23 = Landscape summary - bullets + sidebar text (Blank)
  24 = Summary slide - Competition (Text Slide)
  25 = Section Header - Consumer (Overview Slide)
  91 = Thank You / 谢谢 (Divider Slide)
"""
import copy
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Pt, Emu

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR, PREVIEW_DIR

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "cozyfit_reference.pptx"

# Template slide indices (0-based) — which original slide to clone for each type
T_COVER = 0
T_AGENDA = 1
T_APPROACH = 2
T_STEP_DIVIDER = 3
T_SECTION_CAPABILITIES = 4
T_CONTENT = 5          # title + bullets + insight + image
T_CONTENT_ALT = 6      # alternate content layout
T_SUMMARY = 13         # title + summary paragraph + half-image
T_SECTION_COMPETITION = 14
T_COMPETITOR = 17       # two-column: positioning + key learnings
T_LANDSCAPE = 23        # landscape summary (bullets + sidebar)
T_COMP_SUMMARY = 24
T_SECTION_CONSUMER = 25
T_RESEARCH_APPROACH = 26    # Research methodology (label + detail rows)
T_SEGMENT_DIVIDER = 47      # "Market Segmentation" divider
T_SEGMENT_OVERVIEW = 49     # All segments at a glance (names + % + taglines)
T_MEET_SEGMENT = 51         # "Meet the [Segment]" narrative page
T_TARGET_RECOMMENDATION = 76  # "PRIMARY TARGET: [NAME]" with rationale bullets
T_WHY_TARGET = 77           # "WHY [SEGMENT] IS THE RIGHT FOCUS" with bullets
T_ENABLES = 78              # "WHAT THIS CHOICE ENABLES (AND DOES NOT)"
T_CONSUMER_SUMMARY = 79     # Consumer summary (half-text, half-image)
T_FINAL_SUMMARY = 80        # Three-column summary + closing insight
T_THANK_YOU = 91


# ── Slide Cloning Engine ─────────────────────────────────────

_src_prs = None


def _get_source():
    """Load the reference PPTX once (cached)."""
    global _src_prs
    if _src_prs is None:
        _src_prs = Presentation(str(TEMPLATE_PATH))
    return _src_prs


def _clone_slide(dst_prs, src_slide_idx):
    """Clone a slide from the reference PPTX into dst_prs.

    Copies all shapes (text boxes, images, groups) and their
    relationships (embedded images). Returns the new slide object.
    """
    src_prs = _get_source()
    src_slide = src_prs.slides[src_slide_idx]

    # Find matching layout in dst by name
    src_layout_name = src_slide.slide_layout.name
    dst_layout = None
    for layout in dst_prs.slide_layouts:
        if layout.name == src_layout_name:
            dst_layout = layout
            break
    if not dst_layout:
        dst_layout = dst_prs.slide_layouts[6]  # Blank fallback

    new_slide = dst_prs.slides.add_slide(dst_layout)

    # Clear auto-generated placeholders from layout
    for ph in list(new_slide.placeholders):
        sp = ph._element
        sp.getparent().remove(sp)

    # Copy image/chart relationships, building old→new rId map
    rId_map = {}
    for rel in src_slide.part.rels.values():
        if "image" in rel.reltype or "chart" in rel.reltype:
            new_rId = new_slide.part.rels._add_relationship(
                rel.reltype, rel._target, rel.is_external
            )
            rId_map[rel.rId] = new_rId

    # Copy all shape elements, remapping relationship IDs
    ns_r = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    for shape in src_slide.shapes:
        el = copy.deepcopy(shape._element)
        # Remap rIds in all attributes
        for attr_el in el.iter():
            for attr_name in list(attr_el.attrib):
                if attr_name == f"{ns_r}id" or attr_name.endswith("}id"):
                    old_id = attr_el.attrib[attr_name]
                    if old_id in rId_map:
                        attr_el.attrib[attr_name] = rId_map[old_id]
            if "embed" in attr_el.attrib:
                old_id = attr_el.attrib["embed"]
                if old_id in rId_map:
                    attr_el.attrib["embed"] = rId_map[old_id]
            if f"{ns_r}embed" in attr_el.attrib:
                old_id = attr_el.attrib[f"{ns_r}embed"]
                if old_id in rId_map:
                    attr_el.attrib[f"{ns_r}embed"] = rId_map[old_id]
        new_slide.shapes._spTree.append(el)

    return new_slide


def _find_text_shapes(slide):
    """Return all shapes with text frames, sorted by top then left position."""
    shapes = [s for s in slide.shapes if s.has_text_frame]
    shapes.sort(key=lambda s: (s.top, s.left))
    return shapes


def _set_text_preserve_format(text_frame, new_text):
    """Replace text in a text_frame while preserving per-run and per-paragraph formatting.

    Accepts:
      - str: replaces text line-by-line matching to existing paragraphs/runs
      - list[str]: one string per paragraph, matched 1:1 to existing paragraphs

    Key principle: each original run keeps its font/size/color; we only change .text.
    """
    if isinstance(new_text, list):
        paragraphs = list(text_frame.paragraphs)
        for i, para_text in enumerate(new_text):
            if i < len(paragraphs):
                _replace_para_text(paragraphs[i], para_text)
            else:
                _add_paragraph_after(text_frame, paragraphs[-1], para_text)
        # Remove excess paragraphs
        for i in range(len(new_text), len(paragraphs)):
            p_el = paragraphs[i]._p
            p_el.getparent().remove(p_el)
    else:
        # Split by newlines and match to existing paragraphs/runs
        lines = new_text.split("\n")
        paragraphs = list(text_frame.paragraphs)

        if len(lines) == 1:
            # Single line — distribute across existing runs in first para
            if paragraphs:
                _replace_para_text(paragraphs[0], lines[0])
                for para in paragraphs[1:]:
                    p_el = para._p
                    p_el.getparent().remove(p_el)
        else:
            # Multiple lines — match each line to an existing paragraph
            # If paragraph has multiple runs (different fonts), map lines to runs
            if len(paragraphs) == 1 and len(paragraphs[0].runs) >= len(lines):
                # Single paragraph with multiple runs — map lines to runs
                _replace_runs_text(paragraphs[0], lines)
            else:
                for i, line in enumerate(lines):
                    if i < len(paragraphs):
                        _replace_para_text(paragraphs[i], line)
                    else:
                        _add_paragraph_after(text_frame, paragraphs[-1], line)
                for i in range(len(lines), len(paragraphs)):
                    p_el = paragraphs[i]._p
                    p_el.getparent().remove(p_el)


def _replace_para_text(paragraph, text):
    """Replace text in a paragraph, distributing across existing runs.

    Preserves each run's formatting (font, size, color, bold).
    """
    runs = paragraph.runs
    if not runs:
        paragraph.text = text
        return

    if len(runs) == 1:
        runs[0].text = text
    else:
        # Multiple runs with potentially different formatting.
        # Keep each run, clear all but the first, put text in first.
        runs[0].text = text
        for run in runs[1:]:
            run.text = ""


def _replace_runs_text(paragraph, texts):
    """Replace text run-by-run, one text per run, preserving each run's formatting."""
    runs = paragraph.runs
    for i, text in enumerate(texts):
        if i < len(runs):
            runs[i].text = text
    # Clear excess runs
    for i in range(len(texts), len(runs)):
        runs[i].text = ""


def _add_paragraph_after(text_frame, template_para, text):
    """Add a new paragraph after template_para, copying its formatting."""
    new_p = copy.deepcopy(template_para._p)
    template_para._p.addnext(new_p)
    from pptx.text.text import _Paragraph
    para = _Paragraph(new_p, template_para._parent)
    _replace_para_text(para, text)


# ── Text Truncation ──────────────────────────────────────────

def _truncate(text, max_chars):
    """Truncate text to max_chars, preferring sentence boundaries."""
    if not text or len(text) <= max_chars:
        return text
    # Prefer cutting at last sentence end (period) before limit
    last_period = text[:max_chars].rfind(".")
    if last_period > max_chars * 0.4:
        return text[:last_period + 1]
    # Fall back to last comma or semicolon
    for sep in (",", ";", " —", " –"):
        pos = text[:max_chars].rfind(sep)
        if pos > max_chars * 0.4:
            return text[:pos] + "."
    # Last resort: word boundary
    cut = text[:max_chars].rfind(" ")
    if cut < max_chars // 2:
        cut = max_chars
    return text[:cut].rstrip(" ,;:") + "."


# ── Image Replacement ───────────────────────────────────────

def _replace_slide_image(slide, image_path: Path):
    """Replace the first picture shape on a slide with a new image.

    Pre-crops the image file with PIL to exactly match the box aspect
    ratio (cover + top-bias), then inserts the cropped image at the
    exact box dimensions. No OOXML stretching or srcRect needed —
    the file itself is the right shape.
    """
    if not image_path or not Path(image_path).exists():
        return

    from PIL import Image
    from pptx.shapes.picture import Picture

    for shape in slide.shapes:
        if isinstance(shape, Picture):
            box_left, box_top = shape.left, shape.top
            box_w, box_h = shape.width, shape.height
            box_ratio = box_w / box_h

            try:
                img = Image.open(str(image_path))
                img_w, img_h = img.size
            except Exception:
                return

            img_ratio = img_w / img_h

            # Crop image to match box aspect ratio (cover mode)
            if abs(img_ratio - box_ratio) > 0.05:
                if img_ratio > box_ratio:
                    # Image is wider — crop sides equally
                    new_w = int(img_h * box_ratio)
                    offset = (img_w - new_w) // 2
                    img = img.crop((offset, 0, offset + new_w, img_h))
                else:
                    # Image is taller — crop with top bias (keep ~top 1/3)
                    new_h = int(img_w / box_ratio)
                    # Bias toward top: show top 30% anchor point
                    top_offset = int((img_h - new_h) * 0.15)
                    img = img.crop((0, top_offset, img_w, top_offset + new_h))

            # Save cropped version to a temp file
            cropped_path = image_path.parent / f"_cropped_{image_path.name}"
            img.save(str(cropped_path), quality=92)
            img.close()

            # Remove old picture
            sp = shape._element
            sp.getparent().remove(sp)

            # Insert pre-cropped image at exact box dimensions
            slide.shapes.add_picture(
                str(cropped_path), box_left, box_top, box_w, box_h
            )
            return


class _ImagePool:
    """Manages a pool of collected images, handing them out one at a time.

    Images are categorized: brand images are used first for content slides,
    product images for competitor slides, lifestyle for summaries.
    """

    def __init__(self, images: dict = None):
        self._images = images or {}
        self._brand_idx = 0
        self._product_idx = 0
        self._lifestyle_idx = 0
        self._all_idx = 0

    def next_brand(self) -> Path | None:
        """Get next brand image, cycling through available images."""
        imgs = self._images.get("brand", [])
        if not imgs:
            return self.next_any()
        img = imgs[self._brand_idx % len(imgs)]
        self._brand_idx += 1
        return img

    def next_product(self) -> Path | None:
        """Get next product image."""
        imgs = self._images.get("product", [])
        if not imgs:
            return self.next_brand()
        img = imgs[self._product_idx % len(imgs)]
        self._product_idx += 1
        return img

    def next_lifestyle(self) -> Path | None:
        """Get next lifestyle/stock image."""
        imgs = self._images.get("lifestyle", [])
        if not imgs:
            return self.next_brand()
        img = imgs[self._lifestyle_idx % len(imgs)]
        self._lifestyle_idx += 1
        return img

    def next_any(self) -> Path | None:
        """Get any available image."""
        imgs = self._images.get("all", [])
        if not imgs:
            return None
        img = imgs[self._all_idx % len(imgs)]
        self._all_idx += 1
        return img

    def has_images(self) -> bool:
        return bool(self._images.get("all"))


# ── High-level Slide Builders ────────────────────────────────

def _build_cover(prs, brand_name, date_str):
    """Clone cover slide, replace brand name and date.

    Original cover has one text frame with 2 runs in 1 paragraph:
      Run 0: "CozyFit"  (Montserrat 60pt)
      Run 1: "Brand Discovery" (Montserrat 35pt, preceded by line break)
    We replace run-by-run to preserve each font size.
    """
    slide = _clone_slide(prs, T_COVER)
    shapes = _find_text_shapes(slide)
    if len(shapes) >= 1:
        tf = shapes[0].text_frame
        para = tf.paragraphs[0]
        runs = para.runs
        if len(runs) >= 2:
            # Run 0 = brand name, Run 1 = subtitle
            runs[0].text = brand_name
            runs[1].text = "\nBrand Discovery"
        else:
            _set_text_preserve_format(tf, f"{brand_name}\nBrand Discovery")
    if len(shapes) >= 2:
        _set_text_preserve_format(shapes[1].text_frame, date_str)
    return slide


def _build_agenda(prs):
    """Clone agenda slide (no text changes needed — it's generic)."""
    return _clone_slide(prs, T_AGENDA)


def _build_approach(prs):
    """Clone the 'Our Brand Building Process' approach slide."""
    return _clone_slide(prs, T_APPROACH)


def _build_step_divider(prs):
    """Clone the 'Step 1 – Discovery' divider."""
    return _clone_slide(prs, T_STEP_DIVIDER)


def _build_section_header(prs, section_type):
    """Clone a section header. section_type: 'capabilities'|'competition'|'consumer'."""
    idx_map = {
        "capabilities": T_SECTION_CAPABILITIES,
        "competition": T_SECTION_COMPETITION,
        "consumer": T_SECTION_CONSUMER,
    }
    return _clone_slide(prs, idx_map.get(section_type, T_SECTION_CAPABILITIES))


def _build_content_slide(prs, title, bullets, insight_text, template_idx=T_CONTENT):
    """Clone a content slide (title + bullets + insight + image).

    Template shape layout (sorted by position):
      Shape 0 (top): Title — ALL CAPS, orange, Montserrat Bold
      Shape 1 (middle): Bullets — 3 paragraphs, Montserrat, space_before/after
      Shape 2 (bottom): Insight — teal/blue text, single paragraph
      Shape 3: Image (preserved as-is from template)

    Character limits (from original CozyFit template):
      Title: ~55 chars, Bullets: ~100 chars each, Insight: ~90 chars
    """
    slide = _clone_slide(prs, template_idx)
    shapes = _find_text_shapes(slide)

    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, _truncate(title, 55))
    if len(shapes) >= 2:
        if isinstance(bullets, list):
            bullets = [_truncate(b, 85) for b in bullets[:3]]
        else:
            bullets = [_truncate(bullets, 85)]
        _set_text_preserve_format(shapes[1].text_frame, bullets)
    if len(shapes) >= 3:
        _set_text_preserve_format(shapes[2].text_frame, _truncate(insight_text, 85))

    return slide


def _build_competitor_slide(prs, name, positioning_bullets, learnings_bullets):
    """Clone a competitor deep-dive slide (two-column: positioning + learnings).

    Template shape layout:
      Shape 0: Title — "DICKIES — POSITIONING & KEY LEARNINGS"
      Shape 1: Left column — "POSITIONING\nbullet1\nbullet2\n..."
      Shape 2: Right column — "KEY LEARNINGS\nbullet1\nbullet2\n..."
      Shape 3+: Images (preserved)
    """
    slide = _clone_slide(prs, T_COMPETITOR)
    shapes = _find_text_shapes(slide)

    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, _truncate(f"{name.upper()} — POSITIONING & KEY LEARNINGS", 60))

    if len(shapes) >= 2:
        positioning_text = ["POSITIONING"] + [_truncate(b, 90) for b in positioning_bullets[:3]]
        _set_text_preserve_format(shapes[1].text_frame, positioning_text)

    if len(shapes) >= 3:
        learnings_text = ["KEY LEARNINGS"] + [_truncate(b, 90) for b in learnings_bullets[:3]]
        _set_text_preserve_format(shapes[2].text_frame, learnings_text)

    return slide


def _build_landscape_slide(prs, title, bullets, sidebar_text):
    """Clone the landscape summary slide (slide 24 pattern)."""
    slide = _clone_slide(prs, T_LANDSCAPE)
    shapes = _find_text_shapes(slide)

    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, _truncate(title, 60))
    if len(shapes) >= 2:
        if isinstance(bullets, list):
            bullets = [_truncate(b, 100) for b in bullets]
        else:
            bullets = [_truncate(bullets, 100)]
        _set_text_preserve_format(shapes[1].text_frame, bullets)
    if len(shapes) >= 3:
        _set_text_preserve_format(shapes[2].text_frame, _truncate(sidebar_text, 300))

    return slide


def _build_summary_slide(prs, title, summary_text, template_idx=T_SUMMARY):
    """Clone a summary slide (title + flowing paragraph + half-image)."""
    slide = _clone_slide(prs, template_idx)
    shapes = _find_text_shapes(slide)

    # Summary slide has 2 text shapes: paragraph body and title
    # They may be in different order depending on position sort
    title_shape = None
    body_shape = None
    for s in shapes:
        text = s.text_frame.text.strip().upper()
        if "SUMMARY" in text or len(text) < 40:
            title_shape = s
        else:
            body_shape = s

    if title_shape:
        _set_text_preserve_format(title_shape.text_frame, _truncate(title, 40))
    if body_shape:
        _set_text_preserve_format(body_shape.text_frame, _truncate(summary_text, 260))

    return slide


def _build_thank_you(prs):
    """Clone the Thank You slide."""
    return _clone_slide(prs, T_THANK_YOU)


# ── Consumer Slide Builders ─────────────────────────────────

def _build_research_approach(prs, research_items):
    """Clone research approach slide (slide 26 pattern).

    Template has label+detail rows: Format, Participants, Analysis, Timing.
    Each row is two text shapes side by side (label left, detail right).
    """
    slide = _clone_slide(prs, T_RESEARCH_APPROACH)
    shapes = _find_text_shapes(slide)

    # Shape 0 = title, then pairs of (label, detail)
    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, "RESEARCH APPROACH")

    # Map research_items to the label+detail shape pairs
    pair_idx = 0
    for item in research_items[:5]:
        label_shape_idx = 2 + pair_idx * 2
        detail_shape_idx = label_shape_idx - 1
        # Template order: detail shape comes before label in position sort
        # Actual layout: shapes alternate detail(left-wide) and label(left-narrow)
        if detail_shape_idx < len(shapes) and label_shape_idx < len(shapes):
            _set_text_preserve_format(shapes[label_shape_idx].text_frame, item.get("label", ""))
            _set_text_preserve_format(shapes[detail_shape_idx].text_frame, _truncate(item.get("detail", ""), 200))
        pair_idx += 1

    return slide


def _build_segment_overview(prs, segments):
    """Clone segment overview slide (slide 49 pattern).

    Shows all segments at a glance: name, %, tagline for each.
    Template has 5 columns with: percentage text, image, name, tagline.
    """
    slide = _clone_slide(prs, T_SEGMENT_OVERVIEW)
    shapes = _find_text_shapes(slide)

    # Shape 0 = title
    if shapes:
        _set_text_preserve_format(shapes[0].text_frame, "CONSUMER SEGMENTS AT A GLANCE")

    # Shapes 1-5 = percentages, 11-15 = names, 16-20 = taglines
    # Find percentage shapes (short text, typically "27%")
    pct_shapes = []
    name_shapes = []
    tagline_shapes = []
    for s in shapes[1:]:
        text = s.text_frame.text.strip()
        if text.endswith("%") and len(text) <= 4:
            pct_shapes.append(s)
        elif len(text) < 30 and not text.endswith("%"):
            name_shapes.append(s)
        elif len(text) > 30:
            tagline_shapes.append(s)

    for i, seg in enumerate(segments[:5]):
        if i < len(pct_shapes):
            _set_text_preserve_format(pct_shapes[i].text_frame, f"{seg.get('size_pct', '?')}%")
        if i < len(name_shapes):
            _set_text_preserve_format(name_shapes[i].text_frame, seg.get("name", f"Segment {i+1}"))
        if i < len(tagline_shapes):
            _set_text_preserve_format(tagline_shapes[i].text_frame, _truncate(seg.get("tagline", ""), 80))

    return slide


def _build_meet_segment(prs, segment):
    """Clone 'Meet the [Segment]' slide (slide 51 pattern).

    Full-bleed background image with overlay text:
      Shape 0: background (skip)
      Shape 1: background image
      Shape 2: Segment name (ALL CAPS, large)
      Shape 3: Tagline (one line)
      Shape 4: Narrative paragraph (5-7 sentences)
    """
    slide = _clone_slide(prs, T_MEET_SEGMENT)
    shapes = _find_text_shapes(slide)

    name = segment.get("name", "SEGMENT")
    tagline = segment.get("tagline", "")
    narrative = segment.get("narrative", "")

    # Find the shapes by content length pattern
    for s in shapes:
        text = s.text_frame.text.strip()
        if text.isupper() and len(text) < 30:
            _set_text_preserve_format(s.text_frame, name.upper())
        elif len(text) < 80 and not text.isupper() and "Meet" not in text:
            _set_text_preserve_format(s.text_frame, _truncate(tagline, 70))
        elif len(text) > 80 or "Meet" in text:
            _set_text_preserve_format(s.text_frame, _truncate(narrative, 500))

    return slide


def _build_target_recommendation(prs, target):
    """Clone PRIMARY TARGET slide (slide 76 pattern).

    Shape 0: Title — "PRIMARY TARGET: [SEGMENT NAME]"
    Shape 1: Rationale bullets (4 bullets)
    Shape 2: Image (right half)
    Shape 3: Insight text (bottom)
    """
    slide = _clone_slide(prs, T_TARGET_RECOMMENDATION)
    shapes = _find_text_shapes(slide)

    title = target.get("title", "PRIMARY TARGET")

    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, _truncate(title, 55))
    if len(shapes) >= 2:
        bullets = target.get("rationale_bullets", [])
        bullets = [_truncate(b, 85) for b in bullets[:4]]
        _set_text_preserve_format(shapes[1].text_frame, bullets)
    if len(shapes) >= 3:
        _set_text_preserve_format(shapes[2].text_frame, _truncate(target.get("insight", ""), 85))

    return slide


def _build_why_target(prs, target):
    """Clone WHY [SEGMENT] slide (slide 77 pattern).

    Shape 0: Title
    Shape 1: Rationale bullets (left)
    Shape 2: Image (right)
    Shape 3: Insight (bottom)
    """
    slide = _clone_slide(prs, T_WHY_TARGET)
    shapes = _find_text_shapes(slide)

    segment_name = target.get("primary_segment", "THIS SEGMENT")

    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, _truncate(f"WHY {segment_name.upper()} IS THE RIGHT FOCUS", 55))
    if len(shapes) >= 2:
        bullets = target.get("rationale_bullets", [])
        bullets = [_truncate(b, 85) for b in bullets[:4]]
        _set_text_preserve_format(shapes[1].text_frame, bullets)
    if len(shapes) >= 3:
        _set_text_preserve_format(shapes[2].text_frame, _truncate(target.get("insight", ""), 85))

    return slide


def _build_enables_slide(prs, target):
    """Clone ENABLES slide (slide 78 pattern).

    Shape 0: Title
    Shape 1: "What This Does Not Decide Yet" (right column)
    Shape 2: "What Targeting [X] Unlocks" (left column)
    Shape 3: Closing insight (bottom)
    """
    slide = _clone_slide(prs, T_ENABLES)
    shapes = _find_text_shapes(slide)

    segment_name = target.get("primary_segment", "this segment")
    enables = target.get("enables", [])
    does_not = target.get("does_not_decide", [])

    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, "WHAT THIS CHOICE ENABLES (AND DOES NOT)")

    # Left column = enables, right column = does not decide
    enables_text = f"What Targeting {segment_name} Unlocks\n" + "\n".join(
        _truncate(e, 85) for e in enables[:3]
    )
    does_not_text = "What This Does Not Decide Yet\n" + "\n".join(
        _truncate(d, 85) for d in does_not[:3]
    )

    if len(shapes) >= 3:
        # shapes sorted by top,left — left column first
        _set_text_preserve_format(shapes[2].text_frame, enables_text)
        _set_text_preserve_format(shapes[1].text_frame, does_not_text)
    if len(shapes) >= 4:
        _set_text_preserve_format(shapes[3].text_frame, _truncate(target.get("insight", ""), 100))

    return slide


def _build_consumer_summary(prs, summary_text):
    """Clone consumer summary slide (slide 79 — half-text, half-image)."""
    slide = _clone_slide(prs, T_CONSUMER_SUMMARY)
    shapes = _find_text_shapes(slide)

    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, "CONSUMER SUMMARY")
    if len(shapes) >= 2:
        _set_text_preserve_format(shapes[1].text_frame, _truncate(summary_text, 260))

    return slide


def _build_final_summary(prs, summary_data):
    """Clone three-column summary slide (slide 80 pattern).

    Shape 0: Title — "SUMMARY & NEXT STEPS"
    Shape 1-3: Column headers (Consumer, Capabilities, Competition)
    Shape 4-6: Column text paragraphs
    Shape 7: Closing insight (bottom)
    """
    slide = _clone_slide(prs, T_FINAL_SUMMARY)
    shapes = _find_text_shapes(slide)

    if len(shapes) >= 1:
        _set_text_preserve_format(shapes[0].text_frame, "SUMMARY & NEXT STEPS")

    cap_text = summary_data.get("capabilities_column", "")
    comp_text = summary_data.get("competition_column", "")
    cons_text = summary_data.get("consumer_column", "")
    closing = summary_data.get("closing_insight", "")

    # Find column header shapes (short text) and body shapes (long text)
    headers = []
    bodies = []
    for s in shapes[1:]:
        text = s.text_frame.text.strip()
        if len(text) < 20:
            headers.append(s)
        elif len(text) > 20:
            bodies.append(s)

    # Set headers
    header_labels = ["Capabilities", "Competition", "Consumer"]
    for i, label in enumerate(header_labels):
        if i < len(headers):
            _set_text_preserve_format(headers[i].text_frame, label)

    # Set body paragraphs
    column_texts = [cap_text, comp_text, cons_text]
    for i, txt in enumerate(column_texts):
        if i < len(bodies):
            _set_text_preserve_format(bodies[i].text_frame, _truncate(txt, 250))

    # Closing insight (last shape with substantial width)
    closing_shapes = [s for s in shapes if s.width > 7000000 and s.top > 4000000]
    if closing_shapes:
        _set_text_preserve_format(closing_shapes[0].text_frame, _truncate(closing, 120))

    return slide


# ── Main Generator ───────────────────────────────────────────

async def generate_pptx(
    project_id: int,
    analysis: dict,
    brand_name: str,
    phase: str = "full",
    collected_images: dict = None,
) -> tuple[Path, list[dict]]:
    """Generate a Brand Discovery PPTX from analysis data.

    Clones slides from the CozyFit reference template and replaces
    text content with analysis results. If collected_images is provided,
    replaces template images with brand-specific images.

    Args:
        collected_images: Output from image_collector.collect_images()
            {"brand": [Path], "product": [Path], "lifestyle": [Path], "all": [Path]}

    Returns:
        (pptx_path, slide_previews)
    """
    img_pool = _ImagePool(collected_images)

    # Start from the reference PPTX to get its theme, layouts, fonts
    prs = Presentation(str(TEMPLATE_PATH))

    # Remove ALL existing slides — we'll clone fresh ones
    while len(prs.slides) > 0:
        rId = prs.slides._sldIdLst[0].get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        prs.part.drop_rel(rId)
        prs.slides._sldIdLst.remove(prs.slides._sldIdLst[0])

    slide_meta = []
    date_str = analysis.get("date", "2026")

    # ── 1. Cover ──────────────────────────────────────────────
    _build_cover(prs, brand_name, date_str)
    slide_meta.append({"type": "cover", "content": {"brand_name": brand_name}})

    # ── 2. Agenda ─────────────────────────────────────────────
    _build_agenda(prs)
    slide_meta.append({"type": "agenda", "content": {}})

    # ── 3. Approach ───────────────────────────────────────────
    _build_approach(prs)
    slide_meta.append({"type": "approach", "content": {}})

    # ── 4. Step 1 – Discovery ─────────────────────────────────
    _build_step_divider(prs)
    slide_meta.append({"type": "step", "content": {"step": 1}})

    # ── Capabilities ──────────────────────────────────────────

    _build_section_header(prs, "capabilities")
    slide_meta.append({"type": "section", "content": {"section": "capabilities"}})

    cap = analysis.get("capabilities", {})

    # Content slides for each capability dimension
    content_keys = [
        "execution_summary", "product_offer", "product_fundamentals",
        "pricing_position", "channel_analysis",
    ]
    # Alternate between template slide 6 and 7 for visual variety
    template_pool = [T_CONTENT, T_CONTENT_ALT]

    for i, key in enumerate(content_keys):
        section = cap.get(key)
        if section:
            tmpl = template_pool[i % len(template_pool)]
            slide = _build_content_slide(
                prs,
                title=section.get("title", key.replace("_", " ").upper()),
                bullets=section.get("bullets", []),
                insight_text=section.get("insight", ""),
                template_idx=tmpl,
            )
            if img_pool.has_images():
                _replace_slide_image(slide, img_pool.next_brand())
            slide_meta.append({"type": "insight", "content": section})

    # Brand challenges
    for challenge in cap.get("brand_challenges", []):
        slide = _build_content_slide(
            prs,
            title=challenge.get("title", "BRAND CHALLENGE"),
            bullets=challenge.get("bullets", []),
            insight_text=challenge.get("insight", ""),
        )
        if img_pool.has_images():
            _replace_slide_image(slide, img_pool.next_brand())
        slide_meta.append({"type": "insight", "content": challenge})

    # Capabilities summary
    cap_summary = cap.get("capabilities_summary", "")
    if cap_summary:
        slide = _build_summary_slide(prs, "CAPABILITIES SUMMARY", cap_summary)
        if img_pool.has_images():
            _replace_slide_image(slide, img_pool.next_lifestyle())
        slide_meta.append({"type": "summary", "content": {"text": cap_summary}})

    # ── Competition (Phase 2+) ────────────────────────────────

    if phase in ("market_structure", "full") and analysis.get("competition"):
        _build_section_header(prs, "competition")
        slide_meta.append({"type": "section", "content": {"section": "competition"}})

        comp = analysis.get("competition", {})

        # Market overview
        overview = comp.get("market_overview", {})
        if overview:
            slide = _build_content_slide(
                prs,
                title=overview.get("title", "COMPETITIVE LANDSCAPE"),
                bullets=overview.get("bullets", []),
                insight_text=overview.get("insight", ""),
            )
            if img_pool.has_images():
                _replace_slide_image(slide, img_pool.next_product())
            slide_meta.append({"type": "insight", "content": overview})

        # Competitor deep dives
        for competitor in comp.get("competitor_analyses", []):
            pos_bullets = [
                f"{p['label']}: {p['detail']}"
                for p in competitor.get("positioning", [])
            ]
            learn_bullets = [
                f"{k['label']}: {k['detail']}"
                for k in competitor.get("key_learnings", [])
            ]
            slide = _build_competitor_slide(
                prs,
                name=competitor.get("name", "Competitor"),
                positioning_bullets=pos_bullets,
                learnings_bullets=learn_bullets,
            )
            if img_pool.has_images():
                _replace_slide_image(slide, img_pool.next_product())
            slide_meta.append({"type": "competitor", "content": competitor})

        # Landscape summary
        landscape = comp.get("landscape_summary", {})
        if landscape:
            slide = _build_landscape_slide(
                prs,
                title=landscape.get("title", "A WELL-ESTABLISHED LANDSCAPE"),
                bullets=landscape.get("bullets", []),
                sidebar_text=landscape.get("sidebar", ""),
            )
            slide_meta.append({"type": "landscape", "content": landscape})

        # Competition summary
        comp_summary = comp.get("competition_summary", "")
        if comp_summary:
            slide = _build_summary_slide(prs, "COMPETITION SUMMARY", comp_summary, T_COMP_SUMMARY)
            if img_pool.has_images():
                _replace_slide_image(slide, img_pool.next_lifestyle())
            slide_meta.append({"type": "summary", "content": {"text": comp_summary}})

    # ── Consumer (Full only) ──────────────────────────────────

    if phase == "full" and analysis.get("consumer"):
        _build_section_header(prs, "consumer")
        slide_meta.append({"type": "section", "content": {"section": "consumer"}})

        consumer = analysis.get("consumer", {})

        # Research approach
        research = consumer.get("research_approach", [])
        if research:
            _build_research_approach(prs, research)
            slide_meta.append({"type": "research", "content": {"items": research}})

        # Key consumer insights as content slides
        for insight in consumer.get("key_insights", []):
            slide = _build_content_slide(
                prs,
                title=insight.get("title", "CONSUMER INSIGHT"),
                bullets=insight.get("bullets", []),
                insight_text=insight.get("insight", ""),
            )
            if img_pool.has_images():
                _replace_slide_image(slide, img_pool.next_lifestyle())
            slide_meta.append({"type": "insight", "content": insight})

        # Segmentation divider
        segments = consumer.get("segments", [])
        if segments:
            _clone_slide(prs, T_SEGMENT_DIVIDER)
            slide_meta.append({"type": "divider", "content": {"title": "Market Segmentation"}})

            # Segment overview (all segments at a glance)
            _build_segment_overview(prs, segments)
            slide_meta.append({"type": "segment_overview", "content": {"segments": [s.get("name") for s in segments]}})

            # Individual "Meet the [Segment]" slides
            for seg in segments[:5]:
                slide = _build_meet_segment(prs, seg)
                if img_pool.has_images():
                    _replace_slide_image(slide, img_pool.next_lifestyle())
                slide_meta.append({"type": "meet_segment", "content": seg})

        # Target recommendation
        target = consumer.get("target_recommendation", {})
        if target:
            slide = _build_target_recommendation(prs, target)
            if img_pool.has_images():
                _replace_slide_image(slide, img_pool.next_lifestyle())
            slide_meta.append({"type": "target", "content": target})

            _build_why_target(prs, target)
            slide_meta.append({"type": "why_target", "content": target})

            _build_enables_slide(prs, target)
            slide_meta.append({"type": "enables", "content": target})

        # Consumer summary
        cons_summary = consumer.get("consumer_summary", "")
        if cons_summary:
            slide = _build_consumer_summary(prs, cons_summary)
            if img_pool.has_images():
                _replace_slide_image(slide, img_pool.next_lifestyle())
            slide_meta.append({"type": "consumer_summary", "content": {"text": cons_summary}})

    # ── Final Summary & Next Steps ───────────────────────────

    summary_data = analysis.get("summary_and_next_steps", {})
    if summary_data and phase == "full":
        _build_final_summary(prs, summary_data)
        slide_meta.append({"type": "final_summary", "content": summary_data})

    # ── Thank You ─────────────────────────────────────────────

    _build_thank_you(prs)
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


# ── Preview Generation ───────────────────────────────────────

def _generate_previews(pptx_path: Path, project_id: int) -> list[Path]:
    """Convert PPTX slides to PNG previews via LibreOffice + PyMuPDF."""
    import subprocess
    import tempfile

    preview_dir = PREVIEW_DIR / f"project_{project_id}"
    preview_dir.mkdir(parents=True, exist_ok=True)

    # Clean old previews
    for old in preview_dir.glob("*.png"):
        old.unlink()

    # Step 1: PPTX -> PDF via LibreOffice
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run([
                "soffice", "--headless", "--convert-to", "pdf",
                "--outdir", tmpdir, str(pptx_path)
            ], capture_output=True, timeout=120)

            pdf_files = list(Path(tmpdir).glob("*.pdf"))
            if not pdf_files:
                return _generate_placeholder_previews(pptx_path, preview_dir)

            # Step 2: PDF -> per-page PNG via PyMuPDF
            import fitz
            doc = fitz.open(str(pdf_files[0]))
            paths = []
            for i, page in enumerate(doc):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                png_path = preview_dir / f"slide_{i:03d}.png"
                pix.save(str(png_path))
                paths.append(png_path)
            doc.close()
            return paths

    except (FileNotFoundError, subprocess.TimeoutExpired, ImportError):
        pass

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
