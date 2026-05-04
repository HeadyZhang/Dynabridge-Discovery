# DynaBridge File Taxonomy System -- Technical Documentation

**Date:** April 2026
**Module:** Module B -- Customer Discovery Database
**Source:** `backend/module_b/taxonomy.py`

---

## Section 1: Overview

The DynaBridge File Taxonomy System provides automated classification of brand case files into standardized document types. The system is designed to process files downloaded from Google Drive and assign each file a structured classification that includes a document type, human-readable label, project phase, and confidence score.

**Key Metrics:**

- **15 document types** defined across the taxonomy
- **6 project phases** representing the DynaBridge engagement lifecycle
- **3-tier classification algorithm** with confidence scoring
- **Google Workspace export mapping** for Slides, Docs, and Sheets

The taxonomy serves as the foundation for the completeness audit system (`module_b/audit.py`) and the database schema (`module_b/models.py`), enabling consistent file organization and retrieval across the entire case library.

---

## Section 2: Phase Definitions

The DynaBridge engagement lifecycle is divided into six sequential phases. Each phase represents a distinct stage of the brand development process.

| Phase Order | Phase      | Description                                                                                       |
|-------------|------------|---------------------------------------------------------------------------------------------------|
| 1           | planning   | Project initiation activities including kickoff meetings, scope definition, and stakeholder alignment. |
| 2           | discovery  | Research and analysis phase including brand audits, consumer insights, competitive analysis, and market surveys. |
| 3           | strategy   | Strategic framework development including brand strategy, positioning, naming, and workshop facilitation. |
| 4           | design     | Visual and identity design including logo concepts, visual identity systems, and brand guidelines.  |
| 5           | marketing  | Marketing execution deliverables including social media strategy, content calendars, and campaign planning. |
| 6           | assets     | Supporting assets including product photography, video content, design source files, and archives.  |

Phase ordering is defined in `PHASE_ORDER` and is used by the audit system to structure completeness reports.

---

## Section 3: Document Type Reference

The following table defines all 15 document types recognized by the taxonomy classifier.

| doc_type          | Label               | Phase     | Matching Patterns                                                       | Confidence |
|-------------------|----------------------|-----------|-------------------------------------------------------------------------|------------|
| discovery         | Brand Discovery      | discovery | `discovery`, `brand\s*discovery`                                        | 0.9        |
| strategy          | Brand Strategy       | strategy  | `brand[_\s]*strategy`, `strategy[_\s]*workshop`, `strategy`             | 0.9        |
| assessment        | Brand Assessment     | discovery | `brand\s*assessment`, `brand\s*review`, `preliminary.*review`           | 0.9        |
| naming            | Naming / Renaming    | strategy  | `naming`, `renaming`, `name\s*project`                                  | 0.9        |
| consumer_insights | Consumer Insights    | discovery | `consumer\s*insight`, `persona`, `segmentation`, `customer.*persona`    | 0.9        |
| survey            | Survey / Research    | discovery | `survey`, `questionnaire`, `research\s*(report\|data\|section)`         | 0.9        |
| visual_identity   | Visual Identity      | design    | `visual\s*id`, `vis[_\s]*id`, `logo[_\s]*concept`, `logo[_\s]*round`, `logo[_\s]*r\d` | 0.9 |
| guidelines        | Brand Guidelines     | design    | `guideline`, `brand\s*book`, `design\s*guideline`                       | 0.9        |
| competitor        | Competitor Analysis  | discovery | `competitor`, `competitive`, `market\s*analysis`                        | 0.9        |
| kickoff           | Kickoff / Meeting    | planning  | `kickoff`, `kick[\s-]*off`, `meeting\s*note`                            | 0.9        |
| social_media      | Social Media         | marketing | `social\s*media`, `content\s*calendar`                                  | 0.9        |
| product_image     | Product Image        | assets    | Extension match: `.jpg`, `.jpeg`, `.png`, `.svg`, `.ai`, `.psd`, `.tif`, `.tiff` | 0.7 |
| video             | Video Asset          | assets    | Extension match: `.mp4`, `.mov`, `.avi`, `.mkv`                         | 0.7        |
| design_file       | Design File          | design    | Extension match: `.ai`, `.psd`, `.stp`, `.step`                         | 0.7        |
| archive           | Archive              | assets    | Extension match: `.zip`, `.rar`, `.7z`                                  | 0.7        |

**Notes:**

- Pattern-matched types use regular expressions evaluated against the lowercased filename. The first matching pattern wins.
- Extension-matched types (`product_image`, `video`, `design_file`, `archive`) do not use filename patterns; they match solely on file extension.
- The `design_file` and `product_image` types share the `.ai` and `.psd` extensions. In practice, extension matching iterates in dictionary order, so `product_image` takes precedence for these extensions.

---

## Section 4: Classification Algorithm

The `classify_file()` function implements a three-tier classification strategy with decreasing confidence levels.

### Tier 1: Filename Pattern Matching (Confidence: 0.9)

The classifier iterates through all document types that define `patterns` (11 of 15 types). For each type, it tests each regex pattern against the lowercased filename using `re.search()`. The first match terminates the search and returns the classification.

```
Input: "AEKE Brand Strategy -Dynabridge Version (Updated).xlsx"
Lowercased: "aeke brand strategy -dynabridge version (updated).xlsx"
Match: pattern "brand[_\s]*strategy" in doc_type "strategy"
Result: {doc_type: "strategy", phase: "strategy", confidence: 0.9}
```

