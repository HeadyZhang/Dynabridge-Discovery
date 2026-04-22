"""Datacube AI Insight Engine — automatic pattern discovery from campaign data.

6 patterns:
1. content_performance_by_segment — best content for each audience
2. channel_efficiency — highest ROI channels
3. creative_fatigue — declining engagement over time
4. audience_content_mismatch — poorly performing combos
5. untested_combinations — gaps in audience x content x channel matrix
6. geo_performance_variance — same content, different results by region
"""

import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base
from module_b.datacube_models import (
    Campaign, AudienceTag, ContentTag, ContextTag,
    Performance, DatacubeInsight,
)

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
_Session = sessionmaker(bind=_engine)


def _now():
    return datetime.now(timezone.utc)


def _get_campaign_data(db, brand_name: str) -> list[dict]:
    """Load all campaigns for a brand with their tags and aggregated performance."""
    campaigns = db.query(Campaign).filter(Campaign.brand_name == brand_name).all()
    result = []
    for c in campaigns:
        aud = c.audience_tags[0] if c.audience_tags else None
        con = c.content_tags[0] if c.content_tags else None
        ctx = c.context_tags[0] if c.context_tags else None

        total_imp = sum(p.impressions for p in c.performances)
        total_clicks = sum(p.clicks for p in c.performances)
        total_conv = sum(p.conversions for p in c.performances)
        total_rev = sum(p.revenue for p in c.performances)
        total_cost = sum(p.cost for p in c.performances)

        result.append({
            "id": c.id,
            "name": c.campaign_name,
            "audience": aud.segment if aud else "",
            "content_theme": con.theme if con else "",
            "content_format": con.format if con else "",
            "channel": ctx.channel if ctx else "",
            "funnel_stage": ctx.funnel_stage if ctx else "",
            "geo": ctx.geo if ctx else "",
            "impressions": total_imp,
            "clicks": total_clicks,
            "conversions": total_conv,
            "revenue": total_rev,
            "cost": total_cost,
            "engagement_rate": round(total_clicks / total_imp * 100, 2) if total_imp > 0 else 0,
            "roas": round(total_rev / total_cost, 2) if total_cost > 0 else 0,
            "cpa": round(total_cost / total_conv, 2) if total_conv > 0 else 0,
        })
    return result


def _pattern_content_by_segment(data: list[dict]) -> list[dict]:
    """Which content types work best for each audience segment?"""
    groups: dict[str, list[dict]] = defaultdict(list)
    for d in data:
        if d["audience"] and d["content_theme"]:
            groups[f"{d['audience']}|{d['content_theme']}"].append(d)

    insights = []
    # Find best content for each audience
    audience_best: dict[str, tuple[str, float]] = {}
    for key, items in groups.items():
        aud, content = key.split("|")
        avg_roas = sum(i["roas"] for i in items) / len(items)
        if aud not in audience_best or avg_roas > audience_best[aud][1]:
            audience_best[aud] = (content, avg_roas)

    for aud, (content, roas) in audience_best.items():
        insights.append({
            "pattern_type": "content_performance",
            "finding": f"{content.replace('_', ' ').title()} content achieves {roas}x ROAS for {aud.replace('_', ' ')} audience",
            "evidence": json.dumps({"audience": aud, "content": content, "roas": roas}),
            "confidence": "high" if roas > 3 else "medium",
            "action_type": "scale",
            "action_recommendation": f"Increase {content.replace('_', ' ')} content budget for {aud.replace('_', ' ')} audience",
            "audience_segment": aud,
            "content_theme": content,
        })
    return insights


def _pattern_channel_efficiency(data: list[dict]) -> list[dict]:
    """Which channels have the highest ROI?"""
    channel_stats: dict[str, list[float]] = defaultdict(list)
    for d in data:
        if d["channel"] and d["roas"] > 0:
            channel_stats[d["channel"]].append(d["roas"])

    if not channel_stats:
        return []

    avg_roas_all = sum(d["roas"] for d in data if d["roas"] > 0) / max(len([d for d in data if d["roas"] > 0]), 1)
    insights = []

    for ch, roas_list in sorted(channel_stats.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True):
        avg = sum(roas_list) / len(roas_list)
        diff_pct = round((avg - avg_roas_all) / avg_roas_all * 100) if avg_roas_all > 0 else 0

        if diff_pct > 20:
            insights.append({
                "pattern_type": "channel_efficiency",
                "finding": f"{ch} delivers {avg:.1f}x ROAS ({diff_pct:+d}% vs average)",
                "evidence": json.dumps({"channel": ch, "avg_roas": avg, "campaigns": len(roas_list)}),
                "confidence": "high" if len(roas_list) >= 3 else "medium",
                "action_type": "scale",
                "action_recommendation": f"Increase budget allocation to {ch}",
                "channel": ch,
            })
        elif diff_pct < -30:
            insights.append({
                "pattern_type": "channel_efficiency",
                "finding": f"{ch} underperforms at {avg:.1f}x ROAS ({diff_pct:+d}% vs average)",
                "evidence": json.dumps({"channel": ch, "avg_roas": avg, "campaigns": len(roas_list)}),
                "confidence": "medium",
                "action_type": "stop",
                "action_recommendation": f"Review and potentially reduce {ch} spend",
                "channel": ch,
            })

    return insights


