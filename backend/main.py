import json
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DB_PATH, UPLOAD_DIR, OUTPUT_DIR, HOST, PORT
from models import Base, Project, UploadedFile, Slide, Comment, ProjectStatus, ProjectVersion

# Database setup
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ── Lightweight migrations for new columns ────────────────────
def _migrate_db():
    """Add missing columns to existing tables (idempotent)."""
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(projects)").fetchall()}
    for col, sql in [
        ("survey_mode", "ALTER TABLE projects ADD COLUMN survey_mode VARCHAR(20) DEFAULT 'simulated'"),
        ("survey_json", "ALTER TABLE projects ADD COLUMN survey_json TEXT DEFAULT ''"),
        ("survey_responses_json", "ALTER TABLE projects ADD COLUMN survey_responses_json TEXT DEFAULT ''"),
    ]:
        if col not in existing:
            cursor.execute(sql)
            print(f"[migrate] Added column: projects.{col}")

    # Migrate comments table
    comment_cols = {row[1] for row in cursor.execute("PRAGMA table_info(comments)").fetchall()}
    for col, sql in [
        ("feedback_type", "ALTER TABLE comments ADD COLUMN feedback_type VARCHAR(20) DEFAULT 'other'"),
        ("phase", "ALTER TABLE comments ADD COLUMN phase VARCHAR(30) DEFAULT ''"),
    ]:
        if col not in comment_cols:
            cursor.execute(sql)
            print(f"[migrate] Added column: comments.{col}")

    conn.commit()
    conn.close()

_migrate_db()

app = FastAPI(title="DynaBridge Brand Discovery", version="1.0.0")


