"""Batch ingest all case folders from Google Drive External/ directory.

Usage:
    cd backend
    python3 -m module_b.scripts.batch_ingest_all [--ai-tags] [--skip-download]
"""
import json
import os
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DATA_DIR
from module_b.auth import get_drive_service
from module_b.gdrive import GDriveClient
from module_b.ingest import ingest_case

DOWNLOAD_BASE = Path(os.getenv("CASE_DOWNLOAD_BASE", DATA_DIR / "cases"))
ALREADY_INGESTED_FILE = Path(os.getenv("INGESTED_CASES_FILE", DATA_DIR / "ingested_cases.json"))


def load_ingested() -> dict:
    if ALREADY_INGESTED_FILE.exists():
        with open(ALREADY_INGESTED_FILE) as f:
            return json.load(f)
    return {}


def save_ingested(data: dict):
    ALREADY_INGESTED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ALREADY_INGESTED_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def extract_brand_name(folder_name: str) -> str:
    """Extract clean brand name from folder like '10. AEKE' or '24-CASEKOO'."""
    cleaned = re.sub(r"^\d+[\.\-\s]+", "", folder_name).strip()
    # Remove cross marks and extra whitespace
    cleaned = cleaned.replace("\u274c", "").strip()
    return cleaned


def main():
    use_ai = "--ai-tags" in sys.argv
    skip_download = "--skip-download" in sys.argv

    root_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "10W84WJ3JCx2W5YrzhR3snTOlj4vkhhmt")
    client = GDriveClient()

    # Find External folder
    external = client.find_subfolder(root_id, "External")
    if not external:
        print("ERROR: External folder not found")
        return

    print(f"External folder ID: {external['id']}")

    # List all brand folders
    all_folders = [
        f for f in client.list_folder(external["id"], recursive=False)
        if f["is_folder"]
    ]

    ingested = load_ingested()
    total = len(all_folders)
    success = 0
    errors = []

    print(f"\nFound {total} brand folders. Starting batch ingest...\n")

    for i, folder in enumerate(all_folders):
        brand_name = extract_brand_name(folder["name"])
        folder_id = folder["id"]

        # Skip if already ingested
        if folder_id in ingested:
            print(f"[{i+1}/{total}] SKIP {brand_name} (already ingested)")
            continue

        print(f"[{i+1}/{total}] Processing {brand_name}...")

        try:
            # List files
            files = client.list_folder(folder_id, recursive=True, max_depth=3)
            local_dir = DOWNLOAD_BASE / brand_name

            # Download if not skipping
            if not skip_download:
                client.download_case_folder(
                    folder_id, local_dir, max_depth=3, skip_large_mb=100
                )

            # Ingest
            result = ingest_case(
                brand_name=brand_name,
                drive_folder_id=folder_id,
                drive_folder_name=folder["name"],
                local_dir=str(local_dir),
                drive_files=files,
                use_ai_tags=use_ai,
                build_vector_index=False,
            )

            print(f"  -> ID={result['case_project_id']}, "
                  f"processed={result['files_processed']}, "
                  f"indexed={result['files_indexed']}, "
                  f"errors={len(result['errors'])}")

            ingested[folder_id] = {
                "brand_name": brand_name,
                "folder_name": folder["name"],
                "case_id": result["case_project_id"],
            }
            save_ingested(ingested)
            success += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            errors.append({"brand": brand_name, "error": str(e)})

    print(f"\n--- Batch Ingest Complete ---")
    print(f"Success: {success}/{total}")
    print(f"Errors: {len(errors)}")
    if errors:
        for e in errors:
            print(f"  {e['brand']}: {e['error'][:80]}")


if __name__ == "__main__":
    main()
