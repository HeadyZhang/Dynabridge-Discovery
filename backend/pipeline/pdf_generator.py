"""PDF Report Generator for Brand Discovery phases.

Generates professional PDF reports (3-6 pages each) from analysis JSON.
Uses fpdf2 for layout. Each phase produces a standalone deliverable:
  - Phase 1: Brand Reality Report
  - Phase 2: Market Structure Report
  - Phase 3: Evidence Plan + Consumer Evidence Report
  - Phase 4: Target Selection & Synthesis Report

These complement the PPTX deck — the PDF is a detailed written document,
while the PPTX is visual presentation slides.
"""

import json
import re
from pathlib import Path
from fpdf import FPDF

from config import OUTPUT_DIR

# Logo path (transparent background version)
LOGO_PATH = Path(__file__).parent.parent.parent / "image" / "logo_transparent.png"
# White version for dark backgrounds (cover page)
LOGO_WHITE_PATH = Path(__file__).parent.parent.parent / "image" / "logo_transparent_white.png"


def _has_cjk(text: str) -> bool:
    """Check if text contains CJK (Chinese/Japanese/Korean) characters."""
    for ch in text:
        cp = ord(ch)
        if (0x4E00 <= cp <= 0x9FFF or      # CJK Unified Ideographs
            0x3400 <= cp <= 0x4DBF or      # CJK Extension A
            0x3000 <= cp <= 0x303F or      # CJK Symbols & Punctuation
            0xFF00 <= cp <= 0xFFEF or      # Fullwidth Forms
            0xF900 <= cp <= 0xFAFF or      # CJK Compatibility Ideographs
            0x2E80 <= cp <= 0x2EFF or      # CJK Radicals
            0x3040 <= cp <= 0x309F or      # Hiragana
            0x30A0 <= cp <= 0x30FF or      # Katakana
            0xAC00 <= cp <= 0xD7AF):       # Hangul Syllables
            return True
    return False


def _sanitize(text: str) -> str:
    """Normalize Unicode punctuation. Preserves CJK characters."""
    if not isinstance(text, str):
        return str(text)
    text = text.replace("\u2014", "--")   # em dash
    text = text.replace("\u2013", "-")    # en dash
    text = text.replace("\u2018", "'")    # left single quote
    text = text.replace("\u2019", "'")    # right single quote
    text = text.replace("\u201c", '"')    # left double quote
    text = text.replace("\u201d", '"')    # right double quote
    text = text.replace("\u2026", "...")   # ellipsis
    text = text.replace("\u2022", "*")    # bullet
    text = text.replace("\u2023", ">")    # triangular bullet
    text = text.replace("\u00a0", " ")    # non-breaking space
    return text


# ── Brand colors ──────────────────────────────────────────────
ORANGE = (232, 108, 0)
DARK_BLUE = (45, 58, 74)
TEAL = (0, 128, 128)
LIGHT_GRAY = (245, 245, 245)
WHITE = (255, 255, 255)
BLACK = (30, 30, 30)


# CJK font paths (macOS → Linux fallback)
_CJK_FONT_PATHS = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",        # macOS
    "/System/Library/Fonts/STHeiti Medium.ttc",           # macOS fallback
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
    "/usr/share/fonts/truetype/noto/NotoSansSC-Regular.otf",   # Linux alt
]


