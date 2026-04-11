"""AI Analysis module using Claude API.

Takes scraped website data and parsed documents, produces structured
brand analysis JSON for PPT generation.
"""
import json
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

SYSTEM_PROMPT = """You are a senior brand strategist at DynaBridge, a US-based brand consulting firm
specializing in helping Chinese enterprises build global brands.

Your task is to analyze a brand and produce a structured Brand Discovery report following
DynaBridge's methodology: Capabilities → Competition → Consumer.

You must output valid JSON matching the exact schema provided. Be insightful, evidence-based,
and strategic. Write in a professional consulting tone."""

ANALYSIS_PROMPT = """Analyze this brand and produce a complete Brand Discovery report.

## Brand Information
- Brand Name: {brand_name}
- Website URL: {brand_url}
- Language: {language}

## Website Content
{scrape_data}

## Uploaded Documents
{document_data}

## Competitors
{competitors}

## Required Output Schema

Return a JSON object with this exact structure:

{{
  "brand_name": "{brand_name}",
  "date": "MONTH YEAR",

  "capabilities": {{
    "execution_summary": {{
      "title": "HOW [BRAND] WAS BUILT: ...",
      "bullets": ["point 1", "point 2", "point 3"],
      "insight": "One-sentence strategic insight in blue"
    }},
    "product_offer": {{
      "title": "A FUNCTIONAL, FEATURE-LED...",
      "bullets": ["point 1", "point 2", "point 3"],
      "insight": "..."
    }},
    "pricing_position": {{
      "title": "PRICE-PERFORMANCE DEFINES...",
      "bullets": ["point 1", "point 2", "point 3"],
      "insight": "..."
    }},
    "channel_analysis": {{
      "title": "...",
      "bullets": ["point 1", "point 2", "point 3"],
      "insight": "..."
    }},
    "brand_challenges": [
      {{
        "title": "...",
        "bullets": ["point 1", "point 2", "point 3"],
        "insight": "..."
      }}
    ],
    "capabilities_summary": "2-3 sentence summary of brand capabilities"
  }},

  "competition": {{
    "market_overview": {{
      "title": "A MATURE, HIGHLY DEFINED ... MARKET",
      "competitor_names": ["Brand A", "Brand B", ...],
      "insight": "..."
    }},
    "focused_competitors": ["Brand A", "Brand B", ...],
    "competitor_analyses": [
      {{
        "name": "Competitor Name",
        "positioning": [
          {{"label": "Role descriptor", "detail": "explanation"}},
          {{"label": "...", "detail": "..."}},
          {{"label": "...", "detail": "..."}}
        ],
        "key_learnings": [
          {{"label": "Learning title", "detail": "explanation"}},
          {{"label": "...", "detail": "..."}},
          {{"label": "...", "detail": "..."}}
        ]
      }}
    ],
    "competition_summary": "2-3 sentence summary of the competitive landscape and white space opportunity",
    "competitive_summary": {{
      "market_roles": ["Role 1", "Role 2", ...],
      "white_space": "Where opportunities exist",
      "category_norms": ["Norm 1", "Norm 2", ...]
    }}
  }},

  "consumer": {{
    "overview": "Brief consumer landscape summary",
    "research_approach": [
      {{"label": "Format", "detail": "e.g. Online survey"}},
      {{"label": "Sample", "detail": "e.g. N=500"}},
      {{"label": "Participants", "detail": "Description"}},
      {{"label": "Analysis", "detail": "Method"}},
      {{"label": "Timing", "detail": "When"}}
    ],
    "charts": [
      {{
        "chart_type": "dual",
        "title": "CHART TITLE (ALL CAPS)",
        "subtitle": "Optional italic context line",
        "left_title": "Question for left chart",
        "left_categories": ["Cat1", "Cat2"],
        "left_values": [50, 50],
        "left_type": "donut",
        "right_title": "Question for right chart",
        "right_categories": ["Cat1", "Cat2"],
        "right_values": [60, 40],
        "right_type": "hbar"
      }},
      {{
        "chart_type": "hbar",
        "title": "CHART TITLE",
        "question": "Full question text",
        "categories": ["Cat1", "Cat2"],
        "values": [50, 30]
      }}
    ],
    "segments": [
      {{
        "name": "Segment Name",
        "description": "Who they are",
        "needs": ["Need 1", "Need 2"],
        "behaviors": ["Behavior 1", "Behavior 2"]
      }}
    ],
    "key_insights": [
      {{
        "title": "INSIGHT HEADLINE",
        "bullets": ["point 1", "point 2", "point 3"],
        "insight": "..."
      }}
    ]
  }},

  "next_steps": [
    "Recommended action 1",
    "Recommended action 2",
    "Recommended action 3"
  ]
}}

Be thorough, specific, and evidence-based. Reference actual data from the website and documents.
If the language is "zh" or "en+zh", provide Chinese translations for all text fields as a parallel
"_zh" suffixed field (e.g., "title" and "title_zh").
"""


