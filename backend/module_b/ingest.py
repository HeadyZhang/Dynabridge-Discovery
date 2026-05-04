"""Ingest pipeline: extract → tag → index → store.

Processes downloaded case files through the full pipeline:
1. Extract content from each file (extractor.py)
2. AI-tag the case (ai_tagger.py)
3. Index for search (search_index.py)
4. Store in database (models.py)
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base
from module_b.models import CaseProject, CaseFile
from module_b.extractor import extract_file
from module_b.taxonomy import classify_file
from module_b.search_index import FullTextIndex

# Lazy engine + session
_engine = None
_Session = None


def _get_session():
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
        Base.metadata.create_all(_engine)
        _Session = sessionmaker(bind=_engine)
    return _Session()


def ingest_case(
    brand_name: str,
    drive_folder_id: str,
    drive_folder_name: str,
    local_dir: str,
    drive_files: list[dict],
    use_ai_tags: bool = False,
    build_vector_index: bool = False,
) -> dict:
    """Ingest a complete case into the database and search index.

    Args:
        brand_name: Brand name.
        drive_folder_id: Google Drive folder ID.
        drive_folder_name: Folder display name.
        local_dir: Local directory with downloaded files.
        drive_files: File metadata from GDriveClient.list_folder().
        use_ai_tags: Whether to call Claude for AI tagging.
        build_vector_index: Whether to build vector embeddings.

    Returns:
        {"case_project_id", "files_processed", "files_indexed", "errors"}
    """
    db = _get_session()
    fts = FullTextIndex()

    # Upsert case project
    existing = db.query(CaseProject).filter_by(drive_folder_id=drive_folder_id).first()
    if existing:
        case_proj = existing
    else:
        case_proj = CaseProject(
            brand_name=brand_name,
            drive_folder_id=drive_folder_id,
            drive_folder_name=drive_folder_name,
        )
        db.add(case_proj)
        db.flush()

    local_path = Path(local_dir)
    non_folders = [f for f in drive_files if not f.get("is_folder")]
    files_processed = 0
    files_indexed = 0
    errors = []

    # Track discovery of key deliverable types
    has_discovery = False
    has_strategy = False
    has_guidelines = False
    has_survey = False
    total_size = 0

    # Primary discovery file for AI tagging
    discovery_extracted = None

    for f in non_folders:
        file_name = f["name"]
        file_path_in_tree = f.get("path", file_name)
        local_file = local_path / file_path_in_tree

        # Classify
        classification = classify_file(file_name, f.get("mimeType", ""))
        doc_type = classification["doc_type"]

        # Track deliverable presence
        if doc_type == "discovery":
            has_discovery = True
        elif doc_type == "strategy":
            has_strategy = True
        elif doc_type == "guidelines":
            has_guidelines = True
        elif doc_type == "survey":
            has_survey = True

        total_size += f.get("size", 0)

        # Extract content if file exists locally
        extracted_text = ""
        word_count = 0
        language_hint = ""
        quality = ""

        if local_file.exists():
            try:
                extracted = extract_file(str(local_file))
                raw_text = extracted.get("content", {}).get("raw_text", "")
                extracted_text = raw_text[:100000]
                meta = extracted.get("metadata", {})
                word_count = meta.get("word_count", 0)
                language_hint = meta.get("language_hint", "")
                quality = meta.get("quality", "")

                # Keep first discovery file for AI tagging
                if doc_type == "discovery" and discovery_extracted is None:
                    discovery_extracted = extracted

                files_processed += 1
            except Exception as e:
                errors.append({"file": file_name, "error": str(e)})

        # Upsert case file record
        existing_file = db.query(CaseFile).filter_by(
            case_project_id=case_proj.id,
            drive_file_id=f["id"],
        ).first()

        if existing_file:
            cf = existing_file
            cf.filename = file_name
            cf.doc_type = doc_type
            cf.doc_label = classification["label"]
            cf.phase = classification["phase"]
            cf.confidence = classification["confidence"]
            cf.extracted_text = extracted_text
            cf.word_count = word_count
            cf.language_hint = language_hint
            cf.quality = quality
        else:
            cf = CaseFile(
                case_project_id=case_proj.id,
                drive_file_id=f["id"],
                filename=file_name,
                drive_path=file_path_in_tree,
                mime_type=f.get("mimeType", ""),
                size_bytes=f.get("size", 0),
                doc_type=doc_type,
                doc_label=classification["label"],
                phase=classification["phase"],
                confidence=classification["confidence"],
                local_path=str(local_file) if local_file.exists() else "",
                extracted_text=extracted_text,
                word_count=word_count,
                language_hint=language_hint,
                quality=quality,
            )
            db.add(cf)

        # Index in FTS if there's text
        if extracted_text.strip():
            doc_id = f"case_{case_proj.id}_file_{f['id']}"
            fts.add_document(
                doc_id=doc_id,
                brand_name=brand_name,
                filename=file_name,
                content=extracted_text,
                tags=f"{doc_type} {classification['phase']}",
            )
            files_indexed += 1

    # AI tagging (optional)
    if use_ai_tags and discovery_extracted:
        try:
            from module_b.ai_tagger import tag_case_file
            tags = tag_case_file(discovery_extracted)
            case_proj.ai_tags_json = json.dumps(tags, ensure_ascii=False)
            case_proj.brand_name_zh = tags.get("brand_name_zh", "")
            case_proj.industry = tags.get("industry", "")
            case_proj.sub_category = tags.get("sub_category", "")
            case_proj.positioning_summary = tags.get("positioning_summary", "")
        except Exception as e:
            errors.append({"file": "ai_tagger", "error": str(e)})

    # Vector index (optional)
    if build_vector_index:
        try:
            from module_b.search_index import VectorIndex
            vec = VectorIndex()
            # Index each file with substantial text
            for cf_record in db.query(CaseFile).filter_by(case_project_id=case_proj.id).all():
                if cf_record.extracted_text and cf_record.word_count > 50:
                    vec.add_document(
                        doc_id=f"case_{case_proj.id}_file_{cf_record.drive_file_id}",
                        brand_name=brand_name,
                        filename=cf_record.filename,
                        text=cf_record.extracted_text[:2000],
                    )
        except Exception as e:
            errors.append({"file": "vector_index", "error": str(e)})

    # Update case project summary
    case_proj.total_files = len(non_folders)
    case_proj.total_size_mb = round(total_size / (1024 * 1024), 1)
    case_proj.has_discovery = 1 if has_discovery else 0
    case_proj.has_strategy = 1 if has_strategy else 0
    case_proj.has_guidelines = 1 if has_guidelines else 0
    case_proj.has_survey = 1 if has_survey else 0
    case_proj.last_synced_at = datetime.now(timezone.utc)

    # Completeness score from audit
    from module_b.audit import audit_case
    audit = audit_case(drive_files, brand_name)
    case_proj.completeness_score = audit["completeness_score"]

    db.commit()

    result = {
        "case_project_id": case_proj.id,
        "files_processed": files_processed,
        "files_indexed": files_indexed,
        "errors": errors,
    }

    db.close()
    return result