class BrandPDF(FPDF):
    """Custom FPDF with DynaBridge branding and CJK support."""

    def __init__(self, brand_name: str = "", phase_title: str = ""):
        super().__init__()
        self.brand_name = brand_name
        self.phase_title = phase_title
        self.set_auto_page_break(auto=True, margin=20)
        self._cjk_loaded = False
        self._load_cjk_font()

    def _load_cjk_font(self):
        """Load a CJK font for Chinese/Japanese/Korean text rendering."""
        from pathlib import Path
        for font_path in _CJK_FONT_PATHS:
            if Path(font_path).exists():
                try:
                    self.add_font("CJK", "", font_path)
                    self.add_font("CJK", "B", font_path)  # use same for bold
                    self._cjk_loaded = True
                    return
                except Exception:
                    continue

    def _with_cjk(self, text: str, callback, *args, **kwargs):
        """Auto-switch to CJK font if text contains CJK characters, then restore."""
        text = _sanitize(text) if text else ""
        if text and self._cjk_loaded and _has_cjk(text):
            # Save current font state
            prev_family = self.font_family
            prev_style = self.font_style
            prev_size = self.font_size_pt
            # Switch to CJK font with same size
            style = "B" if "B" in prev_style else ""
            self.set_font("CJK", style, prev_size)
            result = callback(*args, text=text, **kwargs)
            # Restore original font
            self.set_font(prev_family, prev_style, prev_size)
            return result
        return callback(*args, text=text, **kwargs)

    def cell(self, w=0, h=None, text="", **kwargs):
        return self._with_cjk(text, super().cell, w, h, **kwargs)

    def multi_cell(self, w, h=None, text="", **kwargs):
        return self._with_cjk(text, super().multi_cell, w, h, **kwargs)

    def header(self):
        if self.page_no() == 1:
            return  # Cover page has custom header
        logo_h = 5
        header_top = 6
        # Logo in top-left, vertically centered with text
        if LOGO_PATH.exists():
            self.image(str(LOGO_PATH), x=10, y=header_top, h=logo_h)
            text_x = 37
        else:
            text_x = 10
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*DARK_BLUE)
        # Place text vertically centered with logo
        self.set_xy(text_x, header_top + 1)
        self.cell(0, logo_h, f"{self.brand_name.upper()}  |  {self.phase_title}", align="L")
        # Orange line below both logo and text
        line_y = header_top + logo_h + 2
        self.set_draw_color(*ORANGE)
        self.set_line_width(0.5)
        self.line(10, line_y, 200, line_y)
        self.set_y(line_y + 4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"CONFIDENTIAL  |  Page {self.page_no()}", align="C")

    def cover_page(self, brand_name: str, phase: str, date: str):
        """Full-page cover with branding."""
        self.add_page()
        # Top bar
        self.set_fill_color(*DARK_BLUE)
        self.rect(0, 0, 210, 70, "F")

        # Logo on cover (top-left, inside dark bar) — use white version
        cover_logo = LOGO_WHITE_PATH if LOGO_WHITE_PATH.exists() else LOGO_PATH
        if cover_logo.exists():
            self.image(str(cover_logo), x=12, y=6, h=8)

        self.set_y(18)
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*WHITE)
        self.cell(0, 12, "BRAND DISCOVERY", align="C", new_x="LMARGIN", new_y="NEXT")

        self.set_font("Helvetica", "", 16)
        self.cell(0, 10, phase.upper(), align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(6)
        # Orange accent line
        self.set_draw_color(*ORANGE)
        self.set_line_width(1)
        self.line(70, self.get_y(), 140, self.get_y())

        # White area: 70mm–277mm (297 - 20mm margin).
        # Place brand name at vertical center of white area.
        white_mid = 70 + (297 - 20 - 70) / 2   # ~173mm
        self.set_y(white_mid - 20)
        self.set_text_color(*DARK_BLUE)
        self.set_font("Helvetica", "B", 28)
        self.cell(0, 14, brand_name.upper(), align="C", new_x="LMARGIN", new_y="NEXT")

        self.ln(6)
        self.set_font("Helvetica", "", 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, date, align="C", new_x="LMARGIN", new_y="NEXT")

        # Bottom line
        self.set_y(-35)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, "Prepared by DynaBridge  |  Confidential", align="C")

    def section_title(self, title: str):
        """Orange section header."""
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*ORANGE)
        self.cell(0, 8, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ORANGE)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def subsection(self, title: str):
        """Dark blue subsection header."""
        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*DARK_BLUE)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text: str):
        """Standard body paragraph."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*BLACK)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def bullet_list(self, items: list):
        """Bulleted list."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*BLACK)
        for item in items:
            txt = str(item)
            self.cell(6, 5, chr(8226))  # bullet character
            self.multi_cell(0, 5, f"  {txt}")
            self.ln(1)

    def key_finding_box(self, title: str, text: str):
        """Highlighted box for key findings/insights."""
        x = self.get_x()
        y = self.get_y()
        self.set_fill_color(*LIGHT_GRAY)
        # Calculate height needed
        self.set_font("Helvetica", "", 9)
        lines = self.multi_cell(180, 5, text, dry_run=True, output="LINES")
        h = max(20, len(lines) * 5 + 16)
        self.rect(10, y, 190, h, "F")
        self.set_xy(14, y + 3)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*TEAL)
        self.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        self.set_x(14)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*BLACK)
        self.multi_cell(180, 5, text)
        self.set_y(y + h + 3)

    def data_table(self, headers: list, rows: list, col_widths: list = None):
        """Simple data table with header row."""
        n_cols = len(headers)
        if not col_widths:
            col_widths = [190 / n_cols] * n_cols

        # Header
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*DARK_BLUE)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, str(h), border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*BLACK)
        for ri, row in enumerate(rows):
            fill = ri % 2 == 0
            if fill:
                self.set_fill_color(250, 250, 250)
            for i, val in enumerate(row):
                self.cell(col_widths[i], 6, str(val)[:50], border=1, fill=fill, align="L")
            self.ln()
        self.ln(3)


