"""Tests for module_b.search_index."""
import pytest
import tempfile
from pathlib import Path
from module_b.search_index import FullTextIndex


@pytest.fixture
def fts_index():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    idx = FullTextIndex(db_path)
    yield idx
    Path(db_path).unlink(missing_ok=True)


class TestFullTextIndex:
    def test_add_and_search(self, fts_index):
        fts_index.add_document(
            doc_id="test1",
            brand_name="TestBrand",
            filename="discovery.pptx",
            content="brand strategy for global expansion and market positioning",
            tags="discovery strategy",
        )
        results = fts_index.search("brand global")
        assert len(results) > 0
        assert results[0]["doc_id"] == "test1"

    def test_search_no_results(self, fts_index):
        results = fts_index.search("nonexistent_term_xyz")
        assert len(results) == 0

    def test_multiple_documents(self, fts_index):
        fts_index.add_document("d1", "BrandA", "file1.pptx", "competitive analysis market share")
        fts_index.add_document("d2", "BrandB", "file2.pptx", "consumer insights segmentation")
        fts_index.add_document("d3", "BrandA", "file3.pptx", "brand guidelines visual identity")

        results = fts_index.search("brand")
        assert len(results) >= 1

        results = fts_index.search("consumer insights")
        assert any(r["doc_id"] == "d2" for r in results)

    def test_upsert_same_doc_id(self, fts_index):
        fts_index.add_document("same_id", "Brand", "f.pptx", "old content")
        fts_index.add_document("same_id", "Brand", "f.pptx", "new updated content")

        results = fts_index.search("updated")
        assert len(results) == 1

    def test_clear(self, fts_index):
        fts_index.add_document("x", "B", "f.pptx", "test content here")
        fts_index.clear()
        results = fts_index.search("test")
        assert len(results) == 0
