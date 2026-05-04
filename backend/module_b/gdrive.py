"""Google Drive client for browsing and downloading case files."""
import io
import re
from pathlib import Path
from typing import Optional

from googleapiclient.http import MediaIoBaseDownload

from module_b.auth import get_drive_service

# Google Workspace MIME → export format mapping
EXPORT_MAP = {
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".pptx",
    ),
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".docx",
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xlsx",
    ),
}

# File types we care about for case analysis
RELEVANT_EXTENSIONS = {
    ".pptx", ".ppt", ".pdf", ".docx", ".doc", ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".svg", ".ai",
}

# Google Workspace types we'll export
GOOGLE_WORKSPACE_TYPES = set(EXPORT_MAP.keys())


class GDriveClient:
    """High-level Google Drive operations for case library management."""

    def __init__(self):
        self._service = get_drive_service()

    def list_folder(
        self,
        folder_id: str,
        recursive: bool = False,
        max_depth: int = 5,
    ) -> list[dict]:
        """List files in a Drive folder.

        Args:
            folder_id: Google Drive folder ID.
            recursive: Whether to descend into subfolders.
            max_depth: Maximum recursion depth.

        Returns:
            List of file metadata dicts with keys:
            id, name, mimeType, size, path, is_folder
        """
        return self._list_recursive(folder_id, "", 0, max_depth if recursive else 0)

    def _list_recursive(
        self, folder_id: str, prefix: str, depth: int, max_depth: int
    ) -> list[dict]:
        items = []
        page_token = None

        while True:
            resp = self._service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, size)",
                pageSize=100,
                orderBy="name",
                pageToken=page_token,
            ).execute()

            for f in resp.get("files", []):
                is_folder = f["mimeType"] == "application/vnd.google-apps.folder"
                path = f"{prefix}/{f['name']}" if prefix else f["name"]

                entry = {
                    "id": f["id"],
                    "name": f["name"],
                    "mimeType": f["mimeType"],
                    "size": int(f.get("size", 0)),
                    "path": path,
                    "is_folder": is_folder,
                }
                items.append(entry)

                if is_folder and depth < max_depth:
                    children = self._list_recursive(
                        f["id"], path, depth + 1, max_depth
                    )
                    items.extend(children)

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        return items

    def download_file(self, file_id: str, save_path: Path, mime_type: str = "") -> Path:
        """Download a single file from Drive.

        For Google Workspace files (Slides/Docs/Sheets), automatically
        exports to the corresponding Office format.

        Returns:
            The actual path the file was saved to (extension may change for exports).
        """
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if mime_type in EXPORT_MAP:
            export_mime, ext = EXPORT_MAP[mime_type]
            actual_path = save_path.with_suffix(ext)
            request = self._service.files().export_media(
                fileId=file_id, mimeType=export_mime
            )
        else:
            actual_path = save_path
            request = self._service.files().get_media(fileId=file_id)

        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        actual_path.write_bytes(buf.getvalue())
        return actual_path

    def download_case_folder(
        self,
        folder_id: str,
        local_dir: Path,
        max_depth: int = 3,
        skip_large_mb: float = 200,
    ) -> list[dict]:
        """Download all relevant files from a case folder.

        Args:
            folder_id: Drive folder ID for the case.
            local_dir: Local directory to save files into.
            max_depth: How deep to recurse.
            skip_large_mb: Skip files larger than this (MB).

        Returns:
            List of download result dicts: {name, path, size, status}
        """
        files = self.list_folder(folder_id, recursive=True, max_depth=max_depth)
        results = []

        for f in files:
            if f["is_folder"]:
                continue

            # Check if relevant
            name = f["name"]
            ext = Path(name).suffix.lower()
            is_workspace = f["mimeType"] in GOOGLE_WORKSPACE_TYPES
            is_relevant = ext in RELEVANT_EXTENSIONS or is_workspace

            if not is_relevant:
                continue

            # Skip very large files
            size_mb = f["size"] / (1024 * 1024) if f["size"] else 0
            if size_mb > skip_large_mb:
                results.append({
                    "name": name,
                    "path": f["path"],
                    "size": f["size"],
                    "status": "skipped_too_large",
                })
                continue

            # Build local path
            local_path = local_dir / f["path"]
            try:
                actual_path = self.download_file(
                    f["id"], local_path, f["mimeType"]
                )
                results.append({
                    "name": name,
                    "path": str(actual_path),
                    "size": actual_path.stat().st_size,
                    "status": "downloaded",
                })
            except Exception as e:
                results.append({
                    "name": name,
                    "path": f["path"],
                    "size": f["size"],
                    "status": f"error: {e}",
                })

        return results

    def find_subfolder(self, parent_id: str, name_pattern: str) -> Optional[dict]:
        """Find a subfolder by name pattern (case-insensitive substring match).

        Returns:
            File metadata dict or None.
        """
        items = self.list_folder(parent_id, recursive=False)
        pattern = name_pattern.lower()
        for item in items:
            if item["is_folder"] and pattern in item["name"].lower():
                return item
        return None

    def find_case_folders(
        self, external_folder_id: str, case_names: list[str]
    ) -> dict[str, Optional[dict]]:
        """Find multiple case folders under the External/ directory.

        Args:
            external_folder_id: ID of the External/ folder.
            case_names: Brand names to search for.

        Returns:
            Mapping of case_name → folder metadata (or None if not found).
        """
        all_items = self.list_folder(external_folder_id, recursive=False)
        result = {}

        for name in case_names:
            pattern = name.lower()
            match = None
            for item in all_items:
                if item["is_folder"] and pattern in item["name"].lower():
                    match = item
                    break
            result[name] = match

        return result