# ── Report Generators ─────────────────────────────────────────


def generate_phase1_pdf(analysis: dict, brand_name: str, date: str = "") -> Path:
    """Generate Phase 1: Brand Reality Report (PDF, 3-5 pages)."""
    pdf = BrandPDF(brand_name, "PHASE 1 — BRAND REALITY REPORT")
    pdf.cover_page(brand_name, "Phase 1 — Brand Reality Report", date)

    cap = analysis.get("capabilities", {})

    # Executive Summary
    pdf.add_page()
    pdf.section_title("Executive Summary")

    summary = cap.get("capabilities_summary", "")
    if summary:
        pdf.body_text(summary)

    # Next steps as quick findings
    next_steps = analysis.get("next_steps", [])
    if next_steps:
        pdf.subsection("Key Findings")
        pdf.bullet_list(next_steps[:5])

    # Execution Strengths
    pdf.section_title("Execution Strengths")
    exec_sum = cap.get("execution_summary", {})
    if exec_sum:
        pdf.subsection(exec_sum.get("title", "EXECUTION SUMMARY"))
        pdf.bullet_list(exec_sum.get("bullets", []))
        if exec_sum.get("insight"):
            pdf.key_finding_box("INSIGHT", exec_sum["insight"])

    product = cap.get("product_offer", {})
    if product:
        pdf.subsection(product.get("title", "PRODUCT OFFERING"))
        pdf.bullet_list(product.get("bullets", []))
        if product.get("insight"):
            pdf.key_finding_box("INSIGHT", product["insight"])

    fundamentals = cap.get("product_fundamentals", {})
    if fundamentals:
        pdf.subsection(fundamentals.get("title", "PRODUCT FUNDAMENTALS"))
        pdf.bullet_list(fundamentals.get("bullets", []))

    # Pricing & Channels
    pricing = cap.get("pricing_position", {})
    if pricing:
        pdf.section_title("Pricing Position")
        pdf.bullet_list(pricing.get("bullets", []))
        if pricing.get("insight"):
            pdf.key_finding_box("INSIGHT", pricing["insight"])

    channel = cap.get("channel_analysis", {})
    if channel:
        pdf.section_title("Channel Analysis")
        pdf.bullet_list(channel.get("bullets", []))
        if channel.get("insight"):
            pdf.key_finding_box("INSIGHT", channel["insight"])

    # Brand Perception Gaps
    pdf.section_title("Brand Perception Gaps")
    challenges = cap.get("brand_challenges", [])
    for ch in challenges:
        pdf.subsection(ch.get("title", "CHALLENGE"))
        pdf.bullet_list(ch.get("bullets", []))
        if ch.get("insight"):
            pdf.key_finding_box("INSIGHT", ch["insight"])

    # Claims vs Perception
    cvp = cap.get("claims_vs_perception", {})
    if cvp:
        pdf.section_title("Brand Claims vs. Customer Perception")
        claims = cvp.get("brand_claims", [])
        perceptions = cvp.get("customer_perception", [])
        if claims and perceptions:
            rows = []
            for i in range(max(len(claims), len(perceptions))):
                c = claims[i] if i < len(claims) else ""
                p = perceptions[i] if i < len(perceptions) else ""
                rows.append([c[:60], p[:60]])
            pdf.data_table(["Brand Claims", "Customer Perception"], rows, [95, 95])

        if cvp.get("alignment"):
            pdf.subsection("Alignment")
            pdf.body_text(cvp["alignment"])
        if cvp.get("gaps"):
            pdf.subsection("Gaps")
            pdf.body_text(cvp["gaps"])

    # Clarity Assessment
    clarity = analysis.get("clarity_scoring") or cap.get("clarity_scoring", {})
    if clarity:
        pdf.section_title("Clarity Assessment")
        overall = clarity.get("overall_score", 0)
        pdf.body_text(f"Overall Brand Clarity Score: {overall}/100")
        if clarity.get("headline"):
            pdf.key_finding_box("DIAGNOSIS", clarity["headline"])

        dims = clarity.get("dimensions", [])
        if dims:
            rows = [[d.get("name", ""), f"{d.get('score', 0)}/{d.get('max', 10)}", d.get("evidence", "")[:80]] for d in dims]
            pdf.data_table(["Dimension", "Score", "Evidence"], rows, [45, 20, 125])

        if clarity.get("strongest_zone"):
            pdf.body_text(f"Strongest: {clarity['strongest_zone']}")
        if clarity.get("weakest_zone"):
            pdf.body_text(f"Weakest: {clarity['weakest_zone']}")

    # Save
    output_dir = OUTPUT_DIR / f"reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = brand_name.lower().replace(" ", "_")[:20]
    path = output_dir / f"{safe}_phase1_brand_reality.pdf"
    pdf.output(str(path))
    print(f"[pdf] Phase 1 report: {path} ({path.stat().st_size:,} bytes)")
    return path


