"""Survey/Questionnaire design module.

Generates a customized consumer survey questionnaire for any brand/category,
based on DynaBridge's standard Discovery methodology.

Professional survey structure (industry best-practice order):
  Section 1: Screener (2-3 questions — qualify respondents FIRST)
  Section 2: Category Usage & Shopping Behavior (5-7 questions)
  Section 3: Purchase Drivers & Barriers (4-6 questions)
  Section 4: Brand Evaluation — Funnel + NPS + Associations (6-9 questions)
  Section 5: Lifestyle & Psychographics (3-5 questions)
  Section 6: Open-ended Verbatims (2-3 questions)
  Section 7: Demographics (4-5 questions — at END to reduce dropout)

Total: 26-38 questions, targeting 12-15 minute completion.
Includes: unaided awareness, brand funnel, NPS 0-10, attention check,
          skip logic directives, option randomization.
"""
import json
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, MODEL_OPUS

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SURVEY_SYSTEM = """You are a senior quantitative research director at DynaBridge, a brand strategy
consulting firm. You design consumer surveys at the methodological standard of Kantar, Ipsos,
and Nielsen — surveys that produce data clean enough for segmentation modeling and conjoint-level
insight extraction.

## Core Methodology Principles

### 1. Question Order — The Research Flow
The order of sections is critical to data quality. Follow this EXACT sequence:
  1. SCREENER (2-3 Qs) — qualify respondents, terminate unqualified
  2. CATEGORY BEHAVIOR (5-7 Qs) — establish behavioral baseline before introducing brands
  3. PURCHASE DRIVERS & BARRIERS (4-6 Qs) — what matters and what frustrates
  4. BRAND EVALUATION (6-9 Qs) — unaided FIRST, then aided, then funnel, then NPS
  5. LIFESTYLE & PSYCHOGRAPHICS (3-5 Qs) — segment enrichment signals
  6. OPEN-ENDED VERBATIMS (2-3 Qs) — capture voice-of-consumer
  7. DEMOGRAPHICS (4-5 Qs) — age, gender, ethnicity, income AT THE END

WHY THIS ORDER: Demographics at the beginning cause dropout and prime respondents
to think about identity rather than behavior. Asking unaided awareness BEFORE aided
prevents contamination — the aided list biases recall if shown first.

### 2. Brand Evaluation — The Funnel (MANDATORY)
Every brand discovery survey MUST include the full brand funnel in this order:
  a. UNAIDED AWARENESS: "When you think of [category], which brands come to mind?"
     — type: open_ended (free text, not a list)
     — this is the single most valuable brand metric; it measures true mental availability
  b. AIDED AWARENESS: "Which of these brands have you HEARD OF?" — multi_select
     — include 8-12 brands: target brand + competitors + 1-2 decoys
     — RANDOMIZE option order (add "randomize": true)
  c. CONSIDERATION: "Which would you CONSIDER purchasing?" — multi_select
     — skip_logic: only show brands selected in aided awareness
  d. TRIAL: "Which have you PURCHASED in the past 12 months?" — multi_select
  e. REGULAR USE: "Which do you purchase REGULARLY (3+ times/year)?" — multi_select
  f. FAVORITE: "Which is your single favorite, regardless of price?" — single_select
  g. NPS: "How likely are you to recommend [favorite brand] to a friend?"
     — type: nps (0-10 numeric scale, NOT a Likert)
     — 0 = "Not at all likely", 10 = "Extremely likely"

### 3. Attention Checks (MANDATORY — exactly 1)
Insert ONE attention check mid-survey to identify inattentive respondents:
  - Disguised as a real question, e.g.: "For quality purposes, please select 'Somewhat agree'"
  - OR: "Which of these is a color?" with options including non-colors
  - Mark with "attention_check": true so analysis can flag/exclude failures
  - Place it in Section 3 or 4 (not at start or end)

### 4. Skip Logic & Branching
Use "skip_logic" field on questions where branching is needed:
  - Brand satisfaction/NPS: only ask about brands the respondent has purchased
  - Driver deep-dive: only ask if respondent selected that driver
  - Category-specific follow-ups: only if applicable

### 5. Randomization
Add "randomize": true on ALL multi-select and single-select questions where option order
could bias results. Exceptions:
  - Scales (Likert, NPS) — never randomize, maintain natural order
  - Age/income brackets — never randomize, maintain ascending order
  - "Other" / "None of these" — always anchor at bottom regardless of randomization

### 6. Question Quality Standards
- NO leading questions ("Don't you agree that...?" ✗)
- NO double-barreled questions ("How satisfied are you with quality AND price?" ✗)
- NO jargon — use language a high school graduate would understand
- Every option set needs "Other (please specify)" and/or "None of these" where appropriate
- Likert scales: always 5-point, always balanced (2 positive, neutral, 2 negative)
- Multi-select with max_select: always explain the limit in the question text
- Single-select: options must be MECE (mutually exclusive, collectively exhaustive)

### 7. Analysis Blueprint
Every question MUST have:
  - "analysis_use": how this data will be used in the final presentation
  - Purpose must map to a specific slide or analysis output

### 8. Survey Parameters
- Target: 12-15 minutes, 26-38 questions
- Format: unbranded (don't reveal which brand commissioned it)
- Panel: online (Prolific, MTurk, Cint, or similar)
- Sample: n=200 minimum for ±7% margin of error at 95% CI

### 9. What Makes a DynaBridge Survey Different
Our surveys are designed for SEGMENTATION, not just averages. Every question should help
differentiate buyer types. The combination of purchase frequency + spend tier + top drivers +
lifestyle signals enables k-means or latent class clustering into 4-5 actionable segments.
"""

