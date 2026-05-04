"""Tests for Datacube data models and tagging framework."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from models import Base
from module_b.datacube_models import (
    Campaign, AudienceTag, ContentTag, ContextTag,
    Performance, DatacubeInsight, Learning,
)
from module_b.datacube_tags import validate_tags


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestDatacubeModels:
    def test_create_campaign(self, db):
        c = Campaign(id="test1", brand_name="AEKE", campaign_name="Test", campaign_type="paid_media")
        db.add(c)
        db.commit()
        assert db.query(Campaign).count() == 1
        assert db.query(Campaign).first().brand_name == "AEKE"

    def test_create_tags(self, db):
        c = Campaign(id="test2", brand_name="AEKE", campaign_name="Test")
        db.add(c)
        db.commit()

        db.add(AudienceTag(campaign_id="test2", segment="trend_seeker", geo_market="us"))
        db.add(ContentTag(campaign_id="test2", theme="lifestyle", format="video_short_15s", message_type="emotional"))
        db.add(ContextTag(campaign_id="test2", channel="instagram", funnel_stage="awareness"))
        db.commit()

        assert db.query(AudienceTag).count() == 1
        assert db.query(ContentTag).count() == 1
        assert db.query(ContextTag).count() == 1

    def test_create_performance(self, db):
        c = Campaign(id="test3", brand_name="AEKE", campaign_name="Perf Test")
        db.add(c)
        db.commit()

        p = Performance(campaign_id="test3", impressions=50000, clicks=2500, revenue=12500, cost=3000)
        db.add(p)
        db.commit()

        perf = db.query(Performance).first()
        assert perf.impressions == 50000
        assert perf.revenue == 12500

    def test_insight_creation(self, db):
        i = DatacubeInsight(
            brand_name="AEKE",
            pattern_type="content_performance",
            finding="Reviews outperform lifestyle",
            confidence="high",
            action_type="scale",
            action_recommendation="Increase review budget",
        )
        db.add(i)
        db.commit()
        assert db.query(DatacubeInsight).count() == 1

    def test_validate_tags(self):
        errors = validate_tags({"segment": "invalid_value"}, {}, {})
        assert len(errors) == 1
        assert "Invalid audience.segment" in errors[0]

        errors2 = validate_tags(
            {"segment": "self_disciplined_achiever"},
            {"theme": "professional_review"},
            {"channel": "youtube"},
        )
        assert len(errors2) == 0
