"""Web research via Claude Messages API with web_search tool.

Uses the standard Messages API with server-side web_search tool to run
autonomous research — Claude searches the web, reads results, and returns
structured findings in a single API call.

Three-session research pipeline (sequential, context-carrying):
  Session 1: Brand + Category Research — brand background, founding story, category landscape
  Session 2: Competitor Deep Research — 6-10 competitor profiles with positioning, pricing, strengths
  Session 3: Consumer + Market Research — purchase behavior, pain points, channel dynamics, sentiment

Also supports:
  - Competitor discovery (find and analyze competitors)
  - Industry trend research (market size, trends, dynamics)
"""
import json
import re
import asyncio
import time
from anthropic import Anthropic, RateLimitError
from config import ANTHROPIC_API_KEY, MODEL_OPUS

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if not _client and ANTHROPIC_API_KEY:
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _research_sync(system: str, prompt: str, max_tokens: int = 16000, max_searches: int = 10) -> str:
    """Run a research query with web_search tool. Returns the text response.

    Retries up to 3 times on rate limit errors with exponential backoff.
    Logs search queries used for auditability.
    """
    client = _get_client()
    if not client:
        print("[managed_agent] No API client available (missing ANTHROPIC_API_KEY)")
        return ""

    for attempt in range(4):
        try:
            print(f"[managed_agent] Calling API (attempt {attempt+1}/4, max_searches={max_searches})...")
            response = client.messages.create(
                model=MODEL_OPUS,
                max_tokens=max_tokens,
                system=system,
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": max_searches}],
                messages=[{"role": "user", "content": prompt}],
            )

            text_parts = []
            search_count = 0
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                # Log search queries for auditability
                if hasattr(block, "type") and block.type == "tool_use" and hasattr(block, "input"):
                    query = block.input.get("query", "")
                    if query:
                        search_count += 1
                        print(f"[search #{search_count}] {query}")

            result = "".join(text_parts)
            print(f"[managed_agent] Got response: {len(result)} chars, {search_count} searches used")
            return result
        except RateLimitError:
            if attempt < 3:
                wait = 30 * (attempt + 1)
                print(f"[managed_agent] Rate limited, waiting {wait}s (attempt {attempt + 1}/4)")
                time.sleep(wait)
            else:
                raise

    return ""


def _parse_json_response(text: str) -> dict:
    """Extract JSON from response (```json blocks or raw JSON).

    Tries multiple extraction strategies:
    1. ```json code blocks (possibly multiple — pick the largest)
    2. Raw top-level JSON object
    3. Raw top-level JSON array → wrap in {"items": [...]}
    """
    # Strategy 1: All ```json blocks — pick the one that parses to the largest result
    json_blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    best_parsed = None
    best_size = 0
    for block in json_blocks:
        try:
            obj = json.loads(block)
            size = len(block)
            if size > best_size:
                best_parsed = obj
                best_size = size
        except (json.JSONDecodeError, ValueError):
            continue
    if best_parsed is not None:
        if isinstance(best_parsed, list):
            return {"items": best_parsed}
        return best_parsed

    # Strategy 2: Find raw JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: Find raw JSON array
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            arr = json.loads(text[start:end])
            if isinstance(arr, list):
                return {"items": arr}
        except (json.JSONDecodeError, ValueError):
            pass

    return {"raw_text": text}


# ── Competitor Discovery ─────────────────────────────────────

async def discover_competitors_managed(
    brand_name: str,
    brand_url: str = "",
    category_context: str = "",
    max_competitors: int = 8,
) -> list[dict]:
    """Discover competitors using web search.

    Returns:
        [{"name": str, "source": "managed_agent", "confidence": float,
          "category_role": str, "reason": str}]
    """
    if not ANTHROPIC_API_KEY:
        return []

    system = (
        "You are a senior strategist at a top-tier brand consulting firm (McKinsey, Bain, Interbrand level). "
        "You are conducting a rigorous competitive landscape analysis for a client engagement.\n\n"
        "Your standard for competitor identification:\n"
        "- VERIFY each competitor is a REAL brand that currently sells products/services in the same category\n"
        "- Cross-reference multiple sources: industry reports, retailer listings, consumer comparison articles, brand websites\n"
        "- Classify each competitor's strategic role precisely\n"
        "- Exclude parent companies, retailers, or platforms (Amazon, Walmart) — only include product brands\n"
        "- Exclude defunct brands or brands that have pivoted away from the category\n"
        "- Use official brand names with correct capitalization\n\n"
        "Return your final answer as a JSON code block:\n"
        "```json\n"
        '{"competitors": [{"name": "Brand", "category_role": "direct|aspirational|adjacent", '
        '"reason": "1-sentence strategic rationale", "confidence": 0.95, '
        '"price_tier": "value|mid|premium|luxury"}]}\n'
        "```"
    )

    prompt = f"Conduct a competitive landscape analysis for '{brand_name}'.\n"
    if brand_url:
        prompt += f"Website: {brand_url}\n"
    if category_context:
        prompt += f"Known context: {category_context}\n"
    prompt += (
        f"\nIdentify {max_competitors} competitors through systematic desktop research:\n\n"
        f"1. DISCOVER the category: Search '{brand_name}' to understand exactly what they sell, "
        f"their price tier, and target consumer\n"
        f"2. MAP direct competitors: Search '{brand_name} competitors', '{brand_name} vs', "
        f"and '{brand_name} alternatives' — find brands consumers actively compare\n"
        f"3. IDENTIFY category leaders: Search the product category + 'best brands', 'market leaders', "
        f"'industry report' — find the top players by market share and brand equity\n"
        f"4. SCAN retail adjacency: Search Amazon, retailer category pages, and 'best [category] 2024/2025' "
        f"roundups to find brands that compete for the same shelf/search position\n"
        f"5. SPOT emerging threats: Search '[category] new brands', '[category] startup', "
        f"'[category] trending' — find disruptors the client should watch\n\n"
        f"For each competitor, verify they are a real, active brand in the same product category. "
        f"Include a mix of: 3-4 direct head-to-head competitors, 2-3 category leaders/incumbents, "
        f"and 1-2 emerging or aspirational brands.\n\n"
        "Return the JSON result with the competitors array."
    )

    result_text = await asyncio.to_thread(_research_sync, system, prompt, max_tokens=6000, max_searches=15)

    parsed = _parse_json_response(result_text)
    competitors = parsed.get("competitors", [])
    result = []
    for c in competitors[:max_competitors]:
        result.append({
            "name": c.get("name", "Unknown"),
            "source": "managed_agent",
            "confidence": float(c.get("confidence", 0.8)),
            "url": c.get("url"),
            "category_role": c.get("category_role", "direct"),
            "reason": c.get("reason", ""),
        })
    return result


# ── Industry Trend Research ──────────────────────────────────

