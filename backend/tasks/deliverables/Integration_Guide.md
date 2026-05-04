# DynaBridge Module B — Integration Guide

Version 1.0 | April 2026

---

## 1. Module A to Module B Data Sync

### How It Works

When a Module A brand discovery project is approved, the system automatically:

1. **Creates a CaseProject** in the Module B knowledge base
2. **Creates a DiscoveryEngagement** record linking the project
3. **Extracts consumer segments** from the analysis JSON and stores them as DiscoverySegment records

### Trigger Mechanism

The sync is triggered by the `PATCH /api/projects/{project_id}/approve` endpoint in `main.py`:

```python
@app.patch("/api/projects/{project_id}/approve")
async def approve_project(project_id: int):
    # 1. Update project status to APPROVED
    # 2. Call Module B integration
    from module_b.integration import on_project_approved
    result = await on_project_approved(project_id)
    return {"approved": True, "integration": result}
```

### Data Flow

```
Module A: Project (approved)
    |
    +--> analysis_json parsed
    |
    +--> CaseProject created/updated
    |     - brand_name, positioning_summary
    |     - has_discovery, has_strategy flags
    |
    +--> DiscoveryEngagement created
    |     - industry, challenge_type, status
    |     - analysis_summary
    |
    +--> DiscoverySegment records (0..N)
          - segment_name_en/zh, size_percentage
          - profile_json, is_primary_target
```

---

## 2. Google Drive Watcher Configuration

### Manual Execution

```bash
cd backend
source .venv/bin/activate
python3 -m module_b.gdrive_watcher
```

### Cron Setup

```bash
# Edit crontab
crontab -e

# Add this line (runs every 30 minutes)
*/30 * * * * cd /path/to/Dynabridge-Discovery/backend && /path/to/.venv/bin/python -m module_b.gdrive_watcher >> /var/log/dynabridge-watcher.log 2>&1
```

### How It Works

1. On first run, obtains a `startPageToken` from Google Drive Changes API
2. On subsequent runs, queries for changes since the last token
3. New/modified files matching relevant extensions are downloaded
4. State is persisted in `tasks/watcher_state.json`

### State File Format

```json
{
  "page_token": "12345",
  "last_checked": "2026-04-18T00:00:00+00:00",
  "last_changes_count": 3
}
```

---

## 3. API Endpoint Reference

### Module A Endpoints (unchanged)

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/projects` | Project CRUD |
| POST | `/api/projects/{id}/generate` | Generate report (SSE) |
| PATCH | `/api/projects/{id}/approve` | Approve + Module B sync |
| GET | `/api/projects/{id}/download` | Download PPTX |

### Module B — Knowledge Base

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/knowledge/cases` | List cases (filters: industry, challenge_type, segment, has_discovery, has_strategy) |
| GET | `/api/knowledge/cases/{id}` | Case detail with files |
| GET | `/api/knowledge/cases/{id}/similar` | Similar case recommendations |
| GET | `/api/knowledge/search` | Full-text + semantic search (params: q, mode, limit) |
| GET | `/api/knowledge/stats` | Aggregate statistics |
| GET | `/api/knowledge/dashboard` | Dashboard chart data |
| GET | `/api/knowledge/insights` | Cross-case insight explorer (params: q, industry) |
| GET | `/api/knowledge/survey-analytics` | Questionnaire analytics |
| GET | `/api/knowledge/engagements` | Discovery engagements with segments |
| GET | `/api/knowledge/export` | CSV/JSON export (params: format, industry) |

---

## 4. Environment Variables

| Variable | Location | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | `.env` | Claude API key for AI analysis |
| `GOOGLE_DRIVE_FOLDER_ID` | `.env` | Root Google Drive folder ID |
| `NEXT_PUBLIC_API_URL` | `.env` / `docker-compose.yml` | Backend URL for frontend |

### Files (not in version control)

| File | Location | Description |
|------|----------|-------------|
| `service_account.json` | `backend/` | Google Cloud Service Account credentials |
| `dynabridge.db` | project root | Main SQLite database |
| `case_search.db` | project root | FTS5 search index |
| `case_vectors.npz` | project root | Vector embeddings |

---

## 5. Troubleshooting

### Module B routes not loading

**Symptom**: `/api/knowledge/` returns 404

**Check**:
```bash
python3 -c "from module_b.api import router; print('OK')"
```

**Fix**: Ensure `module_b/` directory has `__init__.py` and all dependencies are installed.

### Google Drive auth failures

**Symptom**: `google.auth.exceptions.DefaultCredentialsError`

**Check**:
```bash
ls backend/service_account.json
python3 -c "from module_b.auth import get_drive_service; get_drive_service(); print('OK')"
```

**Fix**: Ensure `service_account.json` exists and the service account has been granted access to the Drive folder.

### Database migration after model changes

**Symptom**: `OperationalError: no such table`

**Fix**:
```bash
python3 -c "from models import Base, engine; from module_b.models import *; Base.metadata.create_all(engine)"
```

### Vector search returns empty

**Symptom**: `/api/knowledge/search?mode=vector` returns `[]`

**Fix**: Rebuild vector index:
```bash
python3 -m module_b.scripts.batch_ingest_all --skip-download
```
Or run the vector index builder manually (see Training Manual Section 5).

### FTS search returns stale results

**Fix**: Clear and rebuild:
```bash
python3 -c "from module_b.search_index import FullTextIndex; FullTextIndex().clear()"
python3 -m module_b.scripts.batch_ingest_all --skip-download
```
