# DynaBridge Case Library Audit Report -- Phase 1

**Date:** April 2026
**Prepared by:** DynaBridge Discovery Team
**Document Status:** Phase 1 Deliverable -- Final

---

## Executive Summary

This report presents the findings of the Phase 1 audit of the DynaBridge case library hosted on Google Drive. The audit evaluated four priority brand cases -- AEKE, CASEKOO, LUMIBRICKS, and CozyFit -- against the standard DynaBridge deliverable framework, which defines nine expected deliverable types across three project phases (discovery, strategy, and design).

Across the four priority cases, completeness scores ranged from 33% (CozyFit) to 78% (AEKE). All four cases contain the two required deliverables (Brand Discovery PPT and Brand Strategy), but optional deliverables -- particularly Consumer Insights, Competitor Analysis, and Brand Guidelines -- are inconsistently present. Two Google Slides files exceeded the export size limit and could not be converted to PPTX during download. The broader library contains 40+ brand folders organized in a numbered directory structure under `External/`.

Phase 2 will extend this audit to the full library, populate the database, and enable search and retrieval through the DynaBridge platform.

---

## Section 1: Audit Methodology

The audit was conducted using the automated completeness auditor defined in `module_b/audit.py`, which operates as follows:

1. **File Enumeration.** All files and folders within a case's Google Drive directory are retrieved via the Google Drive API.

2. **Taxonomy Classification.** Each file is passed through the taxonomy classifier (`module_b/taxonomy.py`), which assigns a `doc_type`, `label`, `phase`, and `confidence` score using a three-tier matching strategy:
   - Pattern matching against filename (confidence: 0.9)
   - File extension matching (confidence: 0.7)
   - MIME type fallback for Google Workspace files (confidence: 0.5)

3. **Phase Coverage Mapping.** Classified files are mapped against the expected deliverable structure, which defines nine deliverable types across three phases:

   | Phase     | Required Deliverables      | Optional Deliverables                                      |
   |-----------|----------------------------|------------------------------------------------------------|
   | Discovery | Brand Discovery PPT        | Brand Assessment, Consumer Insights, Competitor Analysis, Survey / Research Data |
   | Strategy  | Brand Strategy             | Naming Project                                             |
   | Design    | --                         | Visual Identity, Brand Guidelines / Book                   |

4. **Completeness Scoring.** The completeness score is calculated as the ratio of present deliverables to total expected deliverables (9 types). A deliverable is marked "present" if at least one file matches its classification pattern.

5. **Recommendation Generation.** Automated recommendations flag missing consumer insights and brand guidelines, as these are critical for downstream design and marketing work.

---

## Section 2: Priority Case Analysis

### 2.1 AEKE

| Metric            | Value       |
|-------------------|-------------|
| Total Files       | 162         |
| Total Folders     | 15          |
| Total Size        | 2,396.9 MB  |
| Completeness Score | **78%** (7 of 9 deliverable types present) |

**Phase Breakdown:**

| Phase     | Deliverable Type       | Required | Present | Score |
|-----------|------------------------|----------|---------|-------|
| Discovery | Brand Discovery PPT    | Yes      | Yes     | +1    |
| Discovery | Brand Assessment       | No       | Yes     | +1    |
| Discovery | Consumer Insights      | No       | Yes     | +1    |
| Discovery | Competitor Analysis    | No       | No      | 0     |
| Discovery | Survey / Research Data | No       | Yes     | +1    |
| Strategy  | Brand Strategy         | Yes      | Yes     | +1    |
| Strategy  | Naming Project         | No       | Yes     | +1    |
| Design    | Visual Identity        | No       | No      | 0     |
| Design    | Brand Guidelines       | No       | Yes     | +1    |

**Present Deliverables:**

- Brand Discovery PPT: `AEKE Discovery Part 1 - English & Chinese.pptx`
- Brand Assessment: `AEKE - Preliminary Brand Review (English+Chinese).pptx`
- Consumer Insights: `AEKE Consumer Insights Report (EN & CN).pptx`
- Survey / Research Data: `Pronunction Feedback Survey.xlsx`, `One-on-one Questionnaire Requirement`
- Brand Strategy: `AEKE Brand Strategy -Dynabridge Version (Updated).xlsx`, `AEKE Strategy Workshop - Eng. & CN (multiple versions)` (6 files total)
- Naming Project: `AEKE Naming Insights -(English&Chinese).pptx`
- Brand Guidelines: `AEKE - Brand Book (ENG&CN).pdf`, `AEKE - Brand Book (ENT&CN).pptx`, `Aeke_Design_Guidelines_Eng&Cn.pdf`

**Missing Deliverables:**

- Competitor Analysis
- Visual Identity

**Recommendations:**

- Commission a competitor analysis document to strengthen the discovery phase.
- Consider producing a visual identity deliverable (logo concepts or visual direction) to bridge strategy and guidelines.
- The bulk of the 162 files (149 "other" files) are product photography (DSC*.JPG). These are correctly classified as product image assets.