async def research_industry_trends(
    brand_name: str,
    brand_url: str = "",
    category: str = "",
) -> dict:
    if not ANTHROPIC_API_KEY:
        return {}

    system = (
        "You are a market research analyst. Research industry trends, market dynamics, "
        "and brand reputation. Return findings as a JSON code block:\n"
        "```json\n"
        '{"market_size": "...", "growth_rate": "...", '
        '"key_trends": [{"trend": "name", "description": "detail", "impact": "high/medium/low"}], '
        '"opportunities": ["..."], "threats": ["..."], '
        '"reputation": {"sentiment": "...", "notable_events": ["..."], "social_mentions": "..."}}\n'
        "```"
    )

    prompt = (
        f"Research the industry and market trends for '{brand_name}'.\n"
        f"Website: {brand_url}\n"
    )
    if category:
        prompt += f"Category: {category}\n"
    prompt += (
        f"\nPlease research:\n"
        f"1. The overall market size and growth rate for this product category\n"
        f"2. 4-6 key industry trends shaping this market right now\n"
        f"3. Emerging opportunities that '{brand_name}' could capitalize on\n"
        f"4. Threats or headwinds in the market\n"
        f"5. '{brand_name}' brand reputation — any notable press, social media sentiment\n\n"
        "Return the JSON result."
    )

    result_text = await asyncio.to_thread(_research_sync, system, prompt, max_tokens=4000, max_searches=5)
    return _parse_json_response(result_text)


# ── Session 1: Brand + Category Research ───────────────────

BRAND_RESEARCH_SYSTEM = (
    "You are a senior brand research analyst at a top-tier strategy consulting firm (Interbrand, "
    "Landor, Kantar level). Your job is to build the most exhaustive, insight-rich profile possible "
    "of a brand through desktop research — as if a client just gave you the brand name and nothing else.\n\n"
    "Your research feeds directly into a board-level Brand Discovery presentation. The output must "
    "read like a strategic narrative from a $200K consulting engagement, not a data dump.\n\n"
    "RESEARCH DEPTH EXPECTED (use ALL your available searches — you have many):\n\n"
    "PHASE A — Brand Identity & Heritage (6-8 searches):\n"
    "1. Brand website: Read hero messaging, navigation, About page, mission/vision statements\n"
    "2. Founding story: founder background, original insight, pivots, key milestones\n"
    "3. Press coverage: media mentions, funding rounds, awards, controversies\n"
    "4. Leadership: CEO/founder interviews, LinkedIn profiles, their strategic vision\n"
    "5. Brand culture: workplace culture, values, sustainability commitments, community programs\n"
    "6. Recent news: product launches, rebrands, partnerships, acquisitions (last 12 months)\n\n"
    "PHASE B — Product & Commercial Reality (6-8 searches):\n"
    "7. Hero product deep-dive: the brand's flagship/bestselling product — exact name, price, features, "
    "what makes it distinctive, Amazon BSR + rating + review count\n"
    "8. Full product line: SKU breadth, price architecture ($XX-$XX), product families\n"
    "9. Sales/revenue data: search for '[brand] revenue', '[brand] sales figures', '[brand] growth' — "
    "find estimates from Statista, news articles, SEC filings, Crunchbase, etc.\n"
    "10. Patent/innovation: proprietary technology, design patents, R&D investments\n"
    "11. Distribution channels: DTC website, Amazon, Walmart, Target, specialty retail, international\n"
    "12. Pricing strategy: compare to competitors, premium/value positioning with specific data\n\n"
    "PHASE C — Digital & Cultural Footprint (6-8 searches):\n"
    "13. Instagram: follower count AND content strategy (lifestyle/product/UGC/educational)\n"
    "14. TikTok: presence, engagement, viral moments, branded hashtag reach\n"
    "15. YouTube: content type, subscriber count, view counts on top videos\n"
    "16. Influencer/celebrity partnerships: named collaborations with reach data\n"
    "17. Customer reviews deep-dive: read actual Amazon/Google reviews, extract sentiment themes\n"
    "18. Visual identity: packaging design, color system, typography, photography style\n\n"
    "PHASE D — Category & Market Context (6-8 searches):\n"
    "19. Category market size + growth rate with year and source\n"
    "20. Category dynamics: what forces are reshaping how brands compete\n"
    "21. Consumer trends: how buyer behavior is evolving in this category\n"
    "22. Regulatory/sustainability factors affecting the category\n"
    "23. International market data if the brand sells globally\n\n"
    "KEY PRINCIPLE: For every finding, note the STRATEGIC IMPLICATION, not just the fact.\n"
    "BAD: 'Instagram followers: 50K'\n"
    "GOOD: 'Instagram: 50K followers with lifestyle-heavy content (outdoor adventures, family moments) "
    "— signals aspirational rather than functional positioning'\n\n"
    "USE ALL YOUR SEARCHES. More data = better analysis. Don't save searches for later — use them now.\n\n"
    "Return your findings as a JSON code block with this structure:\n"
    "```json\n"
    "{\n"
    '  "brand_profile": {\n'
    '    "founding_story": "Rich narrative of how/when/why the brand was started — include founder motivation, original insight, pivots",\n'
    '    "founders": "Founder names, background, and what their background signals about brand DNA",\n'
    '    "headquarters": "Location if found",\n'
    '    "year_founded": "Year or approximate",\n'
    '    "key_milestones": ["Milestone 1 with date and strategic significance", "Milestone 2"],\n'
    '    "funding": "Investment/funding info — what this signals about growth strategy",\n'
    '    "mission_statement": "Exact brand mission/tagline from their website",\n'
    '    "brand_dna": "What the brand fundamentally stands for — the core belief that drives everything",\n'
    '    "brand_vision": "Where the brand is headed — growth ambitions, category expansion, international plans",\n'
    '    "brand_culture": "Internal culture signals — workplace values, employee reviews, leadership style"\n'
    "  },\n"
    '  "revenue_data": {\n'
    '    "estimated_revenue": "Annual revenue estimate with source (e.g., $150M est. per Statista 2024)",\n'
    '    "growth_trajectory": "Revenue growth trend — is it accelerating, plateauing, or declining?",\n'
    '    "market_share": "Estimated market share in primary category if found",\n'
    '    "employee_count": "Number of employees — signals scale of operation"\n'
    "  },\n"
    '  "hero_products": [\n'
    '    {"name": "Product name", "price": "$XX.XX", "rating": "X.X/5", "reviews": "count", "bsr": "BSR if found", "differentiator": "What makes this specific product distinctive"}\n'
    "  ],\n"
    '  "online_presence": {\n'
    '    "website_summary": "2-3 sentences: What the website communicates — hero messaging, visual mood, key claims, navigation priorities (what they put first signals what they value most)",\n'
    '    "social_media": {\n'
    '      "instagram": "Follower count AND content strategy (lifestyle vs product vs UGC vs educational)",\n'
    '      "tiktok": "Presence, follower count, content style, engagement pattern",\n'
    '      "youtube": "Presence, content type (tutorials, reviews, brand films)",\n'
    '      "facebook": "Presence and community engagement level"\n'
    "    },\n"
    '    "content_strategy": "What story are they telling across channels? Educational, aspirational, community-driven, deal-focused?",\n'
    '    "amazon_presence": {\n'
    '      "product_count": "Number of ASINs/listings",\n'
    '      "hero_product": "Their bestseller — name, price, rating, review count, BSR",\n'
    '      "avg_rating": "Average star rating across catalog",\n'
    '      "total_reviews": "Total review count across all products",\n'
    '      "listing_quality": "A+ content? Brand Store? Video? — signals investment level"\n'
    "    },\n"
    '    "other_channels": "Walmart, Target, DTC, wholesale — distribution breadth and what it signals about strategy"\n'
    "  },\n"
    '  "brand_positioning": {\n'
    '    "target_audience": "Who the brand appears to target — be specific about demographics AND psychographics",\n'
    '    "price_positioning": "Exact price range with specific products cited — and where this sits vs category average",\n'
    '    "key_claims": ["Exact claim from website/listings — quote their language", "Claim 2"],\n'
    '    "messaging_pillars": ["Core message 1 the brand repeats across channels", "Message 2", "Message 3"],\n'
    '    "differentiators": ["What the brand says makes it different — with evidence"],\n'
    '    "brand_voice": "2-3 adjectives with evidence (e.g., Clinical and authoritative — uses lab imagery, cites patents, avoids casual language)",\n'
    '    "visual_identity": "Color palette, photography style, packaging design, typography — and what these choices communicate",\n'
    '    "positioning_gaps": ["Where their positioning has holes or inconsistencies"]\n'
    "  },\n"
    '  "category_landscape": {\n'
    '    "category_name": "The product category this brand operates in",\n'
    '    "market_size": "Estimated market size with year and source",\n'
    '    "growth_rate": "YoY or CAGR growth rate with source",\n'
    '    "key_dynamics": [\n'
    '      {"dynamic": "Category force (e.g., DTC disruption)", "detail": "2-3 sentences explaining this force and its implications"},\n'
    '      {"dynamic": "Another force", "detail": "Detail with evidence"}\n'
    "    ],\n"
    '    "consumer_trends": [\n'
    '      {"trend": "Trend name", "evidence": "Specific data or signal supporting this trend"}\n'
    "    ],\n"
    '    "distribution_shifts": "How the category is sold — channel evolution with data",\n'
    '    "category_maturity": "Emerging, growing, mature, declining — with evidence",\n'
    '    "white_space": "Underserved areas or opportunities nobody is addressing"\n'
    "  },\n"
    '  "press_coverage": [\n'
    '    {"headline": "Article title", "source": "Publication", "date": "Date if found", "summary": "Key strategic takeaway — not just what happened but what it means"}\n'
    "  ],\n"
    '  "reputation_signals": {\n'
    '    "sentiment": "positive/neutral/negative/mixed — with evidence breakdown",\n'
    '    "strengths_mentioned": ["What reviewers/press praise — use their actual words"],\n'
    '    "concerns_mentioned": ["What reviewers/press criticize — use their actual words"],\n'
    '    "notable_events": ["Any PR events, recalls, controversies, awards"],\n'
    '    "review_themes": [\n'
    '      {"theme": "Common review theme", "sentiment": "positive|negative", "frequency": "How common this theme is", "sample_quote": "Actual consumer quote if found"}\n'
    "    ]\n"
    "  },\n"
    '  "strategic_assessment": {\n'
    '    "brand_strengths": ["Strength 1 with evidence — what they do well and why it matters strategically"],\n'
    '    "brand_vulnerabilities": ["Vulnerability 1 — where competitors could attack or where they underperform"],\n'
    '    "growth_levers": ["Untapped opportunity 1 — specific and actionable"],\n'
    '    "strategic_tension": "The core strategic tension the brand faces (e.g., premium aspiration vs value-driven customer base)"\n'
    "  }\n"
    "}\n"
    "```"
)