def generate_phase2_pdf(analysis: dict, brand_name: str, date: str = "") -> Path:
    """Generate Phase 2: Market Structure Report (PDF, 4-6 pages)."""
    pdf = BrandPDF(brand_name, "PHASE 2 — MARKET STRUCTURE REPORT")
    pdf.cover_page(brand_name, "Phase 2 — Market Structure Report", date)

    comp = analysis.get("competition", {})

    # Executive Summary
    pdf.add_page()
    pdf.section_title("Executive Summary")
    comp_summary = comp.get("competition_summary", "")
    if comp_summary:
        pdf.body_text(comp_summary)

    # Market Overview
    overview = comp.get("market_overview", {})
    if overview:
        pdf.section_title("Market Overview")
        pdf.subsection(overview.get("title", "COMPETITIVE LANDSCAPE"))
        pdf.bullet_list(overview.get("bullets", []))
        if overview.get("insight"):
            pdf.key_finding_box("INSIGHT", overview["insight"])

        names = overview.get("competitor_names", [])
        if names:
            pdf.body_text(f"Key players: {', '.join(names)}")

    # Detailed Competitor Analysis
    competitors = comp.get("competitor_analyses", [])
    if competitors:
        pdf.section_title("Detailed Competitor Analysis")
        for c in competitors:
            pdf.subsection(c.get("name", "Competitor"))
            banner = c.get("banner_description", "")
            if banner:
                pdf.body_text(banner)

            positioning = c.get("positioning", [])
            if positioning:
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 5, "Positioning:", new_x="LMARGIN", new_y="NEXT")
                items = [f"{p.get('label', '')}: {p.get('detail', '')}" for p in positioning]
                pdf.bullet_list(items)

            learnings = c.get("key_learnings", [])
            if learnings:
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 5, "Key Learnings:", new_x="LMARGIN", new_y="NEXT")
                items = [f"{l.get('label', '')}: {l.get('detail', '')}" for l in learnings]
                pdf.bullet_list(items)
            pdf.ln(3)

    # Market Roles
    landscape = comp.get("landscape_summary", {})
    if landscape:
        pdf.section_title("Competitive Landscape Roles")
        roles = landscape.get("market_roles", [])
        if roles:
            rows = []
            for r in roles:
                brands = ", ".join(r.get("brands", []))
                rows.append([r.get("role", ""), brands, r.get("description", "")[:60]])
            pdf.data_table(["Role", "Brands", "Description"], rows, [40, 50, 100])

        ws = landscape.get("white_space", "")
        if ws:
            pdf.key_finding_box("WHITE SPACE OPPORTUNITY", ws)

        norms = landscape.get("category_norms", [])
        if norms:
            pdf.subsection("Category Norms")
            pdf.bullet_list(norms)

    # Save
    output_dir = OUTPUT_DIR / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = brand_name.lower().replace(" ", "_")[:20]
    path = output_dir / f"{safe}_phase2_market_structure.pdf"
    pdf.output(str(path))
    print(f"[pdf] Phase 2 report: {path} ({path.stat().st_size:,} bytes)")
    return path


