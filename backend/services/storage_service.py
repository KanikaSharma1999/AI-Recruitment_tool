"""
services/storage_service.py
============================
Legacy storage service — now a thin compatibility wrapper around
services/storage_abstraction.py (Supabase Storage).

This file is kept for backward compatibility with imports in existing routes.
All new code should import from services/storage_abstraction.py directly.
"""

import os
import logging
from services.storage_abstraction import (
    storage,
    BUCKET_RESUMES,
    BUCKET_RECORDINGS,
    BUCKET_WORKSPACE,
    BUCKET_ATTACHMENTS,
)

logger = logging.getLogger(__name__)


class CloudStorageService:
    """
    Legacy-compatible wrapper.
    Delegates all operations to the Supabase Storage abstraction layer.
    """

    async def upload_file(
        self,
        file_path: str,
        filename: str,
        folder: str = "recordings",
    ) -> str:
        """
        Upload a local file to Supabase Storage.
        Returns the public URL string.

        Raises RuntimeError if Supabase is unavailable.
        Does NOT silently fall back to local storage for binary files.
        """
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
        except OSError as exc:
            raise RuntimeError(f"Could not read file '{file_path}': {exc}") from exc

        # Route to the correct bucket based on folder hint
        bucket_map = {
            "resumes": BUCKET_RESUMES,
            "recordings": BUCKET_RECORDINGS,
            "workspace": BUCKET_WORKSPACE,
            "attachments": BUCKET_ATTACHMENTS,
        }
        bucket = bucket_map.get(folder, BUCKET_RECORDINGS)

        metadata = await storage.upload(file_bytes, filename, bucket, folder)
        return metadata["public_url"]

    async def upload_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        folder: str = "resumes",
    ) -> dict:
        """
        Upload raw bytes and return the full metadata dict.
        Prefer this over upload_file() for new code.
        """
        bucket_map = {
            "resumes": BUCKET_RESUMES,
            "recordings": BUCKET_RECORDINGS,
            "workspace": BUCKET_WORKSPACE,
            "attachments": BUCKET_ATTACHMENTS,
        }
        bucket = bucket_map.get(folder, BUCKET_RESUMES)
        return await storage.upload(file_bytes, filename, bucket, folder)

    @property
    def is_configured(self) -> bool:
        return storage.is_configured


# Module-level singleton (backward-compatible)
storage_service = CloudStorageService()
