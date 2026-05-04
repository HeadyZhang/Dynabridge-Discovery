"""Module B API routes — Knowledge Base / Case Library.

FastAPI Router mounted at /api/knowledge.
Does NOT modify any existing Module A routes.
"""
import csv
import io
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base
from module_b.models import (
    CaseProject, CaseFile, DiscoveryEngagement, DiscoverySegment,
    DiscoveryQuestionnaire, QuestionnaireResponse, CrossTabulation,
    ConsumerInsight, MarketGeoData,
)
from module_b.search_index import FullTextIndex

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine)


def _get_db():
    return _Session()


@router.get("/cases")
def list_cases(
    industry: Optional[str] = Query(None),
    has_discovery: Optional[bool] = Query(None),
    has_strategy: Optional[bool] = Query(None),
    has_guidelines: Optional[bool] = Query(None),
    has_survey: Optional[bool] = Query(None),
    challenge_type: Optional[str] = Query(None),
    segment: Optional[str] = Query(None),
):
    """List all case projects with optional filtering.

    Supports filtering by industry, phase flags, challenge type, and segment
    (searches in ai_tags_json for challenge_type and segment).
    """
    db = _get_db()
    q = db.query(CaseProject)

    if industry:
        q = q.filter(CaseProject.industry.ilike(f"%{industry}%"))
    if has_discovery is not None:
        q = q.filter(CaseProject.has_discovery == (1 if has_discovery else 0))
    if has_strategy is not None:
        q = q.filter(CaseProject.has_strategy == (1 if has_strategy else 0))
    if has_guidelines is not None:
        q = q.filter(CaseProject.has_guidelines == (1 if has_guidelines else 0))
    if has_survey is not None:
        q = q.filter(CaseProject.has_survey == (1 if has_survey else 0))
    if challenge_type:
        q = q.filter(CaseProject.ai_tags_json.ilike(f"%{challenge_type}%"))
    if segment:
        q = q.filter(CaseProject.ai_tags_json.ilike(f"%{segment}%"))

    cases = q.order_by(CaseProject.brand_name).all()
    result = [_case_summary(c) for c in cases]
    db.close()
    return result


@router.get("/cases/{case_id}")
def get_case(case_id: int):
    """Get detailed case info including all files."""
    db = _get_db()
    case = db.query(CaseProject).get(case_id)
    if not case:
        db.close()
        raise HTTPException(404, "Case not found")

    files = db.query(CaseFile).filter_by(case_project_id=case_id).order_by(CaseFile.phase, CaseFile.filename).all()

    result = {
        **_case_summary(case),
        "ai_tags": json.loads(case.ai_tags_json) if case.ai_tags_json else {},
        "positioning_summary": case.positioning_summary,
        "files": [_file_dict(f) for f in files],
    }
    db.close()
    return result


