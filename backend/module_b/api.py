"""Module B API routes — Knowledge Base / Case Library.

FastAPI Router mounted at /api/knowledge.
Does NOT modify any existing Module A routes.
"""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_PATH
from models import Base
from module_b.models import CaseProject, CaseFile
from module_b.search_index import FullTextIndex

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(_engine)
_Session = sessionmaker(bind=_engine)


def _get_db():
    return _Session()


@router.get("/cases")
def list_cases(
    industry: Optional[str] = Query(None),
    has_discovery: Optional[bool] = Query(None),
    has_strategy: Optional[bool] = Query(None),
):
    """List all case projects with optional filtering."""
    db = _get_db()
    q = db.query(CaseProject)

    if industry:
        q = q.filter(CaseProject.industry.ilike(f"%{industry}%"))
    if has_discovery is not None:
        q = q.filter(CaseProject.has_discovery == (1 if has_discovery else 0))
    if has_strategy is not None:
        q = q.filter(CaseProject.has_strategy == (1 if has_strategy else 0))

    cases = q.order_by(CaseProject.brand_name).all()
    result = [_case_summary(c) for c in cases]
    db.close()
    return result


@router.get("/cases/{case_id}")
def get_case(case_id: int):
    """Get detailed case info including all files."""
    db = _get_db()
    case = db.query(CaseProject).get(case_id)
    if not case:
        db.close()
        raise HTTPException(404, "Case not found")

    files = db.query(CaseFile).filter_by(case_project_id=case_id).order_by(CaseFile.phase, CaseFile.filename).all()

    result = {
        **_case_summary(case),
        "ai_tags": json.loads(case.ai_tags_json) if case.ai_tags_json else {},
        "positioning_summary": case.positioning_summary,
        "files": [_file_dict(f) for f in files],
    }
    db.close()
    return result


@router.get("/search")
def search_cases(
    q: str = Query(..., min_length=1),
    mode: str = Query("fts", regex="^(fts|vector|hybrid)$"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search across all case files.

    Modes:
      - fts: Full-text keyword search (SQLite FTS5)
      - vector: Semantic similarity search (sentence-transformers)
      - hybrid: Combined FTS + vector results
    """
    results = []

    if mode in ("fts", "hybrid"):
        fts = FullTextIndex()
        fts_results = fts.search(q, limit=limit)
        for r in fts_results:
            results.append({
                "source": "fts",
                "doc_id": r["doc_id"],
                "brand_name": r["brand_name"],
                "filename": r["filename"],
                "snippet": r["snippet"],
                "score": abs(r["rank"]),
            })

    if mode in ("vector", "hybrid"):
        try:
            from module_b.search_index import VectorIndex
            vec = VectorIndex()
            vec_results = vec.search(q, limit=limit)
            for r in vec_results:
                results.append({
                    "source": "vector",
                    "doc_id": r["doc_id"],
                    "brand_name": r["brand_name"],
                    "filename": r["filename"],
                    "snippet": "",
                    "score": r["score"],
                })
        except Exception:
            pass

    # Deduplicate by doc_id for hybrid mode, keeping highest score
    if mode == "hybrid":
        seen = {}
        for r in results:
            key = r["doc_id"]
            if key not in seen or r["score"] > seen[key]["score"]:
                seen[key] = r
        results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

    return results[:limit]


@router.get("/stats")
def get_stats():
    """Get aggregate statistics about the case library."""
    db = _get_db()
    total_cases = db.query(CaseProject).count()
    total_files = db.query(CaseFile).count()

    cases = db.query(CaseProject).all()
    industries = {}
    for c in cases:
        ind = c.industry or "Unclassified"
        industries[ind] = industries.get(ind, 0) + 1

    avg_completeness = (
        sum(c.completeness_score for c in cases) / total_cases
        if total_cases > 0
        else 0
    )

    result = {
        "total_cases": total_cases,
        "total_files": total_files,
        "avg_completeness": round(avg_completeness, 2),
        "industries": industries,
        "cases_with_discovery": sum(1 for c in cases if c.has_discovery),
        "cases_with_strategy": sum(1 for c in cases if c.has_strategy),
        "cases_with_guidelines": sum(1 for c in cases if c.has_guidelines),
    }
    db.close()
    return result


def _case_summary(c: CaseProject) -> dict:
    return {
        "id": c.id,
        "brand_name": c.brand_name,
        "brand_name_zh": c.brand_name_zh or "",
        "industry": c.industry or "",
        "sub_category": c.sub_category or "",
        "total_files": c.total_files,
        "total_size_mb": c.total_size_mb,
        "completeness_score": c.completeness_score,
        "has_discovery": bool(c.has_discovery),
        "has_strategy": bool(c.has_strategy),
        "has_guidelines": bool(c.has_guidelines),
        "has_survey": bool(c.has_survey),
        "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
    }


def _file_dict(f: CaseFile) -> dict:
    return {
        "id": f.id,
        "filename": f.filename,
        "doc_type": f.doc_type,
        "doc_label": f.doc_label,
        "phase": f.phase,
        "size_bytes": f.size_bytes,
        "word_count": f.word_count,
        "language_hint": f.language_hint,
        "quality": f.quality,
    }
