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


def sync_changes(changes: list[dict]) -> dict:
    """Process detected changes — download new/modified files and re-ingest.

    Returns:
        {"processed": int, "skipped": int, "errors": int}
    """
    if not changes:
        return {"processed": 0, "skipped": 0, "errors": 0}

    from module_b.gdrive import GDriveClient, RELEVANT_EXTENSIONS, GOOGLE_WORKSPACE_TYPES

    client = GDriveClient()
    processed = 0
    skipped = 0
    errors = 0

    for change in changes:
        if change["change_type"] == "deleted":
            skipped += 1
            continue

        # Check if file is relevant
        name = change["name"]
        ext = Path(name).suffix.lower()
        is_relevant = ext in RELEVANT_EXTENSIONS or change["mime_type"] in GOOGLE_WORKSPACE_TYPES

        if not is_relevant:
            skipped += 1
            continue

        try:
            # Download to tmp
            save_path = DRIVE_DOWNLOAD_DIR / name
            save_path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(change["file_id"], save_path, change["mime_type"])
            processed += 1
        except Exception:
            errors += 1

    return {"processed": processed, "skipped": skipped, "errors": errors}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    print("Checking for Drive changes...")
    changes = check_for_changes()
    if changes:
        print(f"Found {len(changes)} changes:")
        for c in changes[:10]:
            print(f"  [{c['change_type']}] {c['name']}")
        result = sync_changes(changes)
        print(f"Sync result: {result}")
    else:
        print("No changes detected.")
