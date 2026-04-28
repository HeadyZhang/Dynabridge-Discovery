"""Survey response simulator module.

Takes a structured questionnaire from survey_designer.py and generates
realistic aggregated response distributions using Claude + web search
context. Produces integer percentage distributions for all close-ended
questions in 1-2 API calls.

The output feeds directly into native PowerPoint chart data via
ppt_generator's _build_respondent_profile, _build_social_media_slide, etc.
"""
import json
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, MODEL_SONNET

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SIMULATOR_SYSTEM = """You are a senior quantitative market research analyst at DynaBridge,
specializing in consumer brand strategy. You produce data that rivals McKinsey/Bain
consumer insight reports — grounded in real market dynamics, not generic distributions.

Given a consumer survey questionnaire, brand context, and category research, generate
realistic aggregated response distributions that represent what a real n=200 panel
survey would produce.

## Data Quality Rules
- All percentage distributions for a question must sum to 100 (within ±1 rounding)
- Use integer percentages (no decimals)
- Do NOT produce uniform or obviously round distributions — real survey data is skewed
  with clear leaders and long tails (e.g., 47/31/12/7/3, NOT 20/20/20/20/20)
- Every distribution must tell a story: reveal something non-obvious about the category
- MANDATORY: at least 2-3 data points per survey must be genuinely counter-intuitive —
  the kind of finding that makes a strategist say "wait, really?" Real data always has
  surprises. Without them, the deck feels synthetic and the client won't trust it

## Category-Grounded Realism
- Generation/age: reflect the category's ACTUAL buyer demographics — use the desktop
  research context to determine real demographic skews for this specific category
- Income: match US census proportions ADJUSTED for the category's price tier
- Social media: reflect current US platform penetration rates adjusted for category
  buyer demographics (TikTok/Instagram dominant for younger DTC, Facebook for mass)
- Purchase drivers: ground in REAL category concerns from the research context — not
  generic factors. Reference specific product attributes, competitor pain points, and
  category-specific language consumers actually use
- Brand metrics: reflect ACTUAL market share, brand recall, and competitive dynamics
  from the research context. Smaller brands should show lower unaided awareness.
- Shopping behavior: reflect ACTUAL retail landscape (Amazon vs DTC vs big-box
  channel share should match category reality — e.g., Amazon dominates commodity
  categories, DTC is higher for premium brands)
- For categories with occupational relevance (workwear, professional tools, etc.),
  generate occupation/work detail distributions when relevant

## Verbatim Quality
- Verbatims must sound like REAL people typing quickly into a survey box — NOT
  like a copywriter crafting marketing insights. Think messy, honest, human.
- Mix lengths aggressively: some are 4-6 words ("too many choices honestly"),
  some are 2 sentences with specific personal stories
- Include natural imperfections: lowercase starts, missing apostrophes (dont, cant,
  its), "lol", "tbh", "like", run-on sentences, vague quantifiers ("a few weeks")
- Reference real competitor brands by name casually (not formally) — the way consumers
  actually say them in everyday conversation
- Include specific personal details relevant to how they USE the product in daily life
- Some should reveal hidden insights (collection addiction, TikTok impulse buying,
  trust issues with reviews) while sounding offhand, not analytical
- Avoid polished sentences that read like consultant-written pain points
- Generate at least 26 quotes for each open-ended question
"""

