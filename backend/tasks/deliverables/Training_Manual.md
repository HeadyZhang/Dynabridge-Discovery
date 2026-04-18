# DynaBridge Knowledge Platform — Training Manual

Version 1.0 | April 2026

---

## 1. System Access

### Local Development

| Service | URL | Port |
|---------|-----|------|
| Frontend (Knowledge Platform) | http://localhost:3000 | 3000 |
| Backend API | http://localhost:8000 | 8000 |
| API Documentation (Swagger) | http://localhost:8000/docs | 8000 |

### Starting the System

```bash
# Terminal 1: Start backend
cd backend
source .venv/bin/activate
python3 main.py

# Terminal 2: Start frontend
cd frontend
npm run dev
```

### Environment Requirements

- Python 3.11+ with virtual environment (`.venv/`)
- Node.js 18+ with npm
- Google Drive Service Account (`service_account.json` in `backend/`)
- `.env` file with `GOOGLE_DRIVE_FOLDER_ID`

---

## 2. New Case Ingestion Workflows

### Workflow A: Automatic Module A Sync

When a brand discovery project in Module A is approved:

1. User clicks "Approve" on the project page (or calls `PATCH /api/projects/{id}/approve`)
2. System automatically creates a `DiscoveryEngagement` record
3. Consumer segments from the analysis are stored as `DiscoverySegment` records
4. The case appears in the Knowledge Base immediately

No manual action required.

### Workflow B: Google Drive Auto-Detection

The Drive watcher monitors the Google Drive folder for new files:

```bash
# Run manually
cd backend
python3 -m module_b.gdrive_watcher

# Set up as cron job (every 30 minutes)
*/30 * * * * cd /path/to/backend && .venv/bin/python -m module_b.gdrive_watcher
```

### Workflow C: Manual Batch Ingest

For initial setup or re-processing:

```bash
cd backend
source .venv/bin/activate

# Ingest all cases from Google Drive
python3 -m module_b.scripts.batch_ingest_all

# With AI tagging (uses Claude API, costs apply)
python3 -m module_b.scripts.batch_ingest_all --ai-tags

# Skip download (re-process already downloaded files)
python3 -m module_b.scripts.batch_ingest_all --skip-download
```

---

## 3. Searching and Browsing Cases

### Step-by-Step: Find a Case

1. Open http://localhost:3000/knowledge
2. Type brand name or keyword in the search bar
3. Press Enter to search
4. Review results — each shows brand name, matching file, and text snippet
5. Click a case card to view details

### Step-by-Step: Filter Cases

1. On the Knowledge Base page, locate the filter row below the search bar
2. Select an industry from the dropdown
3. Select "Has Discovery" to show only cases with Brand Discovery documents
4. The case grid updates automatically

### Step-by-Step: View Case Details

1. Click any case card
2. Review the header (brand name, completeness score)
3. Expand file phases (Discovery, Strategy, Design) to see individual files
4. Click the link icon next to any file to open it in Google Drive
5. Scroll to "Similar Cases" to find related brands

---

## 4. Dashboard Interpretation Guide

### Phase Coverage Chart
- Shows how many cases have each deliverable type
- **Action**: If "Guidelines" bar is low, prioritize brand guidelines creation

### Completeness Distribution
- Shows the spread of case quality
- **Ideal**: Most cases in the 75-100% bucket
- **Action**: Focus on upgrading cases in the 0-25% bucket

### Document Types
- Shows which file types dominate the library
- **Insight**: If "product_image" dominates, cases may lack strategic documents

### Language Distribution
- Shows English / Chinese / Bilingual split
- **Insight**: Bilingual files indicate completed deliverables (DynaBridge standard is ENG&CN)

### Top Cases by Completeness
- Ranked list of best-documented cases
- **Use**: Reference these as templates for new engagements

---

## 5. Administrator Operations

### Rebuild Search Index

If search results seem stale:

```bash
cd backend && source .venv/bin/activate

# Rebuild FTS index
python3 -c "
from module_b.search_index import FullTextIndex
fts = FullTextIndex()
fts.clear()
print('FTS index cleared. Re-run batch ingest to rebuild.')
"

# Re-ingest all cases
python3 -m module_b.scripts.batch_ingest_all --skip-download
```

### Check System Health

```bash
# Verify database
python3 -c "
from module_b.models import CaseProject
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DB_PATH
engine = create_engine(f'sqlite:///{DB_PATH}')
Session = sessionmaker(bind=engine)
db = Session()
print(f'Cases: {db.query(CaseProject).count()}')
"

# Verify API
curl http://localhost:8000/api/knowledge/stats

# Verify Drive connection
python3 -c "from module_b.auth import get_drive_service; get_drive_service(); print('OK')"
```

### Data Backup

```bash
# Backup databases
cp dynabridge.db dynabridge.db.backup
cp case_search.db case_search.db.backup
cp case_vectors.npz case_vectors.npz.backup
```

---

## 6. Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "No cases found" | Database empty | Run `batch_ingest_all.py` |
| Search returns no results | FTS index empty | Rebuild index (see Section 5) |
| Google Drive auth fails | Expired credentials | Check `service_account.json` |
| Frontend shows loading forever | Backend not running | Start backend with `python3 main.py` |
| "Module B not installed" warning | Import error | Ensure `module_b/` directory exists with `__init__.py` |
| Case completeness is 0% | Only images in folder | Expected — completeness measures strategic documents |