SURVEY_PROMPT = """Design a complete consumer survey questionnaire for this brand discovery project.

Brand: {brand_name}
Category: {category}
Brand URL: {brand_url}
Language: {language}

## Brands to Include in Aided Awareness (8-12 brands, RANDOMIZE order)
{brand_list}

## Category & Market Context (from desktop research)
{context}

## Known Consumer Pain Points
{pain_points}

## Known Purchase Drivers for This Category
{known_drivers}

Generate a survey with 26-38 questions following DynaBridge's methodology. The section order,
brand funnel, NPS format, attention check, and demographics-at-end rules are NON-NEGOTIABLE.

## Category-Specific Customization Rules
- "Premium" definition options MUST be specific to this category (e.g., "fabric technology" for
  apparel, "filtration performance" for water filters, "ingredient transparency" for baby products)
  — NEVER use generic options like "high quality" without category specifics
- Purchase driver options must reflect REAL category concerns from the research context above
- Channel options must match where this category is actually sold (DTC, Amazon, specialty retail, etc.)
- Brand association matrix: use 6-8 attributes genuinely relevant to competitive differentiation
  in THIS category — not generic attributes like "trustworthy" unless trust is a real battleground
- Lifestyle questions (music, car brand, personal style) are ALWAYS included — they drive segment
  profiling, not category analysis
- Include a "willingness to pay premium" question with a specific price anchor grounded in category
  reality (use the research context for real price ranges)
- Open-ended questions should probe the specific pain points and unmet needs identified in research

## Question Format Requirements
- Every multi-select and single-select (except scales/brackets) MUST have "randomize": true
- Every question MUST have "analysis_use" explaining its role in the final deliverable
- Include exactly ONE attention check question with "attention_check": true
- Use skip_logic where branching is needed (brand satisfaction → only purchased brands)
- NPS must be type "nps" with 0-10 scale, NOT a Likert

Return ONLY a JSON object:
{{
  "survey_title": "Consumer [Category] Survey",
  "estimated_duration": "12-15 minutes",
  "target_sample_size": 200,
  "margin_of_error": "±7% at 95% CI",
  "target_audience": "US adults 18+ who have purchased [category] in the past 12 months",
  "screener_criteria": ["Criterion 1", "Criterion 2"],
  "sections": [
    {{
      "name": "Section Name",
      "purpose": "Why this section exists and what analysis it enables",
      "questions": [
        {{
          "id": "Q1",
          "text": "Full question text — clear, unbiased, no jargon",
          "type": "single_select|multi_select|likert|open_ended|grid|nps|ranking",
          "required": true,
          "options": ["Option 1", "Option 2", "Option 3", "Other (please specify)"],
          "max_select": 3,
          "randomize": true,
          "skip_logic": "Show only if Q13 includes this brand",
          "attention_check": false,
          "analysis_use": "Brand funnel — aided awareness for competitive benchmarking slide"
        }}
      ]
    }}
  ],
  "cross_tab_variables": ["Generation", "Gender", "Income", "Purchase Frequency", "Segment"],
  "segmentation_variables": ["Purchase frequency", "Annual spend", "Top purchase drivers", "Lifestyle identity"],
  "analysis_outputs": [
    "Brand funnel chart (awareness → consideration → trial → regular → favorite)",
    "NPS by brand",
    "Purchase driver ranking (hbar)",
    "Channel mix (donut)",
    "Premium perception (stacked bar)",
    "Brand association matrix (heatmap)",
    "Segment profiles (5 personas)"
  ],
  "notes": "Survey design notes"
}}
"""


