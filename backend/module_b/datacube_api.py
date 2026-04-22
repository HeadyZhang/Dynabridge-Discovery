"""Datacube API — Campaign CRUD, CSV import, attribution, insights, learnings, planning."""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Body
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base
from module_b.datacube_models import (
    Campaign, AudienceTag, ContentTag, ContextTag,
    Performance, DatacubeInsight, Learning,
)
from module_b.datacube_tags import (
    AUDIENCE_TAGS, CONTENT_TAGS, CONTEXT_TAGS, validate_tags,
)

router = APIRouter(prefix="/api/datacube", tags=["Datacube"])

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine)


def _get_db():
    return _Session()


def _now():
    return datetime.now(timezone.utc)


# ── Tags options ──────────────────────────────────────────


@router.get("/tags/options")
def get_tag_options():
    """Return all predefined tag values for frontend dropdowns."""
    return {
        "audience": AUDIENCE_TAGS,
        "content": CONTENT_TAGS,
        "context": CONTEXT_TAGS,
    }


# ── Stats ─────────────────────────────────────────────────


@router.get("/stats")
def get_stats():
    """Datacube overview stats."""
    db = _get_db()
    campaigns = db.query(Campaign).all()
    perfs = db.query(Performance).all()

    total_impressions = sum(p.impressions for p in perfs)
    total_revenue = sum(p.revenue for p in perfs)
    total_cost = sum(p.cost for p in perfs)
    avg_roas = (total_revenue / total_cost) if total_cost > 0 else 0

    # Top channels
    channel_stats: dict[str, dict] = {}
    for c in campaigns:
        for ct in c.context_tags:
            ch = ct.channel or "unknown"
            if ch not in channel_stats:
                channel_stats[ch] = {"campaigns": 0, "revenue": 0, "cost": 0}
            channel_stats[ch]["campaigns"] += 1
        for p in c.performances:
            for ct in c.context_tags:
                ch = ct.channel or "unknown"
                channel_stats.setdefault(ch, {"campaigns": 0, "revenue": 0, "cost": 0})
                channel_stats[ch]["revenue"] += p.revenue
                channel_stats[ch]["cost"] += p.cost

    top_channels = sorted(
        [{"channel": k, "roas": v["revenue"] / v["cost"] if v["cost"] > 0 else 0, **v}
         for k, v in channel_stats.items()],
        key=lambda x: x["roas"], reverse=True,
    )[:5]

    db.close()
    return {
        "campaigns_count": len(campaigns),
        "total_impressions": total_impressions,
        "total_revenue": round(total_revenue, 2),
        "total_cost": round(total_cost, 2),
        "avg_roas": round(avg_roas, 2),
        "top_channels": top_channels,
    }


# ── Campaign CRUD ─────────────────────────────────────────


@router.post("/campaigns")
def create_campaign(body: dict = Body(...)):
    """Create a campaign with tags."""
    db = _get_db()

    cid = str(uuid.uuid4())[:12]
    campaign = Campaign(
        id=cid,
        brand_name=body.get("brand_name", ""),
        campaign_name=body.get("campaign_name", ""),
        campaign_type=body.get("campaign_type", ""),
        status=body.get("status", "active"),
        budget=body.get("budget"),
        notes=body.get("notes"),
        created_at=_now(),
    )
    db.add(campaign)

    aud = body.get("audience", {})
    if aud:
        db.add(AudienceTag(campaign_id=cid, **{k: v for k, v in aud.items() if k in AudienceTag.__table__.columns.keys() and k != "id" and k != "campaign_id"}))

    con = body.get("content", {})
    if con:
        db.add(ContentTag(campaign_id=cid, **{k: v for k, v in con.items() if k in ContentTag.__table__.columns.keys() and k != "id" and k != "campaign_id"}))

    ctx = body.get("context", {})
    if ctx:
        db.add(ContextTag(campaign_id=cid, **{k: v for k, v in ctx.items() if k in ContextTag.__table__.columns.keys() and k != "id" and k != "campaign_id"}))

    db.commit()
    db.close()
    return {"id": cid, "campaign_name": body.get("campaign_name", "")}


