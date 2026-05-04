"""Tests for module_b.extractor."""
import pytest
from pathlib import Path
from module_b.extractor import extract_file, _detect_language


class TestExtractFile:
    def test_pptx_extraction(self):
        path = "/tmp/cases/CozyFit/CozyFit Discovery - Eng&Cn2.3.pptx"
        if not Path(path).exists():
            pytest.skip("CozyFit PPTX not downloaded")
        result = extract_file(path)
        assert result["file_type"] == "pptx"
        assert len(result["content"]["slides"]) > 10
        assert result["metadata"]["word_count"] > 100
        assert result["metadata"]["quality"] == "high"

    def test_pdf_extraction(self):
        path = "/tmp/cases/CozyFit/CozyFit_Brand_Strategy_Eng&Cn-AM.pdf"
        if not Path(path).exists():
            pytest.skip("CozyFit PDF not downloaded")
        result = extract_file(path)
        assert result["file_type"] == "pdf"
        assert result["metadata"]["word_count"] > 0

    def test_docx_extraction(self):
        path = "/tmp/cases/CASEKOO/background/Casekoo Category Discussion.docx"
        if not Path(path).exists():
            pytest.skip("CASEKOO DOCX not downloaded")
        result = extract_file(path)
        assert result["file_type"] == "docx"
        assert len(result["content"].get("paragraphs", [])) > 0

    def test_xlsx_extraction(self):
        path = "/tmp/cases/AEKE/AEKE Brand Strategy -Dynabridge Version (Updated).xlsx"
        if not Path(path).exists():
            pytest.skip("AEKE XLSX not downloaded")
        result = extract_file(path)
        assert result["file_type"] == "xlsx"
        assert len(result["content"].get("sheets", [])) > 0

    def test_image_extraction(self):
        # Find any jpg in cases
        for p in Path("/tmp/cases").rglob("*.jpeg"):
            result = extract_file(str(p))
            assert result["file_type"] == "image"
            assert result["metadata"]["word_count"] == 0
            break
        else:
            pytest.skip("No JPEG found in cases")

    def test_nonexistent_file(self):
        result = extract_file("/tmp/nonexistent_file.pptx")
        assert result["file_type"] == "error"

    def test_unsupported_type(self):
        result = extract_file("/tmp/cases/test.xyz")
        assert result["file_type"] == "error"


class TestDetectLanguage:
    def test_english(self):
        assert _detect_language("This is an English text about branding") == "en"

    def test_chinese(self):
        assert _detect_language("这是一段关于品牌战略的中文文字") == "zh"

    def test_bilingual(self):
        assert _detect_language("Brand Discovery 品牌探索 Strategy 品牌战略") == "en+zh"

    def test_empty(self):
        assert _detect_language("") == "unknown"