async def design_survey(
    brand_name: str,
    brand_url: str = "",
    competitors: list[str] = None,
    category: str = "",
    language: str = "en",
    analysis_context: str = "",
    desktop_research: dict = None,
) -> dict:
    """Generate a customized survey questionnaire for a brand.

    Args:
        brand_name: Brand name
        brand_url: Brand website URL
        competitors: List of competitor names
        category: Product category (auto-detected if empty)
        language: "en" or "zh" or "en+zh"
        analysis_context: Summary of Phase 1-2 findings to inform questions
        desktop_research: Full desktop research dict (brand_context, competitor_profiles, consumer_landscape)

    Returns:
        Survey design as structured JSON
    """
    if not client:
        return _fallback_survey(brand_name, category, competitors or [])

    # ── Extract rich context from desktop research ──
    comp_names = list(competitors or [])
    pain_points_text = "Not yet researched."
    known_drivers_text = "Not yet researched."
    context_text = analysis_context[:4000] if analysis_context else ""

    if desktop_research and isinstance(desktop_research, dict):
        # Extract competitor names from profiles if not provided
        profiles = desktop_research.get("competitor_profiles", [])
        if profiles and not comp_names:
            comp_names = [p.get("name", "") for p in profiles if p.get("name")]

        # Extract consumer pain points
        cl = desktop_research.get("consumer_landscape", {})
        if isinstance(cl, dict):
            cb = cl.get("category_buyers", cl)
            pains = cb.get("pain_points", [])
            if pains:
                if isinstance(pains[0], dict):
                    pain_points_text = "\n".join(
                        f"- {p.get('issue', p.get('pain_point', ''))}: {p.get('detail', '')} ({p.get('frequency_pct', '?')}%)"
                        for p in pains[:8]
                    )
                elif isinstance(pains[0], str):
                    pain_points_text = "\n".join(f"- {p}" for p in pains[:8])

            # Extract known decision drivers
            dd = cb.get("decision_drivers", {})
            if isinstance(dd, dict):
                top_factors = dd.get("top_factors", [])
                if top_factors:
                    if isinstance(top_factors[0], dict):
                        known_drivers_text = "\n".join(
                            f"- {f.get('factor', '')}: {f.get('importance_pct', '?')}%"
                            for f in top_factors[:8]
                        )
                    elif isinstance(top_factors[0], str):
                        known_drivers_text = "\n".join(f"- {f}" for f in top_factors[:8])

            # Add category context
            if not context_text:
                purchase = cb.get("purchase_behavior", {})
                brand_dyn = cb.get("brand_dynamics", {})
                context_parts = []
                if purchase:
                    context_parts.append(f"Purchase behavior: {json.dumps(purchase, default=str)[:800]}")
                if brand_dyn:
                    context_parts.append(f"Brand dynamics: {json.dumps(brand_dyn, default=str)[:800]}")
                context_text = "\n".join(context_parts)

        # Add brand context
        bc = desktop_research.get("brand_context", {})
        if isinstance(bc, dict) and context_text:
            bp = bc.get("brand_positioning", {})
            if isinstance(bp, dict):
                price_pos = bp.get("price_positioning", "")
                if price_pos:
                    context_text += f"\nBrand price positioning: {price_pos}"

    # Build brand list for aided awareness (target brand + competitors + decoys)
    brand_list_items = [brand_name] + [c for c in comp_names[:10] if c]
    # Ensure 8-12 brands
    brand_list_text = "\n".join(f"- {b}" for b in brand_list_items)
    if len(brand_list_items) < 8:
        brand_list_text += f"\n(Add {8 - len(brand_list_items)} more relevant brands to reach 8-12 total. Include 1-2 emerging/niche brands as decoys.)"

    prompt = SURVEY_PROMPT.format(
        brand_name=brand_name,
        category=category or "consumer products",
        brand_url=brand_url,
        language=language,
        brand_list=brand_list_text,
        context=context_text or "No prior analysis available — use your category knowledge.",
        pain_points=pain_points_text,
        known_drivers=known_drivers_text,
    )

    try:
        response = client.messages.create(
            model=MODEL_OPUS,
            max_tokens=12000,
            system=SURVEY_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            survey = json.loads(text[start:end])
            # Structural + LLM quality validation
            survey = _validate_survey_structure(survey, brand_name, category, comp_names)
            survey = _validate_survey_quality(survey, brand_name, category)
            return survey
    except Exception as e:
        print(f"[survey_designer] LLM survey design failed: {e}")

    return _fallback_survey(brand_name, category, competitors or [])


def _validate_survey_structure(survey: dict, brand_name: str, category: str,
                               competitors: list[str] = None) -> dict:
    """Structural validation — checks and FIXES methodological requirements.

    Validates:
    1. Section order (screener first, demographics last)
    2. Brand funnel completeness (unaided → aided → consideration → trial → favorite → NPS)
    3. Attention check presence
    4. Question count and type distribution
    5. Randomization on appropriate questions
    6. Brand list completeness in aided awareness
    """
    all_questions = []
    for section in survey.get("sections", []):
        all_questions.extend(section.get("questions", []))

    if not all_questions:
        print("[survey_struct] No questions found, skipping validation")
        return survey

    issues = []
    fixes = []

    # ── 1. Check section order ──
    section_names = [s.get("name", "").lower() for s in survey.get("sections", [])]
    if section_names:
        # Demographics should be last (or second-to-last before open-ended)
        demo_idx = -1
        for i, name in enumerate(section_names):
            if "demo" in name:
                demo_idx = i
                break
        if demo_idx >= 0 and demo_idx < len(section_names) - 2:
            issues.append(f"Demographics section at position {demo_idx+1}/{len(section_names)} — should be near end")
            # Move demographics section to second-to-last
            sections = survey["sections"]
            demo_section = sections.pop(demo_idx)
            # Insert before last section (usually open-ended) or at end
            insert_pos = max(len(sections) - 1, 0)
            sections.insert(insert_pos, demo_section)
            survey["sections"] = sections
            fixes.append("Moved demographics section to near-end position")

    # ── 2. Check brand funnel ──
    q_types_found = set()
    for q in all_questions:
        text_lower = (q.get("text", "") + " " + q.get("analysis_use", "")).lower()
        if "unaided" in text_lower or ("come to mind" in text_lower and "brand" in text_lower):
            q_types_found.add("unaided_awareness")
        if "aided" in text_lower or ("heard of" in text_lower and q.get("type") == "multi_select"):
            q_types_found.add("aided_awareness")
        if "consider" in text_lower and "purchas" in text_lower:
            q_types_found.add("consideration")
        if ("purchased" in text_lower or "bought" in text_lower) and "past" in text_lower:
            q_types_found.add("trial")
        if "favorite" in text_lower or "favourite" in text_lower:
            q_types_found.add("favorite")
        if q.get("type") == "nps" or "nps" in text_lower or ("recommend" in text_lower and "0" in str(q.get("options", []))):
            q_types_found.add("nps")

    funnel_required = {"unaided_awareness", "aided_awareness", "trial", "favorite"}
    missing_funnel = funnel_required - q_types_found
    if missing_funnel:
        issues.append(f"Brand funnel missing: {', '.join(missing_funnel)}")

    # ── 3. Check attention check ──
    has_attention = any(q.get("attention_check") for q in all_questions)
    if not has_attention:
        issues.append("No attention check question found")
        # Insert one in the middle section
        mid_idx = len(survey["sections"]) // 2
        attention_q = {
            "id": f"QAC",
            "text": "For quality assurance, please select 'Somewhat agree' for this question.",
            "type": "likert",
            "options": ["Strongly agree", "Somewhat agree", "Neutral", "Somewhat disagree", "Strongly disagree"],
            "required": True,
            "attention_check": True,
            "analysis_use": "Attention check — exclude respondents who fail",
        }
        if mid_idx < len(survey["sections"]):
            survey["sections"][mid_idx]["questions"].append(attention_q)
            fixes.append("Inserted attention check question")

    # ── 4. Check NPS format ──
    for q in all_questions:
        text_lower = q.get("text", "").lower()
        if "recommend" in text_lower and "likely" in text_lower:
            if q.get("type") == "likert":
                q["type"] = "nps"
                q["options"] = list(range(0, 11))  # 0-10
                q["scale_labels"] = {"0": "Not at all likely", "10": "Extremely likely"}
                fixes.append(f"Converted {q.get('id', '?')} from Likert to NPS 0-10")

    # ── 5. Add randomization where missing ──
    randomize_count = 0
    for q in all_questions:
        if q.get("type") in ("multi_select", "single_select") and not q.get("randomize"):
            # Don't randomize scales, age brackets, income brackets
            text_lower = q.get("text", "").lower()
            if not any(kw in text_lower for kw in ["age", "income", "born", "household", "year"]):
                options = q.get("options", [])
                # Don't randomize if options are clearly ordered
                if len(options) >= 4 and not any(kw in str(options).lower() for kw in ["under $", "$", "less than", "more than"]):
                    q["randomize"] = True
                    randomize_count += 1
    if randomize_count > 0:
        fixes.append(f"Added randomization to {randomize_count} questions")

    # ── 6. Check brand list in aided awareness ──
    if competitors:
        for q in all_questions:
            if q.get("type") == "multi_select":
                text_lower = q.get("text", "").lower()
                if "heard of" in text_lower or "aided" in q.get("analysis_use", "").lower():
                    options = q.get("options", [])
                    options_lower = [o.lower() for o in options]
                    missing_brands = [c for c in competitors[:10]
                                      if c.lower() not in options_lower and c.lower() != brand_name.lower()]
                    if missing_brands:
                        # Add missing competitor brands
                        insert_pos = len(options) - 1 if options and options[-1].lower().startswith("none") else len(options)
                        for mb in missing_brands[:5]:
                            options.insert(insert_pos, mb)
                            insert_pos += 1
                        q["options"] = options
                        fixes.append(f"Added {len(missing_brands[:5])} missing competitors to aided awareness")
                    break

    # ── 7. Re-number question IDs sequentially ──
    q_counter = 1
    for section in survey.get("sections", []):
        for q in section.get("questions", []):
            if q.get("attention_check"):
                q["id"] = "QAC"
            else:
                q["id"] = f"Q{q_counter}"
                q_counter += 1

    # ── Report ──
    total_q = sum(len(s.get("questions", [])) for s in survey.get("sections", []))
    print(f"[survey_struct] {total_q} questions, {len(survey.get('sections', []))} sections")
    if issues:
        print(f"[survey_struct] Issues found: {'; '.join(issues)}")
    if fixes:
        print(f"[survey_struct] Auto-fixed: {'; '.join(fixes)}")
    else:
        print("[survey_struct] Structure OK — no fixes needed")

    return survey


def _validate_survey_quality(survey: dict, brand_name: str, category: str) -> dict:
    """LLM judge validates survey for bias, clarity, and logical flow.

    If issues are found, attempts to fix them via a second LLM call.
    """
    all_questions = []
    for section in survey.get("sections", []):
        all_questions.extend(section.get("questions", []))

    if len(all_questions) < 5:
        return survey

    # Build a summary for review
    q_summary = []
    for q in all_questions:
        q_id = q.get("id", "?")
        q_text = q.get("text", "")
        q_type = q.get("type", "unknown")
        options = q.get("options", [])
        q_summary.append(f"{q_id} ({q_type}): {q_text}")
        if options and q_type not in ("nps",):
            q_summary.append(f"  Options: {', '.join(str(o) for o in options[:10])}")

    try:
        from config import ANTHROPIC_API_KEY
        judge = Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = judge.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": (
                f"You are a survey methodology expert reviewing a questionnaire for '{brand_name}' ({category}).\n\n"
                f"Questions:\n" + "\n".join(q_summary) + "\n\n"
                "Check for:\n"
                "1. Leading or biased questions (cite Q number and what's biased)\n"
                "2. Double-barreled questions (asking two things at once)\n"
                "3. Overlapping or non-MECE answer options\n"
                "4. Jargon consumers wouldn't understand\n"
                "5. Questions where option order could bias results but randomize is missing\n"
                "6. Missing 'Other' or 'None of these' where needed\n\n"
                "If the survey is good, reply exactly: PASS\n"
                "If issues found, return a JSON array of fixes:\n"
                '[{"q_id": "Q5", "issue": "leading question", "fix": "Rewrite to: <neutral version>"}]\n'
                "Maximum 5 fixes. Only flag genuine issues."
            )}],
        )
        result = resp.content[0].text.strip()

        if result.upper().startswith("PASS"):
            print(f"[survey_judge] Quality check: PASS")
        else:
            print(f"[survey_judge] Quality check found issues")
            # Try to parse and apply fixes
            try:
                fix_start = result.find("[")
                fix_end = result.rfind("]") + 1
                if fix_start >= 0 and fix_end > fix_start:
                    fix_list = json.loads(result[fix_start:fix_end])
                    applied = 0
                    for fix in fix_list[:5]:
                        q_id = fix.get("q_id", "")
                        fix_text = fix.get("fix", "")
                        if not q_id or not fix_text:
                            continue
                        # Find and fix the question
                        for section in survey.get("sections", []):
                            for q in section.get("questions", []):
                                if q.get("id") == q_id:
                                    if "rewrite" in fix.get("issue", "").lower() or "leading" in fix.get("issue", "").lower():
                                        # Extract rewritten text if provided
                                        if ":" in fix_text:
                                            new_text = fix_text.split(":", 1)[1].strip().strip('"').strip("'")
                                            if len(new_text) > 10:
                                                q["text"] = new_text
                                                applied += 1
                                    elif "other" in fix.get("issue", "").lower():
                                        options = q.get("options", [])
                                        if options and not any("other" in o.lower() for o in options):
                                            q["options"].append("Other (please specify)")
                                            applied += 1
                                    print(f"[survey_judge] Fix {q_id}: {fix.get('issue', '')}")
                    if applied:
                        print(f"[survey_judge] Applied {applied} auto-fixes")
            except (json.JSONDecodeError, KeyError):
                print(f"[survey_judge] Could not parse fixes: {result[:200]}")
    except Exception as e:
        print(f"[survey_judge] Validation failed: {e}")

    return survey