@router.get("/campaigns")
def list_campaigns(
    brand: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    audience: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """List campaigns with optional filters."""
    db = _get_db()
    q = db.query(Campaign)
    if brand:
        q = q.filter(Campaign.brand_name.ilike(f"%{brand}%"))
    if status:
        q = q.filter(Campaign.status == status)

    campaigns = q.order_by(Campaign.created_at.desc()).all()
    result = []
    for c in campaigns:
        aud = c.audience_tags[0] if c.audience_tags else None
        con = c.content_tags[0] if c.content_tags else None
        ctx = c.context_tags[0] if c.context_tags else None

        # Apply sub-filters
        if channel and (not ctx or ctx.channel != channel):
            continue
        if audience and (not aud or aud.segment != audience):
            continue

        total_impressions = sum(p.impressions for p in c.performances)
        total_revenue = sum(p.revenue for p in c.performances)
        total_cost = sum(p.cost for p in c.performances)

        result.append({
            "id": c.id,
            "brand_name": c.brand_name,
            "campaign_name": c.campaign_name,
            "campaign_type": c.campaign_type,
            "status": c.status,
            "channel": ctx.channel if ctx else "",
            "audience": aud.segment if aud else "",
            "content_theme": con.theme if con else "",
            "content_format": con.format if con else "",
            "impressions": total_impressions,
            "revenue": round(total_revenue, 2),
            "roas": round(total_revenue / total_cost, 2) if total_cost > 0 else 0,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    db.close()
    return result


@router.get("/campaigns/{campaign_id}")
def get_campaign(campaign_id: str):
    """Campaign detail with tags, performance, and related insights."""
    db = _get_db()
    c = db.query(Campaign).get(campaign_id)
    if not c:
        db.close()
        raise HTTPException(404, "Campaign not found")

    aud = c.audience_tags[0] if c.audience_tags else None
    con = c.content_tags[0] if c.content_tags else None
    ctx = c.context_tags[0] if c.context_tags else None

    performances = [
        {
            "date": p.date.isoformat() if p.date else None,
            "impressions": p.impressions, "clicks": p.clicks,
            "engagement_rate": p.engagement_rate,
            "conversions": p.conversions, "revenue": p.revenue,
            "cost": p.cost, "roas": p.roas, "cpa": p.cpa,
        }
        for p in c.performances
    ]

    insights = db.query(DatacubeInsight).filter(
        DatacubeInsight.brand_name == c.brand_name
    ).order_by(DatacubeInsight.created_at.desc()).limit(10).all()

    db.close()
    return {
        "id": c.id,
        "brand_name": c.brand_name,
        "campaign_name": c.campaign_name,
        "campaign_type": c.campaign_type,
        "status": c.status,
        "budget": c.budget,
        "notes": c.notes,
        "audience": _tag_dict(aud) if aud else {},
        "content": _tag_dict(con) if con else {},
        "context": _tag_dict(ctx) if ctx else {},
        "performances": performances,
        "insights": [_insight_dict(i) for i in insights],
    }


@router.put("/campaigns/{campaign_id}")
def update_campaign(campaign_id: str, body: dict = Body(...)):
    """Update campaign fields."""
    db = _get_db()
    c = db.query(Campaign).get(campaign_id)
    if not c:
        db.close()
        raise HTTPException(404, "Campaign not found")

    for field in ["campaign_name", "campaign_type", "status", "budget", "notes"]:
        if field in body:
            setattr(c, field, body[field])

    db.commit()
    db.close()
    return {"updated": True}


@router.post("/campaigns/{campaign_id}/performance")
def add_performance(campaign_id: str, body: list = Body(...)):
    """Add performance data (batch: JSON array)."""
    db = _get_db()
    c = db.query(Campaign).get(campaign_id)
    if not c:
        db.close()
        raise HTTPException(404, "Campaign not found")

    added = 0
    for entry in body:
        date_str = entry.get("date")
        date_val = datetime.fromisoformat(date_str) if date_str else None
        impressions = entry.get("impressions", 0)
        clicks = entry.get("clicks", 0)
        conversions = entry.get("conversions", 0)
        revenue = entry.get("revenue", 0)
        cost = entry.get("cost", 0)

        p = Performance(
            campaign_id=campaign_id,
            date=date_val,
            impressions=impressions,
            clicks=clicks,
            engagement_rate=round(clicks / impressions * 100, 2) if impressions > 0 else 0,
            conversions=conversions,
            conversion_rate=round(conversions / clicks * 100, 2) if clicks > 0 else 0,
            revenue=revenue,
            cost=cost,
            roas=round(revenue / cost, 2) if cost > 0 else 0,
            cpa=round(cost / conversions, 2) if conversions > 0 else 0,
            cpc=round(cost / clicks, 2) if clicks > 0 else 0,
            cpm=round(cost / impressions * 1000, 2) if impressions > 0 else 0,
        )
        db.add(p)
        added += 1

    db.commit()
    db.close()
    return {"added": added}


# ── CSV Import ────────────────────────────────────────────


@router.post("/import/csv")
async def import_csv(file: UploadFile = File(...)):
    """Bulk import campaigns from CSV."""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))

    db = _get_db()
    imported = 0
    errors: list[str] = []

    for i, row in enumerate(reader):
        try:
            cid = str(uuid.uuid4())[:12]
            campaign = Campaign(
                id=cid,
                brand_name=row.get("brand", ""),
                campaign_name=row.get("campaign_name", ""),
                campaign_type=row.get("campaign_type", "paid_media"),
                status="completed",
                created_at=_now(),
            )
            db.add(campaign)

            db.add(AudienceTag(
                campaign_id=cid,
                segment=row.get("audience_segment", ""),
                geo_market=row.get("geo", ""),
            ))
            db.add(ContentTag(
                campaign_id=cid,
                theme=row.get("content_theme", ""),
                format=row.get("content_format", ""),
                message_type=row.get("message_type", ""),
            ))
            db.add(ContextTag(
                campaign_id=cid,
                channel=row.get("channel", ""),
                funnel_stage=row.get("funnel_stage", ""),
                geo=row.get("geo", ""),
            ))

            date_str = row.get("date", "")
            date_val = datetime.fromisoformat(date_str) if date_str else None
            impressions = int(row.get("impressions", 0))
            clicks = int(row.get("clicks", 0))
            conversions = int(row.get("conversions", 0))
            revenue = float(row.get("revenue", 0))
            cost = float(row.get("cost", 0))

            db.add(Performance(
                campaign_id=cid,
                date=date_val,
                impressions=impressions,
                clicks=clicks,
                engagement_rate=round(clicks / impressions * 100, 2) if impressions > 0 else 0,
                conversions=conversions,
                conversion_rate=round(conversions / clicks * 100, 2) if clicks > 0 else 0,
                revenue=revenue,
                cost=cost,
                roas=round(revenue / cost, 2) if cost > 0 else 0,
                cpa=round(cost / conversions, 2) if conversions > 0 else 0,
                cpc=round(cost / clicks, 2) if clicks > 0 else 0,
                cpm=round(cost / impressions * 1000, 2) if impressions > 0 else 0,
            ))
            imported += 1
        except Exception as e:
            errors.append(f"Row {i + 1}: {e}")

    db.commit()
    db.close()
    return {"imported": imported, "errors": errors}


# ── Attribution ───────────────────────────────────────────


@router.get("/attribution")
def get_attribution(
    audience: Optional[str] = Query(None),
    content_theme: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    funnel_stage: Optional[str] = Query(None),
    geo: Optional[str] = Query(None),
):
    """Attribution query — filter by tags, get aggregated performance."""
    db = _get_db()
    campaigns = db.query(Campaign).all()

    matched = []
    for c in campaigns:
        aud = c.audience_tags[0] if c.audience_tags else None
        con = c.content_tags[0] if c.content_tags else None
        ctx = c.context_tags[0] if c.context_tags else None

        if audience and (not aud or aud.segment != audience):
            continue
        if content_theme and (not con or con.theme != content_theme):
            continue
        if channel and (not ctx or ctx.channel != channel):
            continue
        if funnel_stage and (not ctx or ctx.funnel_stage != funnel_stage):
            continue
        if geo and (not ctx or ctx.geo != geo):
            continue

        matched.append(c)

    # Aggregate performance
    total_imp = sum(p.impressions for c in matched for p in c.performances)
    total_clicks = sum(p.clicks for c in matched for p in c.performances)
    total_conv = sum(p.conversions for c in matched for p in c.performances)
    total_rev = sum(p.revenue for c in matched for p in c.performances)
    total_cost = sum(p.cost for c in matched for p in c.performances)

    # All campaigns average for comparison
    all_perfs = db.query(Performance).all()
    all_imp = sum(p.impressions for p in all_perfs)
    all_clicks = sum(p.clicks for p in all_perfs)
    all_rev = sum(p.revenue for p in all_perfs)
    all_cost = sum(p.cost for p in all_perfs)
    all_count = len(set(p.campaign_id for p in all_perfs)) or 1

    avg_eng = (all_clicks / all_imp * 100) if all_imp > 0 else 0
    matched_eng = (total_clicks / total_imp * 100) if total_imp > 0 else 0
    avg_roas = (all_rev / all_cost) if all_cost > 0 else 0
    matched_roas = (total_rev / total_cost) if total_cost > 0 else 0

    db.close()
    return {
        "filter": {"audience": audience, "content_theme": content_theme, "channel": channel},
        "campaigns_matched": len(matched),
        "aggregate_performance": {
            "total_impressions": total_imp,
            "total_clicks": total_clicks,
            "avg_engagement_rate": round(matched_eng, 2),
            "total_conversions": total_conv,
            "total_revenue": round(total_rev, 2),
            "total_cost": round(total_cost, 2),
            "avg_roas": round(matched_roas, 2),
        },
        "vs_average": {
            "engagement_rate_diff": round(matched_eng - avg_eng, 2),
            "roas_diff": round(matched_roas - avg_roas, 2),
        },
    }


# ── Insights ──────────────────────────────────────────────


@router.get("/insights")
def list_insights(
    brand: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
):
    db = _get_db()
    q = db.query(DatacubeInsight)
    if brand:
        q = q.filter(DatacubeInsight.brand_name == brand)
    if action_type:
        q = q.filter(DatacubeInsight.action_type == action_type)
    insights = q.order_by(DatacubeInsight.created_at.desc()).limit(50).all()
    result = [_insight_dict(i) for i in insights]
    db.close()
    return result


@router.get("/recommendations")
def get_recommendations(brand: str = Query(...)):
    """Scale / Stop / Test recommendations."""
    db = _get_db()
    insights = db.query(DatacubeInsight).filter(
        DatacubeInsight.brand_name == brand,
        DatacubeInsight.confidence.in_(["high", "medium"]),
    ).all()
    db.close()
    return {
        "scale": [_insight_dict(i) for i in insights if i.action_type == "scale"],
        "stop": [_insight_dict(i) for i in insights if i.action_type == "stop"],
        "test": [_insight_dict(i) for i in insights if i.action_type == "test"],
    }


# ── Learnings ─────────────────────────────────────────────


@router.get("/learnings")
def list_learnings(brand: Optional[str] = Query(None)):
    db = _get_db()
    q = db.query(Learning)
    if brand:
        q = q.filter(Learning.brand_name == brand)
    learnings = q.order_by(Learning.evidence_count.desc()).all()
    result = [_learning_dict(le) for le in learnings]
    db.close()
    return result


# ── Helpers ───────────────────────────────────────────────


def _tag_dict(tag) -> dict:
    cols = [c.key for c in tag.__table__.columns if c.key not in ("id", "campaign_id")]
    return {k: getattr(tag, k) for k in cols if getattr(tag, k)}


def _insight_dict(i: DatacubeInsight) -> dict:
    return {
        "id": i.id,
        "brand_name": i.brand_name,
        "pattern_type": i.pattern_type,
        "finding": i.finding,
        "evidence": i.evidence,
        "confidence": i.confidence,
        "action_type": i.action_type,
        "action_recommendation": i.action_recommendation,
        "audience_segment": i.audience_segment,
        "content_theme": i.content_theme,
        "channel": i.channel,
        "is_validated": i.is_validated,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


def _learning_dict(le: Learning) -> dict:
    return {
        "id": le.id,
        "brand_name": le.brand_name,
        "principle": le.principle,
        "evidence_count": le.evidence_count,
        "first_observed": le.first_observed.isoformat() if le.first_observed else None,
        "last_validated": le.last_validated.isoformat() if le.last_validated else None,
        "applicable_audiences": json.loads(le.applicable_audiences) if le.applicable_audiences else [],
        "applicable_content": json.loads(le.applicable_content) if le.applicable_content else [],
        "applicable_channels": json.loads(le.applicable_channels) if le.applicable_channels else [],
        "applicable_geos": json.loads(le.applicable_geos) if le.applicable_geos else [],
        "status": le.status,
    }