async def research_brand_context(
    brand_name: str,
    brand_url: str = "",
    category: str = "",
) -> dict:
    """Session 1: Research the brand itself and its category landscape."""
    if not ANTHROPIC_API_KEY:
        return {}

    prompt = (
        f"Conduct the most comprehensive desktop research possible on the brand '{brand_name}'.\n"
        f"Website: {brand_url or 'Unknown — please search for it'}\n"
    )
    if category:
        prompt += f"Suspected category: {category}\n"
    prompt += (
        "\nThis is a brand discovery project. The client provided only the brand name — "
        "no documents, no briefing. You need to build a complete picture through web research.\n\n"
        "You have 30 web searches available. USE ALL OF THEM. More data = better strategic analysis.\n\n"
        "MANDATORY SEARCH STRATEGY — execute ALL of these:\n\n"
        "--- BRAND IDENTITY (searches 1-8) ---\n"
        f"1. Search '{brand_name}' → find their website, read hero messaging, About page\n"
        f"2. Search '{brand_name} brand story' or '{brand_name} founded' → founding narrative\n"
        f"3. Search '{brand_name} CEO interview' or '{brand_name} founder interview' → vision, strategy\n"
        f"4. Search '{brand_name} mission vision values' → brand DNA, culture\n"
        f"5. Search '{brand_name} news 2025' or '{brand_name} latest' → recent developments\n"
        f"6. Search '{brand_name} funding' or '{brand_name} investors' → financial backing\n"
        f"7. Search '{brand_name} awards' or '{brand_name} press' → media recognition\n"
        f"8. Search '{brand_name} sustainability' or '{brand_name} social responsibility' → values\n\n"
        "--- PRODUCT & COMMERCIAL (searches 9-16) ---\n"
        f"9. Search '{brand_name} Amazon' → hero product with exact price, rating, reviews, BSR\n"
        f"10. Search '{brand_name} best selling' or '{brand_name} most popular' → flagship products\n"
        f"11. Search '{brand_name} product line' or '{brand_name} all products' → SKU breadth\n"
        f"12. Search '{brand_name} revenue' or '{brand_name} sales' → revenue estimates\n"
        f"13. Search '{brand_name} Walmart' or '{brand_name} Target' → retail distribution\n"
        f"14. Search '{brand_name} price comparison' → pricing vs competitors\n"
        f"15. Search '{brand_name} patent' or '{brand_name} technology' → proprietary innovation\n"
        f"16. Search '{brand_name} new product launch 2024 2025' → innovation pipeline\n\n"
        "--- DIGITAL & CULTURAL (searches 17-22) ---\n"
        f"17. Search '{brand_name} Instagram' → follower count, content strategy, engagement\n"
        f"18. Search '{brand_name} TikTok' → viral content, branded hashtags, engagement\n"
        f"19. Search '{brand_name} reviews' → read actual consumer language, sentiment themes\n"
        f"20. Search '{brand_name} influencer' or '{brand_name} collaboration' → partnerships\n"
        f"21. Search '{brand_name} Reddit' → authentic consumer opinions, unfiltered feedback\n"
        f"22. Search '{brand_name} packaging design' → visual identity signals\n\n"
        "--- CATEGORY & MARKET (searches 23-30) ---\n"
        f"23. Identify the product category, then search '[category] market size 2025'\n"
        f"24. Search '[category] industry trends 2025'\n"
        f"25. Search '[category] consumer trends' → how buyer behavior is evolving\n"
        f"26. Search '[category] market report' → find Statista, IBISWorld, or similar data\n"
        f"27. Search '[category] emerging brands' or '[category] disruptors' → competitive dynamics\n"
        f"28. Search '[category] consumer demographics' → who buys in this category\n"
        f"29. Search '[category] sustainability trends' → regulatory/ESG forces\n"
        f"30. Search '[category] global market' → international perspective if relevant\n\n"
        "STRATEGIC IMPLICATIONS — for every finding, think about:\n"
        "- A high BSR + low review count = fast-growing newcomer\n"
        "- Lifestyle imagery on Amazon = aspirational positioning play\n"
        "- No DTC presence = Amazon-dependent, vulnerable to algorithm changes\n"
        "- Celebrity partnerships = cultural capital investment\n"
        "- Patent portfolio = defensible moat\n\n"
        "For Amazon products, always note: product title, price, star rating, number of reviews, "
        "and Best Seller Rank (BSR) if visible. These are critical sales volume proxies.\n\n"
        "BE EXHAUSTIVE. Use every search you have. Return the complete JSON."
    )

    result_text = await asyncio.to_thread(
        _research_sync, BRAND_RESEARCH_SYSTEM, prompt, max_tokens=16000, max_searches=30
    )
    return _parse_json_response(result_text)