def _fallback_survey(brand_name: str, category: str, competitors: list[str]) -> dict:
    """Generate a professional template survey when API is unavailable.

    Follows industry best practice:
    - Screener FIRST (qualify respondents)
    - Behavioral questions MIDDLE (unbiased by brand priming)
    - Brand evaluation with full funnel (unaided → aided → consideration → trial → NPS)
    - Demographics at END (reduce dropout)
    - Attention check in the middle
    - Randomization on all applicable questions
    """
    cat = category or "products"
    cat_singular = cat.rstrip("s") if cat.endswith("s") and not cat.endswith("ss") else cat
    brands = [brand_name] + competitors[:9]
    # Ensure "None of these" is always last
    brands_with_none = brands + ["None of these"]

    # ── Category-adaptive options ──────────────────────────────
    cat_lower = cat.lower()
    _channels = _get_category_channels(cat_lower)
    _triggers = _get_category_triggers(cat_lower)
    _factors = _get_category_factors(cat_lower)
    _spend = _get_category_spend(cat_lower)
    _price_range = _get_category_price_range(cat_lower)

    return {
        "survey_title": f"Consumer {cat.title()} Survey",
        "estimated_duration": "12-15 minutes",
        "target_sample_size": 200,
        "margin_of_error": "±7% at 95% CI",
        "target_audience": f"US adults 18+ who have purchased {cat} in the past 12 months",
        "screener_criteria": [
            f"Must have purchased {cat} in the past 12 months",
            "Must be 18+ years old",
            "Must reside in the United States",
        ],
        "sections": [
            # ── SECTION 1: SCREENER (qualify first, everything else later) ──
            {
                "name": "Screener",
                "purpose": "Qualify respondents — terminate those who don't purchase in this category",
                "questions": [
                    {"id": "Q1", "text": f"Have you purchased {cat} in the past 12 months?",
                     "type": "single_select", "required": True,
                     "options": ["Yes", "No"],
                     "skip_logic": "Terminate if 'No'",
                     "analysis_use": "Screener — disqualify non-buyers"},
                    {"id": "Q2", "text": "Are you 18 years of age or older?",
                     "type": "single_select", "required": True,
                     "options": ["Yes", "No"],
                     "skip_logic": "Terminate if 'No'",
                     "analysis_use": "Age qualification"},
                ],
            },
            # ── SECTION 2: CATEGORY BEHAVIOR (before brand priming) ──
            {
                "name": "Category Usage & Shopping Behavior",
                "purpose": "Establish behavioral baseline for segmentation — asked BEFORE brand questions to avoid priming",
                "questions": [
                    {"id": "Q3", "text": f"In the past 12 months, how often have you purchased {cat}?",
                     "type": "single_select", "required": True,
                     "options": ["Monthly or more", "Every 2-3 months", "2-3 times per year",
                                 "Once per year", "Less than once per year"],
                     "analysis_use": "Purchase frequency — primary segmentation variable & cross-tab"},
                    {"id": "Q4", "text": f"Approximately how much have you spent on {cat} in the past 12 months?",
                     "type": "single_select", "required": True,
                     "options": _spend,
                     "analysis_use": "Spend tier — segmentation variable (heavy/medium/light buyer)"},
                    {"id": "Q5", "text": f"Where have you purchased {cat}? (Select all that apply)",
                     "type": "multi_select", "required": True, "randomize": True,
                     "options": _channels + ["Other (please specify)"],
                     "analysis_use": "Channel mix donut chart — retail strategy insight"},
                    {"id": "Q6", "text": f"What primarily triggers you to purchase {cat_singular}? (Select your top 3)",
                     "type": "multi_select", "required": True, "max_select": 3, "randomize": True,
                     "options": _triggers + ["Other"],
                     "analysis_use": "Purchase trigger analysis — occasion-based segmentation"},
                    {"id": "Q7", "text": "Which social media platforms do you use at least once a week? (Select all that apply)",
                     "type": "multi_select", "required": True, "randomize": True,
                     "options": ["Instagram", "TikTok", "YouTube", "Facebook", "Pinterest",
                                 "X/Twitter", "Reddit", "Snapchat", "None of these"],
                     "analysis_use": "Social media profile for segment personas & media strategy"},
                ],
            },
            # ── SECTION 3: PURCHASE DRIVERS & BARRIERS ──
            {
                "name": "Purchase Drivers & Barriers",
                "purpose": "Identify what matters most, what creates friction, and what 'premium' means",
                "questions": [
                    {"id": "Q8", "text": f"Which factors are MOST important to you when choosing {cat_singular}? (Select your top 3)",
                     "type": "multi_select", "required": True, "max_select": 3, "randomize": True,
                     "options": _factors + ["Other (please specify)"],
                     "analysis_use": "Purchase driver ranking — hbar chart, primary strategic input"},
                    {"id": "Q9", "text": f"Which steps do you typically take before buying {cat_singular}? (Select all that apply)",
                     "type": "multi_select", "required": True, "randomize": True,
                     "options": ["Read online reviews", "Compare prices across retailers",
                                 "Visit brand websites", "Ask friends or family", "Watch YouTube reviews",
                                 "Check social media / TikTok", "Try in-store", "Read expert articles",
                                 "Other"],
                     "analysis_use": "Pre-purchase journey map — informs channel & content strategy"},
                    {"id": "Q10", "text": f"What challenges or frustrations have you experienced when shopping for {cat}?",
                     "type": "open_ended", "required": True,
                     "analysis_use": "Pain point verbatims — feeds challenges slide & segment pain tables"},
                    {"id": "Q11", "text": f"When it comes to {cat}, what does 'premium' mean to you? (Select all that apply)",
                     "type": "multi_select", "required": True, "randomize": True,
                     "options": ["Superior materials / ingredients", "Better design / aesthetics",
                                 "Longer lasting / more durable", "Better performance / functionality",
                                 "Trusted / well-known brand", "Ethical / sustainable practices",
                                 "Innovative features", "Other (please specify)"],
                     "analysis_use": "Premium perception — informs positioning strategy"},
                    # ── ATTENTION CHECK (disguised in middle of survey) ──
                    {"id": "QAC", "text": "For quality assurance, please select 'Somewhat agree' for this question.",
                     "type": "likert", "required": True, "attention_check": True,
                     "options": ["Strongly agree", "Somewhat agree", "Neutral",
                                 "Somewhat disagree", "Strongly disagree"],
                     "analysis_use": "Attention check — exclude respondents who fail"},
                    {"id": "Q12", "text": f"How much do you agree: 'I am willing to pay more for {cat_singular} "
                                          f"that clearly delivers on what matters most to me.'",
                     "type": "likert", "required": True,
                     "options": ["Strongly agree", "Somewhat agree", "Neutral",
                                 "Somewhat disagree", "Strongly disagree"],
                     "analysis_use": "Premium willingness — stacked bar by segment"},
                    {"id": "Q13", "text": f"What price range would you consider appropriate for a high-quality {cat_singular}?",
                     "type": "single_select", "required": True,
                     "options": _price_range,
                     "analysis_use": "Price expectation — pricing strategy input"},
                ],
            },
            # ── SECTION 4: BRAND EVALUATION — FULL FUNNEL ──
            {
                "name": "Brand Evaluation",
                "purpose": "Map competitive landscape with full brand funnel: unaided → aided → consideration → trial → favorite → NPS",
                "questions": [
                    # UNAIDED AWARENESS (free text, BEFORE showing any brand list)
                    {"id": "Q14", "text": f"When you think of {cat}, which brands come to mind first? "
                                          f"(Please list up to 5 brands)",
                     "type": "open_ended", "required": True,
                     "analysis_use": "Unaided brand awareness — the most valuable brand health metric. "
                                     "Measures true mental availability before any priming."},
                    # AIDED AWARENESS
                    {"id": "Q15", "text": f"Which of these {cat} brands have you HEARD OF? (Select all that apply)",
                     "type": "multi_select", "required": True, "randomize": True,
                     "options": brands_with_none,
                     "analysis_use": "Aided awareness — brand funnel top, competitive benchmarking"},
                    # CONSIDERATION
                    {"id": "Q16", "text": f"Which of these brands would you CONSIDER purchasing? (Select all that apply)",
                     "type": "multi_select", "required": True, "randomize": True,
                     "options": brands_with_none,
                     "skip_logic": "Show only brands selected in Q15",
                     "analysis_use": "Consideration — brand funnel stage 2, measures brand desirability"},
                    # TRIAL / PURCHASE
                    {"id": "Q17", "text": f"Which have you actually PURCHASED in the past 12 months? (Select all that apply)",
                     "type": "multi_select", "required": True, "randomize": True,
                     "options": brands_with_none,
                     "analysis_use": "Trial/purchase — brand funnel stage 3, conversion from consideration"},
                    # FAVORITE
                    {"id": "Q18", "text": f"Which is your single FAVORITE {cat_singular} brand, regardless of price?",
                     "type": "single_select", "required": True, "randomize": True,
                     "options": brands + ["No favorite / don't care about brand"],
                     "analysis_use": "Favorite brand — donut chart, ultimate brand preference metric"},
                    # NPS (proper 0-10 scale)
                    {"id": "Q19", "text": "How likely are you to recommend your favorite brand to a friend or colleague?",
                     "type": "nps", "required": True,
                     "options": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                     "scale_labels": {"0": "Not at all likely", "10": "Extremely likely"},
                     "analysis_use": "Net Promoter Score — NPS by brand, industry benchmark comparison"},
                    # BRAND ASSOCIATION MATRIX
                    {"id": "Q20", "text": "Which brand BEST fits each description?",
                     "type": "grid", "required": True, "randomize": True,
                     "options": brands,
                     "rows": ["Best overall quality", "Best value for money", "Most innovative",
                              "Most trustworthy", "Best design / aesthetics",
                              "Would recommend to a friend"],
                     "analysis_use": "Brand association matrix — competitive positioning map"},
                    # SWITCHING PROPENSITY
                    {"id": "Q21", "text": f"How open are you to trying a NEW brand for {cat}?",
                     "type": "single_select", "required": True,
                     "options": ["Very open — I love trying new brands",
                                 "Somewhat open — if it looks promising",
                                 "Neutral", "Somewhat loyal to my current brand(s)",
                                 "Very loyal — I stick with what works"],
                     "analysis_use": "Switching propensity — identifies brand-loyal vs explorer segments"},
                ],
            },
            # ── SECTION 5: LIFESTYLE & PSYCHOGRAPHICS ──
            {
                "name": "Lifestyle & Psychographics",
                "purpose": "Enrich segment profiles with lifestyle signals — style, music, automotive affinities",
                "questions": [
                    {"id": "Q22", "text": "Which best describes your personal style?",
                     "type": "single_select", "required": True, "randomize": True,
                     "options": ["Classic & timeless", "Trendy & fashion-forward",
                                 "Practical & functional", "Athletic & active",
                                 "Minimalist & understated", "Bold & expressive"],
                     "analysis_use": "Style identity — primary lifestyle segmentation variable"},
                    {"id": "Q23", "text": "Which are your favorite music genres? (Select up to 3)",
                     "type": "multi_select", "max_select": 3, "randomize": True,
                     "options": ["Pop", "R&B / Soul", "Hip-Hop / Rap", "Rock / Alternative",
                                 "Country", "Electronic / EDM", "Classical / Jazz", "Latin / Reggaeton",
                                 "Indie / Folk", "K-Pop"],
                     "analysis_use": "Music preference — segment lifestyle enrichment"},
                    {"id": "Q24", "text": "Which car brand best captures YOUR personal style?",
                     "type": "single_select", "randomize": True,
                     "options": ["Toyota / Honda", "BMW / Mercedes-Benz", "Tesla",
                                 "Jeep / Land Rover", "Subaru / Volvo", "Porsche / Lexus",
                                 "Ford / Chevy", "Other / don't drive"],
                     "analysis_use": "Automotive affinity — psychographic positioning signal"},
                    {"id": "Q25", "text": "Which values are MOST important to you personally? (Select your top 3)",
                     "type": "multi_select", "max_select": 3, "randomize": True,
                     "options": ["Quality over quantity", "Sustainability & environment",
                                 "Supporting small / local brands", "Getting the best deal",
                                 "Self-expression & individuality", "Health & wellness",
                                 "Convenience & efficiency", "Community & belonging"],
                     "analysis_use": "Personal values — psychographic segmentation & brand positioning"},
                ],
            },
            # ── SECTION 6: OPEN-ENDED VERBATIMS ──
            {
                "name": "Open-ended Feedback",
                "purpose": "Capture authentic voice-of-consumer for verbatim quotes in the final report",
                "questions": [
                    {"id": "Q26", "text": f"If you could change ONE thing about {cat} available today, what would it be?",
                     "type": "open_ended", "required": True,
                     "analysis_use": "Unmet needs — feeds 'white space' analysis and innovation opportunities"},
                    {"id": "Q27", "text": f"Is there anything else you'd like to share about your experience with {cat}?",
                     "type": "open_ended",
                     "analysis_use": "General verbatims — supplementary quotes for any report section"},
                ],
            },
            # ── SECTION 7: DEMOGRAPHICS (at END to reduce dropout) ──
            {
                "name": "Demographics",
                "purpose": "Cross-tabulation variables — placed at END per research best practice to minimize abandonment",
                "questions": [
                    {"id": "Q28", "text": "Which generation do you belong to?",
                     "type": "single_select", "required": True,
                     "options": ["Gen Z (born 1997-2012)", "Millennial (born 1981-1996)",
                                 "Gen X (born 1965-1980)", "Boomer (born 1946-1964)",
                                 "Silent / other (born before 1946)"],
                     "analysis_use": "Generation cross-tab — demographic donut chart"},
                    {"id": "Q29", "text": "What is your gender?",
                     "type": "single_select", "required": True,
                     "options": ["Male", "Female", "Non-binary / other", "Prefer not to say"],
                     "analysis_use": "Gender cross-tab — demographic split"},
                    {"id": "Q30", "text": "Which best describes your race/ethnicity? (Select all that apply)",
                     "type": "multi_select", "required": True,
                     "options": ["White / Caucasian", "Black / African American",
                                 "Hispanic / Latino", "Asian / Pacific Islander",
                                 "Native American / Alaska Native", "Other / Prefer not to say"],
                     "analysis_use": "Ethnicity cross-tab — demographic diversity breakdown"},
                    {"id": "Q31", "text": "What is your annual household income (before taxes)?",
                     "type": "single_select", "required": True,
                     "options": ["Under $25,000", "$25,000-$49,999", "$50,000-$74,999",
                                 "$75,000-$99,999", "$100,000-$149,999", "$150,000+",
                                 "Prefer not to say"],
                     "analysis_use": "Income cross-tab — demographic bar chart & segment correlation"},
                    {"id": "Q32", "text": "What is your current marital status?",
                     "type": "single_select", "required": True,
                     "options": ["Single / never married", "Married / domestic partnership",
                                 "Divorced / separated", "Widowed", "Prefer not to say"],
                     "analysis_use": "Marital status — demographic profile & segment enrichment"},
                ],
            },
        ],
        "cross_tab_variables": ["Q28 - Generation", "Q29 - Gender", "Q31 - Income",
                                "Q3 - Purchase Frequency", "Segment (derived)"],
        "segmentation_variables": ["Q3 - Purchase frequency", "Q4 - Annual spend",
                                   "Q8 - Top purchase drivers", "Q22 - Personal style",
                                   "Q25 - Personal values"],
        "analysis_outputs": [
            "Brand funnel chart (awareness → consideration → trial → regular → favorite)",
            "NPS by brand (Q19)",
            "Purchase driver ranking hbar (Q8)",
            "Channel mix donut (Q5)",
            "Premium perception stacked bar (Q11 + Q12)",
            "Brand association matrix heatmap (Q20)",
            "5 consumer segment personas (from Q3+Q4+Q8+Q22+Q25 clustering)",
        ],
        "notes": f"Survey designed for {brand_name} brand discovery. Unbranded format. "
                 f"Demographics at end per best practice. Full brand funnel with unaided awareness.",
    }


