"""Tests for module_b.audit case completeness checker."""
import pytest
from module_b.audit import audit_case


def _make_file(name, mime="", size=1000):
    return {"name": name, "mimeType": mime, "size": size, "is_folder": False, "id": "x", "path": name}


def _make_folder(name):
    return {"name": name, "mimeType": "application/vnd.google-apps.folder", "size": 0, "is_folder": True, "id": "x", "path": name}


class TestAuditCase:
    def test_complete_case(self):
        files = [
            _make_file("Brand Discovery.pptx", size=30000000),
            _make_file("Brand Strategy.pptx", size=10000000),
            _make_file("Brand Guidelines.pdf", size=5000000),
            _make_file("Consumer Insights Report.pptx", size=8000000),
            _make_file("Market Research Survey.xlsx", size=500000),
            _make_file("Logo Concepts Round 1.pptx", size=3000000),
            _make_file("competitor analysis.pptx", size=2000000),
            _make_folder("Assets"),
        ]
        result = audit_case(files, "TestBrand")
        assert result["brand_name"] == "TestBrand"
        assert result["total_files"] == 7
        assert result["total_folders"] == 1
        assert result["completeness_score"] >= 0.7
        assert len(result["missing_required"]) == 0

    def test_minimal_case(self):
        files = [
            _make_file("photo.jpg"),
        ]
        result = audit_case(files, "MinBrand")
        assert result["completeness_score"] < 0.3
        assert "Brand Discovery PPT" in result["missing_required"]
        assert "Brand Strategy" in result["missing_required"]

    def test_discovery_only(self):
        files = [
            _make_file("AEKE Discovery Part 1.pptx", size=38000000),
        ]
        result = audit_case(files, "AEKE")
        assert result["total_files"] == 1
        assert result["phase_coverage"]["discovery"]["discovery"]["present"] is True
        assert result["phase_coverage"]["strategy"]["strategy"]["present"] is False

    def test_size_calculation(self):
        files = [
            _make_file("big.pptx", size=10 * 1024 * 1024),
            _make_file("small.pdf", size=1024 * 1024),
        ]
        result = audit_case(files, "SizeTest")
        assert result["total_size_mb"] == pytest.approx(11.0, abs=0.1)

    def test_empty_case(self):
        result = audit_case([], "Empty")
        assert result["total_files"] == 0
        assert result["completeness_score"] == 0.0

    def test_recommendations_present(self):
        files = [_make_file("random.txt")]
        result = audit_case(files, "Recs")
        assert len(result["recommendations"]) > 0