# ── Session 2: Competitor Deep Research ────────────────────

COMPETITOR_RESEARCH_SYSTEM = (
    "You are a senior brand strategist at a top-tier consulting firm conducting competitive "
    "intelligence for a high-stakes client engagement. Your research will directly feed into "
    "a board-level brand strategy presentation.\n\n"
    "For each competitor, you must build a profile rich enough for TWO strategic slides:\n"
    "- POSITIONING SLIDE: 3 bold, insight-driven strategic themes that capture HOW this brand wins\n"
    "- KEY LEARNINGS SLIDE: 3 actionable strategic principles the client can apply\n\n"
    "Research depth expected (desktop research standard):\n"
    "- Brand DNA: website messaging, tagline, About page narrative, founding story, mission statement\n"
    "- Product architecture: hero products, price points ($XX.XX), SKU breadth, innovation pipeline\n"
    "- Channel strategy: DTC vs marketplace vs wholesale split, retail partnerships, pop-ups\n"
    "- Digital footprint: website quality, SEO positioning, social media presence and engagement\n"
    "- Consumer perception: Amazon ratings + review count + BSR, Trustpilot/Google reviews\n"
    "- Brand communication: tone of voice, visual identity system, campaign themes\n"
    "- Strategic moats: patents, proprietary tech, community/loyalty programs, celebrity partnerships\n"
    "- Vulnerabilities: pricing complaints, quality issues, distribution gaps, brand perception weaknesses\n"
    "- Recent moves: new launches, rebrands, funding rounds, acquisitions, leadership changes\n\n"
    "Write positioning themes like a strategist, not a journalist. "
    "Bad: 'Has many products'. Good: 'Category architect — owns the consideration set through SKU dominance'.\n\n"
    "Return findings as a JSON code block:\n"
    "```json\n"
    "{\n"
    '  "competitor_profiles": [\n'
    "    {\n"
    '      "name": "Brand Name",\n'
    '      "tagline": "Their actual tagline or positioning statement from their website",\n'
    '      "category_role": "direct|aspirational|adjacent",\n'
    '      "banner_description": "1-line strategic framing of their role (e.g., Design-led steam specialist positioning as minimalist premium alternative)",\n'
    '      "product_range": "What they sell — key product lines with specifics",\n'
    '      "price_range": "$XX - $XX per piece/unit (cite specific products and prices)",\n'
    '      "price_positioning": "value|mid-market|premium|luxury",\n'
    '      "positioning_themes": [\n'
    '        {"label": "3-5 word strategic theme (e.g., Design-led steam specialist)", "detail": "1-2 sentences of evidence from their site/listings/campaigns"},\n'
    '        {"label": "Another theme (e.g., Buy-it-for-life mindset)", "detail": "Evidence of how this positioning manifests"},\n'
    '        {"label": "Third theme (e.g., Chemical-free authority)", "detail": "What emotional or functional territory this claims"}\n'
    "      ],\n"
    '      "key_learnings": [\n'
    '        {"label": "Strategic principle (e.g., Design creates permission)", "detail": "Why this matters — with evidence"},\n'
    '        {"label": "Another principle (e.g., Longevity is the promise)", "detail": "Where they are vulnerable"},\n'
    '        {"label": "Third principle (e.g., Premium invites challenge)", "detail": "Concrete takeaway for the target brand"}\n'
    "      ],\n"
    '      "channel_strategy": "Where they sell — DTC, Amazon, wholesale, retail — with emphasis on primary channel",\n'
    '      "brand_voice": "How they communicate — clinical/aspirational/utilitarian/community-driven",\n'
    '      "social_following": "Instagram followers, TikTok presence, YouTube subscribers if found",\n'
    '      "amazon_stats": "Rating, review count, BSR if found",\n'
    '      "visual_identity": "Key visual signals — minimalist, colorful, medical, lifestyle — and what this communicates"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "```"
)

