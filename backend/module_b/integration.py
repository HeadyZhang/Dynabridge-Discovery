"""Module A -> Module B integration.

When a Module A project is approved, automatically creates a
case reference in the Module B knowledge base.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base, Project
from module_b.models import CaseProject

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine)


async def on_project_approved(project_id: int) -> dict:
    """Called when a Module A project reaches 'approved' status.

    Creates or updates a CaseProject entry in Module B so the
    completed discovery work is available in the knowledge base.

    Returns:
        {"status": "created"|"updated"|"skipped", "case_project_id": int|None}
    """
    db = _Session()

    project = db.query(Project).get(project_id)
    if not project:
        db.close()
        return {"status": "skipped", "case_project_id": None}

    # Check if case already exists for this project
    existing = db.query(CaseProject).filter_by(
        drive_folder_id=f"module_a_{project_id}"
    ).first()

    analysis = {}
    if project.analysis_json:
        try:
            analysis = json.loads(project.analysis_json)
        except (json.JSONDecodeError, TypeError):
            pass

    brand_name = project.name
    industry = analysis.get("capabilities", {}).get("execution_summary", {}).get("title", "")

    if existing:
        existing.brand_name = brand_name
        existing.positioning_summary = analysis.get("capabilities", {}).get("capabilities_summary", "")
        existing.last_synced_at = datetime.now(timezone.utc)
        existing.has_discovery = 1
        existing.has_strategy = 1 if analysis.get("competition") else 0
        db.commit()
        case_id = existing.id
        status = "updated"
    else:
        case_proj = CaseProject(
            brand_name=brand_name,
            drive_folder_id=f"module_a_{project_id}",
            drive_folder_name=f"Module A: {brand_name}",
            total_files=len(project.files) if project.files else 0,
            has_discovery=1,
            has_strategy=1 if analysis.get("competition") else 0,
            positioning_summary=analysis.get("capabilities", {}).get("capabilities_summary", ""),
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(case_proj)
        db.commit()
        case_id = case_proj.id
        status = "created"

    db.close()
    return {"status": status, "case_project_id": case_id}
