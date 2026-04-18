"""Google Drive authentication via Service Account."""
from pathlib import Path
from functools import lru_cache

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
SERVICE_ACCOUNT_FILE = Path(__file__).parent.parent / "service_account.json"


@lru_cache(maxsize=1)
def get_drive_service():
    """Return an authenticated Google Drive v3 service instance.

    Uses Service Account credentials — no OAuth browser flow needed.
    Cached so repeated calls reuse the same connection.
    """
    creds = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=creds)
