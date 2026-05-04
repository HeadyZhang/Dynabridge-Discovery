"""Tests for module_b.models database tables."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from models import Base
from module_b.models import CaseProject, CaseFile


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestCaseProject:
    def test_create_case_project(self, db_session):
        proj = CaseProject(
            brand_name="AEKE",
            drive_folder_id="abc123",
            drive_folder_name="10. AEKE",
            total_files=162,
            total_size_mb=500.0,
            completeness_score=0.85,
            has_discovery=1,
            has_strategy=1,
            has_guidelines=1,
        )
        db_session.add(proj)
        db_session.commit()

        loaded = db_session.query(CaseProject).first()
        assert loaded.brand_name == "AEKE"
        assert loaded.drive_folder_id == "abc123"
        assert loaded.has_discovery == 1
        assert loaded.completeness_score == 0.85

    def test_unique_drive_folder_id(self, db_session):
        proj1 = CaseProject(brand_name="A", drive_folder_id="same_id")
        db_session.add(proj1)
        db_session.commit()

        proj2 = CaseProject(brand_name="B", drive_folder_id="same_id")
        db_session.add(proj2)
        with pytest.raises(Exception):
            db_session.commit()


class TestCaseFile:
    def test_create_case_file(self, db_session):
        proj = CaseProject(brand_name="Test", drive_folder_id="folder1")
        db_session.add(proj)
        db_session.commit()

        cf = CaseFile(
            case_project_id=proj.id,
            drive_file_id="file1",
            filename="Discovery.pptx",
            doc_type="discovery",
            doc_label="Brand Discovery",
            phase="discovery",
            confidence=0.9,
            size_bytes=30000000,
        )
        db_session.add(cf)
        db_session.commit()

        loaded = db_session.query(CaseFile).first()
        assert loaded.filename == "Discovery.pptx"
        assert loaded.doc_type == "discovery"
        assert loaded.case_project.brand_name == "Test"

    def test_cascade_delete(self, db_session):
        proj = CaseProject(brand_name="Del", drive_folder_id="del1")
        db_session.add(proj)
        db_session.commit()

        cf = CaseFile(
            case_project_id=proj.id,
            drive_file_id="f1",
            filename="test.pdf",
        )
        db_session.add(cf)
        db_session.commit()

        db_session.delete(proj)
        db_session.commit()
        assert db_session.query(CaseFile).count() == 0


class TestTablesExist:
    def test_module_b_tables_created(self, db_session):
        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()
        assert "case_projects" in tables
        assert "case_files" in tables

    def test_module_a_tables_untouched(self, db_session):
        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()
        assert "projects" in tables
        assert "uploaded_files" in tables
        assert "slides" in tables
        assert "comments" in tables
