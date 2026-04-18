"""Tests for module_b.taxonomy file classifier."""
import pytest
from module_b.taxonomy import classify_file, classify_files


class TestClassifyFile:
    def test_discovery_pptx(self):
        result = classify_file("AEKE Discovery Part 1 - English & Chinese.pptx")
        assert result["doc_type"] == "discovery"
        assert result["phase"] == "discovery"
        assert result["confidence"] >= 0.8

    def test_brand_discovery_mixed_case(self):
        result = classify_file("CozyFit Brand Discovery - Eng&Cn.pptx")
        assert result["doc_type"] == "discovery"

    def test_strategy_pptx(self):
        result = classify_file("CASEKOO_Brand_Strategy_ST_12.11[ENG&CN].pptx")
        assert result["doc_type"] == "strategy"
        assert result["phase"] == "strategy"

    def test_assessment(self):
        result = classify_file("Niphean - Preliminary Brand Review (English& Chinese).pptx")
        assert result["doc_type"] == "assessment"

    def test_survey(self):
        result = classify_file("Casekoo Market Research Survey (Draft V3).pdf")
        assert result["doc_type"] == "survey"

    def test_guidelines(self):
        result = classify_file("Aeke_Design_Guidelines_Eng&Cn.pdf")
        assert result["doc_type"] == "guidelines"

    def test_brand_book(self):
        result = classify_file("AEKE - Brand Book (ENG&CN).pdf")
        assert result["doc_type"] == "guidelines"

    def test_naming(self):
        result = classify_file("CozyFit Renaming - EN&CN.pptx")
        assert result["doc_type"] == "naming"

    def test_consumer_insights(self):
        result = classify_file("AEKE Consumer Insights Report (EN & CN).pptx")
        assert result["doc_type"] == "consumer_insights"

    def test_persona(self):
        result = classify_file("CASEKOO Personas（Eng&Cn）.pptx")
        assert result["doc_type"] == "consumer_insights"

    def test_visual_identity(self):
        result = classify_file("Eyoyo_Vis_ID_Final (EN & CN).pptx")
        assert result["doc_type"] == "visual_identity"

    def test_logo_concept(self):
        result = classify_file("Lumibricks_Logo_Round 1 Revisions（Eng&Cn）.pptx")
        assert result["doc_type"] == "visual_identity"

    def test_competitor_analysis(self):
        result = classify_file("competitor.pptx")
        assert result["doc_type"] == "competitor"

    def test_kickoff(self):
        result = classify_file("CF KICKOFF MEETING -eng.docx")
        assert result["doc_type"] == "kickoff"

    def test_social_media(self):
        result = classify_file("Caskeoo Content Calendar（eng&cn）(1).pdf")
        assert result["doc_type"] == "social_media"

    def test_product_image_jpg(self):
        result = classify_file("DSC01412.JPG")
        assert result["doc_type"] == "product_image"
        assert result["phase"] == "assets"

    def test_archive_zip(self):
        result = classify_file("logo-files.zip")
        assert result["doc_type"] == "archive"

    def test_unknown_file(self):
        result = classify_file("random_notes.txt")
        assert result["doc_type"] == "other"
        assert result["confidence"] <= 0.2

    def test_google_slides_mime(self):
        result = classify_file(
            "Some Presentation",
            mime_type="application/vnd.google-apps.presentation",
        )
        assert result["doc_type"] == "presentation"


class TestClassifyFiles:
    def test_batch_classification(self):
        files = [
            {"name": "Discovery.pptx", "mimeType": "", "is_folder": False, "size": 1000},
            {"name": "Strategy.pptx", "mimeType": "", "is_folder": False, "size": 2000},
            {"name": "Images", "mimeType": "", "is_folder": True},
        ]
        results = classify_files(files)
        assert len(results) == 2  # folder excluded
        assert results[0]["doc_type"] == "discovery"
        assert results[1]["doc_type"] == "strategy"
