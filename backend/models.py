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
    REVIEW = "review"
    APPROVED = "approved"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    brand_url = Column(String(500))
    competitor_urls = Column(Text, default="")  # JSON array
    status = Column(String(50), default=ProjectStatus.DRAFT)
    language = Column(String(10), default="en")  # "en" or "zh" or "en+zh"
    analysis_json = Column(Text, default="{}")  # structured AI output
    pptx_path = Column(String(500))
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
    resolved = Column(Integer, default=0)  # 0=open, 1=resolved
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="comments")
