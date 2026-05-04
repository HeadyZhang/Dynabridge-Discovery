# DynaBridge Knowledge Platform — User Guide

Version 1.0 | April 2026

---

## 1. System Overview

The DynaBridge Knowledge Platform (Module B) is a web-based system for managing, searching, and analyzing DynaBridge's historical brand consulting cases. It connects to the company's Google Drive case library, automatically classifies files, extracts content, and provides cross-case search and analytics.

**Key capabilities:**
- Search 48+ brand cases by keyword, industry, challenge type, or semantic meaning
- Browse individual case files with direct Google Drive links
- View cross-case analytics on the Discovery Dashboard
- Export data as CSV or JSON for downstream analysis
- Automatic sync from Google Drive when new files are added

**Access URLs:**
- Knowledge Base: `http://localhost:3000/knowledge`
- Dashboard: `http://localhost:3000/dashboard`
- API Documentation: `http://localhost:8000/docs`

---

## 2. Knowledge Base — Searching Cases

### 2.1 Keyword Search

1. Navigate to `/knowledge`
2. Type your search query in the search bar (supports English and Chinese)
3. Press Enter or click "Search"
4. Results show matching files with highlighted snippets

**Example queries:**
- `brand discovery` — find all discovery documents
- `consumer segmentation` — find consumer insight files
- `pricing strategy` — find pricing-related analyses

### 2.2 Filters

Below the search bar, use the filter dropdowns:

| Filter | Options | Effect |
|--------|---------|--------|
| Industry | All Industries / specific values | Show only cases in selected industry |
| Phase | All Phases / Has Discovery / No Discovery | Filter by deliverable completeness |

### 2.3 Case Cards

Each case card displays:
- **Brand name** (English + Chinese if available)
- **Industry tag** (when classified)
- **Completeness bar** — percentage of expected deliverables present
- **Phase badges** — Discovery, Strategy, Guidelines (green check = present)
- **File count and total size**

Click any card to open the case detail page.

---

## 3. Case Detail Page

### 3.1 Header Section

Shows brand name, industry, sub-category, and overall completeness score (0-100%).

Four summary cards:
- **Files** — total number of files in the case
- **Size** — total storage in MB
- **Discovery** — green check if Brand Discovery PPT exists
- **Strategy** — green check if Brand Strategy document exists

### 3.2 AI-Generated Tags

If AI tagging has been run, you will see:
- **Positioning Summary** — one-paragraph brand positioning overview
- **Core Challenges** — key strategic challenges identified
- **Key Insights** — strategic findings from the analysis
- **Competitors Mentioned** — brands referenced in the documents

### 3.3 File Table

Files are grouped by phase (Planning, Discovery, Strategy, Design, Marketing, Assets). Click a phase header to expand/collapse.

Each file row shows:
| Column | Description |
|--------|-------------|
| File | Original filename |
| Type | Document classification (e.g., "Brand Discovery", "Survey") |
| Size | File size |
| Words | Extracted word count |
| Drive | Click the link icon to open the original file in Google Drive |

### 3.4 Similar Cases

At the bottom, the system recommends up to 3 similar cases based on content similarity. Click any recommendation to navigate to that case.

---

## 4. Discovery Dashboard

Navigate to `/dashboard` to see cross-case analytics.

### 4.1 Top Statistics Bar

| Metric | Description |
|--------|-------------|
| Total Cases | Number of brand cases in the database |
| Total Files | Sum of all files across all cases |
| With Discovery | Cases that have a Brand Discovery document |
| With Strategy | Cases that have a Brand Strategy document |

### 4.2 Charts

| Chart | What it shows |
|-------|---------------|
| Phase Coverage | Bar chart — how many cases have each phase completed |
| Completeness Distribution | Bar chart — distribution of completeness scores (0-25%, 25-50%, etc.) |
| Document Types | Horizontal bar — most common file types across all cases |
| Language Distribution | Pie chart — English vs Chinese vs Bilingual files |
| Top Cases by Completeness | Ranked list with progress bars |
| Industry Breakdown | Pie chart — cases by industry (requires AI tagging) |

### 4.3 Data Export

- Click **Export** to download all case data as CSV
- Click **JSON** to download as JSON format
- CSV includes: Brand, Industry, Files, Size, Completeness, Discovery/Strategy/Guidelines flags

---

## 5. API Reference

All endpoints are prefixed with `/api/knowledge`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/cases` | List cases with optional filters (`?industry=`, `?challenge_type=`, `?segment=`) |
| GET | `/cases/{id}` | Case detail with all files |
| GET | `/cases/{id}/similar` | Similar case recommendations |
| GET | `/search?q=&mode=fts\|vector\|hybrid` | Full-text or semantic search |
| GET | `/stats` | Aggregate statistics |
| GET | `/dashboard` | Dashboard chart data |
| GET | `/insights?q=&industry=` | Cross-case insight explorer |
| GET | `/survey-analytics` | Questionnaire and survey file analytics |
| GET | `/engagements` | Discovery engagement records with segments |
| GET | `/export?format=csv\|json` | Data export |

Full interactive API documentation is available at `http://localhost:8000/docs`.

---

## 6. FAQ

**Q: How do I add a new case to the knowledge base?**
A: Cases are automatically ingested from Google Drive. Place files in the `External/` folder on Drive, then run the batch ingest script or wait for the Drive watcher to detect changes.

**Q: Why is a case showing 0% completeness?**
A: The completeness score measures how many standard DynaBridge deliverables are present (Discovery, Strategy, Guidelines, etc.). A case with only product images will show low completeness.

**Q: Can I search in Chinese?**
A: Yes. The full-text search supports Chinese characters. Semantic search also works cross-lingually.

**Q: How do I trigger AI tagging for a case?**
A: Run the batch ingest script with `--ai-tags` flag: `python3 -m module_b.scripts.batch_ingest_all --ai-tags`

**Q: Where is the data stored?**
A: SQLite database at `dynabridge.db`. FTS index at `case_search.db`. Vector embeddings at `case_vectors.npz`.
