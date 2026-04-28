"""AI Analysis module using Claude API.

Supports phase-based analysis:
  - brand_reality: Capabilities section only (Phase 1)
  - market_structure: Capabilities + Competition (Phase 1+2)
  - full: Everything (Phase 1+2+3+4)
"""
import asyncio
import json
import time
from anthropic import Anthropic, RateLimitError, APIStatusError, APIConnectionError, APITimeoutError
from config import ANTHROPIC_API_KEY, MODEL_OPUS

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# ── System Prompts ────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior brand strategist at DynaBridge, a US-based brand consulting firm
specializing in helping Chinese enterprises build global brands in Western markets.

You follow DynaBridge's Discovery methodology — a 3-step process:
- Step 1: Capabilities — assess what the brand has built, how it executes, and where gaps exist
- Step 2: Competition — map the competitive landscape, identify market roles, and find white space
- Step 3: Consumer — understand who buys, why, what segments exist, and what unmet needs to target

## Writing Style (match this exactly)

SLIDE TITLES: Must be ALL CAPS, descriptive, and opinionated — they state a finding, not a topic.
  GOOD: "HOW [BRAND] WAS BUILT: EXECUTION FIRST"
  GOOD: "A FOUNDER-LED, AMAZON-NATIVE BRAND"
  GOOD: "QUALITY IS A SYSTEM, NOT A CLAIM"
  GOOD: "BUILT TO WIN WHERE OTHERS UNDER-INVEST"
  GOOD: "STRONG PRODUCT FOUNDATION, UNCLEAR BRAND FOCUS"
  GOOD: "THE MEANING BEHIND THE NAME"
  GOOD: "THE NEXT STEP IS A CLEAR, RESEARCH-LED DECISION"
  BAD: "PRODUCT ANALYSIS" or "PRICING OVERVIEW" (too generic, too safe)

There are TWO content formats — match the right one to each field:

### Format A — CONTENT SLIDES (capabilities, competition, challenges)
BULLETS: 3 bullets per slide. Each bullet is a FULL PARAGRAPH: 2-4 sentences, rich with specific
  evidence from the data (prices, percentages, product names, channel details, review quotes,
  revenue figures, hero product performance). Cite the category's actual attributes — not
  generic placeholders.
  GOOD: "[Brand] prioritized getting the product right, pricing competitively, and moving fast on Amazon. The founder-led approach focused on product iteration and review velocity rather than brand definition. This built strong initial traction but deferred the harder work of establishing a clear brand identity." (3 sentences)
  BAD: "[Brand] prioritized product quality and pricing." (too thin — no evidence, no depth)

### Format B — COMPETITOR POSITIONING & KEY LEARNINGS
Each statement uses BOLD-LABEL: DETAIL format. The label is a 3-5 word theme, the detail is ONE concise sentence.
HARD LIMIT: each "label: detail" string must be ≤110 characters total. Longer text WILL be cut off mid-sentence.
  GOOD: "Design creates permission: Minimalist form signals quality in a cluttered category." (82 chars ✓)
  GOOD: "Longevity is the promise: Durability and repairability anchor trust." (68 chars ✓)
  GOOD: "Premium invites challenge: High pricing creates opportunity for value challengers." (81 chars ✓)
  BAD: "Design-led steam specialist: Positions Neat as a minimalist, premium alternative to bulky, disposable appliances." (113 chars ✗ — TOO LONG)

### Format C — CHART SLIDES & INSIGHT BARS
Short text for chart titles and insight bars. MAX 80 characters, 1 sentence.
  GOOD: "[Brand] has built a product — but not yet a brand." (51 chars)
  GOOD: "They buy with evidence, not emotion — performance is the currency." (65 chars)
  BAD: "The brand has both strengths and weaknesses." (too generic)

SUMMARY PARAGRAPHS: 3-5 sentences, MAX 350 characters total. Write as connected prose, not bullets.
  Start with what the brand does well, then what it needs to fix, then what must happen next.
  End with a forward-looking statement that sets up the next phase of work.

## CRITICAL: Character Limits — STRICTLY ENFORCED (text boxes are fixed-size, overflow is hidden)
- Slide title: max 55 characters
- Insight text (blue bar): max 80 characters
- Content bullet (Format A): 2-4 sentences, max 350 characters per bullet
- Competitor label:detail (Format B): max 110 characters TOTAL (label + ": " + detail)
- Summary paragraph: max 350 characters
COUNT YOUR CHARACTERS. Any text exceeding these limits will be truncated and look broken.

## Analysis Standards
- Evidence-based: cite specific data points, prices, phrases from the provided content
- Strategically honest: surface real weaknesses alongside strengths
- Implication-driven: every observation should point to a "so what"
- Category-agnostic: this framework applies to ANY product category. Derive all terminology,
  attributes, and insights from the actual data provided — never reuse example language as templates.
  Every category has its own vocabulary — discover it from the data, never borrow from other categories.
- EVIDENCE HIERARCHY — always distinguish between:
  1. OBSERVED: directly from desktop research, reviews, e-commerce data (strongest)
  2. INFERRED: logical deduction from observed signals (e.g., price point → income bracket)
  3. INDUSTRY KNOWLEDGE: general category/market patterns from your training data (weakest)
  When making claims, prioritize observed evidence. Use industry knowledge only to fill gaps
  and frame the analysis — never to fabricate specific numbers, market share, or revenue data.
- GRACEFUL DEGRADATION: when data is thin for a section, write a shorter but confident
  assessment based on what IS available. A tight 2-sentence insight beats a padded paragraph
  of speculation. Never invent specific statistics (e.g., "15% market share") without source data.
- Authoritative tone: state findings as conclusions, not possibilities. Never use hedge words
  like "likely", "potentially", "could", "may", "seems to", "appears to", or "tends to".
  Write as a senior strategist presenting to a CEO — confident, evidence-backed, decisive.
  Being authoritative does NOT mean fabricating data — it means having a clear point of view
  grounded in whatever evidence exists.
- When desktop research provides brand vision, brand culture, revenue data, or hero products,
  weave these into your analysis as primary evidence. These are high-value signals that
  distinguish a thorough analysis from a superficial one.

## FEW-SHOT EXAMPLES — match this quality, density, and tone exactly:

EXAMPLE 1 (Capabilities — Format A):
{
  "title": "HOW [BRAND] WAS BUILT: EXECUTION FIRST",
  "bullets": [
    "[Brand] prioritized getting the product right, pricing competitively, and moving fast on Amazon. The founder-led approach focused on product iteration and review velocity rather than brand definition.",
    "Amazon-first launch built strong initial traction through product quality and competitive pricing. Early success was driven by execution discipline, not brand storytelling or emotional positioning.",
    "[Brand]'s early success was built on product and channel execution — but execution alone won't sustain growth. Without brand definition, the path from product to brand remains unclear."
  ],
  "insight": "Execution-driven success — but execution alone won't sustain growth.",
  "has_image": true
}

EXAMPLE 2 (Capabilities — Format A):
{
  "title": "A FUNCTIONAL, FEATURE-LED, VALUE-FOCUSED OFFER",
  "bullets": [
    "Across channels, [Brand] emphasizes functional benefits and affordability over emotional storytelling or identity. Product pages communicate specs, features, and performance — functional language that invites direct comparison.",
    "Product fundamentals are competitive for [Brand]'s price tier. Key features match or exceed competitors at similar price points, but the brand lacks a signature innovation or material story to anchor premium perception.",
    "Easy to compare but follows category norms — [Brand] presents as a practical solution rather than a differentiated brand. Without a clear reason to choose [Brand] specifically, customers default to price and availability."
  ],
  "insight": "[Brand] presents as a practical solution, not a differentiated brand.",
  "has_image": true
}

EXAMPLE 3 (Competition — Format B, for POSITIONING field):
{
  "name": "Dupray",
  "banner_description": "Design-led steam specialist positioning Neat as a minimalist premium alternative",
  "positioning": [
    {"label": "Design-led steam specialist", "detail": "Positions Neat as a minimalist, premium alternative to bulky, disposable appliances. Clean aesthetics signal quality in a cluttered category."},
    {"label": "Buy-it-for-life mindset", "detail": "Emphasizes durability, lifetime boiler warranties, and long-term ownership over replacement. Repairability is part of the brand promise."},
    {"label": "Chemical-free authority", "detail": "Frames high-temperature steam as a safer, healthier way to sanitize the home. Health messaging attracts safety-conscious families."}
  ],
  "key_learnings": [
    {"label": "Design creates permission", "detail": "Minimalist form signals quality and seriousness in a cluttered category. Visual restraint earns premium consideration."},
    {"label": "Longevity is the promise", "detail": "Durability and repairability anchor trust more than feature innovation. Lifetime warranties substitute for brand history."},
    {"label": "Premium invites challenge", "detail": "High pricing creates opportunity for brands that can match outcomes with better value. The $300+ tier is vulnerable to credible challengers."}
  ]
}

EXAMPLE 4 (Segment — Consumer narrative):
{
  "name": "Performance Seekers",
  "tagline": "I need gear that performs when it matters — reliability and quality are non-negotiable",
  "size_pct": 27,
  "narrative": "Meet the Performance Seeker: Picture someone who tests products to their limits in real daily use. They've tried the alternatives and know exactly what fails first. This segment represents 27% of the market and skews toward experienced users in demanding contexts. They spend the most annually and set the performance standard for the entire category. For them, 'premium' means evidence of superior materials and construction — proof, not marketing. They don't chase trends — they chase proof.",
  "demographics": {
    "primary_role": "Active professional in demanding daily routines",
    "age_skew": "52% Millennial, 29% Gen X",
    "income": "51% upper-middle income ($75K-$149K)",
    "gender_split": "55% female, 45% male"
  },
  "what_premium_means": "Evidence of superior materials (42%) and build quality (38%) — proof, not marketing"
}

EXAMPLE 5 (De-prioritized segment reasoning):
{
  "name": "Smart Shopper",
  "size_pct": 31,
  "reason": "Promotion-driven and more price-sensitive with lower warranty emphasis. Competing here risks compressing margins and weakening premium positioning."
}

Notice: content bullets are FULL PARAGRAPHS with evidence. Competitor labels are bold themes.
Segment narratives are vivid character stories. De-prioritization states strategic risk.
Your output must match this caliber. Generic or vague analysis is unacceptable.

You must output ONLY valid JSON. No markdown, no commentary before or after."""


# ── Brand Reality Prompt (Phase 1) ────────────────────────────

BRAND_REALITY_PROMPT = """Analyze this brand's current capabilities and produce a Brand Reality assessment.

## Brand Information
- Brand Name: {brand_name}
- Website URL: {brand_url}
- Language: {language}

## Website Content (scraped)
{scrape_data}

## Uploaded Documents
{document_data}

## E-Commerce Data
{ecommerce_data}

## Customer Reviews
{review_data}

## Analysis Instructions

Assess the brand across these 7 dimensions. For each, write exactly 3 bullets.
Each bullet MUST be a FULL PARAGRAPH: 2-4 sentences, rich with specific evidence
from the data (prices, percentages, product names, channel details, review quotes).
Then write one "insight" sentence — a provocative strategic reframe, not a summary.

Think of each bullet as a mini-argument: [OBSERVATION with evidence] → [IMPLICATION for the brand].

### 1. Execution Summary
How was this brand built? Was it product-first, channel-first, or brand-first?
What execution choices defined its trajectory? Infer the founding logic from
website messaging, product range, pricing, channel presence. If revenue data,
founding story, or hero products are available from desktop research, weave them in
as evidence — these are gold for establishing the brand's growth arc.

### 2. Product Offering
What does the brand sell and how does it communicate? Analyze: core benefits emphasized,
feature language (category-specific attributes and claims), product range breadth,
hero products and bestsellers, and whether there is emotional storytelling or purely
functional communication. Reference specific product names, price points, and hero SKUs
from the data — not generic category language.

### 3. Product Fundamentals
How strong is the actual product? Assess: materials and construction quality signals,
feature set vs. category norms, product line depth and breadth, innovation signals
(patents, proprietary technology, design awards). Compare to competitor product claims
if data is available. Are the fundamentals competitive for the price tier?

### 4. Pricing Position
Where does the brand sit on the price spectrum? Cite actual price points from e-commerce data.
Assess whether pricing matches brand aspirations. Compare to competitor pricing if available.
Does the pricing strategy enable or limit growth? If revenue or market share data exists,
use it to contextualize whether the pricing strategy is working.

### 5. Channel Analysis
How does the brand reach customers? Identify the primary growth engine (Amazon, DTC, wholesale,
retail partnerships). Assess website quality, e-commerce presence, social media engagement,
DTC vs. multi-channel mix. If desktop research includes social media follower counts,
engagement metrics, or retail distribution data, cite them. Which channel drives the business
and what does that dependency mean for brand-building?