@app.get("/health")
def health_check():
    """Health check endpoint for deployment monitoring."""
    import sqlite3
    db_ok = False
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("SELECT 1")
        conn.close()
        db_ok = True
    except Exception:
        pass
    return {
        "status": "healthy" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "version": "1.0.0",
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Project CRUD ─────────────────────────────────────────────

@app.get("/api/projects")
def list_projects():
    with Session() as db:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
        return [_project_dict(p) for p in projects]


@app.post("/api/projects")
def create_project(
    name: str = Form(...),
    brand_url: str = Form(""),
    competitor_urls: str = Form("[]"),
    language: str = Form("en"),
    phase: str = Form("brand_reality"),
    survey_mode: str = Form("simulated"),
):
    with Session() as db:
        project = Project(
            name=name,
            brand_url=brand_url,
            competitor_urls=competitor_urls,
            language=language,
            phase=phase,
            survey_mode=survey_mode if survey_mode in ("simulated", "real") else "simulated",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return _project_dict(project)


@app.get("/api/projects/{project_id}")
def get_project(project_id: int):
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        return _project_dict(project, include_slides=True, include_comments=True)


@app.patch("/api/projects/{project_id}")
def update_project(
    project_id: int,
    name: str = Form(None),
    brand_url: str = Form(None),
    competitor_urls: str = Form(None),
    language: str = Form(None),
    phase: str = Form(None),
):
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        if name is not None:
            project.name = name
        if brand_url is not None:
            project.brand_url = brand_url
        if competitor_urls is not None:
            project.competitor_urls = competitor_urls
        if language is not None:
            project.language = language
        if phase is not None:
            project.phase = phase
        db.commit()
        db.refresh(project)
        return _project_dict(project)


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int):
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        db.query(Comment).filter_by(project_id=project_id).delete()
        db.query(Slide).filter_by(project_id=project_id).delete()
        db.query(UploadedFile).filter_by(project_id=project_id).delete()
        db.delete(project)
        db.commit()
        return {"deleted": True}


# ─── File Upload ──────────────────────────────────────────────

@app.post("/api/projects/{project_id}/files")
async def upload_file(project_id: int, file: UploadFile = File(...)):
    project_dir = UPLOAD_DIR / str(project_id)
    project_dir.mkdir(exist_ok=True)

    file_path = project_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    suffix = Path(file.filename).suffix.lower().lstrip(".")
    file_type = {"pdf": "pdf", "docx": "docx", "doc": "docx",
                 "pptx": "pptx", "png": "image", "jpg": "image",
                 "jpeg": "image"}.get(suffix, "other")

    with Session() as db:
        uploaded = UploadedFile(
            project_id=project_id,
            filename=file.filename,
            file_path=str(file_path),
            file_type=file_type,
        )
        db.add(uploaded)
        db.commit()
        return {"id": uploaded.id, "filename": file.filename, "type": file_type}


# ─── Generate Pipeline ───────────────────────────────────────

@app.post("/api/projects/{project_id}/generate")
async def generate_report(project_id: int, phase: str = Form("full"), checkpoint: bool = Form(False)):
    """Trigger the full generation pipeline. Returns SSE stream of progress.

    Args:
        phase: "brand_reality" | "market_structure" | "full"
        checkpoint: If True, pause after generating this phase's slides for user review.
            Sets status to REVIEW_PHASE1/2/3 instead of REVIEW, emits "checkpoint" event.
            Frontend should show slides → collect feedback → call /approve or /regenerate.
    """

    async def event_stream():
        with Session() as db:
            project = db.query(Project).get(project_id)
            if not project:
                yield _sse("error", {"message": "Project not found"})
                return

            # Save the phase to the project
            project.phase = phase

            # In checkpoint mode for phase2/phase3, reuse existing research data
            # instead of re-scraping/re-researching from scratch
            existing_analysis = {}
            _incremental = checkpoint and phase in ("market_structure", "full") and project.analysis_json
            if _incremental:
                try:
                    existing_analysis = json.loads(project.analysis_json)
                except json.JSONDecodeError:
                    _incremental = False

            # Step 1: Scrape website (skip in incremental checkpoint mode)
            scrape_result = {}
            parsed_docs = []
            if _incremental:
                yield _sse("progress", {"step": "scraping", "message": "Reusing previous data (checkpoint mode)", "done": True})
            else:
                yield _sse("progress", {"step": "scraping", "message": "Crawling brand website..."})
                project.status = ProjectStatus.SCRAPING
                db.commit()

                from pipeline.scraper import scrape_brand_website
                scrape_result = await scrape_brand_website(project.brand_url)
                yield _sse("progress", {"step": "scraping", "message": "Website crawled", "done": True})

                # Step 2: Parse uploaded documents
                yield _sse("progress", {"step": "parsing", "message": "Parsing uploaded documents..."})
                project.status = ProjectStatus.PARSING
                db.commit()

                files = db.query(UploadedFile).filter_by(project_id=project_id).all()
                from pipeline.doc_parser import parse_documents
                parsed_docs = await parse_documents([f.file_path for f in files])
                yield _sse("progress", {"step": "parsing", "message": "Documents parsed", "done": True})

            # Step 2b: E-commerce scraping
            ecommerce_data = None
            review_data = None
            if not _incremental:
                try:
                    yield _sse("progress", {"step": "ecommerce", "message": "Scraping e-commerce data..."})
                    from pipeline.ecommerce_scraper import scrape_ecommerce
                    ecommerce_data = await scrape_ecommerce(project.name)
                    yield _sse("progress", {"step": "ecommerce", "message": "E-commerce data collected", "done": True})
                except Exception:
                    yield _sse("progress", {"step": "ecommerce", "message": "E-commerce scraping skipped", "done": True})

                # Step 2c: Review collection
                try:
                    yield _sse("progress", {"step": "reviews", "message": "Collecting customer reviews..."})
                    from pipeline.review_collector import collect_reviews
                    review_data = await collect_reviews(project.name)
                    yield _sse("progress", {"step": "reviews", "message": "Reviews collected", "done": True})
                except Exception:
                    yield _sse("progress", {"step": "reviews", "message": "Review collection skipped", "done": True})
            else:
                yield _sse("progress", {"step": "ecommerce", "message": "Reusing existing data (checkpoint mode)", "done": True})

            # Step 2d: Auto competitor discovery (uses Managed Agent with web_search when available)
            competitor_data = None
            manual_competitors = json.loads(project.competitor_urls) if project.competitor_urls else []
            if not _incremental:
                try:
                    yield _sse("progress", {"step": "competitors", "message": "Discovering competitors (AI agent research)..."})
                    from pipeline.competitor_discovery import discover_competitors
                    discovered = await discover_competitors(
                        brand_name=project.name,
                        brand_url=project.brand_url,
                        scrape_data=scrape_result,
                        ecommerce_data=ecommerce_data,
                        max_competitors=8,
                    )
                    competitor_data = discovered

                    # Merge manual + discovered names (dedup)
                    discovered_names = [c["name"] for c in discovered]
                    all_competitor_names = list(manual_competitors)
                    for name in discovered_names:
                        if name.lower() not in [m.lower() for m in all_competitor_names]:
                            all_competitor_names.append(name)

                    # Save merged list back to project
                    project.competitor_urls = json.dumps(all_competitor_names, ensure_ascii=False)
                    db.commit()

                    yield _sse("progress", {
                        "step": "competitors",
                        "message": f"Found {len(discovered)} competitors",
                        "done": True,
                        "competitors": discovered,
                    })
                except Exception:
                    yield _sse("progress", {"step": "competitors", "message": "Competitor discovery skipped", "done": True})
            else:
                yield _sse("progress", {"step": "competitors", "message": "Reusing existing competitors (checkpoint mode)", "done": True})

            # Step 2e: Desktop research pipeline (3 sequential sessions)
            desktop_research = None
            industry_data = None
            if _incremental:
                yield _sse("progress", {"step": "researching", "message": "Reusing existing research (checkpoint mode)", "done": True})
            if not _incremental:
                try:
                    # Session 1: Brand + Category Research
                    yield _sse("progress", {"step": "researching", "message": "Researching brand background and category..."})
                    from pipeline.managed_agent import research_brand_context
                    brand_context = await research_brand_context(
                        brand_name=project.name,
                        brand_url=project.brand_url,
                    )
                    yield _sse("progress", {"step": "researching", "message": "Brand research complete. Cooling down before next session..."})
                    await asyncio.sleep(30)

                    # Re-discover competitors using brand context if initial discovery was poor
                    comp_names = json.loads(project.competitor_urls) if project.competitor_urls else []

                    def _is_bad_competitor_name(n):
                        n_lower = n.lower()
                        if len(n) > 40 or n.startswith("(") or n.startswith("$"):
                            return True
                        if any(kw in n_lower for kw in ["amazon", "buying", "reviewed", "past month", "/count", "stainless", "recycled", "contains"]):
                            return True
                        if "$" in n or n_lower in ("other", "none", "n/a"):
                            return True
                        return False

                    bad_names = [n for n in comp_names if _is_bad_competitor_name(n)]
                    if len(bad_names) >= len(comp_names) / 2 or not comp_names:
                        yield _sse("progress", {"step": "researching", "message": "Re-discovering competitors with category context..."})
                        cat_name = ""
                        if brand_context and brand_context.get("category_landscape"):
                            cat_name = brand_context["category_landscape"].get("category_name", "")
                        from pipeline.managed_agent import discover_competitors_managed
                        rediscovered = await discover_competitors_managed(
                            brand_name=project.name,
                            brand_url=project.brand_url,
                            category_context=cat_name,
                            max_competitors=8,
                        )
                        if rediscovered and len(rediscovered) >= 3:
                            comp_names = [c["name"] for c in rediscovered]
                            project.competitor_urls = json.dumps(comp_names, ensure_ascii=False)
                            db.commit()
                            yield _sse("progress", {"step": "researching", "message": f"Re-discovered {len(comp_names)} competitors"})
                            await asyncio.sleep(30)

                    # Session 2: Competitor Deep Profiles
                    competitor_profiles = []
                    if comp_names:
                        yield _sse("progress", {"step": "researching", "message": f"Deep-researching {len(comp_names)} competitors..."})
                        from pipeline.managed_agent import research_competitor_profiles
                        competitor_profiles = await research_competitor_profiles(
                            brand_name=project.name,
                            competitors=comp_names,
                            category="",
                            brand_context=brand_context,
                        )
                        yield _sse("progress", {"step": "researching", "message": f"Competitor profiles complete ({len(competitor_profiles)} profiled). Cooling down..."})
                        await asyncio.sleep(30)

                    # Session 3: Consumer + Market Research
                    yield _sse("progress", {"step": "researching", "message": "Researching consumer behavior and market dynamics..."})
                    from pipeline.managed_agent import research_consumer_landscape
                    consumer_landscape = await research_consumer_landscape(
                        brand_name=project.name,
                        category="",
                        brand_context=brand_context,
                        competitor_profiles=competitor_profiles,
                    )
                    yield _sse("progress", {"step": "researching", "message": "Consumer research complete"})

                    desktop_research = {
                        "brand_context": brand_context,
                        "competitor_profiles": competitor_profiles,
                        "consumer_landscape": consumer_landscape,
                    }

                    # Extract industry data from brand_context for backward compatibility
                    if brand_context and brand_context.get("category_landscape"):
                        industry_data = brand_context["category_landscape"]

                except Exception as e:
                    yield _sse("progress", {"step": "researching", "message": f"Desktop research partially complete: {str(e)[:100]}"})

            # Step 3: AI Analysis
            yield _sse("progress", {"step": "analyzing", "message": "Running AI brand analysis..."})
            project.status = ProjectStatus.ANALYZING
            db.commit()

            try:
                from pipeline.analyzer import analyze_brand
                competitors = json.loads(project.competitor_urls) if project.competitor_urls else []
                # Load real survey responses if available
                _survey_mode = getattr(project, "survey_mode", "simulated") or "simulated"
                _real_responses = None
                if _survey_mode == "real" and getattr(project, "survey_responses_json", ""):
                    try:
                        _real_responses = json.loads(project.survey_responses_json)
                        print(f"[main] Using REAL survey responses (n={_real_responses.get('sample_size', '?')})")
                    except json.JSONDecodeError:
                        print("[main] Failed to parse real survey responses, falling back to simulation")
                        _survey_mode = "simulated"

                analysis = await analyze_brand(
                    brand_name=project.name,
                    brand_url=project.brand_url,
                    scrape_data=scrape_result,
                    document_data=parsed_docs,
                    competitors=competitors,
                    language=project.language,
                    phase=phase,
                    ecommerce_data=ecommerce_data,
                    review_data=review_data,
                    competitor_data=competitor_data,
                    desktop_research=desktop_research,
                    survey_mode=_survey_mode,
                    real_survey_responses=_real_responses,
                )
                if industry_data:
                    analysis["industry_trends"] = industry_data

                # In incremental checkpoint mode, merge new phase into existing analysis
                if _incremental and existing_analysis:
                    existing_analysis.update(analysis)
                    analysis = existing_analysis

                project.analysis_json = json.dumps(analysis, ensure_ascii=False)
                db.commit()
                yield _sse("progress", {"step": "analyzing", "message": "Analysis complete", "done": True})
            except Exception as e:
                import traceback
                traceback.print_exc()
                project.status = ProjectStatus.DRAFT
                db.commit()
                yield _sse("error", {"message": f"AI analysis failed: {str(e)}"})
                return

            # Step 3b: Collect images for PPT (with category-aware keywords)
            collected_images = None
            try:
                yield _sse("progress", {"step": "images", "message": "Collecting brand images..."})
                from pipeline.image_collector import collect_images, infer_category_keywords
                cat_keywords = infer_category_keywords(
                    brand_name=project.name,
                    category="",
                    brand_context=desktop_research.get("brand_context") if desktop_research else None,
                )
                collected_images = await collect_images(
                    project_id=project_id,
                    brand_name=project.name,
                    brand_url=project.brand_url,
                    scrape_data=scrape_result,
                    ecommerce_data=ecommerce_data,
                    category_keywords=cat_keywords,
                )
                img_count = len(collected_images.get("all", []))
                yield _sse("progress", {"step": "images", "message": f"Collected {img_count} images", "done": True})
            except Exception:
                yield _sse("progress", {"step": "images", "message": "Image collection skipped", "done": True})

            # Step 4: Generate PPT
            yield _sse("progress", {"step": "generating", "message": "Generating PowerPoint..."})
            project.status = ProjectStatus.GENERATING
            db.commit()

            try:
                from pipeline.ppt_generator import generate_pptx
                # Parse competitor names from project column
                import json as _json
                _comp_names = []
                if project.competitor_urls:
                    try:
                        _comp_names = _json.loads(project.competitor_urls) if isinstance(project.competitor_urls, str) else project.competitor_urls
                    except (ValueError, TypeError):
                        pass
                pptx_path, slide_previews = await generate_pptx(
                    project_id=project_id,
                    analysis=analysis,
                    brand_name=project.name,
                    phase=phase,
                    collected_images=collected_images,
                    brand_url=project.brand_url or "",
                    competitor_names=_comp_names or None,
                )
                project.pptx_path = str(pptx_path)

                # Set status based on checkpoint mode
                if checkpoint:
                    phase_key = PHASE_KEY_MAP.get(phase, "phase3")
                    project.status = PHASE_STATUS_MAP.get(phase_key, ProjectStatus.REVIEW)
                else:
                    project.status = ProjectStatus.REVIEW
                db.commit()

                # Delete old slide records before saving new ones
                db.query(Slide).filter_by(project_id=project_id).delete()
                db.commit()

                # Save slide records
                for i, preview in enumerate(slide_previews):
                    slide = Slide(
                        project_id=project_id,
                        order=i,
                        slide_type=preview.get("type", "unknown"),
                        content_json=json.dumps(preview.get("content", {}), ensure_ascii=False),
                        preview_path=preview.get("preview_path", ""),
                    )
                    db.add(slide)
                db.commit()

                yield _sse("progress", {"step": "generating", "message": "PowerPoint generated", "done": True})

                # In checkpoint mode, emit checkpoint event and stop (no PDFs yet)
                if checkpoint:
                    phase_key = PHASE_KEY_MAP.get(phase, "phase3")
                    idx = PHASE_ORDER.index(phase_key) if phase_key in PHASE_ORDER else -1
                    next_phase = PHASE_ORDER[idx + 1] if idx + 1 < len(PHASE_ORDER) else None
                    yield _sse("checkpoint", {
                        "pptx_path": str(pptx_path),
                        "slide_count": len(slide_previews),
                        "phase": phase_key,
                        "status": str(project.status),
                        "next_phase": next_phase,
                        "message": f"Phase {phase_key} ready for review. Submit feedback on slides, then call /approve or /regenerate.",
                    })
                    return

                # Generate PDF reports (non-blocking — failure doesn't affect PPTX)
                pdf_paths = []
                try:
                    from pipeline.pdf_generator import generate_all_pdfs
                    import datetime
                    _date = datetime.datetime.now().strftime("%B %Y").upper()
                    pdf_paths = generate_all_pdfs(analysis, project.name, _date)
                    yield _sse("progress", {"step": "pdf", "message": f"PDF reports generated ({len(pdf_paths)} files)"})
                except Exception as _pdf_err:
                    print(f"[main] PDF generation failed (non-fatal): {_pdf_err}")

                yield _sse("complete", {"pptx_path": str(pptx_path), "slide_count": len(slide_previews), "pdf_paths": [str(p) for p in pdf_paths]})
            except Exception as e:
                project.status = ProjectStatus.DRAFT
                db.commit()
                yield _sse("error", {"message": f"PPT generation failed: {str(e)}"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ─── Slide Previews ──────────────────────────────────────────

@app.get("/api/projects/{project_id}/slides")
def get_slides(project_id: int):
    import time
    cache_bust = int(time.time())
    with Session() as db:
        slides = db.query(Slide).filter_by(project_id=project_id).order_by(Slide.order).all()
        return [{"order": s.order, "type": s.slide_type,
                 "content": json.loads(s.content_json),
                 "preview_url": f"/api/slides/{s.id}/preview?t={cache_bust}"} for s in slides]


@app.get("/api/slides/{slide_id}/preview")
def get_slide_preview(slide_id: int):
    from starlette.responses import Response
    with Session() as db:
        slide = db.query(Slide).get(slide_id)
        if not slide or not slide.preview_path:
            raise HTTPException(404, "Preview not found")
        resp = FileResponse(slide.preview_path, media_type="image/png")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp


# ─── Comments / Review ───────────────────────────────────────

@app.post("/api/projects/{project_id}/comments")
def add_comment(
    project_id: int,
    slide_order: Optional[int] = Form(None),
    author: str = Form(...),
    content: str = Form(...),
    feedback_type: str = Form("other"),
    phase: str = Form(""),
):
    with Session() as db:
        comment = Comment(
            project_id=project_id,
            slide_order=slide_order,
            author=author,
            content=content,
            feedback_type=feedback_type if feedback_type in ("insight", "image", "data", "text", "layout", "other") else "other",
            phase=phase,
        )
        db.add(comment)
        db.commit()
        return {"id": comment.id, "author": author, "content": content,
                "feedback_type": comment.feedback_type, "phase": comment.phase}


@app.get("/api/projects/{project_id}/comments")
def get_comments(project_id: int, phase: str = None, unresolved_only: bool = False):
    with Session() as db:
        q = db.query(Comment).filter_by(project_id=project_id)
        if phase:
            q = q.filter_by(phase=phase)
        if unresolved_only:
            q = q.filter_by(resolved=0)
        comments = q.order_by(Comment.created_at).all()
        return [{"id": c.id, "slide_order": c.slide_order, "author": c.author,
                 "content": c.content, "feedback_type": getattr(c, "feedback_type", "other"),
                 "phase": getattr(c, "phase", ""), "resolved": bool(c.resolved),
                 "created_at": c.created_at.isoformat()} for c in comments]


@app.patch("/api/comments/{comment_id}/resolve")
def resolve_comment(comment_id: int):
    with Session() as db:
        comment = db.query(Comment).get(comment_id)
        if not comment:
            raise HTTPException(404)
        comment.resolved = 1
        db.commit()
        return {"resolved": True}


# ─── Phase Checkpoint Endpoints ─────────────────────────────

PHASE_ORDER = ["phase1", "phase2", "phase3"]
PHASE_STATUS_MAP = {
    "phase1": ProjectStatus.REVIEW_PHASE1,
    "phase2": ProjectStatus.REVIEW_PHASE2,
    "phase3": ProjectStatus.REVIEW_PHASE3,
}
PHASE_GENERATE_MAP = {
    "phase1": "brand_reality",
    "phase2": "market_structure",
    "phase3": "full",
}
PHASE_KEY_MAP = {"brand_reality": "phase1", "market_structure": "phase2", "full": "phase3"}
PHASE_SECTION_MAP = {"phase1": "capabilities", "phase2": "competition", "phase3": "consumer"}


@app.post("/api/projects/{project_id}/phases/{phase}/approve")
async def approve_phase(project_id: int, phase: str, auto_continue: bool = False):
    """Approve a phase checkpoint and optionally auto-trigger next phase generation.

    Flow: phase1 (Brand Reality) → phase2 (Competition) → phase3 (Consumer) → done
    Approving auto-resolves all open feedback for this phase.

    Args:
        auto_continue: If True, returns SSE stream that approves this phase and
            immediately generates the next phase (checkpoint mode). Saves a round trip.
    """
    if phase not in PHASE_ORDER:
        raise HTTPException(400, f"Invalid phase: {phase}. Use: {PHASE_ORDER}")

    # Determine next phase up front
    idx = PHASE_ORDER.index(phase)
    has_next = idx + 1 < len(PHASE_ORDER)
    next_phase = PHASE_ORDER[idx + 1] if has_next else None

    # If auto_continue and there IS a next phase, return SSE stream
    if auto_continue and has_next:
        async def approve_and_continue():
            with Session() as db:
                project = db.query(Project).get(project_id)
                if not project:
                    yield _sse("error", {"message": "Project not found"})
                    return

                # Resolve feedback
                open_comments = db.query(Comment).filter_by(
                    project_id=project_id, phase=phase, resolved=0
                ).all()
                for c in open_comments:
                    c.resolved = 1
                db.commit()

                yield _sse("progress", {
                    "step": "approved",
                    "message": f"Phase {phase} approved ({len(open_comments)} comments resolved). Starting {next_phase}...",
                    "phase": phase,
                    "next_phase": next_phase,
                    "resolved_comments": len(open_comments),
                })

            # Delegate to generate_report with checkpoint=True for next phase
            next_gen_phase = PHASE_GENERATE_MAP[next_phase]
            gen_response = await generate_report(project_id, phase=next_gen_phase, checkpoint=True)
            # Stream through the generate SSE events
            async for chunk in gen_response.body_iterator:
                yield chunk

        return StreamingResponse(approve_and_continue(), media_type="text/event-stream")

    # Standard (non-streaming) approve
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")

        # Auto-resolve open feedback for this phase
        open_comments = db.query(Comment).filter_by(
            project_id=project_id, phase=phase, resolved=0
        ).all()
        for c in open_comments:
            c.resolved = 1
        db.commit()

        if has_next:
            return {
                "status": "approved",
                "phase": phase,
                "next_phase": next_phase,
                "message": f"Phase {phase} approved. Call POST /generate with phase='{PHASE_GENERATE_MAP[next_phase]}' and checkpoint=true to continue.",
                "resolved_comments": len(open_comments),
            }
        else:
            project.status = ProjectStatus.APPROVED
            db.commit()
            return {
                "status": "approved",
                "phase": phase,
                "next_phase": None,
                "message": "All phases approved. Deck is finalized.",
                "resolved_comments": len(open_comments),
            }


@app.post("/api/projects/{project_id}/phases/{phase}/regenerate")
async def regenerate_phase(project_id: int, phase: str):
    """Regenerate a phase incorporating unresolved feedback.

    Collects all unresolved comments for this phase, builds a feedback summary,
    and re-runs analysis + slide generation for the affected section.
    Returns SSE stream.
    """
    if phase not in PHASE_ORDER:
        raise HTTPException(400, f"Invalid phase: {phase}. Use: {PHASE_ORDER}")

    async def regen_stream():
        with Session() as db:
            project = db.query(Project).get(project_id)
            if not project:
                yield _sse("error", {"message": "Project not found"})
                return

            # Collect unresolved feedback for this phase
            feedback = db.query(Comment).filter_by(
                project_id=project_id, phase=phase, resolved=0
            ).order_by(Comment.slide_order).all()

            if not feedback:
                yield _sse("error", {"message": f"No unresolved feedback for {phase}"})
                return

            # Build feedback summary for LLM context
            feedback_summary = _build_feedback_summary(feedback)
            yield _sse("progress", {
                "step": "feedback",
                "message": f"Incorporating {len(feedback)} feedback items...",
                "feedback_count": len(feedback),
            })

            # Load existing analysis
            analysis = json.loads(project.analysis_json) if project.analysis_json else {}
            if not analysis:
                yield _sse("error", {"message": "No analysis found. Run /generate first."})
                return

            # Snapshot current version before overwriting
            try:
                latest_ver = db.query(ProjectVersion).filter_by(
                    project_id=project_id
                ).order_by(ProjectVersion.version.desc()).first()
                next_ver = (latest_ver.version + 1) if latest_ver else 1

                # Copy current PPTX to versioned path
                old_pptx = None
                if project.pptx_path and Path(project.pptx_path).exists():
                    ver_dir = OUTPUT_DIR / f"project_{project_id}" / "versions"
                    ver_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    old_pptx = str(ver_dir / f"v{next_ver}_{Path(project.pptx_path).name}")
                    shutil.copy2(project.pptx_path, old_pptx)

                snapshot = ProjectVersion(
                    project_id=project_id,
                    version=next_ver,
                    phase=phase,
                    analysis_json=project.analysis_json or "{}",
                    pptx_path=old_pptx,
                    trigger="regenerate",
                )
                db.add(snapshot)
                db.commit()
                yield _sse("progress", {"step": "snapshot", "message": f"Saved version {next_ver} backup"})
            except Exception as snap_err:
                print(f"[regen] Snapshot failed (non-fatal): {snap_err}")
                yield _sse("progress", {
                    "step": "snapshot",
                    "message": "Warning: could not save backup version. Proceeding without rollback safety.",
                    "warning": True,
                })

            # Re-analyze the affected section with feedback
            yield _sse("progress", {"step": "reanalyzing", "message": f"Re-analyzing {phase} with feedback..."})

            try:
                from pipeline.analyzer import revise_section
                section_key = PHASE_SECTION_MAP[phase]
                revised = await revise_section(
                    analysis=analysis,
                    section=section_key,
                    brand_name=project.name,
                    feedback=feedback_summary,
                )
                if revised:
                    analysis[section_key] = revised
                    project.analysis_json = json.dumps(analysis, ensure_ascii=False)
                    db.commit()
                    yield _sse("progress", {"step": "reanalyzing", "message": "Section revised with feedback", "done": True})
                else:
                    yield _sse("progress", {
                        "step": "reanalyzing",
                        "message": "WARNING: Revision returned empty — rebuilding with original analysis. Feedback may not be reflected.",
                        "done": True,
                        "warning": True,
                    })
            except Exception as e:
                import traceback; traceback.print_exc()
                yield _sse("progress", {
                    "step": "reanalyzing",
                    "message": f"WARNING: Revision failed ({e}). Rebuilding with original analysis — feedback NOT applied.",
                    "done": True,
                    "warning": True,
                })

            # Check if any feedback is about images — if so, re-collect
            has_image_feedback = any(
                (getattr(c, "feedback_type", "") or "") == "image" for c in feedback
            )

            # Collect images (reuse existing, or re-collect if image feedback)
            collected_images = {}
            img_dir = OUTPUT_DIR / f"project_{project_id}" / "images"
            if has_image_feedback:
                yield _sse("progress", {"step": "images", "message": "Re-collecting images based on feedback..."})
                try:
                    from pipeline.image_collector import collect_images as _collect_images, infer_category_keywords
                    cat_keywords = infer_category_keywords(
                        brand_name=project.name, category="",
                        brand_context=None,
                    )
                    collected_images = await _collect_images(
                        project_id=project_id,
                        brand_name=project.name,
                        brand_url=project.brand_url or "",
                        scrape_data={},
                        ecommerce_data=None,
                        category_keywords=cat_keywords,
                    )
                    img_count = len(collected_images.get("all", []))
                    yield _sse("progress", {"step": "images", "message": f"Re-collected {img_count} images", "done": True})
                except Exception as img_err:
                    print(f"[regen] Image re-collection failed: {img_err}")
                    # Fallback to existing images
                    if img_dir.exists():
                        for img_file in img_dir.glob("*.*"):
                            collected_images[img_file.stem] = str(img_file)
            else:
                if img_dir.exists():
                    for img_file in img_dir.glob("*.*"):
                        collected_images[img_file.stem] = str(img_file)

            # Regenerate PPT with updated analysis
            yield _sse("progress", {"step": "regenerating", "message": "Rebuilding slides..."})
            try:
                from pipeline.ppt_generator import generate_pptx
                import json as _json

                _comp_names = []
                if project.competitor_urls:
                    try:
                        _comp_names = _json.loads(project.competitor_urls)
                    except (ValueError, TypeError):
                        pass

                pptx_path, slide_previews = await generate_pptx(
                    project_id=project_id,
                    analysis=analysis,
                    brand_name=project.name,
                    phase=PHASE_GENERATE_MAP.get(phase, project.phase or "full"),
                    collected_images=collected_images,
                    brand_url=project.brand_url or "",
                    competitor_names=_comp_names or None,
                )
                project.pptx_path = str(pptx_path)
                db.commit()

                # Update slide records
                db.query(Slide).filter_by(project_id=project_id).delete()
                db.commit()
                for i, preview in enumerate(slide_previews):
                    slide = Slide(
                        project_id=project_id, order=i,
                        slide_type=preview.get("type", "unknown"),
                        content_json=json.dumps(preview.get("content", {}), ensure_ascii=False),
                        preview_path=preview.get("preview_path", ""),
                    )
                    db.add(slide)

                # Mark feedback as resolved
                for c in feedback:
                    c.resolved = 1
                db.commit()

                yield _sse("progress", {"step": "regenerating", "message": "Slides rebuilt", "done": True})
                yield _sse("complete", {
                    "pptx_path": str(pptx_path),
                    "slide_count": len(slide_previews),
                    "feedback_resolved": len(feedback),
                })
            except Exception as e:
                import traceback; traceback.print_exc()
                yield _sse("error", {"message": f"Regeneration failed: {e}"})

    return StreamingResponse(regen_stream(), media_type="text/event-stream")


def _build_feedback_summary(comments: list) -> str:
    """Build a structured feedback summary for LLM context."""
    by_type = {}
    for c in comments:
        ft = getattr(c, "feedback_type", "other") or "other"
        by_type.setdefault(ft, [])
        slide_ref = f"Slide {c.slide_order}" if c.slide_order is not None else "General"
        by_type[ft].append(f"[{slide_ref}] {c.content} (by {c.author})")

    parts = ["## User Feedback to Address\n"]
    type_labels = {
        "insight": "Insight Issues (depth, accuracy, relevance)",
        "image": "Image Issues (wrong, irrelevant, low quality)",
        "data": "Data Issues (incorrect numbers, implausible stats)",
        "text": "Text Issues (overflow, typos, wording)",
        "layout": "Layout Issues (formatting, spacing)",
        "other": "Other Feedback",
    }
    for ft, items in by_type.items():
        parts.append(f"### {type_labels.get(ft, ft)}")
        for item in items:
            parts.append(f"- {item}")
        parts.append("")
    return "\n".join(parts)


# ─── Version History & Rollback ─────────────────────────────

@app.get("/api/projects/{project_id}/versions")
def list_versions(project_id: int):
    """List all saved versions for a project (newest first)."""
    with Session() as db:
        versions = db.query(ProjectVersion).filter_by(
            project_id=project_id
        ).order_by(ProjectVersion.version.desc()).all()
        return [
            {
                "id": v.id,
                "version": v.version,
                "phase": v.phase,
                "trigger": v.trigger,
                "has_pptx": bool(v.pptx_path and Path(v.pptx_path).exists()),
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]


@app.post("/api/projects/{project_id}/versions/{version_id}/rollback")
def rollback_version(project_id: int, version_id: int):
    """Rollback project to a previous version's analysis and PPTX."""
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")

        version = db.query(ProjectVersion).filter_by(
            id=version_id, project_id=project_id
        ).first()
        if not version:
            raise HTTPException(404, "Version not found")

        # Snapshot current state before rollback (so rollback is itself reversible)
        latest_ver = db.query(ProjectVersion).filter_by(
            project_id=project_id
        ).order_by(ProjectVersion.version.desc()).first()
        next_ver = (latest_ver.version + 1) if latest_ver else 1

        pre_rollback = ProjectVersion(
            project_id=project_id,
            version=next_ver,
            phase=version.phase,
            analysis_json=project.analysis_json or "{}",
            pptx_path=project.pptx_path,
            trigger="pre_rollback",
        )
        db.add(pre_rollback)

        # Restore analysis
        project.analysis_json = version.analysis_json

        # Restore PPTX
        if version.pptx_path and Path(version.pptx_path).exists():
            import shutil
            target = OUTPUT_DIR / f"project_{project_id}" / Path(version.pptx_path).name.split("_", 1)[-1] if "_" in Path(version.pptx_path).name else Path(version.pptx_path).name
            # Restore to the standard pptx location
            brand_name = project.name or "Brand"
            target = OUTPUT_DIR / f"project_{project_id}" / f"{brand_name}_Brand_Discovery.pptx"
            shutil.copy2(version.pptx_path, str(target))
            project.pptx_path = str(target)

        db.commit()

        return {
            "status": "rolled_back",
            "restored_version": version.version,
            "pre_rollback_version": next_ver,
            "message": f"Rolled back to version {version.version}. Pre-rollback state saved as version {next_ver}.",
        }


# ─── Survey Design ──────────────────────────────────────────

@app.post("/api/projects/{project_id}/survey")
async def design_survey_endpoint(project_id: int):
    """Generate a customized survey questionnaire for a project."""
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")

        from pipeline.survey_designer import design_survey
        competitors = json.loads(project.competitor_urls) if project.competitor_urls else []

        context = ""
        if project.analysis_json:
            try:
                analysis = json.loads(project.analysis_json)
                cap = analysis.get("capabilities", {})
                comp = analysis.get("competition", {})
                context = f"Capabilities summary: {cap.get('capabilities_summary', '')}\n"
                context += f"Competition summary: {comp.get('competition_summary', '')}"
            except (json.JSONDecodeError, KeyError):
                pass

        survey = await design_survey(
            brand_name=project.name,
            brand_url=project.brand_url,
            competitors=competitors,
            language=project.language,
            analysis_context=context,
        )

        # Persist the designed questionnaire
        project.survey_json = json.dumps(survey, ensure_ascii=False)
        db.commit()

        return survey


@app.get("/api/projects/{project_id}/survey/download")
def download_survey(project_id: int, format: str = "json"):
    """Download the designed questionnaire.

    Query params:
        format: "json" (default) | "qsf" (Qualtrics Survey Format)
    """
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        if not project.survey_json:
            raise HTTPException(404, "No survey designed yet. Call POST /survey first.")
        survey = json.loads(project.survey_json)

        if format == "qsf":
            from pipeline.survey_designer import convert_to_qsf
            qsf = convert_to_qsf(survey, project.name)
            from starlette.responses import JSONResponse
            return JSONResponse(
                content=qsf,
                headers={
                    "Content-Disposition": f'attachment; filename="{project.name}_questionnaire.qsf"',
                    "Content-Type": "application/json",
                },
            )

        from starlette.responses import JSONResponse
        return JSONResponse(
            content=survey,
            headers={
                "Content-Disposition": f'attachment; filename="{project.name}_questionnaire.json"'
            },
        )


@app.post("/api/projects/{project_id}/survey/responses")
async def upload_survey_responses(project_id: int, file: UploadFile = File(...)):
    """Upload real survey responses (JSON or CSV).

    Expected JSON format (matching survey_simulator output):
    {
      "sample_size": 200,
      "question_data": {"Q1": {"categories": [...], "values": [...], ...}, ...},
      "demographics": {...},
      "verbatim_responses": {...}
    }

    CSV format: first row headers matching question IDs, subsequent rows are responses.
    """
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")

        content = await file.read()
        filename = file.filename or "responses"

        if filename.endswith(".json"):
            try:
                responses = json.loads(content.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise HTTPException(400, f"Invalid JSON: {e}")
        elif filename.endswith(".csv"):
            # Parse CSV into aggregated response format
            import csv
            import io
            try:
                reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
                rows = list(reader)
                if not rows:
                    raise HTTPException(400, "CSV is empty")
                responses = _aggregate_csv_responses(rows, project.survey_json)
            except Exception as e:
                raise HTTPException(400, f"CSV parse error: {e}")
        else:
            raise HTTPException(400, "Supported formats: .json, .csv")

        project.survey_responses_json = json.dumps(responses, ensure_ascii=False)
        project.survey_mode = "real"
        db.commit()

        return {
            "status": "uploaded",
            "sample_size": responses.get("sample_size", len(rows) if 'rows' in dir() else 0),
            "question_count": len(responses.get("question_data", {})),
        }


def _aggregate_csv_responses(rows: list[dict], survey_json_str: str = "") -> dict:
    """Aggregate individual CSV survey responses into percentage distributions.

    Each row is one respondent's answers. Columns are question IDs (Q1, Q2, ...).
    Returns format compatible with survey_simulator output.
    """
    n = len(rows)
    if n == 0:
        return {"sample_size": 0, "question_data": {}}

    # Load questionnaire for question metadata
    survey = {}
    if survey_json_str:
        try:
            survey = json.loads(survey_json_str)
        except json.JSONDecodeError:
            pass

    # Build question lookup
    q_lookup = {}
    for section in survey.get("sections", []):
        for q in section.get("questions", []):
            q_lookup[q["id"]] = q

    question_data = {}
    for col in rows[0].keys():
        if not col.startswith("Q"):
            continue

        # Count responses per option
        counts = {}
        for row in rows:
            val = row.get(col, "").strip()
            if not val:
                continue
            # Handle multi-select (semicolon-separated)
            for v in val.split(";"):
                v = v.strip()
                if v:
                    counts[v] = counts.get(v, 0) + 1

        if not counts:
            continue

        q_meta = q_lookup.get(col, {})
        q_type = q_meta.get("type", "single_select")
        categories = list(counts.keys())
        if q_type == "multi_select":
            values = [round(c / n * 100) for c in counts.values()]
        else:
            total = sum(counts.values())
            values = [round(c / total * 100) for c in counts.values()]

        question_data[col] = {
            "question_text": q_meta.get("text", col),
            "categories": categories,
            "values": values,
            "chart_type": "hbar" if len(categories) > 4 else "vbar",
        }

    # Extract demographics from standard columns if present
    demographics = {}
    demo_fields = {
        "generation": ["Gen Z", "Millennial", "Gen X", "Boomer"],
        "gender": None,
        "ethnicity": ["White", "Black", "Hispanic", "Asian", "Other"],
    }
    # Demographics would be parsed from Q1-Q5 typically; for now rely on question_data

    return {
        "sample_size": n,
        "question_data": question_data,
        "demographics": demographics,
    }


@app.get("/api/projects/{project_id}/survey/status")
def survey_status(project_id: int):
    """Check survey design and response collection status."""
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        return {
            "survey_mode": getattr(project, "survey_mode", "simulated") or "simulated",
            "has_survey": bool(project.survey_json),
            "has_responses": bool(project.survey_responses_json),
            "sample_size": json.loads(project.survey_responses_json).get("sample_size", 0) if project.survey_responses_json else 0,
        }


@app.patch("/api/projects/{project_id}/survey-mode")
def set_survey_mode(project_id: int, mode: str = Form(...)):
    """Toggle survey mode between 'simulated' and 'real'."""
    if mode not in ("simulated", "real"):
        raise HTTPException(400, "mode must be 'simulated' or 'real'")
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        project.survey_mode = mode
        db.commit()
        return {"survey_mode": mode}


# ─── Download ─────────────────────────────────────────────────

@app.get("/api/projects/{project_id}/download")
def download_pptx(project_id: int):
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project or not project.pptx_path:
            raise HTTPException(404, "PPTX not ready")
        return FileResponse(
            project.pptx_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=f"{project.name}_Brand_Discovery.pptx",
        )


@app.get("/api/projects/{project_id}/pdfs")
def list_pdfs(project_id: int):
    """List available PDF reports for a project."""
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        safe = project.name.lower().replace(" ", "_")[:20]
        report_dir = OUTPUT_DIR / "reports"
        phases = {
            "phase1": f"{safe}_phase1_brand_reality.pdf",
            "phase2": f"{safe}_phase2_market_structure.pdf",
            "phase3": f"{safe}_phase3_consumer_evidence.pdf",
            "phase4": f"{safe}_phase4_target_synthesis.pdf",
        }
        available = []
        for phase_key, filename in phases.items():
            path = report_dir / filename
            if path.exists():
                available.append({
                    "phase": phase_key,
                    "filename": filename,
                    "size": path.stat().st_size,
                    "download_url": f"/api/projects/{project_id}/pdfs/{phase_key}",
                })
        return available


@app.get("/api/projects/{project_id}/pdfs/{phase}")
def download_pdf(project_id: int, phase: str):
    """Download a specific PDF report (phase1, phase2, phase3, phase4)."""
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        safe = project.name.lower().replace(" ", "_")[:20]
        phase_map = {
            "phase1": f"{safe}_phase1_brand_reality.pdf",
            "phase2": f"{safe}_phase2_market_structure.pdf",
            "phase3": f"{safe}_phase3_consumer_evidence.pdf",
            "phase4": f"{safe}_phase4_target_synthesis.pdf",
        }
        filename = phase_map.get(phase)
        if not filename:
            raise HTTPException(400, f"Invalid phase: {phase}. Use phase1-phase4.")
        path = OUTPUT_DIR / "reports" / filename
        if not path.exists():
            raise HTTPException(404, f"PDF report for {phase} not found. Generate the report first.")
        phase_titles = {
            "phase1": "Brand_Reality",
            "phase2": "Market_Structure",
            "phase3": "Consumer_Evidence",
            "phase4": "Target_Synthesis",
        }
        return FileResponse(
            str(path),
            media_type="application/pdf",
            filename=f"{project.name}_{phase_titles[phase]}.pdf",
        )


@app.get("/api/projects/{project_id}/analysis")
def download_analysis(project_id: int):
    """Download raw analysis JSON for a project."""
    with Session() as db:
        project = db.query(Project).get(project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        if not project.analysis_json:
            raise HTTPException(404, "No analysis data yet. Generate the report first.")
        from starlette.responses import JSONResponse
        analysis = json.loads(project.analysis_json)
        return JSONResponse(
            content=analysis,
            headers={
                "Content-Disposition": f'attachment; filename="{project.name}_analysis.json"'
            },
        )


# ─── Helpers ──────────────────────────────────────────────────

def _project_dict(p: Project, include_slides=False, include_comments=False):
    d = {
        "id": p.id, "name": p.name, "brand_url": p.brand_url,
        "competitor_urls": json.loads(p.competitor_urls) if p.competitor_urls else [],
        "status": p.status, "language": p.language,
        "phase": getattr(p, "phase", None) or "brand_reality",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "has_pptx": bool(p.pptx_path),
        "slide_count": len(p.slides) if p.slides else 0,
        "file_count": len(p.files) if p.files else 0,
        "comment_count": len(p.comments) if p.comments else 0,
        "survey_mode": getattr(p, "survey_mode", "simulated") or "simulated",
        "has_survey": bool(getattr(p, "survey_json", "")),
        "has_survey_responses": bool(getattr(p, "survey_responses_json", "")),
    }
    if include_slides:
        d["slides"] = [{"order": s.order, "type": s.slide_type,
                        "preview_url": f"/api/slides/{s.id}/preview"} for s in p.slides]
    if include_comments:
        d["comments"] = [{"id": c.id, "slide_order": c.slide_order, "author": c.author,
                          "content": c.content, "resolved": bool(c.resolved)} for c in p.comments]
    return d


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