@router.get("/search")
def search_cases(
    q: str = Query(..., min_length=1),
    mode: str = Query("fts", regex="^(fts|vector|hybrid)$"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search across all case files.

    Modes:
      - fts: Full-text keyword search (SQLite FTS5)
      - vector: Semantic similarity search (sentence-transformers)
      - hybrid: Combined FTS + vector results
    """
    results = []

    def _extract_case_id(doc_id: str) -> int | None:
        """Extract numeric case_id from doc_id like 'case_5_file_...'."""
        parts = doc_id.split("_")
        if len(parts) >= 2 and parts[0] == "case" and parts[1].isdigit():
            return int(parts[1])
        return None

    def _extract_file_id(doc_id: str) -> str | None:
        """Extract file_id from doc_id like 'case_5_file_ABC123'."""
        if "_file_" in doc_id:
            return doc_id.split("_file_", 1)[1]
        return None

    if mode in ("fts", "hybrid"):
        fts = FullTextIndex()
        fts_results = fts.search(q, limit=limit)
        for r in fts_results:
            results.append({
                "source": "fts",
                "doc_id": r["doc_id"],
                "case_id": _extract_case_id(r["doc_id"]),
                "file_id": _extract_file_id(r["doc_id"]),
                "brand_name": r["brand_name"],
                "filename": r["filename"],
                "snippet": r["snippet"],
                "score": abs(r["rank"]),
            })

    if mode in ("vector", "hybrid"):
        try:
            from module_b.search_index import VectorIndex
            vec = VectorIndex()
            vec_results = vec.search(q, limit=limit)
            for r in vec_results:
                results.append({
                    "source": "vector",
                    "doc_id": r["doc_id"],
                    "case_id": _extract_case_id(r["doc_id"]),
                    "file_id": _extract_file_id(r["doc_id"]),
                    "brand_name": r["brand_name"],
                    "filename": r["filename"],
                    "snippet": "",
                    "score": r["score"],
                })
        except Exception:
            pass

    # Deduplicate by doc_id for hybrid mode, keeping highest score
    if mode == "hybrid":
        seen = {}
        for r in results:
            key = r["doc_id"]
            if key not in seen or r["score"] > seen[key]["score"]:
                seen[key] = r
        results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

    return results[:limit]


@router.get("/stats")
def get_stats():
    """Get aggregate statistics about the case library."""
    db = _get_db()
    total_cases = db.query(CaseProject).count()
    total_files = db.query(CaseFile).count()

    cases = db.query(CaseProject).all()
    industries = {}
    for c in cases:
        ind = c.industry or "Unclassified"
        industries[ind] = industries.get(ind, 0) + 1

    avg_completeness = (
        sum(c.completeness_score for c in cases) / total_cases
        if total_cases > 0
        else 0
    )

    result = {
        "total_cases": total_cases,
        "total_files": total_files,
        "avg_completeness": round(avg_completeness, 2),
        "industries": industries,
        "cases_with_discovery": sum(1 for c in cases if c.has_discovery),
        "cases_with_strategy": sum(1 for c in cases if c.has_strategy),
        "cases_with_guidelines": sum(1 for c in cases if c.has_guidelines),
    }
    db.close()
    return result


@router.get("/cases/{case_id}/similar")
def get_similar_cases(case_id: int, limit: int = Query(3, ge=1, le=10)):
    """Find cases similar to the given case based on industry and content."""
    db = _get_db()
    case = db.query(CaseProject).get(case_id)
    if not case:
        db.close()
        raise HTTPException(404, "Case not found")

    # Build search query from case metadata
    query_parts = [case.brand_name]
    if case.industry:
        query_parts.append(case.industry)
    if case.sub_category:
        query_parts.append(case.sub_category)

    # Try vector search first, fall back to FTS
    results = []
    try:
        from module_b.search_index import VectorIndex
        vec = VectorIndex()
        vec_results = vec.search(" ".join(query_parts), limit=limit + 5)
        seen_brands = {case.brand_name.lower()}
        for r in vec_results:
            if r["brand_name"].lower() not in seen_brands:
                seen_brands.add(r["brand_name"].lower())
                # Look up full case info
                similar = db.query(CaseProject).filter(
                    func.lower(CaseProject.brand_name) == r["brand_name"].lower()
                ).first()
                if similar:
                    results.append({**_case_summary(similar), "similarity_score": r["score"]})
            if len(results) >= limit:
                break
    except Exception:
        pass

    # Fallback: same industry
    if len(results) < limit and case.industry:
        same_industry = db.query(CaseProject).filter(
            CaseProject.industry == case.industry,
            CaseProject.id != case_id,
        ).limit(limit - len(results)).all()
        existing_ids = {r["id"] for r in results}
        for c in same_industry:
            if c.id not in existing_ids:
                results.append({**_case_summary(c), "similarity_score": 0.5})

    db.close()
    return results[:limit]


@router.get("/export")
def export_cases(
    format: str = Query("csv", regex="^(csv|json)$"),
    industry: Optional[str] = Query(None),
):
    """Export case data as CSV or JSON."""
    db = _get_db()
    q = db.query(CaseProject)
    if industry:
        q = q.filter(CaseProject.industry.ilike(f"%{industry}%"))
    cases = q.order_by(CaseProject.brand_name).all()

    if format == "json":
        data = [_case_summary(c) for c in cases]
        db.close()
        return data

    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Brand", "Industry", "Sub-Category", "Files", "Size (MB)",
        "Completeness", "Discovery", "Strategy", "Guidelines", "Survey",
    ])
    for c in cases:
        writer.writerow([
            c.brand_name, c.industry or "", c.sub_category or "",
            c.total_files, c.total_size_mb, f"{c.completeness_score:.0%}",
            "Yes" if c.has_discovery else "No",
            "Yes" if c.has_strategy else "No",
            "Yes" if c.has_guidelines else "No",
            "Yes" if c.has_survey else "No",
        ])
    db.close()

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dynabridge_cases.csv"},
    )


@router.get("/dashboard")
def get_dashboard_data():
    """Aggregated data for the discovery dashboard."""
    db = _get_db()
    cases = db.query(CaseProject).all()

    # Phase coverage across all cases
    phase_coverage = {
        "discovery": sum(1 for c in cases if c.has_discovery),
        "strategy": sum(1 for c in cases if c.has_strategy),
        "guidelines": sum(1 for c in cases if c.has_guidelines),
        "survey": sum(1 for c in cases if c.has_survey),
    }

    # Completeness distribution
    completeness_buckets = {"0-25%": 0, "25-50%": 0, "50-75%": 0, "75-100%": 0}
    for c in cases:
        score = c.completeness_score
        if score < 0.25:
            completeness_buckets["0-25%"] += 1
        elif score < 0.50:
            completeness_buckets["25-50%"] += 1
        elif score < 0.75:
            completeness_buckets["50-75%"] += 1
        else:
            completeness_buckets["75-100%"] += 1

    # Industry breakdown
    industries = {}
    for c in cases:
        ind = c.industry or "Unclassified"
        industries[ind] = industries.get(ind, 0) + 1

    # File type distribution
    files = db.query(CaseFile).all()
    doc_types = {}
    for f in files:
        dt = f.doc_type or "other"
        doc_types[dt] = doc_types.get(dt, 0) + 1

    # Language distribution
    languages = {}
    for f in files:
        lang = f.language_hint or "unknown"
        languages[lang] = languages.get(lang, 0) + 1

    # Top cases by completeness
    top_cases = sorted(cases, key=lambda c: c.completeness_score, reverse=True)[:10]

    db.close()
    return {
        "total_cases": len(cases),
        "total_files": len(files),
        "phase_coverage": phase_coverage,
        "completeness_distribution": completeness_buckets,
        "industries": industries,
        "doc_types": doc_types,
        "languages": languages,
        "top_cases": [
            {"brand_name": c.brand_name, "completeness": c.completeness_score, "files": c.total_files}
            for c in top_cases
        ],
    }


@router.get("/insights")
def list_insights(
    q: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    insight_type: Optional[str] = Query(None),
    geo: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """Cross-case Consumer Insight search — reads from ConsumerInsight table."""
    db = _get_db()
    query = db.query(ConsumerInsight)
    if industry:
        query = query.filter(ConsumerInsight.industry == industry)
    if insight_type:
        query = query.filter(ConsumerInsight.insight_type == insight_type)
    if geo:
        query = query.filter(ConsumerInsight.geo_market == geo)
    if q:
        query = query.filter(ConsumerInsight.insight_text.ilike(f"%{q}%"))

    total = query.count()
    insights = query.limit(limit).all()
    db.close()
    return {
        "total": total,
        "insights": [
            {
                "id": i.id,
                "case_id": i.case_id,
                "brand_name": i.brand_name,
                "industry": i.industry,
                "text": i.insight_text,
                "text_en": i.insight_text_en,
                "type": i.insight_type,
                "segment": i.target_segment,
                "source": i.evidence_source,
                "geo": i.geo_market,
                "confidence": i.confidence,
            }
            for i in insights
        ],
    }


@router.get("/insights/synthesis")
def synthesize_insights(
    industry: Optional[str] = Query(None),
    insight_type: Optional[str] = Query(None),
    geo: Optional[str] = Query(None),
    lang: str = Query("cn"),
):
    """AI cross-case insight synthesis."""
    db = _get_db()
    query = db.query(ConsumerInsight)
    if industry:
        query = query.filter(ConsumerInsight.industry == industry)
    if insight_type:
        query = query.filter(ConsumerInsight.insight_type == insight_type)
    if geo:
        query = query.filter(ConsumerInsight.geo_market == geo)

    insights = query.all()
    db.close()

    if not insights:
        return {"synthesis": "No insights found for the given filters.", "insights_count": 0}

    insights_text = "\n".join(
        f"[{i.brand_name}/{i.industry}] {i.insight_text}"
        for i in insights[:30]
    )

    try:
        import anthropic
        client = anthropic.Anthropic()

        if lang == "en":
            prompt_text = f"""Analyze the following consumer insights from different brand projects and generate a cross-case synthesis.

{insights_text}

Requirements:
1. Identify common findings across brands (3-5 points)
2. Highlight key differences between industries
3. Provide recommendations for new projects

Output in English only. No JSON needed."""
        else:
            prompt_text = f"""分析以下来自不同品牌项目的消费者洞察，生成一份跨案例综合分析。

{insights_text}

要求：
1. 识别跨品牌的共性发现（3-5 条）
2. 标出行业间的关键差异
3. 给出对新项目的建议

用中文输出，不需要 JSON。"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt_text}],
        )
        synthesis = response.content[0].text
    except Exception:
        from collections import Counter
        type_counts = Counter(i.insight_type for i in insights)
        synthesis = f"共 {len(insights)} 条洞察，类型分布: {dict(type_counts)}"

    return {
        "synthesis": synthesis,
        "insights_count": len(insights),
        "filters": {"industry": industry, "type": insight_type, "geo": geo},
    }


# ── Industry Intelligence ─────────────────────────────────


@router.get("/industries/compare")
def compare_industries(industries: str = Query(...)):
    """Multi-industry comparison (comma-separated)."""
    industry_list = [i.strip() for i in industries.split(",") if i.strip()]
    db = _get_db()

    from collections import Counter
    comparison = {}
    for ind in industry_list:
        cases = db.query(CaseProject).filter(CaseProject.industry == ind).all()
        insights = db.query(ConsumerInsight).filter(ConsumerInsight.industry == ind).all()
        type_dist = Counter(i.insight_type for i in insights)

        comparison[ind] = {
            "case_count": len(cases),
            "insight_count": len(insights),
            "insight_types": dict(type_dist),
            "brands": [c.brand_name for c in cases],
        }

    db.close()
    return comparison


@router.get("/industries/{industry}/report")
def generate_industry_report(industry: str):
    """AI-generated industry experience report."""
    db = _get_db()
    cases = db.query(CaseProject).filter(CaseProject.industry == industry).all()
    insights = db.query(ConsumerInsight).filter(ConsumerInsight.industry == industry).all()
    db.close()

    case_summaries = []
    for c in cases:
        tags = {}
        if c.ai_tags_json:
            try:
                tags = json.loads(c.ai_tags_json) if isinstance(c.ai_tags_json, str) else (c.ai_tags_json or {})
            except (json.JSONDecodeError, TypeError):
                pass
        case_summaries.append(
            f"Brand: {c.brand_name}, Challenges: {tags.get('core_challenges', [])}, "
            f"Insights: {tags.get('key_insights', [])}"
        )

    insight_texts = [f"[{i.brand_name}] {i.insight_text}" for i in insights[:20]]

    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": f"""你是 Dynabridge 品牌咨询公司的行业分析专家。
基于以下 {industry} 行业的历史案例数据，生成一份行业经验报告。

案例:
{chr(10).join(case_summaries)}

消费者洞察:
{chr(10).join(insight_texts)}

报告结构（中英双语）：
1. 行业概况（几个客户，什么类型的品牌）
2. 共同挑战和解决模式
3. 消费者画像共性
4. 定价和定位模式
5. 给新客户的建议

直接输出报告文字。"""}],
        )
        return {"report": response.content[0].text, "case_count": len(cases), "insight_count": len(insights)}
    except Exception as e:
        return {
            "report": f"AI report generation unavailable. {len(cases)} cases, {len(insights)} insights in {industry}.",
            "case_count": len(cases),
            "insight_count": len(insights),
        }


@router.get("/industries/{industry}")
def get_industry_detail(industry: str):
    """Deep analysis for a single industry."""
    db = _get_db()
    cases = db.query(CaseProject).filter(CaseProject.industry == industry).all()
    insights = db.query(ConsumerInsight).filter(ConsumerInsight.industry == industry).all()
    db.close()

    return {
        "industry": industry,
        "cases": [
            {
                "id": c.id,
                "brand": c.brand_name,
                "completeness": c.completeness_score,
                "has_discovery": bool(c.has_discovery),
                "has_strategy": bool(c.has_strategy),
                "challenges": _get_challenges(c),
            }
            for c in cases
        ],
        "insights": [
            {"text": i.insight_text, "type": i.insight_type, "brand": i.brand_name}
            for i in insights[:20]
        ],
        "total_insights": len(insights),
    }


@router.get("/industries")
def list_industries():
    """All industries aggregated overview."""
    db = _get_db()
    cases = db.query(CaseProject).all()

    industries: dict[str, dict] = {}
    for case in cases:
        ind = case.industry or "other"
        if ind not in industries:
            industries[ind] = {"brands": [], "case_count": 0, "challenges": [], "insights_count": 0}
        industries[ind]["brands"].append(case.brand_name)
        industries[ind]["case_count"] += 1
        industries[ind]["challenges"].extend(_get_challenges(case))

    for ind in industries:
        count = db.query(ConsumerInsight).filter(ConsumerInsight.industry == ind).count()
        industries[ind]["insights_count"] = count
        industries[ind]["challenges"] = list(set(industries[ind]["challenges"]))[:5]

    db.close()
    return industries


def _get_challenges(case: CaseProject) -> list[str]:
    if not case.ai_tags_json:
        return []
    try:
        tags = json.loads(case.ai_tags_json) if isinstance(case.ai_tags_json, str) else (case.ai_tags_json or {})
        return tags.get("core_challenges", [])
    except (json.JSONDecodeError, TypeError):
        return []


# ── Marketing Intelligence ────────────────────────────────


@router.get("/market-intelligence")
def get_market_intelligence(
    brand: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    market: str = Query("US"),
    keywords: str = Query(""),
    lang: str = Query("cn"),
):
    """GEO trends + consumer insights → marketing intelligence."""
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not keyword_list:
        if brand and brand != "all":
            keyword_list.append(brand)
        if industry and industry != "all":
            keyword_list.append(industry)
        if not keyword_list:
            keyword_list = ["brand"]

    # 1. Google Trends
    trends: dict = {}
    try:
        from module_b.google_trends import GoogleTrendsClient
        gt = GoogleTrendsClient()
        trends["interest_over_time"] = gt.get_interest_over_time(keyword_list, geo=market)
        trends["related_queries"] = gt.get_related_queries(keyword_list[0], geo=market)
        trends["regional_interest"] = gt.get_interest_by_region(keyword_list[0], geo=market)
    except Exception as e:
        trends["error"] = str(e)

    # 2. Consumer Insights
    db = _get_db()
    insights_query = db.query(ConsumerInsight)
    if industry:
        insights_query = insights_query.filter(ConsumerInsight.industry == industry)
    insights = insights_query.limit(20).all()
    insights_data = [
        {"brand": i.brand_name, "text": i.insight_text, "type": i.insight_type}
        for i in insights
    ]
    db.close()

    # 3. AI Marketing Strategy
    strategy: dict = {}
    try:
        import anthropic
        client = anthropic.Anthropic()

        lang_note = "Output all text values in English." if lang == "en" else "所有文本用中文输出。"

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": f"""You are a brand marketing strategist. Based on the following data, create a marketing strategy.

Brand: {brand or 'Unknown'}
Industry: {industry or 'Unknown'}
Target market: {market}
Keywords: {keywords}

Google Trends data:
- Average search interest: {trends.get('interest_over_time', {}).get('averages', {})}
- Related searches: {trends.get('related_queries', {}).get('top', [])[:5]}
- Top regions: {trends.get('regional_interest', [])[:5]}

Consumer insights ({len(insights_data)} total):
{chr(10).join([f"[{i['brand']}] {i['text']}" for i in insights_data[:10]])}

{lang_note}

Output JSON format:
{{
  "executive_summary": "one paragraph summary",
  "content_strategy": {{"recommended": ["...", "..."], "avoid": ["..."], "rationale": "..."}},
  "channel_strategy": {{"primary": ["..."], "secondary": ["..."], "rationale": "..."}},
  "timing_strategy": {{"peak_months": ["..."], "rationale": "..."}},
  "geo_strategy": {{"priority_regions": ["..."], "rationale": "..."}},
  "keyword_strategy": {{"primary": ["..."], "long_tail": ["..."], "rationale": "..."}}
}}

Output JSON only."""}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        strategy = json.loads(text)
    except Exception as e:
        strategy = {"error": str(e)}

    return {
        "brand": brand,
        "industry": industry,
        "market": market,
        "trends": trends,
        "insights": insights_data,
        "strategy": strategy,
    }


@router.get("/market-intelligence/export")
def export_marketing_report(
    brand: str = Query(...),
    industry: str = Query(...),
    market: str = Query("US"),
    keywords: str = Query(""),
):
    """Export marketing intelligence as JSON."""
    return get_market_intelligence(brand=brand, industry=industry, market=market, keywords=keywords)


@router.get("/survey-analytics")
def survey_analytics():
    """Questionnaire analytics overview — survey files, response data, cross-case stats."""
    db = _get_db()

    # Survey files from case library
    survey_files = db.query(CaseFile).filter(
        CaseFile.doc_type.in_(["survey", "consumer_insights"])
    ).all()

    cases_with_surveys = set()
    file_list = []
    for f in survey_files:
        case = db.query(CaseProject).get(f.case_project_id)
        brand = case.brand_name if case else "Unknown"
        cases_with_surveys.add(brand)
        file_list.append({
            "brand_name": brand,
            "filename": f.filename,
            "doc_type": f.doc_type,
            "size_bytes": f.size_bytes,
            "word_count": f.word_count,
        })

    # Questionnaire records
    questionnaires = db.query(DiscoveryQuestionnaire).all()
    total_responses = db.query(QuestionnaireResponse).count()

    # Cross-tabulations
    cross_tabs = db.query(CrossTabulation).count()

    # Engagements with segments
    engagements = db.query(DiscoveryEngagement).count()
    segments = db.query(DiscoverySegment).count()

    db.close()
    return {
        "total_survey_files": len(survey_files),
        "cases_with_surveys": len(cases_with_surveys),
        "survey_files": file_list,
        "questionnaire_count": len(questionnaires),
        "total_responses": total_responses,
        "cross_tabulation_count": cross_tabs,
        "engagement_count": engagements,
        "segment_count": segments,
        "cases_with_survey_data": sorted(cases_with_surveys),
    }


@router.get("/engagements")
def list_engagements():
    """List all discovery engagements with their segments."""
    db = _get_db()
    engagements = db.query(DiscoveryEngagement).order_by(
        DiscoveryEngagement.created_at.desc()
    ).all()

    result = []
    for eng in engagements:
        segments = db.query(DiscoverySegment).filter_by(engagement_id=eng.id).all()
        result.append({
            "id": eng.id,
            "brand_name": eng.brand_name,
            "industry": eng.industry,
            "challenge_type": eng.challenge_type,
            "status": eng.status,
            "analysis_summary": eng.analysis_summary[:500] if eng.analysis_summary else "",
            "segments": [
                {
                    "name_en": s.segment_name_en,
                    "name_zh": s.segment_name_zh,
                    "size_pct": s.size_percentage,
                    "is_primary": bool(s.is_primary_target),
                }
                for s in segments
            ],
        })
    db.close()
    return result


def _case_summary(c: CaseProject) -> dict:
    return {
        "id": c.id,
        "brand_name": c.brand_name,
        "brand_name_zh": c.brand_name_zh or "",
        "industry": c.industry or "",
        "sub_category": c.sub_category or "",
        "total_files": c.total_files,
        "total_size_mb": c.total_size_mb,
        "completeness_score": c.completeness_score,
        "has_discovery": bool(c.has_discovery),
        "has_strategy": bool(c.has_strategy),
        "has_guidelines": bool(c.has_guidelines),
        "has_survey": bool(c.has_survey),
        "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
    }


def _file_dict(f: CaseFile) -> dict:
    return {
        "id": f.id,
        "filename": f.filename,
        "drive_file_id": f.drive_file_id,
        "doc_type": f.doc_type,
        "doc_label": f.doc_label,
        "phase": f.phase,
        "size_bytes": f.size_bytes,
        "word_count": f.word_count,
        "language_hint": f.language_hint,
        "quality": f.quality,
    }