---

### 2.2 CASEKOO

| Metric            | Value       |
|-------------------|-------------|
| Total Files       | 19          |
| Total Folders     | 5           |
| Total Size        | 145.8 MB    |
| Completeness Score | **44%** (4 of 9 deliverable types present) |

**Phase Breakdown:**

| Phase     | Deliverable Type       | Required | Present | Score |
|-----------|------------------------|----------|---------|-------|
| Discovery | Brand Discovery PPT    | Yes      | Yes     | +1    |
| Discovery | Brand Assessment       | No       | No      | 0     |
| Discovery | Consumer Insights      | No       | Yes     | +1    |
| Discovery | Competitor Analysis    | No       | No      | 0     |
| Discovery | Survey / Research Data | No       | Yes     | +1    |
| Strategy  | Brand Strategy         | Yes      | Yes     | +1    |
| Strategy  | Naming Project         | No       | No      | 0     |
| Design    | Visual Identity        | No       | No      | 0     |
| Design    | Brand Guidelines       | No       | No      | 0     |

**Present Deliverables:**

- Brand Discovery PPT: `CASEKOO Brand Discovery(ENG&CN).pptx` (2 versions), `CASEKOO Brand Discovery(ENG&CN).pdf`
- Consumer Insights: `CASEKOO Personas (Eng&Cn).pptx`
- Survey / Research Data: `Casekoo Market Research Survey (Draft V3) CN.pdf`, `Casekoo Market Research Survey (Draft V3).pdf`
- Brand Strategy: `CASEKOO_Brand_Strategy_ST_12.11[ENG&CN].pptx`, `Casekoo_Social_Media_Strategy_Presentation.pptx`, `CASEKOO Brand Strategy Feedback Overview.pptx`, `CASEKOO Brand Strategy Participant Survey.pptx`

**Missing Deliverables:**

- Brand Assessment
- Competitor Analysis
- Naming Project
- Visual Identity
- Brand Guidelines / Book

**Recommendations:**

- No brand guidelines found -- this is needed for design phase completion.
- No competitor analysis is present; recommend commissioning one or extracting competitive data from existing strategy documents.
- The case has strong strategy coverage (5 strategy-related files) but lacks design phase deliverables entirely.

---

### 2.3 LUMIBRICKS

| Metric            | Value       |
|-------------------|-------------|
| Total Files       | 83          |
| Total Folders     | 5           |
| Total Size        | 326.2 MB    |
| Completeness Score | **67%** (6 of 9 deliverable types present) |

**Phase Breakdown:**

| Phase     | Deliverable Type       | Required | Present | Score |
|-----------|------------------------|----------|---------|-------|
| Discovery | Brand Discovery PPT    | Yes      | Yes     | +1    |
| Discovery | Brand Assessment       | No       | No      | 0     |
| Discovery | Consumer Insights      | No       | No      | 0     |
| Discovery | Competitor Analysis    | No       | Yes     | +1    |
| Discovery | Survey / Research Data | No       | Yes     | +1    |
| Strategy  | Brand Strategy         | Yes      | Yes     | +1    |
| Strategy  | Naming Project         | No       | No      | 0     |
| Design    | Visual Identity        | No       | Yes     | +1    |
| Design    | Brand Guidelines       | No       | Yes     | +1    |

**Present Deliverables:**

- Brand Discovery PPT: `Lumibricks Brand Discovery.pptx`
- Competitor Analysis: `competitor.pptx`
- Survey / Research Data: `Conclusion of the External User Research Section.docx`, `Conclusions of the FO Fan User Research Section.docx`
- Brand Strategy: `Lumibricks_Brand_Strategy_ST_12.14(ENG&CN) (2).pptx`
- Visual Identity: `Lumibricks_Logo_Round 1 Revisions(Eng&Cn).pptx`
- Brand Guidelines: `ENG-BRAND BOOK.pdf`

**Missing Deliverables:**

- Brand Assessment
- Consumer Insights
- Naming Project

**Recommendations:**

- No consumer insights document found -- consider adding persona or segmentation research to strengthen the discovery phase.
- The case has strong end-to-end coverage from discovery through design.
- Notable supplementary files include PESTLE and SWOT analysis documents and user research analysis, which are valuable but not mapped to a formal deliverable type.

---

### 2.4 CozyFit

| Metric            | Value       |
|-------------------|-------------|
| Total Files       | 16          |
| Total Folders     | 1           |
| Total Size        | 97.3 MB     |
| Completeness Score | **33%** (3 of 9 deliverable types present) |

**Phase Breakdown:**

