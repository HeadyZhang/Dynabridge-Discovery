"""Module A -> Module B integration.

When a Module A project is approved, automatically creates a
case reference in the Module B knowledge base, plus a
DiscoveryEngagement and any consumer segments found in the analysis.
"""
import json
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base, Project
from module_b.models import CaseProject, ConsumerInsight, DiscoveryEngagement, DiscoverySegment

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine)


async def on_project_approved(project_id: int) -> dict:
    """Called when a Module A project reaches 'approved' status.

    Creates or updates:
    1. CaseProject in the knowledge base
    2. DiscoveryEngagement record
    3. DiscoverySegment records (if consumer segments exist in analysis)

    Returns:
        {"status", "case_project_id", "engagement_id", "segments_created"}
    """
    db = _Session()

    project = db.query(Project).get(project_id)
    if not project:
        db.close()
        return {"status": "skipped", "case_project_id": None}

    analysis = {}
    if project.analysis_json:
        try:
            analysis = json.loads(project.analysis_json)
        except (json.JSONDecodeError, TypeError):
            pass

    brand_name = project.name
    cap = analysis.get("capabilities", {})
    comp = analysis.get("competition", {})
    consumer = analysis.get("consumer", {})

    # 1. Upsert CaseProject
    existing = db.query(CaseProject).filter_by(
        drive_folder_id=f"module_a_{project_id}"
    ).first()

    if existing:
        existing.brand_name = brand_name
        existing.positioning_summary = cap.get("capabilities_summary", "")
        existing.last_synced_at = datetime.now(timezone.utc)
        existing.has_discovery = 1
        existing.has_strategy = 1 if comp else 0
        db.commit()
        case_id = existing.id
    else:
        case_proj = CaseProject(
            brand_name=brand_name,
            drive_folder_id=f"module_a_{project_id}",
            drive_folder_name=f"Module A: {brand_name}",
            total_files=len(project.files) if project.files else 0,
            has_discovery=1,
            has_strategy=1 if comp else 0,
            positioning_summary=cap.get("capabilities_summary", ""),
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(case_proj)
        db.commit()
        case_id = case_proj.id

    # 2. Upsert DiscoveryEngagement
    existing_eng = db.query(DiscoveryEngagement).filter_by(
        module_a_project_id=project_id
    ).first()

    # Infer challenge type from brand challenges
    challenge_type = ""
    challenges = cap.get("brand_challenges", [])
    if challenges:
        challenge_type = challenges[0].get("title", "")[:200]

    if existing_eng:
        existing_eng.brand_name = brand_name
        existing_eng.industry = analysis.get("industry_trends", {}).get("category_name", "")
        existing_eng.challenge_type = challenge_type
        existing_eng.status = "completed"
        existing_eng.analysis_summary = cap.get("capabilities_summary", "")
        db.commit()
        engagement_id = existing_eng.id
    else:
        engagement = DiscoveryEngagement(
            module_a_project_id=project_id,
            case_project_id=case_id,
            brand_name=brand_name,
            industry=analysis.get("industry_trends", {}).get("category_name", ""),
            challenge_type=challenge_type,
            status="completed",
            analysis_summary=cap.get("capabilities_summary", ""),
        )
        db.add(engagement)
        db.commit()
        engagement_id = engagement.id

    # 3. Create DiscoverySegments from consumer analysis
    segments_created = 0
    consumer_segments = consumer.get("segments", [])
    if consumer_segments:
        # Clear existing segments for this engagement
        db.query(DiscoverySegment).filter_by(engagement_id=engagement_id).delete()
        db.commit()

        for seg in consumer_segments:
            ds = DiscoverySegment(
                engagement_id=engagement_id,
                segment_name_en=seg.get("name", ""),
                segment_name_zh=seg.get("name_zh", ""),
                size_percentage=seg.get("size_percentage", 0),
                description=seg.get("description", ""),
                profile_json=json.dumps(seg, ensure_ascii=False),
                is_primary_target=1 if seg.get("is_primary", False) else 0,
            )
            db.add(ds)
            segments_created += 1

        db.commit()

    # 4. Extract ConsumerInsight records from analysis
    insights_created = 0
    key_insights = analysis.get("key_insights", [])
    core_challenges = analysis.get("core_challenges", [])
    all_raw = key_insights + core_challenges

    if all_raw:
        # Clear existing insights for this case from Module A
        db.query(ConsumerInsight).filter_by(case_id=case_id).delete()
        db.commit()

        industry = analysis.get("industry_trends", {}).get("category_name", "")
        for text in all_raw:
            if not text or len(str(text)) < 10:
                continue
            insight = ConsumerInsight(
                case_id=case_id,
                brand_name=brand_name,
                industry=industry,
                insight_text=str(text),
                insight_type="perception",
                evidence_source="competitive",
                confidence="medium",
                geo_market="us",
            )
            db.add(insight)
            insights_created += 1

        db.commit()

    db.close()
    return {
        "status": "created" if not existing else "updated",
        "case_project_id": case_id,
        "engagement_id": engagement_id,
        "segments_created": segments_created,
        "insights_created": insights_created,
    }