async def analyze_brand(
    brand_name: str,
    brand_url: str,
    scrape_data: dict,
    document_data: list[dict],
    competitors: list[str],
    language: str = "en",
) -> dict:
    """Run Claude AI analysis on brand data and return structured JSON."""

    if not client:
        return _mock_analysis(brand_name)

    # Format inputs for the prompt
    scrape_text = ""
    if scrape_data.get("pages"):
        for page in scrape_data["pages"]:
            scrape_text += f"\n### {page['title']} ({page['url']})\n{page['text'][:2000]}\n"

    doc_text = ""
    for doc in document_data:
        doc_text += f"\n### {doc['filename']}\n{doc['text'][:3000]}\n"

    comp_text = ", ".join(competitors) if competitors else "Not specified — identify key competitors"

    prompt = ANALYSIS_PROMPT.format(
        brand_name=brand_name,
        brand_url=brand_url,
        language=language,
        scrape_data=scrape_text or "No website data available",
        document_data=doc_text or "No documents uploaded",
        competitors=comp_text,
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    # Extract JSON from response
    text = response.content[0].text
    try:
        # Try to find JSON in the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except json.JSONDecodeError:
        pass

    return {"raw_analysis": text, "brand_name": brand_name}


def _mock_analysis(brand_name: str) -> dict:
    """Return a mock analysis for development/testing."""
    return {
        "brand_name": brand_name,
        "date": "APRIL 2026",
        "capabilities": {
            "execution_summary": {
                "title": f"HOW {brand_name.upper()} WAS BUILT: EXECUTION FIRST",
                "bullets": [
                    f"{brand_name} prioritized getting the product right, pricing competitively, and moving quickly to market.",
                    "Early decisions focused on speed, operational efficiency, and reducing risk rather than building a formal brand strategy.",
                    "This execution-first mindset allowed the business to enter a crowded category and scale rapidly.",
                ],
                "insight": f"{brand_name}'s early success was driven by strong execution choices rather than brand-led planning.",
            },
            "product_offer": {
                "title": "A FUNCTIONAL, FEATURE-LED, VALUE-FOCUSED OFFER",
                "bullets": [
                    f"Across channels, {brand_name} emphasizes comfort, fit, features, and affordability over emotional brand storytelling.",
                    "Product pages clearly communicate stretch, pockets, fabric performance, and everyday usability.",
                    "The offer is easy to understand and compare, but largely follows category norms.",
                ],
                "insight": f"Today, {brand_name} presents itself as a practical, feature-driven solution more than as a clearly differentiated brand.",
            },
            "pricing_position": {
                "title": f"PRICE-PERFORMANCE DEFINES {brand_name.upper()}'S CURRENT POSITION",
                "bullets": [
                    f"{brand_name} is positioned below premium lifestyle brands while offering similar functional benefits.",
                    "Messaging reinforces value and practicality rather than exclusivity or status.",
                    "This balance supports trial and volume but limits how premium the brand can feel today.",
                ],
                "insight": f"{brand_name}'s role in the market is defined by strong value and price-performance rather than by brand-led premium positioning.",
            },
            "channel_analysis": {
                "title": "CHANNEL ANALYSIS",
                "bullets": [
                    "Primary distribution through e-commerce platforms.",
                    "Brand website serves as a secondary channel.",
                    "Social media presence supports awareness but not direct conversion.",
                ],
                "insight": "E-commerce has been a powerful engine for growth and customer trust.",
            },
            "brand_challenges": [
                {
                    "title": "BRAND STRUCTURE NEEDS CLARITY",
                    "bullets": [
                        "Current brand architecture lacks clear differentiation.",
                        "Multiple product lines may confuse the market position.",
                        "A clearer brand hierarchy would strengthen market presence.",
                    ],
                    "insight": "The brand structure creates both opportunity and risk for future growth.",
                }
            ],
            "capabilities_summary": f"{brand_name} is an execution-driven brand with competitive products and strong market performance, now facing the need to clarify its naming and brand structure to support long-term growth.",
        },
        "competition": {
            "market_overview": {
                "title": "A MATURE, HIGHLY DEFINED MARKET",
                "competitor_names": ["Competitor A", "Competitor B", "Competitor C"],
                "insight": "These brands set clear standards for how the category should look, feel, and perform.",
            },
            "focused_competitors": ["Competitor A", "Competitor B"],
            "competitor_analyses": [
                {
                    "name": "Competitor A",
                    "positioning": [
                        {"label": "Market leader", "detail": "Established brand with deep category credibility."},
                        {"label": "Professional reliability", "detail": "Emphasizes consistency and quality."},
                        {"label": "Broad line", "detail": "Multiple sub-lines for different needs."},
                    ],
                    "key_learnings": [
                        {"label": "Authority builds confidence", "detail": "Longevity and focus signal trust."},
                        {"label": "Consistency drives loyalty", "detail": "Reliable quality supports repeat purchase."},
                        {"label": "Complexity can dilute clarity", "detail": "Wide portfolios can weaken brand idea."},
                    ],
                }
            ],
            "competition_summary": "The market is defined by a few clear roles — premium lifestyle, professional authority, and value play. The white space opportunity lies at the intersection of quality and accessibility, where no single brand has established clear ownership.",
            "competitive_summary": {
                "market_roles": ["Value Play", "Premium Lifestyle", "Professional Authority"],
                "white_space": "Opportunity exists in the intersection of quality and accessibility.",
                "category_norms": ["Performance claims", "Professional endorsement", "Value messaging"],
            },
        },
        "consumer": {
            "overview": "The target consumer values quality and practicality.",
            "segments": [
                {
                    "name": "Practical Professionals",
                    "description": "Value function and durability above brand status.",
                    "needs": ["Reliable quality", "Fair pricing"],
                    "behaviors": ["Research online before buying", "Read reviews carefully"],
                }
            ],
            "key_insights": [
                {
                    "title": "CONSUMER INSIGHT HEADLINE",
                    "bullets": [
                        "Key finding about consumer behavior.",
                        "Evidence from market data.",
                        "Implication for brand strategy.",
                    ],
                    "insight": "Understanding these patterns is critical for positioning decisions.",
                }
            ],
        },
        "next_steps": [
            "Define clear brand architecture and naming strategy.",
            "Develop positioning that balances value with aspiration.",
            "Build evidence-based consumer segmentation for targeting.",
        ],
    }