### 6. Brand Challenges (identify exactly 3 distinct challenges)
Find 3 real, specific weaknesses. Look for: naming issues, inconsistent messaging across channels,
lack of emotional connection, unclear target audience, visual identity gaps, brand architecture
problems, credibility gaps, brand culture that doesn't translate to consumer perception,
brand vision that isn't reflected in execution. Each challenge gets its own slide with 3 bullets
and an insight. Frame challenge titles as clear statements of the problem (e.g., "THE BRAND
NAME CREATES A STRUCTURAL CHALLENGE" not "NAMING ISSUES").

### 7. Capabilities Summary
A flowing paragraph (3-5 sentences) synthesizing: what this brand is good at (execution strengths),
what it needs to fix (brand/perception gaps), and what must happen next. This is NOT bullets —
write it as a connected narrative paragraph.

## Required Output — return this exact JSON structure:

{{
  "brand_name": "{brand_name}",
  "date": "{date}",

  "capabilities": {{
    "execution_summary": {{
      "title": "HOW {brand_name_upper} WAS BUILT: [DESCRIPTIVE PHRASE IN CAPS]",
      "bullets": [
        "2-3 sentence observation about founding/growth strategy with specific evidence from website or documents",
        "2-3 sentence observation about key execution decisions that shaped the brand trajectory",
        "2-3 sentence assessment of what this execution approach achieved and what it missed or deferred"
      ],
      "insight": "Single provocative sentence reframing the execution story — challenge an assumption",
      "has_image": true
    }},
    "product_offer": {{
      "title": "[DESCRIPTIVE PRODUCT POSITIONING HEADLINE IN CAPS]",
      "bullets": [
        "2-3 sentences about product range with specific SKU/category/feature evidence from the data",
        "2-3 sentences about how the brand communicates product benefits — what language does it use on site and listings",
        "2-3 sentences assessing whether the offer is differentiated or follows category norms, and what that means"
      ],
      "insight": "Strategic reframe of the product positioning — what it enables and what it limits",
      "has_image": true
    }},
    "product_fundamentals": {{
      "title": "[PRODUCT FUNDAMENTALS ASSESSMENT HEADLINE IN CAPS]",
      "bullets": [
        "2-3 sentences about material/fabric quality, construction, and how it compares to competitors",
        "2-3 sentences about feature set depth and key product attributes relative to category norms",
        "2-3 sentences about size/color range, SKU depth, and whether the product line covers the market adequately"
      ],
      "insight": "Strategic assessment of whether product fundamentals are a strength to build on or a gap to close"
    }},
    "pricing_position": {{
      "title": "[PRICING STRATEGY HEADLINE IN CAPS — state the finding]",
      "bullets": [
        "2-3 sentences citing specific price points or ranges found on website/e-commerce with concrete numbers",
        "2-3 sentences about how pricing messaging positions the brand — value language, promotional tactics, perceived tier",
        "2-3 sentences about what the pricing strategy enables (trial, volume) and what it limits (premium perception, margins)"
      ],
      "insight": "Strategic implication of the pricing position for brand growth"
    }},
    "channel_analysis": {{
      "title": "[CHANNEL STRATEGY HEADLINE IN CAPS — state the finding]",
      "bullets": [
        "2-3 sentences about primary distribution channel with specific evidence (Amazon ranking, review count, etc.)",
        "2-3 sentences about secondary channels — DTC website quality, social media, wholesale/retail presence",
        "2-3 sentences assessing channel strategy strengths and dependencies — what happens if the primary channel changes"
      ],
      "insight": "Strategic implication of channel choices for long-term brand building"
    }},
    "brand_challenges": [
      {{
        "title": "[CHALLENGE 1: CLEAR PROBLEM STATEMENT IN CAPS]",
        "bullets": [
          "2-3 sentences with specific evidence of this challenge from website, listings, or reviews",
          "2-3 sentences about how this challenge manifests in the customer experience or brand perception",
          "2-3 sentences about what's at stake — the strategic risk if this isn't addressed"
        ],
        "insight": "Why this challenge matters strategically — connect to growth or positioning"
      }},
      {{
        "title": "[CHALLENGE 2: CLEAR PROBLEM STATEMENT IN CAPS]",
        "bullets": [
          "2-3 sentences with specific evidence of this challenge",
          "2-3 sentences about how it affects brand perception or customer experience",
          "2-3 sentences about the strategic risk"
        ],
        "insight": "Strategic implication — what this blocks or limits"
      }},
      {{
        "title": "[CHALLENGE 3: CLEAR PROBLEM STATEMENT IN CAPS]",
        "bullets": [
          "2-3 sentences describing this challenge with evidence",
          "2-3 sentences about its impact",
          "2-3 sentences about the path forward — frame as opportunity, not just problem"
        ],
        "insight": "Strategic reframe — how addressing this challenge unlocks the next stage"
      }}
    ],
    "capabilities_summary": "A flowing paragraph of 3-5 sentences. Follow this arc: [1] Name the brand and state its core execution strength with evidence. [2] Acknowledge the gap — what it has NOT yet built (brand, perception, positioning). [3] End with a forward-looking statement. Example: '[Brand] is an execution-driven brand with competitive products and strong Amazon performance, now facing the need to clarify its brand positioning to support long-term growth.'",
    "claims_vs_perception": {{
      "brand_claims": ["Specific claim the brand makes about itself — quote from website if possible", "Another specific claim"],
      "customer_perception": ["What customers actually say — quote or paraphrase from reviews", "Another customer perception"],
      "alignment": "Where claims and perception match — be specific about which claims hold up",
      "gaps": "Where they diverge — this is the most strategically important finding. Be specific and cite evidence."
    }},
    "clarity_scoring": {{
      "overall_score": 62,
      "dimensions": [
        {{
          "name": "Positioning Consistency",
          "score": 7,
          "max": 10,
          "evidence": "1-2 sentences explaining the score with specific evidence from website/listings/reviews"
        }},
        {{
          "name": "Core Message Clarity",
          "score": 5,
          "max": 10,
          "evidence": "Is the brand's core promise immediately understandable? Cite specific messaging."
        }},
        {{
          "name": "Category Ownership",
          "score": 8,
          "max": 10,
          "evidence": "Do consumers immediately know what category this brand belongs to?"
        }},
        {{
          "name": "Competitive Differentiation",
          "score": 4,
          "max": 10,
          "evidence": "Can consumers articulate how this brand differs from competitors? Cite review language."
        }},
        {{
          "name": "Cross-Channel Coherence",
          "score": 6,
          "max": 10,
          "evidence": "Is the brand's tone, visual identity, and messaging consistent across website, Amazon, social media?"
        }}
      ],
      "strongest_zone": "Where brand messaging is clearest — e.g., 'Product functionality communication on Amazon listings'",
      "weakest_zone": "Where messaging is most confused — e.g., 'Brand emotional positioning on homepage vs social media'",
      "headline": "ONE-LINE DIAGNOSIS IN CAPS — e.g., 'STRONG PRODUCT STORY, WEAK BRAND STORY'"
    }}
  }},

  "hypotheses": [
    {{
      "id": "H1",
      "statement": "Specific testable hypothesis derived from Phase 1 findings — e.g., 'The brand's primary buyer is Gen Z female'",
      "source": "Where this hypothesis came from — e.g., 'Social media engagement skews young female; TikTok virality'",
      "confidence": "high/medium/low",
      "evidence_needed": "What data would confirm or refute this — e.g., 'Survey demographics Q3+Q4'"
    }},
    {{
      "id": "H2",
      "statement": "Another testable hypothesis — e.g., 'Consumers perceive the brand as overpriced relative to competitors'",
      "source": "Evidence basis — e.g., 'Review sentiment: 15% mention price negatively'",
      "confidence": "medium",
      "evidence_needed": "Consumer willingness-to-pay survey data"
    }},
    {{
      "id": "H3",
      "statement": "Third hypothesis",
      "source": "Evidence basis",
      "confidence": "low",
      "evidence_needed": "Required validation data"
    }},
    {{
      "id": "H4",
      "statement": "Fourth hypothesis",
      "source": "Evidence basis",
      "confidence": "medium",
      "evidence_needed": "Required validation data"
    }},
    {{
      "id": "H5",
      "statement": "Fifth hypothesis",
      "source": "Evidence basis",
      "confidence": "medium",
      "evidence_needed": "Required validation data"
    }}
  ],

  "next_steps": [
    "Specific recommended action 1 tied directly to a finding above",
    "Specific recommended action 2",
    "Specific recommended action 3",
    "Specific recommended action 4"
  ]
}}

CRITICAL RULES:
- Every bullet MUST be a FULL PARAGRAPH: 2-4 sentences with specific evidence (prices, numbers,
  product names, review quotes). One-sentence bullets are unacceptable. Think of each bullet as
  a mini-argument: [OBSERVATION with evidence] → [IMPLICATION for the brand].
- Titles MUST be ALL CAPS and state a finding/opinion, not a generic topic label.
  GOOD: "A FOUNDER-LED, AMAZON-NATIVE BRAND" / "QUALITY IS A SYSTEM, NOT A CLAIM"
  BAD: "PRODUCT ANALYSIS" / "CHANNEL OVERVIEW"
- The insight field MUST be a single sentence a CMO would underline — provocative, not safe.
  GOOD: "The best way in is through the door nobody else is walking through."
  BAD: "The brand needs to improve its positioning."
- brand_challenges MUST contain exactly 3 challenges. Each challenge title should state the
  PROBLEM clearly (e.g., "THE BRAND NAME CREATES A STRUCTURAL CHALLENGE", not "NAMING ISSUES").
- capabilities_summary MUST be a flowing paragraph (not bullets) following the arc:
  strength → gap → forward-looking next step.
- If data is missing for a section, say what's missing and infer from available data.
- Do NOT invent data points — but DO make strategic inferences from real data.
- Output ONLY the JSON object, nothing else"""


# ── Market Structure Prompt (Phase 2) ─────────────────────────

MARKET_STRUCTURE_PROMPT = """Analyze the competitive landscape for {brand_name} and produce a Market Structure assessment.

## Brand Information
- Brand Name: {brand_name}
- Website URL: {brand_url}
- Industry/Category context from Phase 1 capabilities analysis

## Competitor List
{competitors}

## Competitor Website Data (scraped)
{competitor_scrape_data}

## Competitor E-Commerce Data
{competitor_ecommerce_data}

## Competitor Review Data
{competitor_review_data}

## Phase 1 Context (Brand Reality findings)
{phase1_context}

## Analysis Instructions

### Market Overview
Identify ALL notable competitors in the category (aim for 8-12 brands). Assess the overall
market structure: is it mature, fragmented, consolidating? What dynamics shape competition?
Where does {brand_name} currently fit?

### Focused Competitor Review
Select 4-6 competitors for deep analysis — the ones most relevant to {brand_name}'s positioning.
Include a mix: direct competitors (similar price/product), aspirational competitors (where the
brand wants to be), and adjacent competitors (different approach to same customer).

### Individual Competitor Analysis (CRITICAL — this is the most content-rich section)
Each competitor gets TWO conceptual slides in the report: one for POSITIONING, one for KEY LEARNINGS.
Write each entry with the depth and specificity of a dedicated competitor brief.

For each focused competitor, provide:
- POSITIONING: 3 bold-label:detail statements. Each label is a 3-5 word STRATEGIC THEME
  (not generic labels like "Target Audience"). The detail is ONE concise sentence with evidence.
  CRITICAL: "label: detail" must be ≤110 chars total. Text boxes are fixed-width — overflow is hidden.
  GOOD labels: "Design-led steam specialist", "Buy-it-for-life mindset", "Chemical-free authority"
  BAD labels: "Target Audience", "Price Point", "Key Differentiator" (too generic, too template-like)
- KEY LEARNINGS: 3 bold-label:detail insights. Each label states a strategic principle that
  {brand_name} can learn from. The detail is ONE sentence explaining WHY with evidence.
  SAME RULE: "label: detail" ≤110 chars total. No exceptions.
  GOOD labels: "Design creates permission", "Longevity is the promise", "Premium invites challenge"
  BAD labels: "What works", "Vulnerability", "Learning" (too generic)
- banner_description: A 1-line strategic framing of this competitor's role in the market.
  GOOD: "Design-led steam specialist positioning Neat as a minimalist premium alternative"
  GOOD: "Prosumer steam specialist bridging mass-market and premium European players"

### Competitive Landscape Summary
Group brands by STRATEGIC ROLE — use roles that reflect THIS category's actual dynamics,
not generic templates. Examples from different categories:
  - Water bottles: "Lifestyle Hydration", "Performance & Outdoor", "Premium Design", "Value Volume"
  - Cosmetics: "Clean Beauty", "Heritage Luxury", "K-Beauty Innovation", "Mass Accessibility"
  - Tech: "Ecosystem Lock-in", "Budget Disruptor", "Enterprise-First", "Design Premium"
For each role, name the brands and explain what defines that competitive territory. Then
identify the white space — the specific positioning territory that NO brand currently owns.
Be concrete: "No brand currently combines [X capability] with [Y promise]."

### Competition Summary
Write a flowing paragraph of 3-5 sentences. Name specific brands and their winning strategies.
State what the competitive landscape rewards and punishes. End with a forward-looking statement
about what claiming white space requires for {brand_name}. Reference specific evidence from
desktop research (market share, revenue, social following) where available.
GOOD: "The [category] market rewards brands that own a single clear territory — [Competitor A]
wins on [positioning], [Competitor B] on [positioning], [Competitor C] on [positioning] — while
punishing brands that try to be everything to everyone."

## Required Output — return this exact JSON structure:

{{
  "competition": {{
    "market_overview": {{
      "title": "KEY PLAYERS SHAPING THE [CATEGORY] CATEGORY",
      "competitor_names": ["Brand A", "Brand B", "Brand C", "Brand D", "Brand E", "Brand F", "Brand G", "Brand H"],
      "bullets": [
        "2-3 sentences describing the overall market structure and competitive dynamics",
        "2-3 sentences about key trends shaping competition — what's changing and why",
        "2-3 sentences about where {brand_name} currently fits and what that position means"
      ],
      "insight": "Single provocative sentence capturing the competitive reality {brand_name} faces"
    }},
    "focused_competitors": ["Brand A", "Brand B", "Brand C", "Brand D", "Brand E", "Brand F"],
    "competitor_analyses": [
      {{
        "name": "Competitor Name",
        "banner_description": "Strategic 1-line framing of their market role (e.g., 'Design-led steam specialist positioning as minimalist premium alternative')",
        "positioning": [
          {{"label": "3-5 word theme", "detail": "ONE sentence, max 100 chars. Cite specific evidence (prices, claims, channels)."}},
          {{"label": "Another theme", "detail": "ONE sentence, max 100 chars. How this positioning manifests concretely."}},
          {{"label": "Third theme", "detail": "ONE sentence, max 100 chars. What territory does this positioning claim?"}}
        ],
        "key_learnings": [
          {{"label": "Strategic principle", "detail": "ONE sentence, max 100 chars. Why this matters for {brand_name}."}},
          {{"label": "Another principle", "detail": "ONE sentence, max 100 chars. What vulnerability or open territory this reveals."}},
          {{"label": "Third principle", "detail": "ONE sentence, max 100 chars. Concrete takeaway for {brand_name}."}}
        ]
      }}
    ],
    "landscape_summary": {{
      "market_roles": [
        {{"role": "Role Name (e.g., Premium Lifestyle)", "brands": ["Brand1", "Brand2"], "description": "What defines this role"}},
        {{"role": "Role Name", "brands": ["Brand3"], "description": "What defines this role"}},
        {{"role": "Role Name", "brands": ["Brand4", "Brand5"], "description": "What defines this role"}},
        {{"role": "Role Name", "brands": ["Brand6"], "description": "What defines this role"}}
      ],
      "white_space": "Specific positioning territory that no brand currently owns — be concrete about what this looks like",
      "category_norms": [
        "A norm/assumption most brands in this category share",
        "Another shared assumption",
        "A third shared assumption that could be challenged"
      ]
    }},
    "competition_summary": "A flowing paragraph of 3-5 sentences. Synthesize: what the competitive landscape looks like, which brands succeed by owning a clear role, and where the white space opportunity lies for {brand_name}. End with a forward-looking statement about what claiming that white space requires."
  }}
}}

CRITICAL RULES:
- competitor_analyses MUST contain exactly 6 entries — the 6 most strategically relevant competitors
- Each competitor's positioning and key_learnings MUST have exactly 3 entries each
- market_roles MUST contain exactly 4 roles that cover the market structure
- Titles must be ALL CAPS and descriptive (e.g., "KEY PLAYERS SHAPING THE [CATEGORY] CATEGORY")
- competition_summary must be a paragraph, not bullets
- If competitor data is limited, infer from available evidence and state what you're inferring
- Output ONLY the JSON object, nothing else"""


# ── Full Analysis Prompt (all phases) ─────────────────────────

FULL_ANALYSIS_PROMPT = """Produce a complete Brand Discovery report for {brand_name}.

## Brand Information
- Brand Name: {brand_name}
- Website URL: {brand_url}
- Language: {language}

## Website Content (scraped)
{scrape_data}

## Uploaded Documents
{document_data}

## E-Commerce Data
{ecommerce_data}

## Customer Reviews
{review_data}

## Competitors
{competitors}

## Competitor Data
{competitor_data}

## Analysis Instructions

This is a FULL discovery report covering all 3 steps. Follow the structure precisely.

### Step 1: Capabilities
Analyze the brand across 7 dimensions: execution summary, product offer, product fundamentals,
pricing position, channel analysis, 3 brand challenges, and a capabilities summary paragraph.
Each slide needs 3 bullets (2-3 sentences each) + 1 insight sentence.

### Step 2: Competition
Map the competitive landscape: market overview (8-12 brands), focused review (4-6 deep dives),
landscape summary (4 market roles), and competition summary paragraph.

### Step 3: Consumer
This is the MOST important section. Based on available review data, e-commerce data, and any
uploaded research documents, build a comprehensive consumer analysis:

1. Research approach — QUANTITATIVE SURVEY format matching DynaBridge methodology:
   - Format: Always "Online survey", 10 minutes, Unbranded
   - Participants: Generate realistic sample size (200-300), age screener (18+ or 22+ depending on category),
     gender quota appropriate to category (e.g., 70/30 F/M for fashion/beauty, 50/50 for tech/home),
     category-specific screener criteria (professionals who use the product, or consumers who purchase in category),
     and "primary or shared decision-maker" qualifier
   - Analysis sections: Demographics, Shopping Habits, Brand Evaluation, Market Segmentation
   - Timing: Use the provided date
2. Shopping habits and purchase drivers (generate chart data from reviews/e-commerce signals)
3. Brand perception analysis
4. Consumer segmentation: identify 4-5 distinct consumer segments based on the data.
   Each segment MUST include:
   - An evocative 2-word name that captures the segment's core identity
     GOOD: "Endurance First", "Polished Pro", "Tender Caregiver", "Vivid Collector"
     BAD: "Segment 1", "Price Sensitive", "Quality Buyer" (too generic)
   - A first-person tagline that sounds like something the person would actually say
     GOOD: "I need products that perform when it matters most"
     BAD: "This segment values quality and comfort" (third-person, generic)
   - A "Meet the [Segment]" narrative paragraph (5-7 sentences). START with a vivid character
     scene: "Meet the [Name]: Picture a [specific role] halfway through a [specific situation]..."
     Then cover: who they are demographically, how they shop for this category, what matters most,
     what frustrates them, and what would win their loyalty. Use specific details and percentages.
     Write as storytelling, not a data dump.
   - what_premium_means: What this segment specifically considers premium. Not generic — cite
     the exact attributes (e.g., "evidence of superior fabric technology (42%) and premium
     stitching/construction (38%)")
   - lifestyle_signals: 4 lifestyle data points (social media, music genre, car brand, key stat)
     that paint a vivid picture of who this person is beyond the category
   - mini_tables: structured data for purchase_drivers, pain_points, pre_purchase, social_media
     — each with item and pct fields for chart rendering
5. Target audience recommendation:
   - Which segment should {brand_name} prioritize and WHY (4 specific strategic reasons)
   - What targeting this segment ENABLES (3 strategic benefits)
   - What this choice does NOT yet decide (3 open questions for future work)
   - Per-segment de-prioritization reasoning: for EACH non-primary segment, state the specific
     strategic risk of targeting them (e.g., "Promotion-driven, competing here risks compressing margins")
6. Competitive fares: How {brand_name} stacks up against competition for the target segment
7. Consumer summary paragraph tying segment choice to capabilities and competitive position

## Required Output — return this exact JSON:

{{
  "brand_name": "{brand_name}",
  "date": "{date}",

  "capabilities": {{
    "execution_summary": {{
      "title": "HOW {brand_name_upper} WAS BUILT: [DESCRIPTIVE PHRASE]",
      "bullets": ["2-3 sentence point with evidence", "2-3 sentence point", "2-3 sentence point"],
      "insight": "Provocative single sentence reframe",
      "has_image": true
    }},
    "product_offer": {{
      "title": "[DESCRIPTIVE PRODUCT HEADLINE IN CAPS]",
      "bullets": ["2-3 sentence point with evidence", "2-3 sentence point", "2-3 sentence point"],
      "insight": "Strategic reframe",
      "has_image": true
    }},
    "product_fundamentals": {{
      "title": "[PRODUCT FUNDAMENTALS HEADLINE IN CAPS]",
      "bullets": ["2-3 sentence point", "2-3 sentence point", "2-3 sentence point"],
      "insight": "Strategic assessment"
    }},
    "pricing_position": {{
      "title": "[PRICING HEADLINE IN CAPS]",
      "bullets": ["2-3 sentence point with prices", "2-3 sentence point", "2-3 sentence point"],
      "insight": "Strategic implication"
    }},
    "channel_analysis": {{
      "title": "[CHANNEL HEADLINE IN CAPS]",
      "bullets": ["2-3 sentence point", "2-3 sentence point", "2-3 sentence point"],
      "insight": "Strategic implication"
    }},
    "brand_challenges": [
      {{
        "title": "[CHALLENGE 1 STATEMENT IN CAPS]",
        "bullets": ["2-3 sentence point", "2-3 sentence point", "2-3 sentence point"],
        "insight": "Strategic implication"
      }},
      {{
        "title": "[CHALLENGE 2 STATEMENT IN CAPS]",
        "bullets": ["2-3 sentence point", "2-3 sentence point", "2-3 sentence point"],
        "insight": "Strategic implication"
      }},
      {{
        "title": "[CHALLENGE 3 STATEMENT IN CAPS]",
        "bullets": ["2-3 sentence point", "2-3 sentence point", "2-3 sentence point"],
        "insight": "Strategic reframe — path forward"
      }}
    ],
    "capabilities_summary": "Flowing paragraph 3-5 sentences: execution strengths + brand gaps + what needs to happen next",
    "claims_vs_perception": {{
      "brand_claims": ["Specific claim from website/listings"],
      "customer_perception": ["What customers say in reviews"],
      "alignment": "Where they match",
      "gaps": "Where they diverge — cite evidence"
    }}
  }},

  "competition": {{
    "market_overview": {{
      "title": "A [ADJ], [ADJ] [CATEGORY] MARKET",
      "competitor_names": ["Brand1", "Brand2", "Brand3", "Brand4", "Brand5", "Brand6"],
      "bullets": ["2-3 sentence market structure", "2-3 sentence trends", "2-3 sentence brand position"],
      "insight": "Competitive reality sentence"
    }},
    "focused_competitors": ["Brand A", "Brand B", "Brand C", "Brand D"],
    "competitor_analyses": [
      {{
        "name": "Competitor Name",
        "banner_description": "Strategic 1-line role framing (e.g., 'Design-led steam specialist positioning as minimalist premium alternative')",
        "positioning": [
          {{"label": "3-5 word strategic theme", "detail": "1-2 sentences with specific evidence — cite product claims, prices, visual identity"}},
          {{"label": "Another strategic theme", "detail": "1-2 sentences. Be specific about HOW this positioning manifests"}},
          {{"label": "Third strategic theme", "detail": "1-2 sentences. What emotional or functional territory does this claim?"}}
        ],
        "key_learnings": [
          {{"label": "Strategic principle (e.g., 'Design creates permission')", "detail": "1-2 sentences. What can {brand_name} learn, borrow, or challenge?"}},
          {{"label": "Another principle (e.g., 'Longevity is the promise')", "detail": "1-2 sentences. Where is this competitor vulnerable?"}},
          {{"label": "Third principle (e.g., 'Premium invites challenge')", "detail": "1-2 sentences. Concrete takeaway for {brand_name}."}}
        ]
      }}
    ],
    "landscape_summary": {{
      "market_roles": [
        {{"role": "Role Name", "brands": ["Brand1", "Brand2"], "description": "What defines this role"}},
        {{"role": "Role Name", "brands": ["Brand3"], "description": "What defines this role"}},
        {{"role": "Role Name", "brands": ["Brand4"], "description": "What defines this role"}},
        {{"role": "Role Name", "brands": ["Brand5", "Brand6"], "description": "What defines this role"}}
      ],
      "white_space": "Specific unclaimed positioning territory",
      "category_norms": ["Shared norm 1", "Shared norm 2", "Shared norm 3"]
    }},
    "competition_summary": "Flowing paragraph 3-5 sentences synthesizing competitive landscape and opportunity"
  }},

  "consumer": {{
    "overview": "2-3 sentence consumer landscape summary — who buys in this category and what matters to them",
    "research_approach": [
      {{"label": "Format", "detail": "Methodology:\tOnline survey\nLength:\t\t10 minutes\nBranding:\tUnbranded"}},
      {{"label": "Participants", "detail": "Total of [N] US Consumers:\nUS resident; [age]+ years old\nQuota on Gender: Female ([X]%) Male ([Y]%)\n[Category-specific screener — derive from the actual product category]\n[Additional qualification if relevant to this specific category]\nPrimary or shared decision-maker when purchasing their own [category]"}},
      {{"label": "Analysis", "detail": "Demographics & Background\nShopping Habits, Category Usage and Ownership\nBrand Evaluation & Competitor Analysis\nMarket Segmentation"}},
      {{"label": "Timing", "detail": "Fielding: {date}"}}
    ],
    "gender_data": {{"male_pct": 30, "female_pct": 70}},
    "marital_data": {{"married_pct": 52, "single_pct": 33, "divorced_pct": 15}},
    "charts": [
      // SECTION: Demographics (4 charts) — divider auto-inserted
      {{
        "chart_type": "hbar",
        "section": "demographics",
        "title": "GENERATION",
        "subtitle": "Generation distribution of survey respondents",
        "categories": ["Gen Z (1997 to 2009)", "Millennials (1981 to 1996)", "Gen X (1965 to 1980)", "Boomers (1946 to 1964)"],
        "values": [15, 45, 30, 10]
      }},
      {{
        "chart_type": "vbar",
        "section": "demographics",
        "title": "RACE / ETHNICITY",
        "subtitle": "Respondent racial and ethnic composition",
        "categories": ["White or Caucasian", "Black or African American", "Hispanic or Latino", "Asian", "Other"],
        "values": [52, 22, 15, 8, 3]
      }},
      {{
        "chart_type": "vbar",
        "section": "demographics",
        "title": "HOUSEHOLD INCOME",
        "subtitle": "Annual household income distribution",
        "categories": ["Low income", "Lower middle income", "Upper middle income", "High income"],
        "values": [8, 24, 40, 28]
      }},
      {{
        "chart_type": "hbar",
        "section": "demographics",
        "title": "SOCIAL MEDIA PLATFORM USAGE",
        "subtitle": "Which social media platforms do you frequently use?",
        "categories": ["Facebook", "YouTube", "Instagram", "TikTok", "Snapchat", "X/Twitter", "LinkedIn", "Other"],
        "values": [78, 75, 65, 55, 40, 32, 28, 2]
      }},
      // SECTION: Shopping Habits (6-8 charts) — divider auto-inserted
      {{
        "chart_type": "dual",
        "title": "PURCHASE FREQUENCY AND ANNUAL SPEND",
        "subtitle": "How often and how much respondents spend on [category]",
        "left_type": "donut", "left_title": "Purchase frequency (past 12 months)",
        "left_categories": ["Monthly+", "Every 2-3 months", "2-3x/year", "Once/year", "When needed"],
        "left_values": [18, 42, 27, 7, 6],
        "right_type": "hbar", "right_title": "Annual spend on [category]",
        "right_categories": ["Under $50", "$50-$99", "$100-$199", "$200-$499", "$500+"],
        "right_values": [12, 22, 30, 25, 11]
      }},
      {{
        "chart_type": "hbar",
        "title": "WHERE CONSUMERS PURCHASE [CATEGORY]",
        "subtitle": "Primary purchase channels (select all that apply)",
        "categories": ["Amazon", "Brand website (DTC)", "Walmart", "Specialty stores", "Target", "Other"],
        "values": [59, 41, 38, 35, 26, 15]
      }},
      {{
        "chart_type": "hbar",
        "title": "WHEN AND WHY CONSUMERS USE [CATEGORY]",
        "subtitle": "Usage occasions (select all that apply)",
        "categories": ["Occasion1", "Occasion2", "Occasion3", "Occasion4", "Occasion5"],
        "values": [72, 55, 42, 35, 28]
      }},
      {{
        "chart_type": "hbar",
        "title": "PRE-PURCHASE ACTIVITIES",
        "subtitle": "Steps taken before buying [category]",
        "categories": ["Read online reviews", "Compare prices", "Visit brand website", "Ask friends/family", "Watch video reviews", "Try in store", "Check social media"],
        "values": [78, 65, 48, 42, 38, 32, 28]
      }},
      // SECTION: Purchase Drivers (3-4 charts)
      {{
        "chart_type": "hbar",
        "title": "TOP PURCHASE DRIVERS",
        "subtitle": "Most important factors when buying [category] (select top 3)",
        "categories": ["Driver1", "Driver2", "Driver3", "Driver4", "Driver5", "Driver6", "Driver7", "Driver8"],
        "values": [65, 52, 48, 42, 38, 35, 28, 22]
      }},
      {{
        "chart_type": "hbar",
        "title": "WHAT DOES 'PREMIUM' MEAN IN [CATEGORY]?",
        "subtitle": "Consumer definition of premium (select all that apply)",
        "categories": ["Premium1", "Premium2", "Premium3", "Premium4", "Premium5", "Premium6"],
        "values": [55, 48, 42, 35, 30, 25]
      }},
      {{
        "chart_type": "dual",
        "title": "WILLINGNESS TO PAY FOR QUALITY",
        "subtitle": "Price sensitivity and premium willingness",
        "left_type": "donut", "left_title": "Willing to pay more for quality",
        "left_categories": ["Strongly agree", "Somewhat agree", "Neutral", "Disagree"],
        "left_values": [35, 40, 15, 10],
        "right_type": "hbar", "right_title": "Expected price range for quality [category]",
        "right_categories": ["Under $25", "$25-$49", "$50-$99", "$100-$199", "$200+"],
        "right_values": [8, 25, 38, 22, 7]
      }},
      {{
        "chart_type": "wordcloud",
        "title": "WHAT CONSUMERS SAY ABOUT [CATEGORY]",
        "subtitle": "Word frequency from open-ended responses and reviews",
        "words": "Generate 15-20 words/phrases that consumers in THIS specific category actually use. Derive from review data, brand messaging, and category vocabulary. Each word gets a frequency weight 20-100."
      }},
      // SECTION: Brand Evaluation (4-5 charts) — divider auto-inserted
      {{
        "chart_type": "grouped_bar",
        "title": "BRAND METRICS — AWARENESS TO ADVOCACY",
        "subtitle": "Brand performance across key metrics",
        "horizontal": true,
        "categories": ["Brand1", "Brand2", "Brand3", "Brand4", "Brand5"],
        "groups": [
          {{"name": "Awareness", "values": [85, 72, 60, 45, 38]}},
          {{"name": "Purchase", "values": [55, 40, 30, 20, 15]}},
          {{"name": "Satisfaction", "values": [80, 65, 55, 50, 42]}},
          {{"name": "Recommend", "values": [60, 45, 35, 30, 22]}}
        ]
      }},
      {{
        "chart_type": "donut",
        "title": "FAVORITE BRAND REGARDLESS OF PRICE",
        "subtitle": "Which brand is your favorite?",
        "center_text": "N=200",
        "categories": ["Brand1", "Brand2", "Brand3", "Brand4", "Brand5", "No favorite"],
        "values": [28, 22, 18, 12, 8, 12]
      }},
      {{
        "chart_type": "hbar",
        "title": "LIKELIHOOD TO TRY A NEW BRAND",
        "subtitle": "How open are consumers to switching?",
        "categories": ["Very likely", "Somewhat likely", "Neutral", "Somewhat unlikely", "Very unlikely"],
        "values": [22, 35, 25, 12, 6]
      }},
      {{
        "chart_type": "matrix",
        "title": "BRAND ASSOCIATION MATRIX",
        "subtitle": "Which brand best fits each description?",
        "row_labels": ["High quality", "Good value", "Innovative", "Trustworthy", "Stylish", "Premium"],
        "col_labels": ["Brand1", "Brand2", "Brand3", "Brand4"],
        "values": [
          [45, 30, 20, 15],
          [25, 40, 35, 50],
          [30, 25, 15, 10],
          [40, 35, 25, 20],
          [20, 15, 35, 10],
          [35, 20, 15, 10]
        ]
      }}
    ],
    "verbatim_quotes": [
      {{"theme": "Theme name (e.g., Comfort)", "quotes": ["Direct quote from review 1", "Direct quote from review 2", "Direct quote from review 3"]}},
      {{"theme": "Another theme", "quotes": ["Quote 1", "Quote 2", "Quote 3"]}}
    ],
    "segments": [
      {{
        "name": "Evocative 2-word name (e.g., Endurance First, Smart Shopper, Tender Caregiver, Polished Pro, Vivid Collector, Mindful Sustainer)",
        "tagline": "I want/need [what this segment prioritizes] — one sentence, first person, sounds like something they'd actually say",
        "size_pct": 27,
        "persona_quote": "First-person statement that captures this segment's mindset — e.g., 'I compare prices carefully and focus on reliable products that meet my needs without paying extra for features I won't use.'",
        "narrative": "Meet the [Segment Name]: Picture a [specific role/person] [in a specific situation that reveals their relationship to the category]. [2-3 sentences about who they are: demographics, income, lifestyle]. [1-2 sentences about how they shop: channels, frequency, research behavior]. [1-2 sentences about what matters most and what frustrates them]. [1 sentence about what premium/quality means to them specifically]. For example: 'Meet the Performance Seeker: Picture someone testing the product to its limits in their daily routine. They've tried the alternatives and know exactly what fails first. They need something that keeps up with their demands without compromise.'",
        "demographics": {{
          "primary_role": "Most common role/profession",
          "age_skew": "e.g., 58% Millennial, 23% Gen X",
          "income": "e.g., 51% upper-middle income",
          "gender_split": "e.g., 67% female, 33% male"
        }},
        "shopping_behavior": {{
          "annual_spend": "$XXX median",
          "primary_channel": "Where they buy most",
          "purchase_frequency": "How often they buy",
          "brand_loyalty": "High/Medium/Low — with reasoning"
        }},
        "top_needs": ["Need 1 with percentage if available", "Need 2", "Need 3"],
        "pain_points": ["Pain point 1 with percentage if available", "Pain point 2", "Pain point 3"],
        "what_premium_means": "What this segment considers premium — e.g., fabric tech, design, durability",
        "social_media": ["YouTube (78%)", "Instagram (65%)", "TikTok (45%)", "Facebook (38%)"],
        "music_preferences": "e.g., 37% prefer Hip-Hop / Rap, 28% like R&B / Soul",
        "car_brand_affinities": "e.g., 18% said Jeep best captures their style",
        "lifestyle_values": ["e.g., Sustainability", "Convenience", "Community"],
        "lifestyle_signals": [
          {{"category": "Social Media", "detail": "e.g., 78% use YouTube more than any other platform"}},
          {{"category": "Music", "detail": "e.g., 37% prefer R&B / Soul music"}},
          {{"category": "Car Brand", "detail": "e.g., 25% said Mercedes-Benz best captures their style"}},
          {{"category": "Key Stat", "detail": "e.g., 71% prefer brands with a sustainability commitment"}}
        ],
        "mini_tables": {{
          "social_media": [{{"item": "YouTube", "pct": 78}}, {{"item": "Instagram", "pct": 65}}, {{"item": "TikTok", "pct": 45}}],
          "purchase_drivers": [{{"item": "Comfort", "pct": 72}}, {{"item": "Durability", "pct": 58}}, {{"item": "Value", "pct": 51}}],
          "pain_points": [{{"item": "Inconsistent sizing", "pct": 45}}, {{"item": "Poor fabric quality", "pct": 32}}, {{"item": "Limited styles", "pct": 28}}],
          "pre_purchase": [{{"item": "Read reviews", "pct": 82}}, {{"item": "Compare prices", "pct": 65}}, {{"item": "Visit brand site", "pct": 48}}]
        }}
      }}
    ],
    "target_recommendation": {{
      "primary_segment": "Name of recommended primary target segment",
      "title": "PRIMARY TARGET: [SEGMENT NAME] IN CAPS",
      "rationale_bullets": [
        "Reason 1 why this segment should be the primary target — with data",
        "Reason 2 — connect to brand strengths",
        "Reason 3 — connect to market opportunity",
        "Reason 4 — connect to channel fit"
      ],
      "insight": "For this segment, [specific reframe of what premium/quality/value means to them]",
      "enables": ["What targeting this segment unlocks — strategic benefit 1", "Strategic benefit 2", "Strategic benefit 3"],
      "does_not_decide": ["What this choice does NOT determine yet", "Another open question", "Third open question"]
    }},
    "deprioritized_segments": [
      {{
        "name": "Segment Name",
        "size_pct": 17,
        "reason": "Specific reason this segment is not the primary target — e.g., 'Promotion-driven, more price-sensitive, competing here risks compressing margins'"
      }}
    ],
    "competitive_fares": {{
      "brand_strengths": "What each leading competitor wins on — e.g., 'Brand A → Innovation, Brand B → Heritage, Brand C → Value'",
      "category_compromise": "What the category forces buyers to compromise on — no brand combines [X] and [Y]",
      "strategic_opportunity": "The specific combination of strengths no brand currently owns",
      "strategic_question": "What would it look like to build a brand that didn't force that compromise?"
    }},
    "consumer_summary": "Flowing paragraph 3-5 sentences. Name the recommended segment, state why they matter, and connect to the brand's capabilities and competitive position. End with a forward-looking statement.",
    "key_insights": [
      {{
        "title": "KEY CONSUMER INSIGHT HEADLINE IN CAPS",
        "bullets": [
          "2-3 sentence insight about purchase behavior with evidence",
          "2-3 sentence insight about unmet needs",
          "2-3 sentence insight about brand perception or willingness to pay",
          "2-3 sentence insight about channel or influence patterns"
        ],
        "insight": "Single sentence strategic reframe of consumer opportunity"
      }}
    ]
  }},

  "summary_and_next_steps": {{
    "capabilities_column": "2-3 sentence paragraph summarizing Step 1 findings. Name the brand and its core strength. State the key gap. Example: '[Brand] is an execution-driven brand with competitive products and strong channel performance, now facing the need to clarify its brand positioning to support long-term growth.'",
    "competition_column": "2-3 sentence paragraph summarizing Step 2 findings. Name specific competitors and their roles. State the white space. Example: 'The market is well established, with leading brands succeeding by owning a clear and focused role—such as innovation, heritage, or value—rather than trying to compete across everything at once.'",
    "consumer_column": "2-3 sentence paragraph summarizing Step 3 findings. Name the target segment and why they matter. Example: 'The primary segment spends the most, sets the highest performance standards, and defines what quality means in the category—making them the most valuable and influential audience.'",
    "closing_insight": "1-2 sentence forward-looking statement connecting all three pillars. Example: 'Building on these insights, we will define a clear and differentiated brand position—one that resonates with its most demanding customers and scales credibly across the broader market.'"
  }},

  "next_steps": [
    "Specific action 1 tied to capabilities findings — what to fix or build",
    "Specific action 2 tied to competitive positioning — how to differentiate",
    "Specific action 3 tied to consumer targeting — how to activate the target segment",
    "Specific action 4 tied to brand building — the next phase of work"
  ]
}}

CRITICAL RULES:
- This is a COMPREHENSIVE report. Every section must be thorough and evidence-based.
- segments MUST contain 4-5 entries. Each needs:
  * An evocative 2-word name (GOOD: "Endurance First", "Polished Pro", "Tender Caregiver", "Vivid Collector")
  * A first-person tagline that sounds authentic, not corporate
  * A "Meet the [Name]" narrative (5-7 sentences) that OPENS with a vivid character scene
  * Specific what_premium_means (cite attributes and percentages, not generic "quality")
  * 4 lifestyle_signals (social media, music, car brand, key stat) for cultural profiling
  * mini_tables with item+pct data for purchase_drivers, pain_points, pre_purchase, social_media
- brand_challenges MUST contain exactly 3 entries, each with Format A bullets (2-4 sentence paragraphs).
- competitor_analyses MUST contain exactly 6 entries — the 6 most strategically relevant competitors.
  Each must use Format B (bold-label: detail) for both positioning and key_learnings.
  Labels must be STRATEGIC THEMES, not generic labels like "Target Audience" or "What works".
- All content bullets must be 2-4 sentence paragraphs with specific evidence (Format A).
- All titles must be ALL CAPS and state a finding, not a generic topic.
- All summary fields must be flowing paragraphs connecting strength → gap → next step.
- deprioritized_segments: for EACH non-primary segment, state the specific strategic risk
  (e.g., "Promotion-driven, competing here risks compressing margins and weakening premium positioning")
- competitive_fares must name specific competitors and what they win on (e.g., "Brand A → Innovation, Brand B → Heritage")
- Include top-level "gender_data": {"male_pct": XX, "female_pct": XX} and "marital_data": {"married_pct": XX, "single_pct": XX, "divorced_pct": XX} in the consumer object (not as charts). Do NOT create a separate gender chart — gender is displayed via icon, not chart.
- Generate 15-20 charts organized in 4 sections (real cases average 22-29 chart slides):
  * Demographics (4 SEPARATE charts — do NOT combine them): (1) generation hbar with chart_type "hbar" and title containing "GENERATION" (labels like "Gen Z (1997 to 2009)", "Millennials (1981 to 1996)", etc.), (2) race/ethnicity vbar with chart_type "vbar" and title containing "RACE" or "ETHNICITY" (labels like "White or Caucasian", "Black or African American", etc.), (3) household income vbar with chart_type "vbar" and title containing "INCOME" (4 brackets: "Low income", "Lower middle income", "Upper middle income", "High income"), (4) social media platform usage hbar with chart_type "hbar" and title containing "SOCIAL MEDIA"
  * Shopping Habits (5-7): purchase frequency+spend dual, channels hbar, occasions hbar, pre-purchase hbar
  * Purchase Drivers (3-4): top drivers hbar, premium definition hbar, willingness-to-pay dual, wordcloud (MUST include 40-60 words with varied frequencies from 5 to 100)
  * Brand Evaluation (4-5): brand metrics grouped_bar (brands on Y, Awareness/Purchase/Satisfaction/Recommend as groups), favorite brand donut, brand switching hbar, brand association matrix
  Use plausible percentages grounded in review/e-commerce evidence. Values must sum logically (donut/pie slices should total ~100).
  Valid chart_type values: "hbar", "dual", "donut", "pie", "vbar", "stacked", "grouped_bar", "wordcloud", "matrix", "table".
- If the language is "zh" or "en+zh", add "_zh" suffixed fields for all text.
- Output ONLY the JSON object, nothing else."""


# ── Analysis Functions ────────────────────────────────────────

async def analyze_brand(
    brand_name: str,
    brand_url: str,
    scrape_data: dict,
    document_data: list[dict],
    competitors: list[str],
    language: str = "en",
    phase: str = "full",
    ecommerce_data: dict = None,
    review_data: dict = None,
    competitor_data: list[dict] = None,
    desktop_research: dict = None,
    survey_mode: str = "simulated",
    real_survey_responses: dict = None,
) -> dict:
    """Run Claude AI analysis on brand data and return structured JSON.

    Args:
        phase: "brand_reality" | "market_structure" | "full"
        desktop_research: Output from 3-session research pipeline
            {"brand_context": {...}, "competitor_profiles": [...], "consumer_landscape": {...}}
    """
    if not client:
        return _mock_analysis(brand_name, phase)

    # Format inputs
    scrape_text = _format_scrape_data(scrape_data)
    doc_text = _format_documents(document_data)
    comp_text = ", ".join(competitors) if competitors else "Not specified — identify key competitors"
    comp_detail_text = _format_competitor_data(competitor_data) if competitor_data else "No competitor discovery data"
    ecom_text = _format_ecommerce(ecommerce_data) if ecommerce_data else "No e-commerce data collected"
    review_text = _format_reviews(review_data) if review_data else "No review data collected"
    research_text = _format_desktop_research(desktop_research) if desktop_research else ""

    import datetime
    date_str = datetime.datetime.now().strftime("%B %Y").upper()

    if phase == "full":
        # Split into 3 sequential calls to avoid token limits
        # Phase 1: Capabilities
        # Inject desktop research into scrape/doc sections for richer context
        brand_research_block = ""
        if research_text:
            brand_research_block = f"\n\n## Desktop Research (Web Search Findings)\n{research_text}\n"

        p1_prompt = BRAND_REALITY_PROMPT.format(
            brand_name=brand_name,
            brand_name_upper=brand_name.upper(),
            brand_url=brand_url,
            language=language,
            scrape_data=(scrape_text or "No website data available") + brand_research_block,
            document_data=doc_text or "No documents uploaded",
            ecommerce_data=ecom_text,
            review_data=review_text,
            date=date_str,
        )
        p1_result = await _call_claude(p1_prompt, max_tokens=12000)
        if "raw_analysis" in p1_result:
            print("[analyzer] Phase 1 JSON parse failed, retrying...")
            await asyncio.sleep(10)
            p1_result = await _call_claude(p1_prompt, max_tokens=12000)
        print(f"[analyzer] Phase 1 complete. Keys: {list(p1_result.keys()) if isinstance(p1_result, dict) else 'not dict'}")
        await asyncio.sleep(5)  # Brief cooldown between API calls

        # Phase 2: Competition (feed Phase 1 summary as context)
        p1_context = ""
        if isinstance(p1_result, dict):
            cap = p1_result.get("capabilities", {})
            p1_context = cap.get("capabilities_summary", "")

        # Enrich competitor data with desktop research profiles
        comp_enriched = comp_detail_text
        if desktop_research and desktop_research.get("competitor_profiles"):
            profiles = desktop_research["competitor_profiles"]
            profile_lines = ["\n### Web-Researched Competitor Profiles"]
            for cp in profiles:
                profile_lines.append(
                    f"\n**{cp.get('name', 'Unknown')}** ({cp.get('category_role', 'direct')})\n"
                    f"  Products: {cp.get('product_range', 'N/A')}\n"
                    f"  Pricing: {cp.get('price_range', 'N/A')} ({cp.get('price_positioning', 'N/A')})\n"
                    f"  Target: {cp.get('target_audience', 'N/A')}\n"
                    f"  Differentiator: {cp.get('key_differentiator', 'N/A')}\n"
                    f"  Channels: {cp.get('channel_strategy', 'N/A')}\n"
                    f"  Strengths: {', '.join(cp.get('strengths', []))}\n"
                    f"  Vulnerabilities: {', '.join(cp.get('vulnerabilities', []))}\n"
                    f"  Amazon: {cp.get('amazon_stats', 'N/A')}\n"
                    f"  Learning: {cp.get('key_learning', 'N/A')}"
                )
            comp_enriched = comp_detail_text + "\n".join(profile_lines)

        p2_prompt = MARKET_STRUCTURE_PROMPT.format(
            brand_name=brand_name,
            brand_url=brand_url,
            competitors=comp_text,
            competitor_scrape_data=comp_enriched,
            competitor_ecommerce_data=comp_enriched,
            competitor_review_data=comp_enriched,
            phase1_context=p1_context or "Phase 1 analysis completed — assess competition independently",
        )
        p2_result = await _call_claude(p2_prompt, max_tokens=12000)
        if "raw_analysis" in p2_result:
            print("[analyzer] Phase 2 JSON parse failed, retrying...")
            await asyncio.sleep(10)
            p2_result = await _call_claude(p2_prompt, max_tokens=12000)
        print(f"[analyzer] Phase 2 complete. Keys: {list(p2_result.keys()) if isinstance(p2_result, dict) else 'not dict'}")

        # Phase 3: Consumer (feed Phase 1+2 summaries as context)
        p2_context = ""
        if isinstance(p2_result, dict):
            comp_section = p2_result.get("competition", {})
            p2_context = comp_section.get("competition_summary", "")

        p3_prompt = FULL_ANALYSIS_PROMPT.format(
            brand_name=brand_name,
            brand_name_upper=brand_name.upper(),
            brand_url=brand_url,
            language=language,
            scrape_data="[See Phase 1 for website data — focus on consumer analysis]",
            document_data=doc_text or "No documents uploaded",
            ecommerce_data=ecom_text,
            review_data=review_text,
            competitors=comp_text,
            competitor_data=comp_detail_text,
            date=date_str,
        )
        # Build consumer research context from desktop research
        consumer_research_block = ""
        if desktop_research and desktop_research.get("consumer_landscape"):
            cl = desktop_research["consumer_landscape"]
            consumer_research_block = "\n\n## Consumer Research (Web Search Findings)\n"
            consumer_research_block += json.dumps(cl, indent=2, default=str)[:8000]

        # ── Survey-backed data: design questionnaire + simulate/use real responses ──
        survey_data_block = ""
        survey_responses = None

        # If real survey responses were uploaded, use them directly
        if survey_mode == "real" and real_survey_responses:
            survey_responses = real_survey_responses
            if survey_responses.get("demographics"):
                demo = survey_responses["demographics"]
                survey_data_block = "\n\n## Real Survey Data (uploaded responses, use these exact numbers for charts)\n"
                survey_data_block += json.dumps({
                    "demographics": demo,
                    "question_data": survey_responses.get("question_data", {}),
                    "category_specific": survey_responses.get("category_specific", []),
                }, indent=2, default=str)[:5000]
                print(f"[analyzer] Using REAL survey responses: {survey_responses.get('sample_size', '?')} respondents, {len(survey_responses.get('question_data', {}))} questions")

        # Otherwise, design + simulate
        if not survey_responses:
            try:
                from pipeline.survey_designer import design_survey
                from pipeline.survey_simulator import simulate_survey_responses

                # Detect category from Phase 1
                category = ""
                if isinstance(p1_result, dict):
                    cap = p1_result.get("capabilities", {})
                    category = cap.get("category", cap.get("product_category", ""))

                questionnaire = await design_survey(
                    brand_name=brand_name,
                    brand_url=brand_url,
                    competitors=competitors or [],
                    category=category,
                    language=language,
                    analysis_context=p2_context[:2000],
                    desktop_research=desktop_research,
                )

                # Build context summary for simulation grounding
                sim_context = f"Category: {category}\n"
                if consumer_research_block:
                    sim_context += consumer_research_block[:2000]
                if p2_context:
                    sim_context += f"\nCompetitive context: {p2_context[:1000]}"

                survey_responses = await simulate_survey_responses(
                    questionnaire=questionnaire,
                    brand_name=brand_name,
                    category=category,
                    brand_context=sim_context,
                    sample_size=200,
                )

                if survey_responses and survey_responses.get("demographics"):
                    demo = survey_responses["demographics"]
                    survey_data_block = "\n\n## Simulated Survey Data (n=200, use these exact numbers for charts)\n"
                    survey_data_block += json.dumps({
                        "demographics": demo,
                        "question_data": {k: v for k, v in survey_responses.get("question_data", {}).items()},
                        "category_specific": survey_responses.get("category_specific", []),
                    }, indent=2, default=str)[:5000]
                    print(f"[analyzer] Survey simulation complete: {len(survey_responses.get('question_data', {}))} questions simulated")
            except Exception as e:
                print(f"[analyzer] Survey simulation failed (non-fatal): {e}")

        # Build enriched Phase 1 context with brand vision/culture/revenue for consumer grounding
        p1_enriched_context = p1_context
        if desktop_research and desktop_research.get("brand_context"):
            bc = desktop_research["brand_context"]
            enrichment_parts = []
            if bc.get("brand_vision"):
                enrichment_parts.append(f"Brand Vision: {bc['brand_vision']}")
            if bc.get("brand_culture"):
                enrichment_parts.append(f"Brand Culture: {bc['brand_culture']}")
            revenue = bc.get("revenue_data", {})
            if isinstance(revenue, dict) and revenue.get("estimated_revenue"):
                enrichment_parts.append(f"Revenue: {revenue['estimated_revenue']}")
                if revenue.get("growth_trajectory"):
                    enrichment_parts.append(f"Growth: {revenue['growth_trajectory']}")
            hero = bc.get("hero_products", [])
            if hero:
                hero_names = [h.get("name", h) if isinstance(h, dict) else str(h) for h in hero[:5]]
                enrichment_parts.append(f"Hero Products: {', '.join(hero_names)}")
            cat_land = bc.get("category_landscape", {})
            if isinstance(cat_land, dict):
                if cat_land.get("category_name"):
                    enrichment_parts.append(f"Category: {cat_land['category_name']}")
                if cat_land.get("market_size"):
                    enrichment_parts.append(f"Market Size: {cat_land['market_size']}")
            if enrichment_parts:
                p1_enriched_context = p1_context + "\n\n### Brand Intelligence (from desktop research)\n" + "\n".join(enrichment_parts)

        # Override the full prompt to only request consumer + summary sections
        consumer_only_prompt = f"""Based on the following Phase 1 and Phase 2 findings, produce the CONSUMER section and final summary.

## Phase 1 Summary (Capabilities)
{p1_enriched_context}

## Phase 2 Summary (Competition)
{p2_context}

## E-Commerce Data
{ecom_text}

## Customer Reviews
{review_text}

## Competitor Data
{comp_detail_text}
{consumer_research_block}
{survey_data_block}

## Uploaded Documents
{doc_text or "No documents uploaded"}

Produce the consumer analysis for {brand_name} ({brand_url}).
Language: {language}. Date: {date_str}.

Return this JSON structure:
{{
  "consumer": {{... the full consumer section as specified in the system prompt ...}},
  "hypothesis_validation": [
    {{
      "id": "H1",
      "statement": "The hypothesis from Phase 1/2 being tested",
      "source_phase": "Phase 1 or Phase 2",
      "status": "confirmed|partially_supported|refuted",
      "evidence": "2-3 sentences citing specific consumer data that validates or contradicts this hypothesis. Reference survey percentages, segment data, or review themes.",
      "implication": "1 sentence on what this means for brand strategy"
    }}
  ],
  "conflict_matrix": {{
    "segments": ["Segment A", "Segment B", "Segment C", "Segment D", "Segment E"],
    "conflicts": [
      {{
        "segment_a": "Segment A name",
        "segment_b": "Segment B name",
        "severity": "high|medium|low",
        "description": "1-2 sentences explaining the core conflict — what Segment A wants that directly contradicts Segment B's preferences. Be specific about the trade-off."
      }}
    ],
    "strategic_implication": "2-3 sentences summarizing what the conflict pattern means for target selection. Which segments are compatible? Which are mutually exclusive?"
  }},
  "evidence_plan": {{
    "hypotheses_to_validate": [
      {{
        "hypothesis": "H1 statement",
        "data_type": "Quantitative survey / Review mining / Social listening",
        "collection_method": "Specific survey questions or data sources",
        "sample_target": "n=200, age 18+, category purchasers"
      }}
    ],
    "questionnaire_summary": {{
      "total_questions": 22,
      "sections": ["Demographics (5 questions)", "Shopping Habits (6)", "Purchase Drivers (4)", "Brand Evaluation (4)", "Lifestyle (3)"],
      "target_respondent": "Description of ideal survey respondent — derive from the actual product category and target market",
      "estimated_duration": "10 minutes"
    }},
    "coverage_gaps": [
      "Data limitation 1 — e.g., 'No in-store shopper journey data available'",
      "Data limitation 2 — e.g., 'Social listening limited to public posts; no DM/community sentiment'"
    ]
  }},
  "summary_and_next_steps": {{
    "capabilities_column": "Paragraph summarizing Step 1 findings",
    "competition_column": "Paragraph summarizing Step 2 findings",
    "consumer_column": "Paragraph summarizing Step 3 findings",
    "closing_insight": "Single sentence tying all three together"
  }},
  "next_steps": ["Action 1", "Action 2", "Action 3", "Action 4"]
}}

CRITICAL RULES:
- If "Simulated Survey Data" is provided above, you MUST use those exact numbers for all demographics charts (generation, ethnicity, income, social media, gender, marital). Do NOT invent your own numbers — use the survey data verbatim. For other charts (shopping, drivers, brand), also use survey question_data values where available.
- If category_specific data is provided (e.g., occupation charts), include those as additional charts with section "Demographics" right after social media.
- Include "gender_data": {{"male_pct": XX, "female_pct": XX}} and "marital_data": {{"married_pct": XX, "single_pct": XX, "divorced_pct": XX}} at consumer top level. Do NOT create a separate gender chart. Generate 15-20 charts in 4 sections: Demographics (4 SEPARATE charts — never combine: generation hbar with chart_type "hbar" and title "GENERATION" with birth-year labels, race/ethnicity vbar with chart_type "vbar" and title "RACE / ETHNICITY", household income vbar with chart_type "vbar" and title "HOUSEHOLD INCOME" with 4 brackets, social media hbar with chart_type "hbar" and title "SOCIAL MEDIA PLATFORM USAGE"), Shopping Habits (5-7: frequency+spend dual, channels hbar, occasions hbar, pre-purchase hbar), Purchase Drivers (3-4: top drivers hbar, premium definition hbar, WTP dual, wordcloud with 40-60 words), Brand Evaluation (4-5: grouped_bar brand metrics, favorite brand donut, switching hbar, association matrix). MUST include at least one "grouped_bar" and one "matrix" chart.

## GENERALIZATION — Category-Agnostic Quality Standards
- This analysis framework works for ANY product category. NEVER use category-specific language
  from examples as templates. Instead, derive ALL terminology, attributes, pain points, and
  purchase drivers from the ACTUAL data provided (e-commerce listings, reviews, desktop research,
  competitor data).
- Chart labels, purchase drivers, pain points, and premium definitions MUST reflect the
  SPECIFIC category being analyzed. Derive these from the brand's actual reviews, competitor
  landscape, and consumer data — NEVER reuse example labels verbatim.
- Segment names, taglines, and narratives must be grounded in the category's actual consumer
  dynamics — not generic archetypes. Use desktop research consumer landscape data, review themes,
  and competitive positioning to inform segment creation.
- The wordcloud MUST contain 40-60 words derived from actual review language and category
  terminology — not generic placeholder words.

## Segment Quality Standards
- Generate 4-5 consumer segments, each with:
  * Evocative 2-word name (GOOD: "Endurance First", "Vivid Collector", "Tender Caregiver")
  * First-person tagline that sounds authentic, not corporate
  * "Meet the [Name]" narrative (5-7 sentences) OPENING with a vivid character scene
    Example: "Meet the Performance Seeker: Picture someone testing the product to its limits in daily use..."
  * Specific what_premium_means (cite attributes + percentages)
  * 4 lifestyle_signals for cultural profiling (social media, music, car brand, key stat)
  * mini_tables with item+pct data for chart rendering — items MUST be category-specific
    (NOT generic "Quality", "Price" — use specific attributes from the actual product category)
- MUST include "deprioritized_segments" array: for EACH non-primary segment, state the specific
  strategic risk (e.g., "Promotion-driven, competing here risks compressing margins and weakening
  premium positioning. Too narrow to build long-term brand authority around.")
- MUST include "competitive_fares" object: brand_strengths (name competitors and what they win on,
  e.g., "Brand A → Innovation, Brand B → Heritage, Brand C → Value"), category_compromise,
  strategic_opportunity, strategic_question.

## Writing Quality — Non-Negotiable
- State findings as conclusions, not possibilities. Never use hedge words: "likely", "potentially",
  "could", "may", "seems", "appears to", "tends to", "suggests that".
- Write as a senior strategist presenting to a CEO. Every sentence earns its place with evidence
  or strategic implication. No filler, no throat-clearing, no "It is worth noting that".
- Segment narratives must be cinematic: open with a specific scene, not a data dump. The reader
  should SEE the person before reading the numbers.
- Output ONLY JSON."""
        p3_result = await _call_claude(consumer_only_prompt, max_tokens=16000, use_thinking=True)

        # Debug: log what Phase 3 returned
        if isinstance(p3_result, dict):
            p3_keys = list(p3_result.keys())
            consumer_keys = list(p3_result.get("consumer", {}).keys()) if isinstance(p3_result.get("consumer"), dict) else "not a dict"
            print(f"[analyzer] Phase 3 keys: {p3_keys}, consumer keys: {consumer_keys}")
            if "raw_analysis" in p3_result:
                print(f"[analyzer] Phase 3 JSON parse FAILED. Raw text (first 500 chars): {p3_result['raw_analysis'][:500]}")
        else:
            print(f"[analyzer] Phase 3 returned non-dict: {type(p3_result)}")

        # Merge all three phases
        merged = {"brand_name": brand_name, "date": date_str}
        if isinstance(p1_result, dict):
            merged["capabilities"] = p1_result.get("capabilities", {})
            merged["next_steps"] = p1_result.get("next_steps", [])
            # Phase 1 hypotheses + clarity scoring
            if p1_result.get("hypotheses"):
                merged["hypotheses_phase1"] = p1_result["hypotheses"]
            cap = p1_result.get("capabilities", {})
            if cap.get("clarity_scoring"):
                merged["clarity_scoring"] = cap["clarity_scoring"]
        if isinstance(p2_result, dict):
            merged["competition"] = p2_result.get("competition", {})
        if isinstance(p3_result, dict):
            merged["consumer"] = p3_result.get("consumer", {})
            merged["summary_and_next_steps"] = p3_result.get("summary_and_next_steps", {})
            if p3_result.get("next_steps"):
                merged["next_steps"] = p3_result["next_steps"]
            # Phase 3 new fields
            if p3_result.get("hypothesis_validation"):
                merged["hypothesis_validation"] = p3_result["hypothesis_validation"]
            if p3_result.get("conflict_matrix"):
                merged["conflict_matrix"] = p3_result["conflict_matrix"]
            if p3_result.get("evidence_plan"):
                merged["evidence_plan"] = p3_result["evidence_plan"]
        # Attach raw survey question_data for dynamic chart generation in ppt_generator
        if survey_responses and survey_responses.get("question_data"):
            merged["survey_question_data"] = survey_responses["question_data"]
        if survey_responses and survey_responses.get("verbatim_responses"):
            merged["survey_verbatim"] = survey_responses["verbatim_responses"]

        # ── Quality validation: catch gaps before PPT generation ──
        merged = await _validate_and_patch_analysis(merged, brand_name, ecom_text, review_text)

        # ── Strategy coherence judge: cross-section consistency check ──
        merged = await _coherence_judge(merged, brand_name)

        return merged

    elif phase == "brand_reality":
        prompt = BRAND_REALITY_PROMPT.format(
            brand_name=brand_name,
            brand_name_upper=brand_name.upper(),
            brand_url=brand_url,
            language=language,
            scrape_data=scrape_text or "No website data available",
            document_data=doc_text or "No documents uploaded",
            ecommerce_data=ecom_text,
            review_data=review_text,
            date=date_str,
        )
        return await _call_claude(prompt, max_tokens=8000)

    else:  # market_structure
        # Run Phase 1 first to get real capabilities context
        brand_research_block = ""
        if research_text:
            brand_research_block = f"\n\n## Desktop Research (Web Search Findings)\n{research_text}\n"
        p1_prompt = BRAND_REALITY_PROMPT.format(
            brand_name=brand_name,
            brand_name_upper=brand_name.upper(),
            brand_url=brand_url,
            language=language,
            scrape_data=(scrape_text or "No website data available") + brand_research_block,
            document_data=doc_text or "No documents uploaded",
            ecommerce_data=ecom_text,
            review_data=review_text,
            date=date_str,
        )
        p1_result = await _call_claude(p1_prompt, max_tokens=12000)
        p1_context = ""
        if isinstance(p1_result, dict):
            cap = p1_result.get("capabilities", {})
            p1_context = cap.get("capabilities_summary", "")

        # Enrich competitor data with desktop research
        comp_enriched = comp_detail_text
        if desktop_research and desktop_research.get("competitor_profiles"):
            profiles = desktop_research["competitor_profiles"]
            profile_lines = ["\n### Web-Researched Competitor Profiles"]
            for cp in profiles:
                profile_lines.append(
                    f"\n**{cp.get('name', 'Unknown')}** ({cp.get('category_role', 'direct')})\n"
                    f"  Products: {cp.get('product_range', 'N/A')}\n"
                    f"  Pricing: {cp.get('price_range', 'N/A')} ({cp.get('price_positioning', 'N/A')})\n"
                    f"  Target: {cp.get('target_audience', 'N/A')}\n"
                    f"  Differentiator: {cp.get('key_differentiator', 'N/A')}\n"
                )
            comp_enriched = comp_detail_text + "\n".join(profile_lines)

        prompt = MARKET_STRUCTURE_PROMPT.format(
            brand_name=brand_name,
            brand_url=brand_url,
            competitors=comp_text,
            competitor_scrape_data=comp_enriched,
            competitor_ecommerce_data=comp_enriched,
            competitor_review_data=comp_enriched,
            phase1_context=p1_context or "Phase 1 analysis completed — assess competition independently",
        )
        p2_result = await _call_claude(prompt, max_tokens=12000)

        # Merge Phase 1 + Phase 2
        merged = {}
        if isinstance(p1_result, dict):
            merged.update(p1_result)
        if isinstance(p2_result, dict):
            merged.update(p2_result)
        return merged


async def _call_claude(prompt: str, max_tokens: int = 8000, use_thinking: bool = False) -> dict:
    """Call Claude API and parse JSON response. Retries on transient errors.

    Args:
        use_thinking: If True, enable extended thinking for deeper analysis.
            Best for complex consumer/segmentation analysis where reasoning quality matters.
    """
    for attempt in range(4):
        try:
            kwargs = {
                "model": MODEL_OPUS,
                "max_tokens": max_tokens,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            }
            if use_thinking:
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": min(10000, max_tokens // 2),
                }
            response = await asyncio.to_thread(client.messages.create, **kwargs)
            break
        except RateLimitError:
            if attempt < 3:
                wait = 30 * (attempt + 1)
                print(f"[analyzer] Rate limited, waiting {wait}s (attempt {attempt + 1}/4)")
                await asyncio.sleep(wait)
            else:
                raise
        except (APIStatusError, APIConnectionError, APITimeoutError) as e:
            if attempt < 3:
                wait = 10 * (attempt + 1)
                print(f"[analyzer] Transient error ({type(e).__name__}), retrying in {wait}s (attempt {attempt + 1}/4)")
                await asyncio.sleep(wait)
            else:
                raise

    # Extract text from response (may have thinking blocks)
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text = block.text
            break
    if not text:
        # Fallback
        text = response.content[0].text if response.content else ""

    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            return result
    except json.JSONDecodeError:
        pass

    return {"raw_analysis": text}


# ── Post-Analysis Quality Validation ─────────────────────────

async def _validate_and_patch_analysis(
    merged: dict, brand_name: str, ecom_text: str, review_text: str
) -> dict:
    """Inspect merged 3-phase analysis and auto-patch quality gaps.

    Checks for empty/placeholder/generic content across all three phases,
    then uses Claude to fill gaps so PPT generator always receives complete,
    category-specific data.

    Returns the patched merged dict (mutated in place).
    """
    if not client:
        return merged

    gaps = []  # list of (section, field, reason)

    # ── Phase 1: Capabilities ──
    cap = merged.get("capabilities", {})
    if not isinstance(cap, dict) or not cap:
        gaps.append(("capabilities", "*", "entire capabilities section is empty"))
    else:
        # Critical fields that must exist and be non-empty
        for key in ("execution_summary", "product_offer", "product_fundamentals",
                     "pricing_position", "channel_analysis"):
            section = cap.get(key)
            if not section or not isinstance(section, dict):
                gaps.append(("capabilities", key, "missing"))
            elif not section.get("bullets") or len(section.get("bullets", [])) < 2:
                gaps.append(("capabilities", key, "fewer than 2 bullets"))
            elif not section.get("insight"):
                gaps.append(("capabilities", key, "missing insight line"))
        if not cap.get("capabilities_summary"):
            gaps.append(("capabilities", "capabilities_summary", "missing summary paragraph"))
        if not cap.get("brand_challenges") or len(cap.get("brand_challenges", [])) < 1:
            gaps.append(("capabilities", "brand_challenges", "no brand challenges"))

    # ── Phase 2: Competition ──
    comp = merged.get("competition", {})
    if not isinstance(comp, dict) or not comp:
        gaps.append(("competition", "*", "entire competition section is empty"))
    else:
        if not comp.get("market_overview") or not isinstance(comp.get("market_overview"), dict):
            gaps.append(("competition", "market_overview", "missing"))
        competitors = comp.get("competitor_analyses", [])
        if not competitors or len(competitors) < 2:
            gaps.append(("competition", "competitor_analyses", f"only {len(competitors)} competitors (need 3+)"))
        if not comp.get("competition_summary"):
            gaps.append(("competition", "competition_summary", "missing summary"))

    # ── Phase 3: Consumer ──
    consumer = merged.get("consumer", {})
    if not isinstance(consumer, dict) or not consumer:
        gaps.append(("consumer", "*", "entire consumer section is empty"))
    else:
        segments = consumer.get("segments", [])
        if not segments or len(segments) < 3:
            gaps.append(("consumer", "segments", f"only {len(segments)} segments (need 4-5)"))
        else:
            for i, seg in enumerate(segments):
                if not seg.get("narrative") or len(seg.get("narrative", "")) < 50:
                    gaps.append(("consumer", f"segments[{i}].narrative", "missing or too short"))
                if not seg.get("demographics"):
                    gaps.append(("consumer", f"segments[{i}].demographics", "missing"))
        if not consumer.get("key_insights") or len(consumer.get("key_insights", [])) < 2:
            gaps.append(("consumer", "key_insights", "fewer than 2 key insights"))
        if not consumer.get("target_recommendation"):
            gaps.append(("consumer", "target_recommendation", "missing target recommendation"))

    # ── Summary & Next Steps ──
    summary = merged.get("summary_and_next_steps", {})
    for col in ("capabilities_column", "competition_column", "consumer_column", "closing_insight"):
        if not summary.get(col) or len(summary.get(col, "")) < 20:
            gaps.append(("summary_and_next_steps", col, "missing or too short"))

    if not gaps:
        print(f"[analyzer] Quality validation passed — no gaps found")
        return merged

    print(f"[analyzer] Quality validation found {len(gaps)} gap(s):")
    for section, field, reason in gaps:
        print(f"  - {section}.{field}: {reason}")

    # ── Auto-patch with Claude ──
    gap_descriptions = "\n".join(
        f"- {section}.{field}: {reason}" for section, field, reason in gaps
    )

    # Build context from available data
    context_parts = []
    if cap.get("capabilities_summary"):
        context_parts.append(f"Capabilities summary: {cap['capabilities_summary'][:500]}")
    if comp.get("competition_summary"):
        context_parts.append(f"Competition summary: {comp['competition_summary'][:500]}")
    if ecom_text:
        context_parts.append(f"E-commerce data: {ecom_text[:1500]}")
    if review_text:
        context_parts.append(f"Review data: {review_text[:1500]}")
    existing_context = "\n\n".join(context_parts) if context_parts else "Limited data available."

    patch_prompt = f"""You are patching gaps in a brand analysis for {brand_name}.

## Existing Analysis (partial)
{json.dumps(merged, indent=2, default=str)[:8000]}

## Supporting Data
{existing_context}

## Gaps to Fix
{gap_descriptions}

For each gap listed above, generate the missing content. Match the style, depth, and
specificity of the existing analysis — do NOT produce generic/placeholder text.

Return ONLY a JSON object with the patched sections. Use the EXACT same key structure
as the original analysis. Only include the sections/fields that need patching.

Example structure:
{{
  "capabilities": {{
    "capabilities_summary": "...",
    "brand_challenges": [
      {{"title": "...", "bullets": ["...", "..."], "insight": "..."}}
    ]
  }},
  "competition": {{
    "competition_summary": "..."
  }},
  "consumer": {{
    "target_recommendation": {{
      "segment_name": "...",
      "rationale": "...",
      "consumer_summary": "...",
      "summary_consumer": "..."
    }}
  }},
  "summary_and_next_steps": {{
    "capabilities_column": "...",
    "competition_column": "...",
    "consumer_column": "...",
    "closing_insight": "..."
  }}
}}
"""

    try:
        patch_result = await _call_claude(patch_prompt, max_tokens=6000)
        if "raw_analysis" in patch_result:
            print(f"[analyzer] Patch call returned unparseable text, skipping auto-patch")
            return merged

        # Deep-merge patches into merged dict
        patched_count = 0
        for section_key, patch_data in patch_result.items():
            if section_key not in merged or not isinstance(merged.get(section_key), dict):
                merged[section_key] = patch_data
                patched_count += 1
                continue
            if isinstance(patch_data, dict):
                for field_key, field_val in patch_data.items():
                    existing = merged[section_key].get(field_key)
                    # Only overwrite if the existing value is empty/missing
                    if not existing or (isinstance(existing, str) and len(existing) < 20) or \
                       (isinstance(existing, list) and len(existing) < 2):
                        merged[section_key][field_key] = field_val
                        patched_count += 1

        print(f"[analyzer] Auto-patched {patched_count} field(s)")

    except Exception as e:
        print(f"[analyzer] Auto-patch failed ({e}), returning analysis as-is")

    return merged


async def _coherence_judge(analysis: dict, brand_name: str) -> dict:
    """Cross-section strategy coherence check.

    Reads the full analysis and flags/fixes contradictions between sections:
    - competition says X wins, but target recommendation ignores X
    - capabilities highlight a strength that consumer data contradicts
    - segment narrative conflicts with demographic data
    """
    if not client:
        return analysis

    # Build a compact summary for the judge
    sections = {}
    cap = analysis.get("capabilities", {})
    if cap:
        sections["capabilities_insight"] = cap.get("execution_summary", {}).get("insight", "")
        sections["product_insight"] = cap.get("product_offer", {}).get("insight", "")

    comp = analysis.get("competition", {})
    if comp:
        sections["competition_summary"] = comp.get("competition_summary", "")

    consumer = analysis.get("consumer", {})
    if consumer:
        sections["consumer_summary"] = consumer.get("consumer_summary", "")
        target = consumer.get("target_recommendation", {})
        if target:
            sections["target_segment"] = target.get("primary_segment", "")
            sections["target_rationale"] = " | ".join(target.get("rationale_bullets", [])[:3])
            sections["target_insight"] = target.get("insight", "")
        segments = consumer.get("segments", [])
        if segments:
            sections["segments"] = [
                {"name": s.get("name"), "size_pct": s.get("size_pct"), "tagline": s.get("tagline")}
                for s in segments[:5]
            ]

    if len(sections) < 3:
        return analysis  # Not enough data to judge

    try:
        import json as _json
        summary = _json.dumps(sections, indent=1, ensure_ascii=False, default=str)[:4000]

        response = await asyncio.to_thread(
            client.messages.create,
            model=MODEL_SONNET,
            max_tokens=800,
            messages=[{"role": "user", "content": f"""You are a senior brand strategist reviewing a brand discovery analysis for "{brand_name}".

Check for LOGICAL CONTRADICTIONS between sections. Specifically:

1. Does the target segment choice contradict the competitive analysis? (e.g., competition says "differentiation wins" but target is the most generic segment)
2. Does the capabilities assessment conflict with consumer data? (e.g., capabilities say brand is "innovation-led" but consumers rank innovation last)
3. Is the target rationale actually supported by the segment data? (e.g., claims "highest spend" but another segment spends more)
4. Are the deprioritization reasons logically sound? (e.g., deprioritizing a segment for being "too small" when it's actually 25%)

Analysis summary:
{summary}

If coherent, reply: COHERENT — [one sentence on the strategic logic]
If contradictions found, reply: CONTRADICTIONS — [list each with fix suggestion]

Keep response under 200 words."""}],
        )
        result = response.content[0].text.strip()
        print(f"[coherence_judge] {result[:150]}")

        # If contradictions found, store them for potential future auto-fix
        if "CONTRADICTION" in result.upper():
            analysis["_coherence_issues"] = result

    except Exception as e:
        print(f"[coherence_judge] Check failed: {e}")

    return analysis


# ── Feedback-Aware Section Revision ──────────────────────────

REVISE_SECTION_PROMPT = """You are revising the **{section}** section of a brand discovery report for **{brand_name}**.

## Current {section} analysis
```json
{current_json}
```

## User Feedback
{feedback}

## Instructions
1. Read the user feedback carefully. Each item references a specific slide or general issue.
2. Revise ONLY the parts that the feedback addresses. Do not rewrite content that wasn't criticized.
3. For "insight" feedback: deepen the analysis, add specificity, replace generic observations with concrete findings.
4. For "data" feedback: fix incorrect numbers. If you cannot verify, mark with evidence tier INFERRED.
5. For "image" feedback: update `has_image`, `image_keywords`, or `banner_description` fields so the image collector can find better matches.
6. For "text" feedback: fix wording, shorten overly long bullets (≤350 chars), fix typos.
7. For "layout" feedback: adjust content structure (e.g., reduce bullet count, split dense slides).
8. Preserve the EXACT same JSON structure and all field names. Return the complete revised section.
9. Maintain the authoritative, insight-driven tone. No hedge words (avoid, perhaps, might, could).
10. All slide titles must remain ALL CAPS.

Return ONLY the revised JSON object for the "{section}" key. No wrapping, no explanation."""


def _identify_affected_submodules(section: str, feedback: str) -> list[str]:
    """Parse feedback to identify which sub-modules of a section are affected.

    For the consumer section, this avoids sending the entire 30k+ char JSON to Claude
    by only revising the parts the user complained about.
    """
    if section != "consumer":
        return []  # capabilities and competition are small enough to revise whole

    feedback_lower = feedback.lower()
    affected = []

    # Map slide content keywords → consumer sub-module keys
    _SUBMODULE_SIGNALS = {
        "segments": ["segment", "persona", "target audience", "demographic profile",
                      "narrative", "tagline", "lifestyle", "mini_table", "pain point",
                      "shopping behavior", "annual spend"],
        "target_recommendation": ["target", "primary segment", "rationale",
                                   "enables", "does not decide"],
        "deprioritized_segments": ["deprioritize", "low priority", "not target",
                                    "strategic risk"],
        "charts": ["chart", "graph", "bar", "donut", "data visualization",
                    "percentage", "survey result", "response data"],
        "key_insights": ["insight", "key finding", "takeaway", "strategic implication"],
        "competitive_fares": ["competitive", "brand strength", "white space",
                               "opportunity", "category compromise"],
        "survey": ["survey", "questionnaire", "sample size", "methodology"],
        "consumer_summary": ["summary", "conclusion", "wrap up", "consumer overview"],
    }

    for submod, signals in _SUBMODULE_SIGNALS.items():
        if any(sig in feedback_lower for sig in signals):
            affected.append(submod)

    # If we can't identify specific sub-modules, fall back to full revision
    if not affected:
        return []

    return affected


async def revise_section(
    analysis: dict,
    section: str,
    brand_name: str,
    feedback: str,
) -> dict | None:
    """Re-analyze a single section of the brand discovery report incorporating user feedback.

    For large sections (consumer), identifies affected sub-modules from feedback and
    only sends those parts to Claude for revision, then merges back. This prevents
    token limit issues and produces more focused revisions.

    Args:
        analysis: Full analysis dict (all phases merged)
        section: "capabilities" | "competition" | "consumer"
        brand_name: Brand name for context
        feedback: Structured feedback summary from _build_feedback_summary()

    Returns:
        Revised section dict, or None if revision fails.
    """
    if not client:
        print("[revise_section] No API client, skipping revision")
        return None

    current_section = analysis.get(section)
    if not current_section:
        print(f"[revise_section] Section '{section}' not found in analysis")
        return None

    # For large consumer sections, try sub-module revision first
    affected = _identify_affected_submodules(section, feedback)
    current_json = json.dumps(current_section, indent=2, ensure_ascii=False)

    if affected and len(current_json) > 15000:
        print(f"[revise_section] Large '{section}' section ({len(current_json)} chars). "
              f"Revising sub-modules: {affected}")
        return await _revise_submodules(current_section, section, brand_name, feedback, affected)

    # Standard full-section revision (capabilities, competition, or small consumer)
    if len(current_json) > 30000:
        current_json = current_json[:30000] + "\n... (truncated)"

    prompt = REVISE_SECTION_PROMPT.format(
        section=section,
        brand_name=brand_name,
        current_json=current_json,
        feedback=feedback,
    )

    print(f"[revise_section] Revising '{section}' with {len(feedback)} chars of feedback")
    result = await _call_claude(prompt, max_tokens=12000)

    if "raw_analysis" in result:
        print("[revise_section] JSON parse failed on first attempt, retrying...")
        await asyncio.sleep(5)
        result = await _call_claude(prompt, max_tokens=12000)

    if "raw_analysis" in result:
        print("[revise_section] Revision failed — could not parse revised JSON")
        return None

    # The LLM should return the section content directly.
    # If it wrapped it in the section key, unwrap.
    if section in result and len(result) == 1:
        result = result[section]

    print(f"[revise_section] Section '{section}' revised. Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
    return result


REVISE_SUBMODULE_PROMPT = """You are revising part of the **{section}** section of a brand discovery report for **{brand_name}**.

## Sub-module to revise: {submodule_key}
```json
{submodule_json}
```

## User Feedback (relevant to this sub-module)
{feedback}

## Instructions
1. Revise ONLY the content in this sub-module based on the feedback.
2. For "insight" feedback: deepen the analysis with concrete, specific findings.
3. For "data" feedback: fix incorrect numbers. Mark unverifiable data as INFERRED.
4. For "image" feedback: update image-related fields (has_image, image_keywords, banner_description).
5. For "text" feedback: fix wording, enforce ≤350 char bullets, fix typos.
6. For "layout" feedback: restructure content (reduce bullets, split dense sections).
7. Preserve the EXACT same JSON structure and all field names.
8. Authoritative tone only. No hedge words.
9. All slide titles remain ALL CAPS.

Return ONLY the revised JSON for this sub-module. No wrapping, no explanation."""


async def _revise_submodules(
    current_section: dict,
    section: str,
    brand_name: str,
    feedback: str,
    affected: list[str],
) -> dict:
    """Revise only the affected sub-modules of a large section, then merge back."""
    revised_section = dict(current_section)  # shallow copy

    for submod_key in affected:
        submod_data = current_section.get(submod_key)
        if submod_data is None:
            print(f"[revise_submodules] Sub-module '{submod_key}' not found, skipping")
            continue

        submod_json = json.dumps(submod_data, indent=2, ensure_ascii=False)
        if len(submod_json) > 20000:
            submod_json = submod_json[:20000] + "\n... (truncated)"

        prompt = REVISE_SUBMODULE_PROMPT.format(
            section=section,
            brand_name=brand_name,
            submodule_key=submod_key,
            submodule_json=submod_json,
            feedback=feedback,
        )

        print(f"[revise_submodules] Revising '{submod_key}' ({len(submod_json)} chars)")
        result = await _call_claude(prompt, max_tokens=8000)

        if "raw_analysis" in result:
            print(f"[revise_submodules] '{submod_key}' revision failed, keeping original")
            continue

        # Unwrap if Claude wrapped it in the key
        if submod_key in result and len(result) == 1:
            result = result[submod_key]

        revised_section[submod_key] = result
        print(f"[revise_submodules] '{submod_key}' revised successfully")

        # Brief cooldown between sub-module revisions
        if submod_key != affected[-1]:
            await asyncio.sleep(3)

    return revised_section


# ── Input Formatters ──────────────────────────────────────────

def _format_scrape_data(scrape_data: dict) -> str:
    if not scrape_data or not scrape_data.get("pages"):
        return ""
    parts = []
    for page in scrape_data["pages"]:
        parts.append(f"\n### {page.get('title', 'Page')} ({page.get('url', '')})\n{page.get('text', '')[:3000]}\n")
    return "".join(parts)


def _format_documents(documents: list[dict]) -> str:
    if not documents:
        return ""
    parts = []
    for doc in documents:
        parts.append(f"\n### {doc.get('filename', 'Document')}\n{doc.get('text', '')[:5000]}\n")
    return "".join(parts)


def _format_competitor_data(data: list[dict]) -> str:
    if not data:
        return "No competitor discovery data"
    parts = [f"### Auto-Discovered Competitors ({len(data)} found)"]
    for c in data:
        source = c.get("source", "unknown")
        confidence = c.get("confidence", 0)
        role = c.get("category_role", "")
        reason = c.get("reason", "")
        line = f"- {c['name']} (source: {source}, confidence: {confidence:.0%}"
        if role:
            line += f", role: {role}"
        line += ")"
        if reason:
            line += f"\n  {reason}"
        parts.append(line)
    return "\n".join(parts)


def _format_ecommerce(data: dict) -> str:
    if not data:
        return "No e-commerce data"
    parts = []
    if data.get("price_range"):
        pr = data["price_range"]
        parts.append(f"Price Range: ${pr.get('min', 'N/A')} - ${pr.get('max', 'N/A')} (avg ${pr.get('avg', 'N/A')})")
    if data.get("rating_summary"):
        rs = data["rating_summary"]
        parts.append(f"Rating Summary: {rs.get('average', 'N/A')}/5 across {rs.get('total_products', 0)} products ({rs.get('total_reviews', 0)} total reviews)")
    parts.append(f"\n### Products ({len(data.get('products', []))} found)")
    for product in data.get("products", [])[:20]:
        name = product.get("name", "Product")
        price = product.get("price", "N/A")
        rating = product.get("rating", "N/A")
        reviews = product.get("review_count", 0)
        desc = product.get("description", "")[:300]
        features = ", ".join(product.get("features", [])[:5])
        line = f"- {name}: ${price} | {rating}★ ({reviews} reviews)"
        if desc:
            line += f"\n  Description: {desc}"
        if features:
            line += f"\n  Features: {features}"
        parts.append(line)
    return "\n".join(parts) if parts else "No e-commerce data"


def _format_reviews(data: dict) -> str:
    if not data:
        return "No reviews"
    parts = []
    if data.get("summary"):
        s = data["summary"]
        parts.append(f"### Review Summary")
        parts.append(f"Average Rating: {s.get('average_rating', 'N/A')}/5 ({s.get('total_reviews', 0)} reviews)")
        if s.get("rating_distribution"):
            parts.append(f"Rating Distribution: {s['rating_distribution']}")
    if data.get("sentiment"):
        sent = data["sentiment"]
        parts.append(f"\n### Sentiment Analysis")
        parts.append(f"Positive: {sent.get('positive', 0)}% | Neutral: {sent.get('neutral', 0)}% | Negative: {sent.get('negative', 0)}%")
    if data.get("themes"):
        parts.append(f"\n### Top Themes from Reviews")
        themes = data["themes"]
        if isinstance(themes, dict):
            for sentiment_type in ("positive", "negative"):
                for theme in themes.get(sentiment_type, [])[:5]:
                    name = theme.get("theme", theme.get("name", "Theme"))
                    count = theme.get("count", 0)
                    parts.append(f"- {name} ({sentiment_type}): {count} mentions")
                    for quote in theme.get("examples", theme.get("sample_quotes", []))[:2]:
                        parts.append(f'  "{quote}"')
        else:
            for theme in list(themes)[:10]:
                parts.append(f"- {theme.get('theme', 'Theme')}: {theme.get('count', 0)} mentions ({theme.get('sentiment', 'mixed')} sentiment)")
                for quote in theme.get("sample_quotes", [])[:2]:
                    parts.append(f'  "{quote}"')
    parts.append(f"\n### Individual Reviews ({len(data.get('reviews', []))} collected)")
    for review in data.get("reviews", [])[:40]:
        stars = review.get("rating", "")
        title = review.get("title", "")
        text = review.get("text", "")[:300]
        line = f"  [{stars}★]"
        if title:
            line += f" {title} —"
        line += f" {text}"
        parts.append(line)
    return "\n".join(parts) if parts else "No reviews"


def _format_desktop_research(data: dict) -> str:
    """Format desktop research data (from 3-session pipeline) for the analyzer."""
    if not data:
        return ""

    parts = []

    # Brand context (Session 1)
    bc = data.get("brand_context", {})
    if bc and not bc.get("raw_text"):
        bp = bc.get("brand_profile", {})
        if bp:
            parts.append("### Brand Profile (from web research)")
            if bp.get("founding_story"):
                parts.append(f"Founding: {bp['founding_story']}")
            if bp.get("founders"):
                parts.append(f"Founders: {bp['founders']}")
            if bp.get("year_founded"):
                parts.append(f"Founded: {bp['year_founded']}")
            if bp.get("headquarters"):
                parts.append(f"HQ: {bp['headquarters']}")
            milestones = bp.get("key_milestones", [])
            if milestones:
                parts.append(f"Milestones: {'; '.join(milestones[:5])}")
            if bp.get("funding"):
                parts.append(f"Funding: {bp['funding']}")

        op = bc.get("online_presence", {})
        if op:
            parts.append("\n### Online Presence")
            if op.get("website_summary"):
                parts.append(f"Website: {op['website_summary']}")
            sm = op.get("social_media", {})
            for platform in ("instagram", "tiktok", "youtube", "facebook"):
                if sm.get(platform):
                    parts.append(f"  {platform.title()}: {sm[platform]}")
            if op.get("amazon_presence"):
                parts.append(f"Amazon: {op['amazon_presence']}")
            if op.get("other_channels"):
                parts.append(f"Other channels: {op['other_channels']}")

        pos = bc.get("brand_positioning", {})
        if pos:
            parts.append("\n### Brand Positioning Signals")
            if pos.get("target_audience"):
                parts.append(f"Target: {pos['target_audience']}")
            if pos.get("price_positioning"):
                parts.append(f"Price position: {pos['price_positioning']}")
            claims = pos.get("key_claims", [])
            if claims:
                parts.append(f"Key claims: {'; '.join(claims[:5])}")
            diffs = pos.get("differentiators", [])
            if diffs:
                parts.append(f"Differentiators: {'; '.join(diffs[:5])}")
            if pos.get("brand_voice"):
                parts.append(f"Brand voice: {pos['brand_voice']}")

        cat = bc.get("category_landscape", {})
        if cat:
            parts.append("\n### Category Landscape")
            if cat.get("category_name"):
                parts.append(f"Category: {cat['category_name']}")
            if cat.get("market_size"):
                parts.append(f"Market size: {cat['market_size']}")
            if cat.get("growth_rate"):
                parts.append(f"Growth: {cat['growth_rate']}")
            dynamics = cat.get("key_dynamics", [])
            if dynamics:
                parts.append(f"Key dynamics: {'; '.join(dynamics[:5])}")
            trends = cat.get("consumer_trends", [])
            if trends:
                parts.append(f"Consumer trends: {'; '.join(trends[:5])}")

        press = bc.get("press_coverage", [])
        if press:
            parts.append("\n### Press Coverage")
            for article in press[:5]:
                parts.append(f"- {article.get('source', '')}: {article.get('headline', '')} — {article.get('summary', '')}")

        rep = bc.get("reputation_signals", {})
        if rep:
            parts.append(f"\n### Reputation: {rep.get('sentiment', 'unknown')}")
            strengths = rep.get("strengths_mentioned", [])
            if strengths:
                parts.append(f"Praised for: {'; '.join(strengths[:5])}")
            concerns = rep.get("concerns_mentioned", [])
            if concerns:
                parts.append(f"Criticized for: {'; '.join(concerns[:5])}")

        # New enriched research fields (from upgraded managed_agent.py)
        brand_vision = bc.get("brand_vision", "")
        if brand_vision:
            parts.append(f"\n### Brand Vision & Mission\n{brand_vision}")

        brand_culture = bc.get("brand_culture", "")
        if brand_culture:
            parts.append(f"\n### Brand Culture & Values\n{brand_culture}")

        revenue = bc.get("revenue_data", {})
        if revenue and isinstance(revenue, dict):
            parts.append("\n### Revenue & Business Data")
            if revenue.get("estimated_revenue"):
                parts.append(f"Estimated Revenue: {revenue['estimated_revenue']}")
            if revenue.get("growth_trajectory"):
                parts.append(f"Growth: {revenue['growth_trajectory']}")
            if revenue.get("market_share"):
                parts.append(f"Market Share: {revenue['market_share']}")
            if revenue.get("employee_count"):
                parts.append(f"Employees: {revenue['employee_count']}")

        hero_products = bc.get("hero_products", [])
        if hero_products:
            parts.append("\n### Hero Products")
            for hp in hero_products[:8]:
                if isinstance(hp, dict):
                    line = f"- {hp.get('name', 'Product')}"
                    if hp.get("price"):
                        line += f" (${hp['price']})"
                    if hp.get("description"):
                        line += f": {hp['description'][:150]}"
                    if hp.get("bestseller"):
                        line += " ★ BESTSELLER"
                    parts.append(line)
                elif isinstance(hp, str):
                    parts.append(f"- {hp}")

    return "\n".join(parts) if parts else ""


# ── Mock Analysis ─────────────────────────────────────────────

def _mock_analysis(brand_name: str, phase: str = "full") -> dict:
    """Return mock analysis for development/testing."""
    bn = brand_name
    BN = brand_name.upper()

    capabilities = {
        "execution_summary": {
            "title": f"HOW {BN} WAS BUILT: EXECUTION FIRST",
            "bullets": [
                f"{bn} prioritized product quality and pricing over brand building. Messaging is purely functional.",
                f"Amazon-first launch with product iteration over brand — a founder-led, execution-first approach.",
                f"Built sales velocity and reviews, but deferred brand definition — gaps that now limit growth.",
            ],
            "insight": f"{bn}'s success was execution-driven — but execution alone cannot sustain premium growth.",
            "has_image": True,
        },
        "product_offer": {
            "title": "A FUNCTIONAL, FEATURE-LED, VALUE-FOCUSED OFFER",
            "bullets": [
                f"{bn} emphasizes comfort, fit, and affordability. Product pages list functional benefits only.",
                "No aspirational imagery or lifestyle positioning. Communication is purely rational, not emotional.",
                f"Easy to compare on Amazon — drives conversion but positions {bn} as interchangeable.",
            ],
            "insight": f"{bn} presents as a practical solution — a strong product, but not yet a brand.",
            "has_image": True,
        },
        "product_fundamentals": {
            "title": f"PRODUCT FUNDAMENTALS ARE STRONG",
            "bullets": [
                f"{bn}'s core technology matches premium competitors at lower prices.",
                "Competitive features across the product range with growing variety.",
                "Core categories covered but no accessories ecosystem — limiting loyalty drivers.",
            ],
            "insight": f"The product is {bn}'s strongest asset — competitive enough for a premium position.",
        },
        "pricing_position": {
            "title": f"PRICE-PERFORMANCE DEFINES {BN}'S POSITION",
            "bullets": [
                f"{bn} sits below premium competitors with comparable performance. Strong value proposition.",
                "Promotional language (deals, bundles) anchors the brand in accessible tier, not premium.",
                "Drives volume but limits premium perception. Moving up requires brand story, not just price.",
            ],
            "insight": f"{bn}'s role is defined by value, not brand — solid base, but a ceiling if not evolved.",
        },
        "channel_analysis": {
            "title": f"AMAZON DRIVES GROWTH AND TRUST",
            "bullets": [
                f"Primary channel: Amazon with 2,000+ reviews and 4.3+ rating. Amazon's trust does the work.",
                "Brand website (Shopify) is a store, not a brand experience. Minimal lifestyle content.",
                "Social media lacks consistent cadence, engagement strategy, or ambassador programs.",
            ],
            "insight": f"Amazon builds Amazon's brand, not {bn}'s. Equity requires owning the relationship.",
        },
        "brand_challenges": [
            {
                "title": f"THE {BN} NAME CREATES A CHALLENGE",
                "bullets": [
                    "The name signals comfort but may not convey professional credibility or performance.",
                    "Leading competitors carry clear positioning — a generic name risks pigeonholing.",
                    "The name shapes Amazon search impressions and CTR — structural, not cosmetic.",
                ],
                "insight": "A brand name is the first promise — and it may be making the wrong one.",
            },
            {
                "title": "BRAND NARRATIVE AND EMOTIONAL CONNECTION ABSENT",
                "bullets": [
                    "No origin story or mission messaging. The brand says what it sells, not why.",
                    "Top competitors build community and heritage. Even value brands tell a story.",
                    f"Without narrative, {bn} competes on features and price — most vulnerable position.",
                ],
                "insight": "A brand without a story is a commodity — or a canvas waiting to be defined.",
            },
            {
                "title": "THE NEXT STEP IS RESEARCH-LED CLARITY",
                "bullets": [
                    f"{bn} has reached an inflection point: execution alone won't drive next-stage growth.",
                    "Positioning and audience decisions require consumer research, not intuition.",
                    "Strong fundamentals + channel traction = foundation. Delay risks losing territory.",
                ],
                "insight": f"{bn} has built the engine — now it needs a destination.",
            },
        ],
        "capabilities_summary": (
            f"{bn} is execution-driven with strong products and Amazon traction, "
            "but lacks brand narrative and emotional positioning. "
            "Product fundamentals can support a premium position — the brand just hasn't been built yet. "
            "Next steps: consumer insight and competitive clarity."
        ),
        "claims_vs_perception": {
            "brand_claims": [
                "Premium quality and design for active consumers",
                "High-quality fabric technology at accessible prices",
            ],
            "customer_perception": [
                "Comfortable and good value for the price — strong functional satisfaction",
                "Not seen as a 'brand' — viewed as a good Amazon product, not a lifestyle choice",
            ],
            "alignment": "Customers confirm the comfort and value claims — the product delivers on its functional promises.",
            "gaps": "The brand claims 'premium' but customers perceive 'good value' — there is a credibility gap between aspiration and perception that must be closed through brand building, not just product quality.",
        },
    }

    result = {
        "brand_name": bn,
        "date": "APRIL 2026",
        "capabilities": capabilities,
        "next_steps": [
            "Define a clear brand narrative and origin story that goes beyond functional benefits.",
            "Clarify brand architecture — establish the relationship between parent brand and product lines.",
            "Develop emotional positioning that complements existing functional strengths.",
            "Audit visual identity consistency across Amazon, website, and social channels.",
        ],
    }

    if phase == "brand_reality":
        return result

    # Add competition for market_structure and full
    result["competition"] = {
        "market_overview": {
            "title": "A MATURE, WELL-ESTABLISHED CONSUMER PRODUCTS MARKET",
            "competitor_names": ["Competitor A", "Competitor B", "Competitor C", "Competitor D", "Competitor E", "Competitor F", "Competitor G", "Competitor H", "Competitor I", "Competitor J"],
            "bullets": [
                "Market exceeds $10B with clear roles: premium leaders, heritage brands, and value challengers.",
                "Key shifts: wholesale to DTC, Amazon as discovery channel, demand for modern fits and athletic silhouettes.",
                f"Top brands own a clear market role. {bn} competes on features and price — no distinct brand identity yet.",
            ],
            "insight": "Winning brands own a clear role — not by trying to be everything to everyone.",
        },
        "focused_competitors": ["Competitor A", "Competitor B", "Competitor C", "Competitor D", "Competitor E", "Competitor G"],
        "competitor_analyses": [
            {
                "name": "Competitor A",
                "banner_description": "Premium lifestyle pioneer proving products buyers will pay for brand",
                "positioning": [
                    {"label": "Target Audience", "detail": "Young pros (25-40) who see products as lifestyle. Skews female, urban."},
                    {"label": "Price Point", "detail": "$38-$90/piece, firmly premium. Price signals quality."},
                    {"label": "Key Differentiator", "detail": "Created fashion-forward category products. Strong DTC + community."},
                ],
                "key_learnings": [
                    {"label": "Brand-led growth works", "detail": "Proved products buyers pay premium for brand, not just function."},
                    {"label": "Ambassador model scales", "detail": "Influencer program drives acquisition. Community = switching costs."},
                    {"label": "Premium fatigue", "detail": "Some buyers seek premium quality at lower prices. Territory is open."},
                ],
            },
            {
                "name": "Competitor B",
                "banner_description": "Heritage authority — decades of trust, slow to modernize",
                "positioning": [
                    {"label": "Target Audience", "detail": "Broad workforce, value-conscious. Skews older, less brand-sensitive."},
                    {"label": "Price Point", "detail": "$18-$45/piece, accessible mid-market with frequent promos."},
                    {"label": "Key Differentiator", "detail": "84% brand awareness + widest distribution in the category."},
                ],
                "key_learnings": [
                    {"label": "Trust via longevity", "detail": "Decades of credibility newer brands can't easily replicate."},
                    {"label": "Distribution depth", "detail": "Available everywhere but inconsistent brand experience."},
                    {"label": "Slow to modernize", "detail": "Website and social lag behind DTC competitors. Vulnerable."},
                ],
            },
            {
                "name": "Competitor C",
                "banner_description": "Durability icon crossing from industrial into consumer market",
                "positioning": [
                    {"label": "Target Audience", "detail": "Workers who value 'hard work' culture. Strong male appeal."},
                    {"label": "Price Point", "detail": "$25-$55/piece, mid-to-premium. Heritage brand pricing."},
                    {"label": "Key Differentiator", "detail": "Iconic 'built to last' credibility transfers to products."},
                ],
                "key_learnings": [
                    {"label": "Brand transfer works", "detail": "Adjacent category credibility creates instant trust."},
                    {"label": "Limited depth", "detail": "Narrower range — products are an extension, not core business."},
                    {"label": "Gender gap", "detail": "Masculine brand limits appeal to 70% female consumer base."},
                ],
            },
            {
                "name": "Competitor D",
                "banner_description": "Fashion-forward products with modern fits and bold patterns",
                "positioning": [
                    {"label": "Target Audience", "detail": "Style-conscious pros wanting good-looking products. Young, female."},
                    {"label": "Price Point", "detail": "$30-$55/piece, mid-to-premium for design quality."},
                    {"label": "Key Differentiator", "detail": "Bold prints, modern silhouettes, trend-responsive collections."},
                ],
                "key_learnings": [
                    {"label": "Style drives loyalty", "detail": "Buyers choose on style as much as function. High repeat rate."},
                    {"label": "Niche limits scale", "detail": "Fashion-forward appeals to one segment but not mass market."},
                    {"label": "Pattern over platform", "detail": "Innovates on color, not fabric tech. Style+substance gap open."},
                ],
            },
        ],
        "landscape_summary": {
            "market_roles": [
                {"role": "Premium Lifestyle", "brands": ["Competitor A", "Competitor G"], "description": "Brand-led, DTC, aspirational. Highest prices + loyalty."},
                {"role": "Heritage Authority", "brands": ["Competitor B", "Competitor F"], "description": "Decades of trust, wide distribution, but not modern."},
                {"role": "Performance Crossover", "brands": ["Competitor C"], "description": "Adjacent category equity. Durable but limited depth."},
                {"role": "Fashion-Forward", "brands": ["Competitor D", "Competitor E"], "description": "Style-first with modern fits and bold patterns."},
            ],
            "white_space": f"No brand owns 'real performance at accessible price.' {bn}'s fundamentals could fill this gap with a clear brand story.",
            "category_norms": [
                "Comfort/stretch are table stakes — every brand offers 4-way stretch",
                "Color variety expected (20+ colors) and growing",
                "Pocket count/design are key Amazon differentiators",
            ],
        },
        "competition_summary": (
            f"Leading products brands win by owning a clear role — lifestyle, heritage, durability, or style. "
            f"The white space for {bn} is premium product performance at accessible pricing. "
            "Claiming this requires a defined brand strategy, target audience, and consistent execution."
        ),
    }

    if phase == "market_structure":
        return result

    # Add consumer for full — category-agnostic mock data
    result["consumer"] = {
        "overview": f"Consumers who actively research and purchase in this category represent a diverse but segmentable market, with clear behavioral clusters that differ in purchase drivers, channel preferences, and willingness to pay for quality.",
        "research_approach": [
            {"label": "Format", "detail": "Review analysis + e-commerce data mining + secondary research"},
            {"label": "Data Sources", "detail": "Amazon reviews, brand website content, competitor listings, industry reports"},
            {"label": "Participants", "detail": "Active consumers who regularly purchase and use products in this category; primary purchase decision-makers"},
            {"label": "Analysis", "detail": "Sentiment analysis, theme extraction, behavioral clustering, competitive benchmarking"},
            {"label": "Timing", "detail": "APRIL 2026"},
        ],
        "gender_data": {"male_pct": 45, "female_pct": 55},
        "marital_data": {"married_pct": 48, "single_pct": 37, "divorced_pct": 15},
        "charts": [
            {"chart_type": "hbar", "section": "demographics", "title": "GENERATION", "subtitle": "Generation distribution of survey respondents", "categories": ["Gen Z (1997 to 2009)", "Millennials (1981 to 1996)", "Gen X (1965 to 1980)", "Boomers (1946 to 1964)"], "values": [15, 42, 28, 15]},
            {"chart_type": "vbar", "section": "demographics", "title": "RACE / ETHNICITY", "subtitle": "Respondent racial and ethnic composition", "categories": ["White or Caucasian", "Black or African American", "Hispanic or Latino", "Asian", "Other"], "values": [52, 18, 17, 9, 4]},
            {"chart_type": "vbar", "section": "demographics", "title": "HOUSEHOLD INCOME", "subtitle": "Annual household income distribution", "categories": ["Low income", "Lower middle income", "Upper middle income", "High income"], "values": [10, 25, 40, 25]},
            {"chart_type": "hbar", "section": "demographics", "title": "SOCIAL MEDIA PLATFORM USAGE", "subtitle": "Which social media platforms do you frequently use?", "categories": ["Facebook", "YouTube", "Instagram", "TikTok", "Snapchat", "X/Twitter", "LinkedIn", "Other"], "values": [72, 70, 60, 52, 35, 30, 25, 5]},
            {"chart_type": "dual", "title": "PURCHASE FREQUENCY AND ANNUAL SPEND", "subtitle": "How often and how much respondents spend", "left_type": "donut", "left_title": "Purchase frequency (past 12 months)", "left_categories": ["Monthly+", "Every 2-3 months", "2-3x/year", "Once/year", "When needed"], "left_values": [15, 35, 30, 12, 8], "right_type": "hbar", "right_title": "Annual spend in category", "right_categories": ["Under $50", "$50-$99", "$100-$199", "$200-$499", "$500+"], "right_values": [12, 25, 30, 22, 11]},
            {"chart_type": "hbar", "title": "WHERE CONSUMERS PURCHASE", "subtitle": "Primary purchase channels (select all that apply)", "categories": ["Amazon", "Specialty retailers", "Brand websites (DTC)", "Walmart / Target", "Other online", "In-store"], "values": [62, 42, 38, 35, 22, 18]},
            {"chart_type": "hbar", "title": "PURCHASE TRIGGERS", "subtitle": "What triggers a new purchase?", "categories": ["Replacement / worn out", "Better option discovered", "Seasonal need", "Sale / promotion", "Gift", "New to category"], "values": [58, 42, 30, 25, 15, 10]},
            {"chart_type": "hbar", "title": "PRE-PURCHASE ACTIVITIES", "subtitle": "Steps taken before buying", "categories": ["Read online reviews", "Compare prices", "Visit brand website", "Ask friends/family", "Watch video reviews", "Try in store", "Check social media"], "values": [75, 60, 42, 38, 32, 28, 22]},
            {"chart_type": "hbar", "title": f"WHAT MATTERS MOST IN THIS CATEGORY", "subtitle": "Top purchase drivers (select top 3)", "categories": ["Core performance / quality", "Durability / longevity", "Design / aesthetics", "Price / value", "Brand reputation", "Innovation / features", "Sustainability", "Ease of use"], "values": [58, 45, 38, 35, 28, 22, 18, 15]},
            {"chart_type": "hbar", "title": "WHAT DOES 'PREMIUM' MEAN?", "subtitle": "Consumer definition of premium (select all that apply)", "categories": ["Superior materials / build", "Strong brand reputation", "Modern design / aesthetics", "Longer lasting", "Sustainable / ethical", "Expert endorsements"], "values": [52, 38, 35, 32, 28, 22]},
            {"chart_type": "dual", "title": "WILLINGNESS TO PAY FOR QUALITY", "subtitle": "Price sensitivity and premium willingness", "left_type": "donut", "left_title": "Willing to pay more\nfor quality", "left_categories": ["Strongly agree", "Somewhat agree", "Neutral", "Disagree"], "left_values": [30, 42, 18, 10], "right_type": "hbar", "right_title": "Expected price range\nfor quality product", "right_categories": ["Budget", "Mid-range", "Premium", "Ultra-premium"], "right_values": [10, 35, 40, 15]},
            {"chart_type": "wordcloud", "title": f"WHAT CONSUMERS SAY ABOUT {BN}", "subtitle": "Word frequency from reviews and open-ended responses", "words": {"quality": 100, "value": 90, "durable": 85, "design": 80, "reliable": 75, "affordable": 70, "premium": 65, "performance": 62, "recommend": 58, "innovative": 55, "easy to use": 50, "well made": 48, "functional": 45, "stylish": 42, "worth it": 40, "versatile": 38, "practical": 35, "modern": 32, "sustainable": 28, "love it": 25}},
            {"chart_type": "grouped_bar", "title": "BRAND METRICS — AWARENESS TO ADVOCACY", "subtitle": "Brand performance across key metrics", "horizontal": True, "categories": ["Competitor A", "Competitor B", "Competitor C", "Competitor D", f"{bn}", "Competitor E"], "groups": [{"name": "Awareness", "values": [82, 75, 62, 55, 35, 22]}, {"name": "Purchase", "values": [50, 45, 32, 28, 18, 12]}, {"name": "Satisfaction", "values": [70, 72, 78, 68, 80, 65]}, {"name": "Recommend", "values": [55, 52, 65, 48, 68, 42]}]},
            {"chart_type": "donut", "title": f"FAVORITE BRAND IN CATEGORY", "subtitle": "Which brand is your absolute favorite?", "center_text": "N=200", "categories": ["Competitor A", "Competitor B", "Competitor C", f"{bn}", "Competitor D", "No favorite"], "values": [25, 20, 15, 12, 10, 18]},
            {"chart_type": "hbar", "title": "LIKELIHOOD TO TRY A NEW BRAND", "subtitle": "How open are consumers to switching?", "categories": ["Very likely", "Somewhat likely", "Neutral", "Somewhat unlikely", "Very unlikely"], "values": [20, 35, 25, 14, 6]},
            {"chart_type": "matrix", "title": "BRAND ASSOCIATION MATRIX", "subtitle": "Which brand best fits each description?", "row_labels": ["Best quality", "Best value", "Most innovative", "Most trustworthy", "Most stylish", "Would recommend"], "col_labels": ["Competitor A", "Competitor B", "Competitor C", f"{bn}", "Competitor D"], "values": [[42, 18, 22, 20, 12], [12, 35, 28, 38, 15], [38, 10, 15, 22, 28], [35, 42, 38, 18, 12], [40, 10, 12, 15, 35], [38, 22, 25, 28, 15]]},
        ],
        "verbatim_quotes": [
            {"theme": "Quality & Performance", "quotes": [f"I need {bn} products that actually deliver on their promises", "Quality has gone up — this brand is getting serious", "Performs well but the brand doesn't match the product quality"]},
            {"theme": "Value & Price", "quotes": ["Price is fair for what you get", "Would pay more if the brand felt more premium", "Great value compared to the big names"]},
            {"theme": "Design & Experience", "quotes": ["Love the design but wish there were more options", "The unboxing experience could be better", "Functional but not exciting — needs more personality"]},
        ],
        "segments": [
            {
                "name": "Performance Seeker",
                "tagline": "I want the best-performing product, period",
                "size_pct": 28,
                "narrative": f"The Performance Seeker prioritizes functional excellence above all else. They research extensively, compare specifications, and are willing to pay a premium for products that demonstrably outperform alternatives. They are {bn}'s most valuable potential advocates — if the product wins them, their word-of-mouth sets the category standard.",
                "demographics": {"primary_role": "Demanding power user", "age_skew": "65% under 45 — Millennial-heavy", "income": "35% household income over $100K", "gender_split": "55% female, 45% male"},
                "shopping_behavior": {"annual_spend": "Highest of all segments", "primary_channel": "Amazon + brand DTC", "purchase_frequency": "Most frequent buyers", "brand_loyalty": "Loyal to performance, not logos"},
                "top_needs": ["Superior core performance", "Durability / longevity", "Consistent quality"],
                "pain_points": ["Inconsistent quality across purchases", "Products that don't match marketing claims", "Lack of detailed product information"],
                "what_premium_means": "Proof of superior materials and engineering. Premium = evidence of performance.",
                "lifestyle_signals": [{"category": "Research", "detail": "Heavy pre-purchase researcher — reads reviews, watches comparisons"}, {"category": "Advocacy", "detail": "Recommends products they trust to friends and online communities"}],
            },
            {
                "name": "Style-Driven",
                "tagline": "I want products that express who I am",
                "size_pct": 24,
                "narrative": f"The Style-Driven buyer sees purchases in this category as a form of self-expression. Design, aesthetics, and brand image matter as much as function. They follow trends, engage with brands on social media, and are drawn to products that feel curated and intentional.",
                "demographics": {"primary_role": "Trend-aware consumer", "age_skew": "55% under 35 — Gen Z and young Millennial", "income": "Mixed income levels", "gender_split": "60% female, 40% male"},
                "shopping_behavior": {"annual_spend": "Mid-range", "primary_channel": "Instagram/TikTok discovery → DTC or Amazon", "purchase_frequency": "Moderate — driven by new releases and trends", "brand_loyalty": "Moderate — follows brands with strong visual identity"},
                "top_needs": ["Modern design / aesthetics", "Color and style variety", "Brand with personality"],
                "pain_points": ["Limited color/style options", "Brands that feel generic or outdated", "Poor social media / community presence"],
                "what_premium_means": "Visual identity + brand story. Premium = a brand worth being seen with.",
                "lifestyle_signals": [{"category": "Social Media", "detail": "Instagram and TikTok-first — discovers products through content"}, {"category": "Identity", "detail": "Products are part of personal brand expression"}],
            },
            {
                "name": "Value Optimizer",
                "tagline": "I want the best I can get for what I spend",
                "size_pct": 22,
                "narrative": f"The Value Optimizer is strategic, not cheap. They compare extensively, hunt deals, and demand quality-per-dollar. They'll pay more for proven value but resist premium pricing without clear justification.",
                "demographics": {"primary_role": "Comparison shopper", "age_skew": "Broadly distributed — 40% Millennial, 30% Gen X", "income": "Predominantly middle income", "gender_split": "52% female, 48% male"},
                "shopping_behavior": {"annual_spend": "Below average", "primary_channel": "Amazon + price comparison sites", "purchase_frequency": "Deliberate — buys on need or deal", "brand_loyalty": "Low — loyal to value, not brand"},
                "top_needs": ["Fair price for quality", "Durability (cost per use)", "Easy returns"],
                "pain_points": ["Paying premium for marginal improvement", "Hidden costs or misleading claims", "Products that don't last"],
                "what_premium_means": "Measurable quality difference that justifies the price gap. Premium = provable ROI.",
                "lifestyle_signals": [{"category": "Shopping", "detail": "Uses price tracking tools and waits for deals"}, {"category": "Reviews", "detail": "Trusts verified purchase reviews over influencer content"}],
            },
            {
                "name": "Loyalist",
                "tagline": "I found what works — don't make me switch",
                "size_pct": 18,
                "narrative": f"The Loyalist has found their go-to brand and sticks with it. Switching is a hassle they'd rather avoid. They value consistency, reliability, and a brand relationship built on repeated positive experiences.",
                "demographics": {"primary_role": "Repeat buyer / habitual purchaser", "age_skew": "Older skew — 45% Gen X and Boomer", "income": "Upper-middle to high income", "gender_split": "50% female, 50% male"},
                "shopping_behavior": {"annual_spend": "Moderate but consistent", "primary_channel": "Brand DTC + auto-replenish", "purchase_frequency": "Regular cycle — predictable", "brand_loyalty": "Very high — switching cost is emotional, not financial"},
                "top_needs": ["Consistent quality across purchases", "Reliable availability", "Brand they trust"],
                "pain_points": ["Product changes without warning", "Discontinuation of favorites", "Declining quality over time"],
                "what_premium_means": "Trusted brand with consistent track record. Premium = reliability you don't have to think about.",
                "lifestyle_signals": [{"category": "Advocacy", "detail": "Strong word-of-mouth — recommends their brand to everyone"}, {"category": "Resistance", "detail": "Skeptical of new brands — needs strong reason to try"}],
            },
            {
                "name": "Minimal Buyer",
                "tagline": "I just need something that works",
                "size_pct": 8,
                "narrative": f"The Minimal Buyer views this category as purely functional. They spend the least, research the least, and have no brand loyalty. They represent the commodity floor of the market.",
                "demographics": {"primary_role": "Infrequent / convenience buyer", "age_skew": "Broadly distributed", "income": "Lower income", "gender_split": "50% female, 50% male"},
                "shopping_behavior": {"annual_spend": "Lowest of all segments", "primary_channel": "Whatever is most convenient", "purchase_frequency": "Only when needed", "brand_loyalty": "None"},
                "top_needs": ["Low price", "Availability", "Good enough quality"],
                "pain_points": ["Having to spend money in this category at all"],
                "what_premium_means": "Not relevant to this segment",
                "lifestyle_signals": [],
            },
        ],
        "target_recommendation": {
            "primary_segment": "Performance Seeker",
            "title": "PRIMARY TARGET: PERFORMANCE SEEKERS",
            "rationale_bullets": [
                f"Defines category standards: Performance Seekers set the quality bar. Winning them validates {bn} for every other segment.",
                f"Highest value: Spend the most annually and willing to pay premium for proven performance.",
                f"Strong product fit: Their unmet needs align with {bn}'s execution strengths — the product delivers, the brand just needs to communicate it.",
                f"Natural channel fit: Already active in {bn}'s primary sales channels.",
            ],
            "insight": f"For Performance Seekers, 'premium' means proof of superior execution — not image or lifestyle. This is a credibility path for {bn}.",
            "enables": ["A clear decision filter for product and quality standards", f"A credible path to brand elevation for {bn}", "Natural spillover to adjacent segments"],
            "does_not_decide": ["Final brand positioning or tone", "Pricing architecture", "Channel strategy"],
        },
        "deprioritized_segments": [
            {"name": "Style-Driven", "size_pct": 24, "reason": "Requires strong visual brand assets not yet built — strong future target after brand elevation."},
            {"name": "Value Optimizer", "size_pct": 22, "reason": "Price-driven positioning risks margin compression and brand dilution."},
            {"name": "Loyalist", "size_pct": 18, "reason": "Already committed to incumbents — high switching cost makes acquisition expensive."},
        ],
        "competitive_fares": {
            "brand_strengths": "Competitor A → Category leadership, Competitor B → Heritage & Trust, Competitor C → Innovation, Competitor D → Value",
            "category_compromise": "The category forces buyers to choose between performance excellence and accessible pricing. No brand owns both.",
            "strategic_opportunity": f"{bn}'s execution strengths position it to bridge this gap — proven performance at accessible prices with a credible modern identity.",
            "strategic_question": f"What would it look like to build a brand that earns the trust of the most demanding consumers — and grows from there?",
        },
        "consumer_summary": (
            f"Performance Seekers define quality standards in this category and spend the most. "
            f"Their needs align directly with {bn}'s product strengths. "
            "Next: define a brand position that resonates with performance-first buyers."
        ),
        "key_insights": [
            {
                "title": "KEY CONSUMER INSIGHTS",
                "bullets": [
                    "Core performance is the #1 driver across all segments. Functional excellence is the entry ticket.",
                    "Amazon dominates discovery and purchase, but DTC shows growing traction among high-value segments.",
                    "Consumers will pay more for quality — but they need a clear brand reason to believe.",
                ],
                "insight": "The market rewards brands that prove performance first and build identity second.",
            },
        ],
    }

    # Add summary & next steps for full report
    result["summary_and_next_steps"] = {
        "capabilities_column": (
            f"{bn} is an execution-driven brand with competitive products and growing market presence, "
            "now facing the need to define a clear brand identity to support long-term growth."
        ),
        "competition_column": (
            "The market is well-established, with leading brands succeeding by owning a clear and "
            "focused role rather than trying to compete across everything at once."
        ),
        "consumer_column": (
            "Performance Seekers spend the most, set the highest standards, and define "
            "what quality means — making them the most valuable segment to win first."
        ),
        "closing_insight": (
            f"Building on these insights, we will define a clear and differentiated brand position for {bn} — "
            "one that resonates with its most demanding customers and scales credibly across the broader market."
        ),
    }

    return result