async def research_competitor_profiles(
    brand_name: str,
    competitors: list[str],
    category: str = "",
    brand_context: dict = None,
) -> list[dict]:
    """Session 2: Deep-research each competitor's positioning, pricing, and strategy."""
    if not ANTHROPIC_API_KEY or not competitors:
        return []

    category_context = ""
    if brand_context:
        cat_data = brand_context.get("category_landscape", {})
        brand_data = brand_context.get("brand_positioning", {})
        category_context = (
            f"Category: {cat_data.get('category_name', category)}\n"
            f"Market size: {cat_data.get('market_size', 'Unknown')}\n"
            f"Brand's price positioning: {brand_data.get('price_positioning', 'Unknown')}\n"
        )

    comp_list = ", ".join(competitors[:10])
    prompt = (
        f"Conduct deep competitive profiles for '{brand_name}' against these competitors:\n"
        f"Competitors: {comp_list}\n\n"
        f"{category_context}\n"
        f"You have 40 web searches. That's roughly 4 searches per competitor. Use them strategically.\n\n"
        f"For EACH competitor, execute this search protocol:\n"
        f"SEARCH 1: '[competitor name]' → visit their website, read About page, hero messaging, tagline\n"
        f"SEARCH 2: '[competitor name] Amazon' → find hero product with exact price, rating, reviews, BSR\n"
        f"SEARCH 3: '[competitor name] vs {brand_name}' or '[competitor name] review' → consumer perception\n"
        f"SEARCH 4: '[competitor name] brand strategy' or '[competitor name] news 2025' → recent moves\n\n"
        f"After individual competitor searches, use remaining searches for:\n"
        f"- '[category] market share by brand' → relative market positions\n"
        f"- '[category] brand comparison' → head-to-head consumer comparisons\n"
        f"- '[category] brand ranking 2025' → category hierarchy\n\n"
        f"POSITIONING THEMES — think like a strategist, not a journalist:\n"
        f"BAD: 'Has many products'  GOOD: 'Category architect — owns the consideration set through SKU dominance'\n"
        f"BAD: 'Popular brand'  GOOD: 'Cultural velocity engine — converts TikTok virality into shelf pull'\n\n"
        f"KEY LEARNINGS — what can {brand_name} specifically learn from each competitor?\n"
        f"Not generic advice. Specific strategic principles with evidence.\n\n"
        f"Research all {len(competitors[:10])} competitors with equal depth. "
        "Return the complete JSON with all competitor profiles."
    )

    result_text = await asyncio.to_thread(
        _research_sync, COMPETITOR_RESEARCH_SYSTEM, prompt, max_tokens=16000, max_searches=40
    )

    if not result_text:
        print(f"[managed_agent] Session 2 returned empty response")
        return []

    parsed = _parse_json_response(result_text)
    profiles = parsed.get("competitor_profiles", [])
    if not profiles:
        # Try common alternative keys
        for key in ["items", "competitors", "profiles", "results"]:
            val = parsed.get(key, [])
            if isinstance(val, list) and len(val) > 0:
                profiles = val
                break
    if not profiles and "raw_text" not in parsed:
        # Try any list value in the parsed dict
        for key in parsed:
            if isinstance(parsed[key], list) and len(parsed[key]) > 0:
                profiles = parsed[key]
                break
    if not profiles and "raw_text" in parsed:
        print(f"[managed_agent] Session 2 JSON parse failed, first 500 chars: {result_text[:500]}")
    print(f"[managed_agent] Session 2 parsed {len(profiles)} competitor profiles (response: {len(result_text)} chars)")
    return profiles


# ── Session 3: Consumer + Market Research ──────────────────

CONSUMER_RESEARCH_SYSTEM = (
    "You are a consumer research analyst at a brand consulting firm. "
    "You research consumer behavior, purchase patterns, and sentiment for a product category.\n\n"
    "Your research feeds directly into consumer segmentation and target audience selection. "
    "The analyst who uses your data will create 4-5 distinct consumer segments, each with:\n"
    "- A vivid character narrative ('Meet the [Segment Name]...')\n"
    "- Demographic and psychographic profiles\n"
    "- Lifestyle signals (social media, music, car brand, cultural markers)\n"
    "- Specific purchase drivers with percentages\n"
    "- What 'premium' means to different buyer types\n\n"
    "So you must find data that enables SEGMENTATION — not just averages. Look for:\n"
    "- How DIFFERENT types of buyers behave differently (by age, income, motivation)\n"
    "- What divides heavy vs light buyers, brand-loyal vs switchers\n"
    "- Lifestyle/cultural signals that differentiate buyer segments\n"
    "- Social media platform preferences by buyer type\n"
    "- Music, fashion, automotive brand affinities of category buyers\n"
    "- What 'premium' means to different buyer types (not just the average)\n\n"
    "Search for industry reports, consumer surveys, market research, Reddit discussions, "
    "review analysis articles, and forum posts. Cite sources when possible.\n\n"
    "Return findings as a JSON code block:\n"
    "```json\n"
    "{\n"
    '  "category_buyers": {\n'
    '    "demographics": {\n'
    '      "gender_split": "e.g., 70% female, 30% male",\n'
    '      "age_distribution": "e.g., 55% Millennial, 25% Gen X, 15% Gen Z",\n'
    '      "income_profile": "Income distribution of category buyers with brackets",\n'
    '      "key_roles": "e.g., nurses, medical assistants — or parents, athletes",\n'
    '      "marital_status": "e.g., 48% married/partnered, 34% single",\n'
    '      "household_composition": "e.g., 62% have children, 55% pet owners"\n'
    "    },\n"
    '    "purchase_behavior": {\n'
    '      "purchase_frequency": "How often they buy — with % breakdowns if available",\n'
    '      "annual_spend": "Average/median annual spend in category with range",\n'
    '      "primary_channels": ["Channel 1 with %", "Channel 2 with %"],\n'
    '      "purchase_triggers": ["Trigger 1 with %", "Trigger 2 with %"],\n'
    '      "pre_purchase_steps": ["Step 1 with %", "Step 2 with %"],\n'
    '      "price_range_expected": "What buyers expect to pay — with brackets"\n'
    "    },\n"
    '    "decision_drivers": {\n'
    '      "top_factors": [{"factor": "name", "importance_pct": 65}],\n'
    '      "premium_definition": [\n'
    '        {"attribute": "What premium means 1 (e.g., superior fabric technology)", "pct": 42},\n'
    '        {"attribute": "What premium means 2 (e.g., premium stitching)", "pct": 38}\n'
    "      ],\n"
    '      "willingness_to_pay": "% willing to pay more for quality — with premium %",\n'
    '      "deal_breakers": ["Deal breaker 1 with %", "Deal breaker 2 with %"]\n'
    "    },\n"
    '    "pain_points": [\n'
    '      {"issue": "Pain point name", "frequency_pct": 45, "detail": "Specific consumer language"}\n'
    "    ],\n"
    '    "brand_dynamics": {\n'
    '      "loyalty_level": "How brand-loyal are category buyers — with %",\n'
    '      "switching_propensity": "% open to trying new brands",\n'
    '      "brand_awareness_order": ["Most known brand with %", "Second with %", "Third with %"],\n'
    '      "favorite_brand": "Declared favorite regardless of price — with %",\n'
    '      "what_builds_trust": ["Trust factor 1 with %", "Trust factor 2 with %"]\n'
    "    },\n"
    '    "lifestyle_signals": {\n'
    '      "social_media_platforms": [{"platform": "YouTube", "usage_pct": 78}, {"platform": "Instagram", "usage_pct": 65}],\n'
    '      "music_preferences": "What genres category buyers prefer if found",\n'
    '      "car_brand_affinities": "Automotive brand preferences if found",\n'
    '      "lifestyle_values": ["Value 1 (e.g., sustainability)", "Value 2 (e.g., convenience)"],\n'
    '      "content_influences": ["What content types drive purchase decisions with %"]\n'
    "    },\n"
    '    "information_sources": {\n'
    '      "social_media": ["Platform 1 with %", "Platform 2 with %"],\n'
    '      "review_platforms": ["Where they read reviews"],\n'
    '      "influencer_impact": "How much influencers/KOLs affect purchase — with %",\n'
    '      "word_of_mouth": "Role of peer recommendations — with %"\n'
    "    },\n"
    '    "segmentation_signals": {\n'
    '      "buyer_types": ["Type 1: description of how they differ", "Type 2: description"],\n'
    '      "motivation_spectrum": "Range from functional to emotional — what drives different groups",\n'
    '      "spend_tiers": ["Heavy spenders: who and why", "Light spenders: who and why"],\n'
    '      "brand_relationship_types": ["Loyal advocates", "Price-driven switchers", "Researchers"]\n'
    "    },\n"
    '    "unmet_needs": [\n'
    '      "Specific unmet need 1 — what no brand currently delivers",\n'
    '      "Specific unmet need 2"\n'
    "    ],\n"
    '    "verbatim_themes": [\n'
    '      {"theme": "Theme name", "sentiment": "positive|negative|mixed", '
    '       "example_quotes": ["Actual consumer quote 1", "Quote 2", "Quote 3"]}\n'
    "    ]\n"
    "  },\n"
    '  "data_sources": ["Source 1 with URL if available", "Source 2"]\n'
    "}\n"
    "```"
)

