"""
Local Storage Service
======================
Stores all files on the local server filesystem.
No cloud storage. No S3. No Supabase. No API keys. No cost.

Files are stored under /uploads/ with sub-folders per type.
"""

import os
import uuid
import shutil
from pathlib import Path


UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", "uploads"))
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class LocalStorageService:
    """
    Manages file persistence on the local server filesystem.
    All resumes and recordings are stored in /uploads/.
    """

    def _ensure_dir(self, folder: str) -> Path:
        dir_path = UPLOAD_ROOT / folder
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    async def upload_file(self, file_path: str, filename: str, folder: str = "recordings") -> str:
        """
        Copies a file to local storage and returns a URL path.

        Args:
            file_path: Absolute path to the source file.
            filename:  Original filename (used as suffix for uniqueness).
            folder:    Sub-folder inside /uploads/ (e.g. 'resumes', 'recordings').

        Returns:
            Public URL string (served by FastAPI StaticFiles mount).
        """
        dest_dir = self._ensure_dir(folder)
        dest_filename = f"{uuid.uuid4().hex}_{filename}"
        dest_path = dest_dir / dest_filename

        try:
            shutil.copy2(file_path, dest_path)
        except Exception as e:
            raise RuntimeError(f"[LocalStorage] Failed to copy file to storage: {e}")

        return f"{BACKEND_URL}/uploads/{folder}/{dest_filename}"

    def delete_file(self, file_url: str) -> bool:
        """
        Deletes a file given its URL (as returned by upload_file).
        Safe — ignores missing files.

        Returns: True if deleted, False if file not found.
        """
        try:
            # Extract path from URL
            prefix = f"{BACKEND_URL}/uploads/"
            if file_url.startswith(prefix):
                relative = file_url[len(prefix):]
            elif file_url.startswith("/uploads/"):
                relative = file_url[len("/uploads/"):]
            else:
                return False

            file_path = UPLOAD_ROOT / relative
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception as e:
            print(f"[LocalStorage] Failed to delete {file_url}: {e}")
        return False

    def get_local_path(self, file_url: str) -> str | None:
        """Returns the absolute filesystem path from a storage URL."""
        try:
            prefix = f"{BACKEND_URL}/uploads/"
            if file_url.startswith(prefix):
                relative = file_url[len(prefix):]
                return str((UPLOAD_ROOT / relative).resolve())
            elif file_url.startswith("/uploads/"):
                relative = file_url[len("/uploads/"):]
                return str((UPLOAD_ROOT / relative).resolve())
        except Exception:
            pass
        return None


storage_service = LocalStorageService()