# ── Category-Adaptive Option Helpers ──────────────────────────

def _detect_price_tier(cat: str) -> str:
    """Detect approximate price tier: 'low' (<$50), 'mid' ($50-$200), 'high' (>$200)."""
    high_ticket = ["furniture", "appliance", "electronics", "mattress", "laptop", "computer",
                   "camera", "bicycle", "golf", "jewelry", "watch", "luggage"]
    low_ticket = ["snack", "candy", "drink", "beverage", "pet food", "cleaning",
                  "candle", "soap", "toothbrush", "socks"]
    for kw in high_ticket:
        if kw in cat:
            return "high"
    for kw in low_ticket:
        if kw in cat:
            return "low"
    return "mid"


def _get_category_channels(cat: str) -> list[str]:
    """Return purchase channel options appropriate for the category."""
    base = ["Amazon", "Brand website (DTC)", "Walmart", "Target"]
    if any(kw in cat for kw in ["outdoor", "sport", "fitness", "camping", "hiking"]):
        return base + ["REI / outdoor specialty", "Dick's Sporting Goods", "Costco / Sam's Club"]
    if any(kw in cat for kw in ["beauty", "cosmetic", "skincare", "makeup"]):
        return base + ["Sephora", "Ulta Beauty", "Drugstore (CVS/Walgreens)"]
    if any(kw in cat for kw in ["fashion", "apparel", "clothing", "shoes"]):
        return base + ["Nordstrom", "TJ Maxx / Marshalls", "Specialty boutiques"]
    if any(kw in cat for kw in ["electronics", "tech", "computer", "phone"]):
        return base + ["Best Buy", "Apple Store", "Manufacturer website"]
    if any(kw in cat for kw in ["food", "snack", "beverage", "drink", "pet"]):
        return base + ["Grocery store", "Costco / Sam's Club", "Chewy / specialty"]
    if any(kw in cat for kw in ["home", "furniture", "decor", "kitchen"]):
        return base + ["IKEA", "Wayfair", "HomeGoods / TJ Maxx"]
    # Generic fallback
    return base + ["Specialty retailers", "Costco / Sam's Club", "Other"]


