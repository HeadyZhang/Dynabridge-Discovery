"""Module B database models — appended to the shared SQLAlchemy Base.

These tables track the case library, Drive sync state, and file taxonomy.
They do NOT modify any Module A tables.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from models import Base


class CaseProject(Base):
    """A brand case from the Google Drive library."""
    __tablename__ = "case_projects"

    id = Column(Integer, primary_key=True)
    brand_name = Column(String(255), nullable=False)
    drive_folder_id = Column(String(100), nullable=False, unique=True)
    drive_folder_name = Column(String(500))
    drive_path = Column(String(1000))
    total_files = Column(Integer, default=0)
    total_size_mb = Column(Float, default=0.0)
    completeness_score = Column(Float, default=0.0)
    has_discovery = Column(Integer, default=0)
    has_strategy = Column(Integer, default=0)
    has_guidelines = Column(Integer, default=0)
    has_survey = Column(Integer, default=0)
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    files = relationship("CaseFile", back_populates="case_project",
                         cascade="all, delete-orphan")


class CaseFile(Base):
    """A file within a case project, with taxonomy classification."""
    __tablename__ = "case_files"

    id = Column(Integer, primary_key=True)
    case_project_id = Column(Integer, ForeignKey("case_projects.id"), nullable=False)
    drive_file_id = Column(String(100), nullable=False)
    filename = Column(String(500), nullable=False)
    drive_path = Column(String(1000))
    mime_type = Column(String(200))
    size_bytes = Column(Integer, default=0)
    doc_type = Column(String(50))       # from taxonomy classifier
    doc_label = Column(String(100))     # human-readable type label
    phase = Column(String(50))          # discovery, strategy, design, etc.
    confidence = Column(Float, default=0.0)
    local_path = Column(String(1000))   # path if downloaded locally
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    case_project = relationship("CaseProject", back_populates="files")
