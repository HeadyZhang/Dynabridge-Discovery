from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    SCRAPING = "scraping"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    # Phase checkpoints — user reviews slides before proceeding
    REVIEW_PHASE1 = "review_phase1"     # Brand Reality slides ready for review
    REVIEW_PHASE2 = "review_phase2"     # + Competition slides ready for review
    REVIEW_PHASE3 = "review_phase3"     # + Consumer slides ready for review
    REVIEW = "review"                    # Full deck ready (legacy / non-checkpoint mode)
    APPROVED = "approved"


class FeedbackType(str, enum.Enum):
    INSIGHT = "insight"      # Insight is wrong, shallow, or missing
    IMAGE = "image"          # Image is wrong, irrelevant, or low quality
    DATA = "data"            # Data/numbers are incorrect or implausible
    TEXT = "text"             # Text overflow, typo, or wording issue
    LAYOUT = "layout"        # Layout or formatting problem
    OTHER = "other"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    brand_url = Column(String(500))
    competitor_urls = Column(Text, default="")  # JSON array
    status = Column(String(50), default=ProjectStatus.DRAFT)
    language = Column(String(10), default="en")  # "en" or "zh" or "en+zh"
    phase = Column(String(30), default="brand_reality")  # brand_reality | market_structure | full
    analysis_json = Column(Text, default="{}")  # structured AI output
    pptx_path = Column(String(500))
    survey_mode = Column(String(20), default="simulated")  # "simulated" | "real"
    survey_json = Column(Text, default="")  # designed questionnaire JSON
    survey_responses_json = Column(Text, default="")  # uploaded real responses JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    files = relationship("UploadedFile", back_populates="project")
    slides = relationship("Slide", back_populates="project", order_by="Slide.order")
    comments = relationship("Comment", back_populates="project")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))  # pdf, docx, pptx, image
    parsed_text = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="files")


class Slide(Base):
    __tablename__ = "slides"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    order = Column(Integer, nullable=False)
    slide_type = Column(String(50))  # cover, agenda, section, insight, competitor, summary
    content_json = Column(Text, default="{}")  # structured content for this slide
    preview_path = Column(String(500))  # path to PNG preview
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="slides")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    slide_order = Column(Integer)  # which slide this comment is on (null = general)
    author = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    feedback_type = Column(String(20), default="other")  # insight|image|data|text|layout|other
    phase = Column(String(30), default="")  # which phase this feedback belongs to
    resolved = Column(Integer, default=0)  # 0=open, 1=resolved
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="comments")


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, nullable=False)  # auto-incrementing per project
    phase = Column(String(30), default="")  # which phase triggered this snapshot
    analysis_json = Column(Text, default="{}")
    pptx_path = Column(String(500))
    trigger = Column(String(50), default="regenerate")  # "regenerate" | "generate"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project")
