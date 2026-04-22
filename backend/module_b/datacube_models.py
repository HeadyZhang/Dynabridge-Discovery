"""Datacube data models — the decision-making engine.

All tables use dc_ prefix to avoid conflicts with existing Module B tables.
Campaign → Tags (Audience/Content/Context) → Performance → Insights → Learnings
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey,
)
from sqlalchemy.orm import relationship

from models import Base


def _uuid() -> str:
    return str(uuid.uuid4())[:12]


def _now():
    return datetime.now(timezone.utc)


class Campaign(Base):
    """A marketing campaign / content deployment."""
    __tablename__ = "dc_campaigns"

    id = Column(String(20), primary_key=True, default=_uuid)
    brand_name = Column(String(255), nullable=False)
    campaign_name = Column(String(500), nullable=False)
    campaign_type = Column(String(50))  # paid_media / organic_social / email / creator / ecommerce
    status = Column(String(20), default="active")  # active / completed / paused
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    budget = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now)

    audience_tags = relationship("AudienceTag", back_populates="campaign", cascade="all, delete-orphan")
    content_tags = relationship("ContentTag", back_populates="campaign", cascade="all, delete-orphan")
    context_tags = relationship("ContextTag", back_populates="campaign", cascade="all, delete-orphan")
    performances = relationship("Performance", back_populates="campaign", cascade="all, delete-orphan")


class AudienceTag(Base):
    """WHO the content is for."""
    __tablename__ = "dc_audience_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(20), ForeignKey("dc_campaigns.id"), nullable=False)

    segment = Column(String(100))
    persona = Column(String(200), nullable=True)
    age_range = Column(String(20), nullable=True)
    gender = Column(String(20), nullable=True)
    income_level = Column(String(50), nullable=True)
    motivation = Column(String(100), nullable=True)
    need_state = Column(String(50), nullable=True)
    geo_market = Column(String(50), nullable=True)

    campaign = relationship("Campaign", back_populates="audience_tags")


class ContentTag(Base):
    """WHAT the content is."""
    __tablename__ = "dc_content_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(20), ForeignKey("dc_campaigns.id"), nullable=False)

    theme = Column(String(100))
    format = Column(String(100))
    message_type = Column(String(100))
    creative_approach = Column(String(100), nullable=True)
    language = Column(String(20), nullable=True)
    content_url = Column(String(500), nullable=True)

    campaign = relationship("Campaign", back_populates="content_tags")


class ContextTag(Base):
    """WHERE and HOW it ran."""
    __tablename__ = "dc_context_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(20), ForeignKey("dc_campaigns.id"), nullable=False)

    channel = Column(String(100))
    placement = Column(String(100), nullable=True)
    funnel_stage = Column(String(50))
    geo = Column(String(100), nullable=True)
    timing = Column(String(100), nullable=True)

    campaign = relationship("Campaign", back_populates="context_tags")


class Performance(Base):
    """Effect data — linked to Campaign, supports time series by date."""
    __tablename__ = "dc_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(20), ForeignKey("dc_campaigns.id"), nullable=False)

    date = Column(DateTime, nullable=True)

    # Engagement
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0)
    video_views = Column(Integer, default=0)
    watch_time_seconds = Column(Integer, default=0)

    # Conversion
    conversions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0)
    add_to_cart = Column(Integer, default=0)

    # Revenue
    revenue = Column(Float, default=0)
    cost = Column(Float, default=0)
    roas = Column(Float, default=0)
    cpa = Column(Float, default=0)
    cpc = Column(Float, default=0)
    cpm = Column(Float, default=0)

    campaign = relationship("Campaign", back_populates="performances")


class DatacubeInsight(Base):
    """AI-discovered insight from campaign data."""
    __tablename__ = "dc_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_name = Column(String(255))

    pattern_type = Column(String(50))  # content_performance / channel_efficiency / creative_fatigue / ...
    finding = Column(Text)
    evidence = Column(Text, default="{}")  # JSON — campaign_ids, metrics
    confidence = Column(String(20))  # high / medium / low

    action_type = Column(String(20))  # scale / stop / test
    action_recommendation = Column(Text)

    audience_segment = Column(String(100), nullable=True)
    content_theme = Column(String(100), nullable=True)
    channel = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=_now)
    is_validated = Column(Boolean, default=False)


class Learning(Base):
    """Cumulative knowledge — distilled from validated insights."""
    __tablename__ = "dc_learnings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_name = Column(String(255))

    principle = Column(Text)
    evidence_count = Column(Integer, default=1)
    first_observed = Column(DateTime, default=_now)
    last_validated = Column(DateTime, default=_now)

    applicable_audiences = Column(Text, default="[]")  # JSON array
    applicable_content = Column(Text, default="[]")
    applicable_channels = Column(Text, default="[]")
    applicable_geos = Column(Text, default="[]")

    status = Column(String(20), default="active")  # active / superseded / invalidated