async def research_consumer_landscape(
    brand_name: str,
    category: str = "",
    brand_context: dict = None,
    competitor_profiles: list[dict] = None,
) -> dict:
    """Session 3: Research consumer behavior, purchase patterns, and sentiment."""
    if not ANTHROPIC_API_KEY:
        return {}

    context_parts = []
    if brand_context:
        cat = brand_context.get("category_landscape", {})
        context_parts.append(f"Category: {cat.get('category_name', category)}")
        context_parts.append(f"Market size: {cat.get('market_size', 'Unknown')}")
        trends = cat.get("consumer_trends", [])
        if trends:
            context_parts.append(f"Known trends: {', '.join(trends[:5])}")

    if competitor_profiles:
        comp_names = [c.get("name", "") for c in competitor_profiles[:8]]
        context_parts.append(f"Key competitors: {', '.join(comp_names)}")
        price_points = [c.get("price_range", "") for c in competitor_profiles[:5] if c.get("price_range")]
        if price_points:
            context_parts.append(f"Competitor pricing: {'; '.join(price_points)}")

    context_block = "\n".join(context_parts)
    cat_name = category
    if brand_context:
        cat_name = brand_context.get("category_landscape", {}).get("category_name", category)

    prompt = (
        f"Research consumer behavior in the '{cat_name or brand_name}' category.\n\n"
        f"Context from prior research:\n{context_block}\n\n"
        f"You have 30 web searches. USE ALL OF THEM. Consumer insight quality depends on search depth.\n\n"
        "MANDATORY SEARCH STRATEGY — execute ALL of these:\n\n"
        "--- DEMOGRAPHICS & PURCHASE BEHAVIOR (searches 1-7) ---\n"
        f"1. Search '{cat_name} consumer demographics' or '{cat_name} buyer demographics'\n"
        f"2. Search '{cat_name} market research report 2025' or '{cat_name} consumer survey'\n"
        f"3. Search '{cat_name} purchase behavior' or 'how consumers buy {cat_name}'\n"
        f"4. Search '{cat_name} purchase frequency' or '{cat_name} annual spending'\n"
        f"5. Search '{cat_name} where to buy' or '{cat_name} shopping channels'\n"
        f"6. Search '{cat_name} consumer trends 2025'\n"
        f"7. Search 'Statista {cat_name}' or 'IBISWorld {cat_name}' for industry data\n\n"
        "--- PAIN POINTS & NEEDS (searches 8-13) ---\n"
        f"8. Search '{cat_name} Reddit' → find actual consumer discussions\n"
        f"9. Search '{cat_name} complaints' or '{cat_name} frustrations'\n"
        f"10. Search '{cat_name} pain points' or 'problems with {cat_name}'\n"
        f"11. Search 'best {cat_name} 2025 review' → see what reviewers praise/criticize\n"
        f"12. Search '{cat_name} buyer guide' → what factors experts recommend evaluating\n"
        f"13. Search '{cat_name} common issues' → product-specific frustrations\n\n"
        "--- BRAND DYNAMICS & LOYALTY (searches 14-18) ---\n"
        f"14. Search '{cat_name} brand loyalty' or '{cat_name} brand preference'\n"
        f"15. Search '{cat_name} brand awareness' or 'most popular {cat_name} brands'\n"
        f"16. Search '{cat_name} brand switching' or 'why switch {cat_name} brands'\n"
        f"17. Search 'what does premium mean {cat_name}' or '{cat_name} premium vs budget'\n"
        f"18. Search '{cat_name} price sensitivity' or 'willingness to pay {cat_name}'\n\n"
        "--- LIFESTYLE & SEGMENTATION SIGNALS (searches 19-25) ---\n"
        f"19. Search '{cat_name} buyer types' or '{cat_name} consumer segments'\n"
        f"20. Search '{cat_name} influencer' or '{cat_name} social media trends'\n"
        f"21. Search '{cat_name} lifestyle' or '{cat_name} culture' → cultural signals\n"
        f"22. Search '{brand_name} target audience' → brand-specific buyer profile\n"
        f"23. Search '{cat_name} gift' or '{cat_name} gifting trends' → purchase occasions\n"
        f"24. Search '{cat_name} sustainability consumer' → eco-conscious buyer segment\n"
        f"25. Search '{cat_name} Gen Z' or '{cat_name} millennial' → generational differences\n\n"
        "--- DEEP DIVES (searches 26-30) ---\n"
        f"26. Search '{cat_name} satisfaction survey' or '{cat_name} NPS' → satisfaction benchmarks\n"
        f"27. Search '{cat_name} brand comparison chart' or '{cat_name} vs' → head-to-head data\n"
        f"28. Search '{cat_name} unboxing' or '{cat_name} first impression' → first-use experience themes\n"
        f"29. Search '{cat_name} community forum' or '{cat_name} enthusiast' → power-user insights\n"
        f"30. Search '{cat_name} gift guide 2025' or 'best {cat_name} under $XX' → purchase occasion data\n\n"
        "CRITICAL: Find REAL DATA with percentages whenever possible. Consumer insight slides need "
        "specific numbers (e.g., '67% of buyers prioritize durability'), not vague observations.\n\n"
        "Look for SEGMENTATION SIGNALS — how different types of buyers behave differently. "
        "The analyst will create 4-5 distinct consumer personas, so you need data that shows "
        "HOW buyers differ, not just the average.\n\n"
        "Return the complete JSON."
    )

    result_text = await asyncio.to_thread(
        _research_sync, CONSUMER_RESEARCH_SYSTEM, prompt, max_tokens=16000, max_searches=30
    )
    return _parse_json_response(result_text)


