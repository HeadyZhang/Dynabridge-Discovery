"""Tests for module_b.ai_tagger."""
import pytest
from module_b.ai_tagger import _fallback_tags


class TestFallbackTags:
    def test_extracts_brand_from_filename(self):
        extracted = {
            "source_file": "/tmp/cases/AEKE/AEKE Discovery.pptx",
            "content": {"raw_text": "Some text"},
        }
        tags = _fallback_tags(extracted)
        assert tags["brand_name_en"] == "AEKE"

    def test_returns_empty_for_no_text(self):
        extracted = {
            "source_file": "test.pptx",
            "content": {"raw_text": ""},
        }
        tags = _fallback_tags(extracted)
        assert isinstance(tags["core_challenges"], list)
        assert isinstance(tags["key_insights"], list)
        assert isinstance(tags["consumer_segments"], list)
        assert isinstance(tags["tags"], list)

    def test_tag_structure(self):
        extracted = {
            "source_file": "/tmp/test.pptx",
            "content": {"raw_text": "hello"},
        }
        tags = _fallback_tags(extracted)
        required_keys = [
            "brand_name_en", "brand_name_zh", "industry", "sub_category",
            "project_types", "core_challenges", "key_insights",
            "consumer_segments", "competitors_mentioned",
            "positioning_summary", "tags",
        ]
        for key in required_keys:
            assert key in tags, f"Missing key: {key}"
