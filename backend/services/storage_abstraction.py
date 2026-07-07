"""
services/storage_abstraction.py
=================================
Storage Abstraction Layer for HireIQ.

This module provides a unified interface for file storage.
Currently backed by Supabase Storage.

Future migration to AWS S3 or Azure Blob Storage requires ONLY:
  1. Implementing a new provider class (e.g. S3StorageProvider)
  2. Changing the STORAGE_PROVIDER env variable
  3. Zero changes elsewhere in the codebase.

Usage:
    from services.storage_abstraction import storage, BUCKET_RESUMES
    metadata = await storage.upload(file_bytes, "resume.pdf", BUCKET_RESUMES, "uploads")
    # Store `metadata` dict in MongoDB, never the file bytes.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Re-export bucket constants ────────────────────────────────────────────────
from services.supabase_storage import (
    BUCKET_RESUMES,
    BUCKET_RECORDINGS,
    BUCKET_WORKSPACE,
    BUCKET_ATTACHMENTS,
    supabase_storage,
)


class StorageRouter:
    """
    Routes storage operations to the configured provider.

    Provider selection via STORAGE_PROVIDER env var (default: "supabase").
    Supported values: "supabase"  (extend here for "s3", "azure", "local")
    """

    def __init__(self):
        self._provider_name = (os.getenv("STORAGE_PROVIDER") or "supabase").lower()
        self._provider = self._init_provider()

    def _init_provider(self):
        if self._provider_name == "supabase":
            logger.info("[Storage] Using Supabase Storage provider.")
            return supabase_storage

        # Placeholder: add S3/Azure providers here without touching callers.
        # elif self._provider_name == "s3":
        #     from services.s3_storage import s3_storage
        #     return s3_storage

        logger.warning(
            "[Storage] Unknown STORAGE_PROVIDER '%s'. Defaulting to Supabase.",
            self._provider_name,
        )
        return supabase_storage

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def is_configured(self) -> bool:
        return getattr(self._provider, "is_configured", False)

    async def upload(
        self,
        file_bytes: bytes,
        original_filename: str,
        bucket: str,
        folder: str = "",
        *,
        upsert: bool = False,
    ) -> dict:
        """
        Upload file bytes and return storage metadata.

        Returns:
        {
            "storage_provider": "supabase",
            "bucket": str,
            "file_name": str,
            "file_path": str,
            "public_url": str,
            "uploaded_at": str,
            "file_size": int
        }

        Raises RuntimeError if provider is unavailable.
        MongoDB should ONLY store this dict, never the bytes.
        """
        return await self._provider.upload(
            file_bytes, original_filename, bucket, folder, upsert=upsert
        )

    async def download(self, bucket: str, file_path: str) -> bytes:
        """
        Retrieve raw bytes from storage.
        Used when recruiter clicks 'Open Resume' or 'Download Resume'.
        Raises RuntimeError with a meaningful message if storage is unavailable.
        """
        return await self._provider.download(bucket, file_path)

    async def download_from_url(self, url: str) -> bytes:
        """Fetch bytes from a known public URL."""
        return await self._provider.download_from_public_url(url)

    async def delete(self, bucket: str, file_path: str) -> bool:
        """Remove an object from storage."""
        return await self._provider.delete(bucket, file_path)

    async def get_signed_url(
        self,
        bucket: str,
        file_path: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a time-limited signed URL for private bucket access."""
        return await self._provider.get_signed_url(bucket, file_path, expires_in)

    async def health_check(self) -> dict:
        """Verify storage provider connectivity."""
        return await self._provider.health_check()


# ── Module-level singleton ────────────────────────────────────────────────────
storage = StorageRouter()