def _get_category_triggers(cat: str) -> list[str]:
    """Return purchase trigger options appropriate for the category."""
    base = ["Old one broke / wore out", "Gift for someone", "Social media / influencer",
            "Friend recommendation", "Impulse buy"]
    if any(kw in cat for kw in ["fashion", "apparel", "clothing", "shoes"]):
        return base + ["Saw a design I loved", "Seasonal color drop", "Wanted a different size"]
    if any(kw in cat for kw in ["electronics", "tech", "phone", "computer"]):
        return base + ["New model / upgrade released", "Better features needed", "Sale / deal"]
    if any(kw in cat for kw in ["beauty", "cosmetic", "skincare"]):
        return base + ["Ran out of current product", "Saw results on someone else", "Seasonal skin change"]
    if any(kw in cat for kw in ["food", "snack", "beverage", "pet"]):
        return base + ["Ran out / needed restock", "Trying something new", "Sale / coupon"]
    # Generic (drinkware, home, etc.)
    return base + ["Wanted a different style/color", "Needed for a specific use", "Sale / deal"]


def _get_category_factors(cat: str, brand_name: str = "") -> list[str]:
    """Use LLM to generate category-specific purchase decision factors."""
    try:
        from anthropic import Anthropic
        from config import ANTHROPIC_API_KEY
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": (
                f"List exactly 8 purchase decision factors for the '{cat}' product category"
                f"{f' (brand: {brand_name})' if brand_name else ''}. "
                "These are the top reasons consumers choose one product over another in this category. "
                "Return ONLY a JSON array of 8 short strings (3-5 words each). "
                "Always include 'Price / value' and 'Brand reputation'. "
                "The other 6 must be specific to THIS category — not generic. "
                "Example for headphones: [\"Sound quality\", \"Noise cancellation\", ...]\n"
                "Return ONLY the JSON array, no other text."
            )}],
        )
        import json
        factors = json.loads(resp.content[0].text.strip())
        if isinstance(factors, list) and len(factors) >= 6:
            return factors[:8]
    except Exception as e:
        print(f"[survey] LLM factor generation failed: {e}")
    # Generic fallback
    return ["Product quality / durability", "Price / value", "Design / aesthetics",
            "Brand reputation", "Reviews / ratings", "Ease of use", "Innovation", "Sustainability"]