def generate_phase3_pdf(analysis: dict, brand_name: str, date: str = "") -> Path:
    """Generate Phase 3: Evidence Plan + Consumer Evidence Report (PDF, 4-6 pages)."""
    pdf = BrandPDF(brand_name, "PHASE 3 — CONSUMER EVIDENCE REPORT")
    pdf.cover_page(brand_name, "Phase 3 — Evidence Plan & Consumer Analysis", date)

    consumer = analysis.get("consumer", {})
    evidence_plan = analysis.get("evidence_plan", {})

    # Evidence Collection Plan (contract requires this as separate section)
    pdf.add_page()
    pdf.section_title("Evidence Collection Plan")

    qs = evidence_plan.get("questionnaire_summary", {})
    if qs:
        pdf.subsection("Questionnaire Design")
        pdf.body_text(f"Target respondent: {qs.get('target_respondent', 'N/A')}")
        pdf.body_text(f"Total questions: {qs.get('total_questions', 'N/A')} | Duration: {qs.get('estimated_duration', 'N/A')}")
        sections = qs.get("sections", [])
        if sections:
            pdf.bullet_list(sections)

    hyps_plan = evidence_plan.get("hypotheses_to_validate", [])
    if hyps_plan:
        pdf.subsection("Hypotheses to Validate")
        rows = []
        for h in hyps_plan:
            rows.append([
                h.get("hypothesis", "")[:60],
                h.get("data_type", "")[:30],
                h.get("collection_method", "")[:40],
            ])
        pdf.data_table(["Hypothesis", "Data Type", "Method"], rows, [80, 40, 70])

    gaps = evidence_plan.get("coverage_gaps", [])
    if gaps:
        pdf.subsection("Coverage Gaps")
        pdf.bullet_list(gaps)

    # Hypothesis Validation Results
    hyp_val = analysis.get("hypothesis_validation", [])
    if hyp_val:
        pdf.section_title("Hypothesis Validation Results")
        rows = []
        for h in hyp_val:
            status = h.get("status", "").replace("_", " ").title()
            rows.append([
                h.get("id", ""),
                h.get("statement", "")[:50],
                status,
                h.get("evidence", "")[:60],
            ])
        pdf.data_table(["#", "Hypothesis", "Status", "Evidence"], rows, [12, 60, 28, 90])

    # Consumer Insights
    insights = consumer.get("key_insights", [])
    if insights:
        pdf.section_title("Key Consumer Insights")
        for ins in insights:
            pdf.subsection(ins.get("title", "INSIGHT"))
            pdf.bullet_list(ins.get("bullets", []))
            if ins.get("insight"):
                pdf.key_finding_box("INSIGHT", ins["insight"])

    # Consumer Need-State Map (segments overview)
    segments = consumer.get("segments", [])
    if segments:
        pdf.section_title("Consumer Need-State Mapping")
        pdf.body_text(f"{len(segments)} distinct consumer segments identified:")
        rows = []
        for s in segments:
            rows.append([
                s.get("name", ""),
                f"{s.get('size_pct', '?')}%",
                s.get("tagline", "")[:60],
            ])
        pdf.data_table(["Segment", "Size", "Tagline"], rows, [45, 20, 125])

    # Purchase Driver Hierarchy
    charts = consumer.get("charts", [])
    driver_chart = next((c for c in charts if "driver" in c.get("title", "").lower()), None)
    if driver_chart:
        pdf.section_title("Purchase Driver Hierarchy")
        cats = driver_chart.get("categories", [])
        vals = driver_chart.get("values", [])
        if cats and vals:
            rows = [[c, f"{v}%"] for c, v in zip(cats, vals)]
            pdf.data_table(["Factor", "% Citing"], rows, [130, 60])

    # Save
    output_dir = OUTPUT_DIR / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = brand_name.lower().replace(" ", "_")[:20]
    path = output_dir / f"{safe}_phase3_consumer_evidence.pdf"
    pdf.output(str(path))
    print(f"[pdf] Phase 3 report: {path} ({path.stat().st_size:,} bytes)")
    return path