| Phase     | Deliverable Type       | Required | Present | Score |
|-----------|------------------------|----------|---------|-------|
| Discovery | Brand Discovery PPT    | Yes      | Yes     | +1    |
| Discovery | Brand Assessment       | No       | No      | 0     |
| Discovery | Consumer Insights      | No       | No      | 0     |
| Discovery | Competitor Analysis    | No       | No      | 0     |
| Discovery | Survey / Research Data | No       | No      | 0     |
| Strategy  | Brand Strategy         | Yes      | Yes     | +1    |
| Strategy  | Naming Project         | No       | Yes     | +1    |
| Design    | Visual Identity        | No       | No      | 0     |
| Design    | Brand Guidelines       | No       | No      | 0     |

**Present Deliverables:**

- Brand Discovery PPT: `CozyFit Discovery - Eng&Cn2.3.pptx`
- Brand Strategy: `CozyFit_Brand_Strategy_Eng&Cn-AM.pdf`, `CozyFit_Brand_Strategy_Eng&Cn-AM.pptx`
- Naming Project: `CozyFit Renaming - EN&CN.pptx`

**Missing Deliverables:**

- Brand Assessment
- Consumer Insights
- Competitor Analysis
- Survey / Research Data
- Visual Identity
- Brand Guidelines / Book

**Recommendations:**

- No consumer insights document found -- consider adding persona or segmentation research.
- No brand guidelines found -- needed for design phase completion.
- This is the least complete case in the priority set. Discovery phase has only the core Discovery PPT with no supporting research.
- 11 of 16 files are product photography (timestamped JPEGs), indicating the asset base exists but strategic documentation is thin.
- A kickoff meeting document (`CF KICKOFF MEETING -eng.docx`) is present and classified under the planning phase.

---

## Section 3: Export Failures

During the Google Drive download process, two files exceeded the Google API export size limit and could not be converted to their target format:

| Brand      | File Name                                         | Error                       |
|------------|---------------------------------------------------|-----------------------------|
| AEKE       | `Aeke_Design_Guidelines_Eng&Cn` (Google Slides)  | `exportSizeLimitExceeded` -- file too large to export as PPTX |
| LUMIBRICKS | `Lumibricks_Logo_Round 1 Revisions(Eng&Cn)` (Google Slides) | `exportSizeLimitExceeded` -- file too large to export as PPTX |

Both files are Google Slides presentations that exceed the 100 MB export threshold imposed by the Google Drive API. The underlying Google Slides files remain accessible in the browser. For Phase 2, the following mitigations are recommended:

1. **Manual export** -- Open each file in Google Slides and use File > Download > PPTX to export directly.
2. **Chunked export** -- Split large presentations into multiple parts before export.
3. **Direct link storage** -- Store the Google Slides URL in the database as an alternative access path.

---

## Section 4: Full Library Overview

The DynaBridge case library is organized under the `External/` directory on Google Drive. The library contains **40+ brand case folders** arranged in a numbered directory structure. The four priority cases audited in this report represent a cross-section of completeness levels:

| Completeness Tier | Brands                      | Score Range |
|-------------------|-----------------------------|-------------|
| High              | AEKE                        | 70--100%    |
| Medium            | LUMIBRICKS                  | 50--69%     |
| Low               | CASEKOO                     | 40--49%     |
| Minimal           | CozyFit                     | 0--39%      |

The numbered folder structure (e.g., `01_AEKE/`, `02_CASEKOO/`) provides a sequential ordering that reflects the chronological order of brand engagements. Each brand folder typically contains subfolders for project phases, though the internal structure varies significantly across brands.

The remaining 36+ brands in the library have not yet been audited and will be evaluated in Phase 2. Based on the priority case audit, it is expected that completeness scores will follow a similar distribution, with most cases clustering in the 40--70% range.

---

## Section 5: Recommendations for Phase 2

### 5.1 Library-Wide Audit

- Extend the automated audit to all 40+ brand cases in the `External/` directory.
- Generate per-brand completeness scores and aggregate statistics.
- Identify brands with critical gaps (missing required deliverables).

### 5.2 Database Population

- Ingest all case metadata into the `case_projects` and `case_files` tables defined in Module B.
- Run the taxonomy classifier against all files to populate `doc_type`, `phase`, and `confidence` fields.
- Store Google Drive folder IDs and file IDs for direct linking.

### 5.3 Export Failure Resolution

- Implement fallback strategies for oversized Google Workspace files (manual export, chunked export, or URL-based access).
- Log all export failures in the database for tracking.

### 5.4 Taxonomy Refinement

- Review classification confidence scores across the full library to identify low-confidence patterns.
- Add new document type patterns as needed (e.g., PESTLE analysis, SWOT analysis, content calendar).
- Consider adding a `kickoff` deliverable to the expected deliverables framework.

### 5.5 Search and Retrieval

- Build a search index over case file metadata to enable brand-level and document-type-level queries.
- Plan vector embedding generation for slide-level content search (Phase 2 extension).

### 5.6 Quality Assurance

- Establish a review workflow for cases with completeness scores below 50%.
- Define minimum completeness thresholds for "production-ready" cases.
- Flag duplicate files (e.g., CASEKOO has two copies of the Discovery PPTX at different sizes).

---

*End of Report*