def _get_category_spend(cat: str) -> list[str]:
    """Return annual spend brackets appropriate for the category price tier."""
    tier = _detect_price_tier(cat)
    if tier == "high":
        return ["Under $100", "$100-$249", "$250-$499", "$500-$999", "$1,000+"]
    if tier == "low":
        return ["Under $20", "$20-$49", "$50-$99", "$100-$199", "$200+"]
    # Mid tier
    return ["Under $30", "$30-$59", "$60-$99", "$100-$149", "$150+"]


def _get_category_price_range(cat: str) -> list[str]:
    """Return per-item price range expectations for the category."""
    tier = _detect_price_tier(cat)
    if tier == "high":
        return ["Under $100", "$100-$249", "$250-$499", "$500-$999", "$1,000+"]
    if tier == "low":
        return ["Under $5", "$5-$14", "$15-$29", "$30-$49", "$50+"]
    # Mid tier
    return ["Under $25", "$25-$49", "$50-$99", "$100-$199", "$200+"]


# ── Qualtrics QSF Export ──────────────────────────────────────

def convert_to_qsf(survey: dict, project_name: str = "Survey") -> dict:
    """Convert DynaBridge survey JSON to Qualtrics Survey Format (QSF).

    QSF is the native import format for Qualtrics — the most widely used
    enterprise survey platform. This produces a valid .qsf file that can
    be imported via Qualtrics → Create Survey → Import from File.

    Supports: single_select, multi_select, likert, nps, open_ended, grid.
    Includes: skip logic, randomization, attention check flagging.
    """
    import uuid
    survey_id = f"SV_{uuid.uuid4().hex[:15]}"

    # QSF type mapping
    TYPE_MAP = {
        "single_select": "MC",    # Multiple Choice (single answer)
        "multi_select": "MC",     # Multiple Choice (multi answer)
        "likert": "MC",           # Rendered as MC with Likert selector
        "nps": "MC",              # NPS is a special MC scale
        "open_ended": "TE",       # Text Entry
        "grid": "Matrix",         # Matrix table
        "ranking": "RO",          # Rank Order
    }
    # Qualtrics selector sub-types
    SELECTOR_MAP = {
        "single_select": "SAVR",  # Single Answer Vertical
        "multi_select": "MAVR",   # Multi Answer Vertical
        "likert": "SAVR",
        "nps": "NPS",
        "open_ended": "SL",       # Single Line
        "grid": "Likert",
        "ranking": "DND",         # Drag and Drop
    }

    elements = []
    question_order = []
    q_counter = 0

    # Survey header block
    elements.append({
        "SurveyID": survey_id,
        "Element": "BL",
        "PrimaryAttribute": "Survey Blocks",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {},
    })

    # Build question elements
    block_questions = []
    for section in survey.get("sections", []):
        for q in section.get("questions", []):
            q_counter += 1
            q_id = q.get("id", f"Q{q_counter}")
            q_type = q.get("type", "single_select")
            q_text = q.get("text", "")
            options = q.get("options", [])

            qsf_type = TYPE_MAP.get(q_type, "MC")
            qsf_selector = SELECTOR_MAP.get(q_type, "SAVR")

            # Build choices
            choices = {}
            choice_order = []
            if q_type != "open_ended":
                for i, opt in enumerate(options, 1):
                    choices[str(i)] = {"Display": str(opt)}
                    choice_order.append(i)

            # Build question payload
            q_payload = {
                "QuestionID": f"QID{q_counter}",
                "QuestionText": q_text,
                "QuestionType": qsf_type,
                "Selector": qsf_selector,
                "DataExportTag": q_id,
                "QuestionDescription": q.get("analysis_use", ""),
                "Validation": {
                    "Settings": {
                        "ForceResponse": "ON" if q.get("required") else "OFF",
                    }
                },
            }

            if choices:
                q_payload["Choices"] = choices
                q_payload["ChoiceOrder"] = choice_order

            # Multi-select: set sub-selector
            if q_type == "multi_select":
                q_payload["SubSelector"] = "TX"
                max_sel = q.get("max_select")
                if max_sel:
                    q_payload["Validation"]["Settings"]["CustomValidation"] = {
                        "Type": "MaxChoices",
                        "MaxChoices": max_sel,
                    }

            # NPS: use 0-10 scale
            if q_type == "nps":
                q_payload["Selector"] = "NPS"
                q_payload["Choices"] = {str(i): {"Display": str(i)} for i in range(11)}
                q_payload["ChoiceOrder"] = list(range(11))

            # Grid/matrix
            if q_type == "grid":
                rows = q.get("rows", [])
                q_payload["Answers"] = {
                    str(i): {"Display": str(opt)} for i, opt in enumerate(options, 1)
                }
                q_payload["AnswerOrder"] = list(range(1, len(options) + 1))
                q_payload["Choices"] = {
                    str(i): {"Display": row} for i, row in enumerate(rows, 1)
                }
                q_payload["ChoiceOrder"] = list(range(1, len(rows) + 1))

            # Randomization
            if q.get("randomize") and q_type in ("single_select", "multi_select"):
                q_payload["Randomization"] = {
                    "Type": "All",
                    "Advanced": None,
                }
                # Anchor "None of these" / "Other" at bottom
                for i, opt in enumerate(options, 1):
                    opt_lower = str(opt).lower()
                    if any(kw in opt_lower for kw in ["none of", "other", "prefer not"]):
                        q_payload["Randomization"].setdefault("FixedOrder", [])
                        q_payload["Randomization"]["FixedOrder"].append(str(i))

            # Skip logic
            skip = q.get("skip_logic", "")
            if skip and "terminate" in skip.lower():
                q_payload["SkipLogic"] = {
                    "Type": "TerminateByChoice",
                    "Description": skip,
                }

            elements.append({
                "SurveyID": survey_id,
                "Element": "SQ",
                "PrimaryAttribute": f"QID{q_counter}",
                "SecondaryAttribute": q_text[:80],
                "TertiaryAttribute": None,
                "Payload": q_payload,
            })
            block_questions.append(f"QID{q_counter}")
            question_order.append(f"QID{q_counter}")

    # Update block element with question order
    elements[0]["Payload"] = {
        "1": {
            "Type": "Standard",
            "SubType": "",
            "Description": "Default Question Block",
            "BlockElements": [
                {"Type": "Question", "QuestionID": qid} for qid in block_questions
            ],
        }
    }

    # Flow element
    elements.append({
        "SurveyID": survey_id,
        "Element": "FL",
        "PrimaryAttribute": "Survey Flow",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "Type": "Root",
            "FlowID": "FL_1",
            "Flow": [
                {"Type": "Standard", "ID": "BL_1", "FlowID": "FL_2"},
            ],
        },
    })

    # Survey options
    elements.append({
        "SurveyID": survey_id,
        "Element": "SO",
        "PrimaryAttribute": "Survey Options",
        "SecondaryAttribute": None,
        "TertiaryAttribute": None,
        "Payload": {
            "Title": survey.get("survey_title", f"{project_name} Survey"),
            "SurveyExpiration": "None",
            "SurveyProtection": "PublicSurvey",
            "SurveyTermination": "DefaultMessage",
            "ProgressBarDisplay": "Text",
            "BackButton": "false",
            "SkinLibrary": "google",
            "SkinType": "MQ",
        },
    })

    return {
        "SurveyEntry": {
            "SurveyID": survey_id,
            "SurveyName": survey.get("survey_title", f"{project_name} Survey"),
            "SurveyDescription": survey.get("notes", ""),
            "SurveyStatus": "Inactive",
            "SurveyStartDate": "",
            "SurveyExpirationDate": "",
        },
        "SurveyElements": elements,
    }