SIMULATOR_PROMPT = """Generate realistic survey response distributions for ALL close-ended questions.

Brand: {brand_name}
Category: {category}
Sample Size: {sample_size}

## Category & Market Context
{context}

## Questionnaire
{questionnaire_json}

For each close-ended question (single_select, multi_select, likert, grid), produce the
aggregated percentage distribution. For open_ended questions, generate verbatim quotes
in the "verbatim_responses" section instead.

Return ONLY a JSON object:
{{
  "sample_size": {sample_size},
  "question_data": {{
    "Q1": {{
      "question_text": "Original question text",
      "section": "demographics",
      "chart_type": "vbar",
      "chart_title": "CONCISE ALL-CAPS CHART TITLE",
      "categories": ["Option A", "Option B", "Option C"],
      "values": [45, 35, 20]
    }},
    "Q2": {{ ... }}
  }},
  "demographics": {{
    "generation": {{
      "categories": ["Gen Z (1997-2007)", "Millennial (1981-1996)", "Gen X (1965-1980)", "Boomer (1946-1964)"],
      "values": [15, 47, 31, 7]
    }},
    "gender": {{
      "male_pct": 35,
      "female_pct": 65
    }},
    "ethnicity": {{
      "categories": ["White/Caucasian", "Black/African American", "Hispanic/Latino", "Asian/Pacific Islander", "Other"],
      "values": [55, 20, 15, 7, 3]
    }},
    "income": {{
      "categories": ["Under $25k", "$25k-$50k", "$50k-$75k", "$75k-$100k", "$100k-$150k", "$150k+"],
      "values": [8, 18, 24, 22, 18, 10]
    }},
    "marital": {{
      "married_pct": 48,
      "single_pct": 38,
      "divorced_pct": 14
    }},
    "social_media": {{
      "categories": ["Instagram", "YouTube", "TikTok", "Facebook", "Pinterest", "X/Twitter", "Reddit"],
      "values": [72, 68, 55, 48, 35, 25, 20]
    }}
  }},
  "category_specific": [
    {{
      "title": "OCCUPATION AND WORK DETAILS",
      "slide_type": "occupation",
      "categories": ["Category 1", "Category 2"],
      "values": [30, 25]
    }}
  ],
  "verbatim_responses": {{
    "shopping_challenges": {{
      "question_text": "What challenges or issues have you experienced when shopping for [category]?",
      "chart_title": "CHALLENGES WHEN PURCHASING [CATEGORY]",
      "section": "shopping",
      "quotes": [
        "Realistic consumer quote about pain point 1",
        "Realistic consumer quote about pain point 2"
      ]
    }}
  }}
}}

IMPORTANT:
- "demographics" must always include generation, gender, ethnicity, income, marital, social_media
- "category_specific" is optional — include ONLY if the category warrants occupation/role charts
  (e.g., workwear → trade occupations, professional tools → industry roles)
- Multi-select question values can sum to >100 (each option is independent)
- Single-select question values must sum to 100
- Values are integers representing percentages
- INSIGHT MOMENTS: Include 2-3 counter-intuitive or surprising data points that would
  make a strategist pause. Real survey data ALWAYS has surprises. Examples:
  * A "value" segment that actually spends MORE than the "premium" segment (they buy more often)
  * The youngest demographic preferring a traditional channel over digital
  * The #1 purchase driver being something unexpected (not "quality" or "price")
  * A low-awareness brand scoring highest on satisfaction (hidden gem signal)
  These surprises must be PLAUSIBLE and grounded in category logic — not random.
  They are what separates a generic report from genuine strategic insight.
- Each question_data entry MUST include:
  * "section": one of "demographics", "shopping", "drivers", "brand", "lifestyle"
    (match the questionnaire section the question belongs to)
  * "chart_type": recommended chart type — "hbar", "vbar", "donut", "stacked", "dual"
    (hbar for ranked lists/multi-select, vbar for categories, donut for single-select with few options)
  * "chart_title": concise ALL-CAPS title for the slide (max 55 chars)
- "verbatim_responses" must include at least one entry with 15-20 realistic consumer quotes
  for the category's main pain-point/challenge open-ended question. Quotes should sound like
  real survey respondents (varied length, casual tone, specific details, some typos/grammar).
"""


async def simulate_survey_responses(
    questionnaire: dict,
    brand_name: str,
    category: str = "",
    brand_context: str = "",
    sample_size: int = 200,
) -> dict:
    """Generate realistic aggregated survey response distributions.

    Args:
        questionnaire: Structured survey from design_survey()
        brand_name: Brand name
        category: Product category
        brand_context: Phase 1-2 analysis findings for grounding
        sample_size: Target sample size

    Returns:
        Simulated response distributions keyed by question ID
    """
    if not client:
        return _fallback_responses(questionnaire, brand_name, category, sample_size)

    # Trim questionnaire to just questions (remove verbose fields)
    q_slim = {
        "sections": [
            {
                "name": s.get("name", ""),
                "questions": [
                    {
                        "id": q["id"],
                        "text": q["text"],
                        "type": q["type"],
                        "options": q.get("options", []),
                        "max_select": q.get("max_select"),
                    }
                    for q in s.get("questions", [])
                    # Include open_ended so simulator can generate verbatim quotes
                ],
            }
            for s in questionnaire.get("sections", [])
        ]
    }

    prompt = SIMULATOR_PROMPT.format(
        brand_name=brand_name,
        category=category or "consumer products",
        sample_size=sample_size,
        context=brand_context[:4000] if brand_context else "No prior analysis available.",
        questionnaire_json=json.dumps(q_slim, indent=2)[:6000],
    )

    try:
        response = client.messages.create(
            model=MODEL_SONNET,
            max_tokens=8000,
            system=SIMULATOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            result["sample_size"] = sample_size
            return result
    except Exception:
        pass

    return _fallback_responses(questionnaire, brand_name, category, sample_size)


def _fallback_responses(questionnaire: dict, brand_name: str, category: str,
                        sample_size: int) -> dict:
    """Generate basic response distributions when API is unavailable."""
    return {
        "sample_size": sample_size,
        "question_data": {},
        "demographics": {
            "generation": {
                "categories": [
                    "Gen Z (1997-2007)",
                    "Millennial (1981-1996)",
                    "Gen X (1965-1980)",
                    "Boomer (1946-1964)",
                ],
                "values": [18, 42, 28, 12],
            },
            "gender": {"male_pct": 35, "female_pct": 65},
            "ethnicity": {
                "categories": [
                    "White/Caucasian",
                    "Black/African American",
                    "Hispanic/Latino",
                    "Asian/Pacific Islander",
                    "Other",
                ],
                "values": [52, 18, 17, 8, 5],
            },
            "income": {
                "categories": [
                    "Under $25k",
                    "$25k-$50k",
                    "$50k-$75k",
                    "$75k-$100k",
                    "$100k-$150k",
                    "$150k+",
                ],
                "values": [10, 20, 25, 20, 15, 10],
            },
            "marital": {"married_pct": 48, "single_pct": 38, "divorced_pct": 14},
            "social_media": {
                "categories": [
                    "Instagram",
                    "YouTube",
                    "TikTok",
                    "Facebook",
                    "Pinterest",
                    "X/Twitter",
                    "Reddit",
                ],
                "values": [72, 68, 55, 48, 35, 25, 20],
            },
        },
        "category_specific": [],
    }