# ── Full Desktop Research Pipeline ─────────────────────────

async def run_desktop_research(
    brand_name: str,
    brand_url: str = "",
    category: str = "",
    competitors: list[str] = None,
) -> dict:
    """Run the full 3-session desktop research pipeline with retry on failure."""

    # Session 1: Brand Research (retry once if empty)
    print(f"[desktop_research] Session 1: Brand + Category Research for '{brand_name}'")
    brand_context = await research_brand_context(
        brand_name=brand_name,
        brand_url=brand_url,
        category=category,
    )
    if not brand_context or "raw_text" in brand_context:
        print("[desktop_research] Session 1 failed or returned raw text, retrying...")
        time.sleep(15)
        brand_context = await research_brand_context(
            brand_name=brand_name,
            brand_url=brand_url,
            category=category,
        )
    _quality = sum(1 for k in ["brand_profile", "brand_positioning", "category_landscape",
                                "online_presence", "strategic_assessment"]
                   if k in brand_context and brand_context[k])
    print(f"[desktop_research] Session 1 complete: {_quality}/5 sections populated")

    # Session 2: Competitor Research (retry once if empty)
    comp_names = competitors or []
    competitor_profiles = []
    if comp_names:
        print(f"[desktop_research] Session 2: Competitor Profiles for {len(comp_names)} competitors")
        competitor_profiles = await research_competitor_profiles(
            brand_name=brand_name,
            competitors=comp_names,
            category=category,
            brand_context=brand_context,
        )
        if not competitor_profiles:
            print("[desktop_research] Session 2 failed, retrying...")
            time.sleep(15)
            competitor_profiles = await research_competitor_profiles(
                brand_name=brand_name,
                competitors=comp_names,
                category=category,
                brand_context=brand_context,
            )
        print(f"[desktop_research] Session 2 complete: {len(competitor_profiles)} profiles")

    # Session 3: Consumer Research (retry once if empty)
    print(f"[desktop_research] Session 3: Consumer + Market Research")
    consumer_landscape = await research_consumer_landscape(
        brand_name=brand_name,
        category=category,
        brand_context=brand_context,
        competitor_profiles=competitor_profiles,
    )
    if not consumer_landscape or "raw_text" in consumer_landscape:
        print("[desktop_research] Session 3 failed or returned raw text, retrying...")
        time.sleep(15)
        consumer_landscape = await research_consumer_landscape(
            brand_name=brand_name,
            category=category,
            brand_context=brand_context,
            competitor_profiles=competitor_profiles,
        )
    print(f"[desktop_research] Session 3 complete")

    # ── Validate research quality ──
    quality_report = _validate_research_quality(brand_context, competitor_profiles, consumer_landscape)
    print(f"[desktop_research] All 3 sessions complete for '{brand_name}' — Quality: {quality_report['score']}/10")
    if quality_report["warnings"]:
        for w in quality_report["warnings"]:
            print(f"[desktop_research] ⚠ {w}")

    result = {
        "brand_context": brand_context,
        "competitor_profiles": competitor_profiles,
        "consumer_landscape": consumer_landscape,
        "_quality": quality_report,
    }

    # ── Gap-fill: targeted follow-up searches for missing data ──
    if quality_report["score"] < 8:
        print(f"[desktop_research] Quality {quality_report['score']}/10 < 8 — running gap-fill searches...")
        patches = await _fill_research_gaps(
            brand_name=brand_name,
            category=category,
            brand_context=brand_context,
            competitor_profiles=competitor_profiles,
            consumer_landscape=consumer_landscape,
            quality_report=quality_report,
        )
        if patches:
            result = _apply_patches(result, patches)
            # Re-validate after patching
            quality_after = _validate_research_quality(
                result["brand_context"], result["competitor_profiles"], result["consumer_landscape"]
            )
            print(f"[desktop_research] Post-gap-fill quality: {quality_after['score']}/10 "
                  f"(was {quality_report['score']}/10)")
            result["_quality"] = quality_after

    return result


def _validate_research_quality(brand_context: dict, competitor_profiles: list, consumer_landscape: dict) -> dict:
    """Score overall research quality and identify gaps."""
    score = 0
    warnings = []

    # Session 1: Brand Context (max 4 points)
    if isinstance(brand_context, dict) and "raw_text" not in brand_context:
        s1_fields = ["brand_profile", "brand_positioning", "category_landscape",
                      "online_presence", "reputation_signals", "brand_vision",
                      "brand_culture", "revenue_data", "hero_products"]
        populated = sum(1 for k in s1_fields if brand_context.get(k))
        if populated >= 7:
            score += 4
        elif populated >= 5:
            score += 3
        elif populated >= 3:
            score += 2
        else:
            score += 1
            warnings.append(f"Brand context sparse: only {populated}/{len(s1_fields)} fields populated")

        # Check critical sub-fields
        bp = brand_context.get("brand_profile", {})
        if isinstance(bp, dict):
            if not bp.get("founding_story"):
                warnings.append("Missing founding story — critical for execution summary slide")
            if not bp.get("year_founded"):
                warnings.append("Missing founding year")
        if not brand_context.get("hero_products"):
            warnings.append("No hero products found — product offer slide will lack specifics")
        if not brand_context.get("revenue_data"):
            warnings.append("No revenue data found — ok for private brands, but limits analysis depth")
    else:
        warnings.append("Session 1 returned raw text or empty — brand analysis will be superficial")

    # Session 2: Competitor Profiles (max 3 points)
    if isinstance(competitor_profiles, list) and len(competitor_profiles) > 0:
        if len(competitor_profiles) >= 6:
            score += 3
        elif len(competitor_profiles) >= 4:
            score += 2
        else:
            score += 1
            warnings.append(f"Only {len(competitor_profiles)} competitor profiles (target: 6+)")

        # Check profile completeness
        thin_profiles = []
        for cp in competitor_profiles:
            if isinstance(cp, dict):
                filled = sum(1 for k in ["product_range", "price_range", "key_differentiator",
                                          "strengths", "vulnerabilities"]
                             if cp.get(k))
                if filled < 3:
                    thin_profiles.append(cp.get("name", "Unknown"))
        if thin_profiles:
            warnings.append(f"Thin competitor profiles: {', '.join(thin_profiles[:3])}")
    else:
        warnings.append("No competitor profiles — competition section will rely on scraped data only")

    # Session 3: Consumer Landscape (max 3 points)
    if isinstance(consumer_landscape, dict) and "raw_text" not in consumer_landscape:
        cl_fields = ["purchase_behavior", "pain_points", "brand_perception",
                      "channel_dynamics", "price_sensitivity", "demographic_signals"]
        populated = sum(1 for k in cl_fields if consumer_landscape.get(k))
        if populated >= 5:
            score += 3
        elif populated >= 3:
            score += 2
        else:
            score += 1
            warnings.append(f"Consumer landscape sparse: only {populated}/{len(cl_fields)} fields")
    else:
        warnings.append("Session 3 returned raw text or empty — consumer analysis will rely on reviews/survey simulation")

    return {"score": score, "max": 10, "warnings": warnings}