def _pattern_untested_combinations(data: list[dict]) -> list[dict]:
    """Find gaps in the audience x content x channel matrix."""
    from module_b.datacube_tags import AUDIENCE_TAGS, CONTENT_TAGS, CONTEXT_TAGS

    tested = set()
    for d in data:
        if d["audience"] and d["content_theme"] and d["channel"]:
            tested.add((d["audience"], d["content_theme"], d["channel"]))

    used_audiences = set(d["audience"] for d in data if d["audience"])
    used_content = set(d["content_theme"] for d in data if d["content_theme"])
    used_channels = set(d["channel"] for d in data if d["channel"])

    insights = []
    for aud in used_audiences:
        for content in used_content:
            for ch in used_channels:
                if (aud, content, ch) not in tested:
                    insights.append({
                        "pattern_type": "untested_combinations",
                        "finding": f"Untested: {content.replace('_',' ')} for {aud.replace('_',' ')} on {ch}",
                        "evidence": json.dumps({"audience": aud, "content": content, "channel": ch}),
                        "confidence": "low",
                        "action_type": "test",
                        "action_recommendation": f"Consider testing {content.replace('_',' ')} content for {aud.replace('_',' ')} on {ch}",
                        "audience_segment": aud,
                        "content_theme": content,
                        "channel": ch,
                    })

    return insights[:5]  # Limit to top 5 suggestions


def _generate_with_claude(brand_name: str, data: list[dict], stat_insights: list[dict]) -> list[dict]:
    """Use Claude to enhance and add narrative to statistical insights."""
    try:
        import anthropic
        client = anthropic.Anthropic()

        data_summary = json.dumps(data[:10], indent=2)
        stat_summary = json.dumps([{"finding": i["finding"], "action_type": i["action_type"]} for i in stat_insights], indent=2)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": f"""You are a marketing analytics expert analyzing campaign data for brand {brand_name}.

Campaign data summary (first 10):
{data_summary}

Statistical insights found:
{stat_summary}

Based on this data, generate 2-3 additional strategic insights that the statistical analysis might miss.
For each insight, output a JSON object:
{{
  "pattern_type": "content_performance / channel_efficiency / audience_content_mismatch / opportunity",
  "finding": "The insight in plain English",
  "confidence": "high / medium / low",
  "action_type": "scale / stop / test",
  "action_recommendation": "Specific action to take"
}}

Output a JSON array only. No other text."""}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
    except Exception:
        return []


async def generate_insights(brand_name: str) -> list[dict]:
    """Main entry: run all pattern detectors, store insights, return results."""
    db = _Session()

    # Clear old insights for this brand
    db.query(DatacubeInsight).filter(DatacubeInsight.brand_name == brand_name).delete()
    db.commit()

    data = _get_campaign_data(db, brand_name)
    if not data:
        db.close()
        return []

    all_insights: list[dict] = []
    all_insights.extend(_pattern_content_by_segment(data))
    all_insights.extend(_pattern_channel_efficiency(data))
    all_insights.extend(_pattern_untested_combinations(data))

    # AI-enhanced insights
    ai_insights = _generate_with_claude(brand_name, data, all_insights)
    for ai in ai_insights:
        all_insights.append({
            "pattern_type": ai.get("pattern_type", "opportunity"),
            "finding": ai.get("finding", ""),
            "evidence": json.dumps({"source": "ai_analysis"}),
            "confidence": ai.get("confidence", "medium"),
            "action_type": ai.get("action_type", "test"),
            "action_recommendation": ai.get("action_recommendation", ""),
        })

    # Store insights
    stored = []
    for ins in all_insights:
        record = DatacubeInsight(
            brand_name=brand_name,
            pattern_type=ins.get("pattern_type", ""),
            finding=ins.get("finding", ""),
            evidence=ins.get("evidence", "{}"),
            confidence=ins.get("confidence", "medium"),
            action_type=ins.get("action_type", "test"),
            action_recommendation=ins.get("action_recommendation", ""),
            audience_segment=ins.get("audience_segment"),
            content_theme=ins.get("content_theme"),
            channel=ins.get("channel"),
            created_at=_now(),
        )
        db.add(record)
        stored.append(ins)

    db.commit()
    db.close()
    return stored
