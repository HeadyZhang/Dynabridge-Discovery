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
    brand_name_zh = Column(String(255), default="")
    drive_folder_id = Column(String(100), nullable=False, unique=True)
    drive_folder_name = Column(String(500))
    drive_path = Column(String(1000))
    industry = Column(String(200), default="")
    sub_category = Column(String(200), default="")
    total_files = Column(Integer, default=0)
    total_size_mb = Column(Float, default=0.0)
    completeness_score = Column(Float, default=0.0)
    has_discovery = Column(Integer, default=0)
    has_strategy = Column(Integer, default=0)
    has_guidelines = Column(Integer, default=0)
    has_survey = Column(Integer, default=0)
    # AI-generated metadata (JSON)
    ai_tags_json = Column(Text, default="{}")
    positioning_summary = Column(Text, default="")
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
    extracted_text = Column(Text, default="")  # raw text from extractor
    word_count = Column(Integer, default=0)
    language_hint = Column(String(10), default="")
    quality = Column(String(20), default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    case_project = relationship("CaseProject", back_populates="files")


# ── Customer Discovery Database tables ────────────────────────

class DiscoveryEngagement(Base):
    """A brand discovery engagement record — links Module A projects to Module B."""
    __tablename__ = "discovery_engagements"

    id = Column(Integer, primary_key=True)
    module_a_project_id = Column(Integer, nullable=True)  # FK conceptual, not enforced
    case_project_id = Column(Integer, ForeignKey("case_projects.id"), nullable=True)
    brand_name = Column(String(255), nullable=False)
    brand_name_zh = Column(String(255), default="")
    industry = Column(String(200), default="")
    challenge_type = Column(String(200), default="")  # e.g. "market entry", "rebrand"
    status = Column(String(50), default="active")  # active, completed, archived
    analysis_summary = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    segments = relationship("DiscoverySegment", back_populates="engagement",
                            cascade="all, delete-orphan")
    questionnaires = relationship("DiscoveryQuestionnaire", back_populates="engagement",
                                  cascade="all, delete-orphan")


class DiscoverySegment(Base):
    """Consumer segment identified during a discovery engagement."""
    __tablename__ = "discovery_segments"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("discovery_engagements.id"), nullable=False)
    segment_name_en = Column(String(255), nullable=False)
    segment_name_zh = Column(String(255), default="")
    size_percentage = Column(Float, default=0.0)
    description = Column(Text, default="")
    profile_json = Column(Text, default="{}")  # demographics, behaviors, needs
    is_primary_target = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    engagement = relationship("DiscoveryEngagement", back_populates="segments")


class DiscoveryQuestionnaire(Base):
    """A survey/questionnaire design used in a discovery engagement."""
    __tablename__ = "discovery_questionnaires"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("discovery_engagements.id"), nullable=False)
    title = Column(String(500), nullable=False)
    variant = Column(String(100), default="")  # e.g. "Draft V3", "CN version"
    question_count = Column(Integer, default=0)
    questions_json = Column(Text, default="[]")  # [{question, type, options, required}]
    platform = Column(String(100), default="")  # e.g. "SurveyMonkey", "Google Forms"
    response_count = Column(Integer, default=0)
    source_file_id = Column(Integer, nullable=True)  # optional FK to case_files
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    engagement = relationship("DiscoveryEngagement", back_populates="questionnaires")
    responses = relationship("QuestionnaireResponse", back_populates="questionnaire",
                             cascade="all, delete-orphan")


class QuestionnaireResponse(Base):
    """Individual response to a questionnaire."""
    __tablename__ = "questionnaire_responses"

    id = Column(Integer, primary_key=True)
    questionnaire_id = Column(Integer, ForeignKey("discovery_questionnaires.id"), nullable=False)
    respondent_id = Column(String(100), default="")  # anonymized ID
    answers_json = Column(Text, default="{}")  # {question_id: answer}
    demographics_json = Column(Text, default="{}")  # {age, gender, location, ...}
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    questionnaire = relationship("DiscoveryQuestionnaire", back_populates="responses")


class CrossTabulation(Base):
    """Cross-tabulation analysis result from questionnaire data."""
    __tablename__ = "cross_tabulations"

    id = Column(Integer, primary_key=True)
    questionnaire_id = Column(Integer, ForeignKey("discovery_questionnaires.id"), nullable=True)
    engagement_id = Column(Integer, ForeignKey("discovery_engagements.id"), nullable=True)
    dimension_a = Column(String(200), nullable=False)  # e.g. "age_group"
    dimension_b = Column(String(200), nullable=False)  # e.g. "purchase_frequency"
    result_json = Column(Text, default="{}")  # cross-tab matrix
    statistical_significance = Column(Float, default=0.0)  # p-value
    sample_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