### Tier 2: File Extension Matching (Confidence: 0.7)

If no pattern matches, the classifier extracts the file extension and checks it against extension sets defined on 4 document types (`product_image`, `video`, `design_file`, `archive`).

```
Input: "DSC02285.JPG"
Extension: ".jpg"
Match: ".jpg" in product_image extensions
Result: {doc_type: "product_image", phase: "assets", confidence: 0.7}
```

### Tier 3: MIME Type Fallback (Confidence: 0.5)

If neither pattern nor extension matches, the classifier inspects the MIME type string for Google Workspace indicators:

| MIME Type Contains | Assigned doc_type | Phase    |
|--------------------|-------------------|----------|
| `presentation`     | presentation      | strategy |
| `document`         | document          | planning |
| `spreadsheet`      | spreadsheet       | planning |

### Tier 4: Default (Confidence: 0.1)

Files that match no criteria receive: `{doc_type: "other", phase: "assets", confidence: 0.1}`.

### Classification Flow

```
classify_file(filename, mime_type)
    |
    +--> [1] Pattern match on filename? --> YES --> return (confidence 0.9)
    |                                       NO
    +--> [2] Extension match?           --> YES --> return (confidence 0.7)
    |                                       NO
    +--> [3] MIME type match?           --> YES --> return (confidence 0.5)
    |                                       NO
    +--> [4] Default "other"            --> return (confidence 0.1)
```

---

## Section 5: Usage Examples

### Example 1: AEKE Case Files

| Filename                                               | doc_type          | Phase     | Confidence |
|--------------------------------------------------------|-------------------|-----------|------------|
| AEKE Discovery Part 1 - English & Chinese.pptx        | discovery         | discovery | 0.9        |
| AEKE - Preliminary Brand Review (English+Chinese).pptx | assessment        | discovery | 0.9        |
| AEKE Consumer Insights Report (EN & CN).pptx          | consumer_insights | discovery | 0.9        |
| AEKE Brand Strategy -Dynabridge Version (Updated).xlsx | strategy          | strategy  | 0.9        |
| AEKE Strategy Workshop - Eng. & CN.pptx               | strategy          | strategy  | 0.9        |
| AEKE Naming Insights -(English&Chinese).pptx           | naming            | strategy  | 0.9        |
| Pronunction Feedback Survey.xlsx                        | survey            | discovery | 0.9        |
| AEKE - Brand Book (ENG&CN).pdf                         | guidelines        | design    | 0.9        |
| DSC02285.JPG                                           | product_image     | assets    | 0.7        |

### Example 2: CozyFit Case Files

| Filename                                    | doc_type      | Phase     | Confidence |
|---------------------------------------------|---------------|-----------|------------|
| CozyFit Discovery - Eng&Cn2.3.pptx         | discovery     | discovery | 0.9        |
| CozyFit_Brand_Strategy_Eng&Cn-AM.pptx      | strategy      | strategy  | 0.9        |
| CozyFit_Brand_Strategy_Eng&Cn-AM.pdf        | strategy      | strategy  | 0.9        |
| CozyFit Renaming - EN&CN.pptx              | naming        | strategy  | 0.9        |
| CF KICKOFF MEETING -eng.docx               | kickoff       | planning  | 0.9        |
| 20251206-125005.jpeg                        | product_image | assets    | 0.7        |

### Observations

- All strategic deliverables (Discovery, Strategy, Naming) are classified at the highest confidence tier (0.9) due to strong filename pattern matches.
- Product photography is reliably classified at confidence 0.7 via extension matching.
- The kickoff document for CozyFit demonstrates the `kickoff` pattern matcher working against the abbreviation "KICKOFF" in the filename.

---

## Section 6: Google Workspace Export Mapping

Files stored as native Google Workspace formats (Slides, Docs, Sheets) are exported to standard Office formats during the download process. The following mapping is applied:

| Google Workspace Format | Export MIME Type                                                              | Target Extension |
|-------------------------|-------------------------------------------------------------------------------|------------------|
| Google Slides           | `application/vnd.openxmlformats-officedocument.presentationml.presentation`  | `.pptx`          |
| Google Docs             | `application/vnd.openxmlformats-officedocument.wordprocessingml.document`    | `.docx`          |
| Google Sheets           | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`          | `.xlsx`          |

### Export Limitations

The Google Drive API imposes a file size limit on exports. Files exceeding approximately 100 MB in their exported format will return an `exportSizeLimitExceeded` error (HTTP 403). This was observed in the Phase 1 audit for two files:

- `Aeke_Design_Guidelines_Eng&Cn` (AEKE, Google Slides)
- `Lumibricks_Logo_Round 1 Revisions(Eng&Cn)` (LUMIBRICKS, Google Slides)

### MIME Type Classification

When native Google Workspace files cannot be exported and only their MIME type is available, the taxonomy classifier falls back to Tier 3 (MIME type matching) with a confidence of 0.5. The MIME type strings used for detection are:

- `application/vnd.google-apps.presentation` -- contains "presentation"
- `application/vnd.google-apps.document` -- contains "document"
- `application/vnd.google-apps.spreadsheet` -- contains "spreadsheet"

After export, the resulting files carry standard Office extensions and are classified using the standard Tier 1 and Tier 2 rules.

---

*End of Document*