async def _fill_research_gaps(
    brand_name: str,
    category: str,
    brand_context: dict,
    competitor_profiles: list,
    consumer_landscape: dict,
    quality_report: dict,
) -> dict:
    """Targeted follow-up searches to fill specific gaps identified by quality validation.

    Only fires when quality score < 8/10 and specific gaps are actionable.
    Returns updated research dict with patched fields.
    """
    if not ANTHROPIC_API_KEY:
        return {}
    score = quality_report.get("score", 10)
    warnings = quality_report.get("warnings", [])

    if score >= 8 or not warnings:
        print("[gap_fill] Quality score sufficient, skipping follow-up searches")
        return {}

    # Classify gaps into actionable follow-up queries
    gap_queries = []
    cat_name = category
    if isinstance(brand_context, dict):
        cat_name = brand_context.get("category_landscape", {}).get("category_name", category) or category

    for w in warnings:
        w_lower = w.lower()
        if "founding story" in w_lower or "founding year" in w_lower:
            gap_queries.append({
                "target": "brand_context",
                "field": "brand_profile",
                "query": f"Search for '{brand_name} founded', '{brand_name} origin story', "
                         f"'{brand_name} founder interview'. Find the founding year, founder names, "
                         f"and the story behind why/how the brand was created.",
            })
        elif "hero products" in w_lower:
            gap_queries.append({
                "target": "brand_context",
                "field": "hero_products",
                "query": f"Search for '{brand_name} best selling products', '{brand_name} Amazon', "
                         f"'{brand_name} flagship product'. Find product names, prices, ratings, "
                         f"and review counts.",
            })
        elif "competitor profiles" in w_lower or "thin competitor" in w_lower:
            thin_names = []
            for cp in competitor_profiles:
                if isinstance(cp, dict):
                    filled = sum(1 for k in ["product_range", "price_range", "key_differentiator",
                                              "strengths", "vulnerabilities", "positioning_themes"]
                                 if cp.get(k))
                    if filled < 3:
                        thin_names.append(cp.get("name", ""))
            if thin_names:
                for name in thin_names[:3]:
                    gap_queries.append({
                        "target": "competitor_supplement",
                        "field": name,
                        "query": f"Search for '{name} brand', '{name} Amazon', '{name} vs {brand_name}'. "
                                 f"Find their product range, price points, positioning, and what makes "
                                 f"them different from {brand_name}.",
                    })
        elif "consumer landscape sparse" in w_lower:
            gap_queries.append({
                "target": "consumer_landscape",
                "field": "purchase_behavior",
                "query": f"Search for '{cat_name} consumer survey', '{cat_name} purchase behavior 2025', "
                         f"'{cat_name} buyer demographics', '{cat_name} Reddit buying advice'. "
                         f"Find purchase frequency, channel preferences, decision factors with percentages.",
            })
        elif "session 1" in w_lower and ("raw text" in w_lower or "empty" in w_lower):
            gap_queries.append({
                "target": "brand_context",
                "field": "full_retry",
                "query": f"Search for '{brand_name}', '{brand_name} about', '{brand_name} products', "
                         f"'{brand_name} reviews'. Build a basic brand profile: what they sell, "
                         f"who they target, price range, key differentiators.",
            })

    if not gap_queries:
        print("[gap_fill] No actionable gaps identified from warnings")
        return {}

    print(f"[gap_fill] Filling {len(gap_queries)} research gaps...")

    gap_system = (
        "You are a research analyst filling specific data gaps in a brand strategy report. "
        "You have already conducted initial research but some critical fields are missing or thin. "
        "Search thoroughly for the specific information requested. Return ONLY a JSON object "
        "with the requested fields — no markdown, no explanation."
    )

    patches = {}
    for gap in gap_queries[:4]:  # Cap at 4 follow-up calls to control cost
        prompt = (
            f"Brand: {brand_name}\n"
            f"Category: {cat_name}\n\n"
            f"GAP TO FILL: {gap['query']}\n\n"
            f"Return a JSON object with the findings. Use the same field structure as a brand "
            f"strategy report. If you cannot find the information after searching, return "
            f'{{"not_found": true, "reason": "explanation"}}.'
        )

        try:
            result_text = await asyncio.to_thread(
                _research_sync, gap_system, prompt, max_tokens=4000, max_searches=8
            )
            parsed = _parse_json_response(result_text)
            if "raw_text" not in parsed and not parsed.get("not_found"):
                patches[gap["field"]] = parsed
                print(f"[gap_fill] ✓ Filled gap: {gap['field']}")
            else:
                print(f"[gap_fill] ✗ Could not fill gap: {gap['field']}")
        except Exception as e:
            print(f"[gap_fill] ✗ Error filling {gap['field']}: {e}")

    return patches


def _apply_patches(research: dict, patches: dict) -> dict:
    """Merge gap-fill patches into the research results."""
    brand_context = research.get("brand_context", {})
    competitor_profiles = research.get("competitor_profiles", [])

    for field, data in patches.items():
        if field == "brand_profile" and isinstance(data, dict):
            bp = brand_context.get("brand_profile", {})
            if isinstance(bp, dict):
                for k, v in data.items():
                    if v and not bp.get(k):
                        bp[k] = v
                brand_context["brand_profile"] = bp
                print(f"[patch] Merged brand_profile fields: {list(data.keys())}")
        elif field == "hero_products" and isinstance(data, (dict, list)):
            existing = brand_context.get("hero_products", [])
            if not existing:
                products = data if isinstance(data, list) else data.get("hero_products", [])
                if products:
                    brand_context["hero_products"] = products
                    print(f"[patch] Added {len(products)} hero products")
        elif field == "purchase_behavior" and isinstance(data, dict):
            cl = research.get("consumer_landscape", {})
            if isinstance(cl, dict):
                cb = cl.get("category_buyers", {})
                if isinstance(cb, dict):
                    for k, v in data.items():
                        if v and not cb.get(k):
                            cb[k] = v
                    cl["category_buyers"] = cb
                research["consumer_landscape"] = cl
                print(f"[patch] Merged consumer landscape fields")
        elif field == "full_retry" and isinstance(data, dict):
            for k, v in data.items():
                if v and not brand_context.get(k):
                    brand_context[k] = v
            print(f"[patch] Merged full brand context retry")
        else:
            # Competitor supplement — find and patch the matching profile
            for cp in competitor_profiles:
                if isinstance(cp, dict) and cp.get("name", "").lower() == field.lower():
                    for k, v in data.items():
                        if v and not cp.get(k):
                            cp[k] = v
                    print(f"[patch] Enriched competitor profile: {field}")
                    break

    research["brand_context"] = brand_context
    research["competitor_profiles"] = competitor_profiles
    return research
