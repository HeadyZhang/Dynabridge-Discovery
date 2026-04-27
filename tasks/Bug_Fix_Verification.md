# Bug Fix Verification Report

Date: 2026-04-27

## Summary

8 bugs identified during demo review, all fixed and verified.

## Results

| Bug | Issue | Fix | Status |
|-----|-------|-----|--------|
| 1 | "价格战" returns 0 results | FTS5 query expansion: Chinese progressive shortening + English prefix wildcards | ✅ 16 results |
| 2 | Search results link to case page without file context | Added `file_id` to search results, detail page scrolls to matching file with highlight | ✅ file_id present |
| 3 | Insights lack source traceability | Added expandable detail panel showing source case, evidence type, confidence, market | ✅ case_id present, UI expandable |
| 4 | AI Synthesis always outputs Chinese | Backend accepts `lang` param, frontend passes current language | ✅ English output confirmed |
| 5 | Marketing Intelligence always Chinese | Backend accepts `lang` param, localized all hardcoded labels | ✅ lang param accepted |
| 6 | Google Trends 429 rate limiting | Added 24h file cache + 3x retry with exponential backoff | ✅ source=google_trends |
| 7 | Datacube shows sample data without disclaimer | Added yellow warning banner + marked all campaigns as SAMPLE | ✅ banner + notes marked |
| 8 | Insights not bilingual | Added `insight_text_en` column + translation script + frontend lang-aware display | ✅ column exists, script ready |

## Commits

1. `95ca4d8` - fix: improve search recall with Chinese fuzzy matching and English prefix wildcards
2. `4e51b0e` - fix: search results link to specific file with highlight and scroll-to-file
3. `a5f19f5` - fix: insights cards show expandable source details with case link
4. `dd31ac4` - fix: AI synthesis respects language setting (en/cn)
5. `63c9304` - fix: marketing intelligence respects language setting + localize labels
6. `3491ec1` - fix: Google Trends 429 handling with retry, cache, and graceful degradation
7. `5004adf` - fix: datacube dashboard shows sample data disclaimer banner
8. `d1c1f56` - fix: insights support bilingual display with insight_text_en column

## Notes

- BUG 8 translations require a valid `ANTHROPIC_API_KEY`. Run `python -m module_b.scripts.translate_insights` once key is configured.
- BUG 6 cache is stored at `/tmp/trends_cache/` with 24h TTL.
- BUG 7 sample data banner will remain until real campaign data is imported.