def generate_phase4_pdf(analysis: dict, brand_name: str, date: str = "") -> Path:
    """Generate Phase 4: Target Selection & Synthesis Report (PDF, 4-6 pages)."""
    pdf = BrandPDF(brand_name, "PHASE 4 — TARGET SELECTION & SYNTHESIS")
    pdf.cover_page(brand_name, "Phase 4 — Target Selection & Synthesis", date)

    consumer = analysis.get("consumer", {})
    segments = consumer.get("segments", [])
    target = consumer.get("target_recommendation", {})
    conflict = analysis.get("conflict_matrix", {})
    summary = analysis.get("summary_and_next_steps", {})

    # Executive Summary
    pdf.add_page()
    pdf.section_title("Executive Summary")
    if target.get("primary_segment"):
        pdf.body_text(f"Recommended Primary Target: {target['primary_segment']}")
    cons_summary = target.get("consumer_summary") or consumer.get("consumer_summary", "")
    if cons_summary:
        pdf.body_text(cons_summary)

    # Detailed Segment Profiles
    if segments:
        pdf.section_title("Consumer Segment Profiles")
        for s in segments:
            pdf.subsection(f"{s.get('name', 'Segment')} ({s.get('size_pct', '?')}%)")
            narrative = s.get("narrative", "")
            if narrative:
                pdf.body_text(narrative)

            demo = s.get("demographics", {})
            if demo:
                demo_parts = []
                for k, v in demo.items():
                    demo_parts.append(f"{k.replace('_', ' ').title()}: {v}")
                pdf.body_text(" | ".join(demo_parts))

            needs = s.get("top_needs", [])
            if needs:
                pdf.set_font("Helvetica", "B", 8)
                pdf.cell(0, 5, "Top Needs:", new_x="LMARGIN", new_y="NEXT")
                pdf.bullet_list(needs)

    # Conflict Matrix
    if conflict and conflict.get("conflicts"):
        pdf.section_title("Inter-Segment Conflict Matrix")
        conflicts_list = conflict.get("conflicts", [])
        rows = []
        for c in conflicts_list:
            rows.append([
                c.get("segment_a", ""),
                c.get("segment_b", ""),
                c.get("severity", "").upper(),
                c.get("description", "")[:60],
            ])
        pdf.data_table(["Segment A", "Segment B", "Severity", "Conflict"], rows, [35, 35, 20, 100])

        imp = conflict.get("strategic_implication", "")
        if imp:
            pdf.key_finding_box("STRATEGIC IMPLICATION", imp)

    # Target Recommendation
    if target:
        pdf.section_title("Primary Target Recommendation")
        pdf.subsection(target.get("title", f"PRIMARY TARGET: {target.get('primary_segment', '')}"))

        rationale = target.get("rationale_bullets", [])
        if rationale:
            pdf.subsection("Rationale")
            pdf.bullet_list(rationale)

        if target.get("insight"):
            pdf.key_finding_box("INSIGHT", target["insight"])

        enables = target.get("enables", [])
        if enables:
            pdf.subsection("What This Choice Enables")
            pdf.bullet_list(enables)

        does_not = target.get("does_not_decide", [])
        if does_not:
            pdf.subsection("What This Choice Does NOT Decide")
            pdf.bullet_list(does_not)

    # Deprioritized Segments
    depri = consumer.get("deprioritized_segments", [])
    if depri:
        pdf.section_title("Why Not Other Segments")
        rows = []
        for d in depri:
            rows.append([d.get("name", ""), f"{d.get('size_pct', '?')}%", d.get("reason", "")[:80]])
        pdf.data_table(["Segment", "Size", "Reason for Deprioritization"], rows, [40, 15, 135])

    # Strategic Synthesis
    pdf.section_title("Discovery Synthesis")
    if summary.get("capabilities_column"):
        pdf.subsection("Brand Reality (Phase 1)")
        pdf.body_text(summary["capabilities_column"])
    if summary.get("competition_column"):
        pdf.subsection("Market Context (Phase 2)")
        pdf.body_text(summary["competition_column"])
    if summary.get("consumer_column"):
        pdf.subsection("Target Audience (Phase 3-4)")
        pdf.body_text(summary["consumer_column"])
    if summary.get("closing_insight"):
        pdf.key_finding_box("CLOSING INSIGHT", summary["closing_insight"])

    # Next Steps
    next_steps = analysis.get("next_steps", [])
    if next_steps:
        pdf.section_title("Recommended Next Steps")
        pdf.bullet_list(next_steps)

    # Save
    output_dir = OUTPUT_DIR / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = brand_name.lower().replace(" ", "_")[:20]
    path = output_dir / f"{safe}_phase4_target_synthesis.pdf"
    pdf.output(str(path))
    print(f"[pdf] Phase 4 report: {path} ({path.stat().st_size:,} bytes)")
    return path


def generate_all_pdfs(analysis: dict, brand_name: str, date: str = "") -> list[Path]:
    """Generate all phase PDFs from a full analysis. Returns list of paths."""
    paths = []
    try:
        paths.append(generate_phase1_pdf(analysis, brand_name, date))
    except Exception as e:
        print(f"[pdf] Phase 1 PDF failed: {e}")
    try:
        paths.append(generate_phase2_pdf(analysis, brand_name, date))
    except Exception as e:
        print(f"[pdf] Phase 2 PDF failed: {e}")
    try:
        paths.append(generate_phase3_pdf(analysis, brand_name, date))
    except Exception as e:
        print(f"[pdf] Phase 3 PDF failed: {e}")
    try:
        paths.append(generate_phase4_pdf(analysis, brand_name, date))
    except Exception as e:
        print(f"[pdf] Phase 4 PDF failed: {e}")
    return paths
