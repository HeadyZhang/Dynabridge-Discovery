"""Google Drive authentication via Service Account.

Credential resolution order (first hit wins):
  1. GOOGLE_SERVICE_ACCOUNT_JSON env var — raw JSON string (Railway-friendly).
  2. GOOGLE_SERVICE_ACCOUNT_FILE env var — path to JSON on disk.
  3. backend/service_account.json — local-dev default (gitignored).
"""
import json
import os
from pathlib import Path
from functools import lru_cache

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DEFAULT_SERVICE_ACCOUNT_FILE = Path(__file__).parent.parent / "service_account.json"


def _load_credentials():
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        try:
            info = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is set but not valid JSON"
            ) from e
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    path = Path(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", DEFAULT_SERVICE_ACCOUNT_FILE))
    if not path.exists():
        raise RuntimeError(
            f"No Google service account credentials found. Set "
            f"GOOGLE_SERVICE_ACCOUNT_JSON (raw JSON) or "
            f"GOOGLE_SERVICE_ACCOUNT_FILE (path), or place the JSON at {path}."
        )
    return service_account.Credentials.from_service_account_file(str(path), scopes=SCOPES)


@lru_cache(maxsize=1)
def get_drive_service():
    """Return an authenticated Google Drive v3 service instance.

    Uses Service Account credentials — no OAuth browser flow needed.
    Cached so repeated calls reuse the same connection.
    """
    return build("drive", "v3", credentials=_load_credentials())
