"""Google Drive change detection for case library auto-sync.

Designed to be called periodically (cron / scheduled task).
Detects new or modified files in the monitored Drive folder
and triggers re-ingestion for affected cases.

Usage:
    cd backend
    python3 -m module_b.gdrive_watcher
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from module_b.auth import get_drive_service

STATE_FILE = Path(os.getenv("WATCHER_STATE_FILE", DATA_DIR / "watcher_state.json"))
DRIVE_DOWNLOAD_DIR = Path(os.getenv("DRIVE_DOWNLOAD_DIR", DATA_DIR / "drive_updates"))
INGESTED_CASES_FILE = Path(os.getenv("INGESTED_CASES_FILE", DATA_DIR / "ingested_cases.json"))
CASE_DOWNLOAD_BASE = Path(os.getenv("CASE_DOWNLOAD_BASE", DATA_DIR / "cases"))


def _load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def check_for_changes() -> list[dict]:
    """Check Google Drive for changes since last check.

    Returns:
        List of changed items: [{"file_id", "name", "change_type", "parent_id"}]
    """
    service = get_drive_service()
    state = _load_state()
    start_page_token = state.get("page_token")

    # Get initial page token if first run
    if not start_page_token:
        resp = service.changes().getStartPageToken().execute()
        start_page_token = resp.get("startPageToken")
        _save_state({"page_token": start_page_token, "last_checked": _now_iso()})
        return []

    changes = []
    page_token = start_page_token

    while page_token:
        resp = service.changes().list(
            pageToken=page_token,
            spaces="drive",
            fields="nextPageToken, newStartPageToken, changes(fileId, file(name, mimeType, parents, trashed))",
            pageSize=100,
        ).execute()

        for change in resp.get("changes", []):
            file_info = change.get("file", {})
            if file_info.get("trashed"):
                change_type = "deleted"
            else:
                change_type = "modified"

            changes.append({
                "file_id": change["fileId"],
                "name": file_info.get("name", ""),
                "mime_type": file_info.get("mimeType", ""),
                "change_type": change_type,
                "parent_ids": file_info.get("parents", []),
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            new_token = resp.get("newStartPageToken")
            if new_token:
                _save_state({
                    "page_token": new_token,
                    "last_checked": _now_iso(),
                    "last_changes_count": len(changes),
                })
            break

    return changes


def _load_ingested_cases() -> dict:
    """Map of {drive_folder_id: {brand_name, folder_name, case_id}} for known brand folders."""
    if INGESTED_CASES_FILE.exists():
        with open(INGESTED_CASES_FILE) as f:
            return json.load(f)
    return {}


def _save_ingested_cases(data: dict):
    INGESTED_CASES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INGESTED_CASES_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _find_brand_folder_id(parent_ids: list[str], known_brand_ids: set[str], service, cache: dict) -> str | None:
    """Walk up the parent chain until we hit a known brand folder.

    Drive's changes.list only gives the immediate parent. A change to
    External/<BRAND>/subfolder/file.pdf has parent=subfolder. We climb until
    we find a folder that's in our known_brand_ids set, or run out of parents.
    """
    for pid in parent_ids:
        if pid in known_brand_ids:
            return pid
        if pid in cache:
            resolved = cache[pid]
            if resolved is not None:
                return resolved
            continue
        try:
            meta = service.files().get(fileId=pid, fields="parents").execute()
        except Exception:
            cache[pid] = None
            continue
        resolved = _find_brand_folder_id(meta.get("parents", []), known_brand_ids, service, cache)
        cache[pid] = resolved
        if resolved:
            return resolved
    return None


def sync_changes(changes: list[dict]) -> dict:
    """Process detected changes: group by brand folder → re-download → re-ingest.

    Returns:
        {"affected_brands": int, "files_seen": int, "skipped": int, "errors": int,
         "ingest_results": [{"brand_name", "case_project_id", "files_processed", ...}]}
    """
    base = {"affected_brands": 0, "files_seen": 0, "skipped": 0, "errors": 0, "ingest_results": []}
    if not changes:
        return base

    from module_b.gdrive import GDriveClient, RELEVANT_EXTENSIONS, GOOGLE_WORKSPACE_TYPES
    from module_b.ingest import ingest_case

    client = GDriveClient()
    service = get_drive_service()
    ingested_map = _load_ingested_cases()
    known_brand_ids = set(ingested_map.keys())
    parent_cache: dict[str, str | None] = {}

    affected: dict[str, dict] = {}  # brand_folder_id -> brand_info
    skipped = 0
    files_seen = 0

    for change in changes:
        files_seen += 1
        if change["change_type"] == "deleted":
            skipped += 1
            continue

        ext = Path(change["name"]).suffix.lower()
        is_relevant = ext in RELEVANT_EXTENSIONS or change["mime_type"] in GOOGLE_WORKSPACE_TYPES
        if not is_relevant:
            skipped += 1
            continue

        brand_id = _find_brand_folder_id(change["parent_ids"], known_brand_ids, service, parent_cache)
        if not brand_id:
            # Unknown brand (probably a new folder under External/) — skip; the
            # operator should run batch_ingest_all to register it first.
            skipped += 1
            continue

        affected[brand_id] = ingested_map[brand_id]

    errors = 0
    results = []
    for brand_id, info in affected.items():
        brand_name = info["brand_name"]
        try:
            files = client.list_folder(brand_id, recursive=True, max_depth=3)
            local_dir = CASE_DOWNLOAD_BASE / brand_name
            client.download_case_folder(brand_id, local_dir, max_depth=3, skip_large_mb=100)
            result = ingest_case(
                brand_name=brand_name,
                drive_folder_id=brand_id,
                drive_folder_name=info.get("folder_name", brand_name),
                local_dir=str(local_dir),
                drive_files=files,
                use_ai_tags=True,
                build_vector_index=False,
            )
            ingested_map[brand_id] = {
                **info,
                "case_id": result["case_project_id"],
                "last_synced": _now_iso(),
            }
            results.append({"brand_name": brand_name, **result})
        except Exception as e:
            errors += 1
            results.append({"brand_name": brand_name, "error": str(e)[:200]})

    if affected:
        _save_ingested_cases(ingested_map)

    return {
        "affected_brands": len(affected),
        "files_seen": files_seen,
        "skipped": skipped,
        "errors": errors,
        "ingest_results": results,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    print("Checking for Drive changes...")
    changes = check_for_changes()
    if not changes:
        print("No changes detected.")
        sys.exit(0)
    print(f"Found {len(changes)} changes:")
    for c in changes[:10]:
        print(f"  [{c['change_type']}] {c['name']}")
    result = sync_changes(changes)
    print(
        f"Sync result: affected_brands={result['affected_brands']}, "
        f"files_seen={result['files_seen']}, skipped={result['skipped']}, "
        f"errors={result['errors']}"
    )
    for r in result["ingest_results"]:
        if "error" in r:
            print(f"  ERROR {r['brand_name']}: {r['error']}")
        else:
            print(
                f"  OK {r['brand_name']}: case_id={r.get('case_project_id')}, "
                f"processed={r.get('files_processed')}, indexed={r.get('files_indexed')}"
            )
