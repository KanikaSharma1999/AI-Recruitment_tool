"""
services/supabase_storage.py
============================
Supabase Storage Provider for HireIQ.
Implements the StorageProvider protocol.

Handles:
  - Resume PDFs
  - Interview recordings
  - Workspace documents
  - Candidate attachments

Never stores binary content in MongoDB.
MongoDB only stores the metadata dict returned by upload().
"""

import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ── Bucket names (one per file category) ─────────────────────────────────────
BUCKET_RESUMES       = "resumes"
BUCKET_RECORDINGS    = "recordings"
BUCKET_WORKSPACE     = "workspace"
BUCKET_ATTACHMENTS   = "attachments"

CONTENT_TYPES = {
    ".pdf":  "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc":  "application/msword",
    ".txt":  "text/plain",
    ".webm": "audio/webm",
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
}


class SupabaseStorageProvider:
    """
    Primary cloud storage provider.

    All public methods are async.
    upload() → returns a metadata dict (never bytes).
    get_download_url() → returns a signed or public URL for the file.
    delete() → removes the object from the bucket.
    """

    def __init__(self):
        self.url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY") or ""
        self._ready = bool(self.url and self.key)
        if not self._ready:
            logger.warning(
                "[SupabaseStorage] SUPABASE_URL / SUPABASE_SERVICE_KEY not configured. "
                "Storage uploads will fail unless env vars are set."
            )

    @property
    def is_configured(self) -> bool:
        return self._ready

    # ── internal helpers ──────────────────────────────────────────────────────

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }

    def _storage_base(self) -> str:
        return f"{self.url}/storage/v1"

    def _public_url(self, bucket: str, path: str) -> str:
        return f"{self._storage_base()}/object/public/{bucket}/{path}"

    # ── core upload ───────────────────────────────────────────────────────────

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
        Upload raw bytes to Supabase Storage.

        Returns metadata dict:
        {
            "storage_provider": "supabase",
            "bucket": str,
            "file_name": str,
            "file_path": str,   # e.g. "resumes/uuid-original.pdf"
            "public_url": str,
            "uploaded_at": str (ISO-8601),
            "file_size": int
        }

        Raises RuntimeError on failure (never silently falls back).
        """
        if not self._ready:
            raise RuntimeError(
                "Supabase Storage is not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file."
            )

        ext = Path(original_filename).suffix.lower()
        content_type = CONTENT_TYPES.get(ext, "application/octet-stream")
        unique_name = f"{uuid.uuid4()}-{original_filename}"
        file_path   = f"{folder}/{unique_name}" if folder else unique_name

        upload_url = f"{self._storage_base()}/object/{bucket}/{file_path}"

        headers = {
            **self._headers(),
            "Content-Type": content_type,
        }
        if upsert:
            headers["x-upsert"] = "true"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(upload_url, content=file_bytes, headers=headers)

            if resp.status_code not in (200, 201):
                logger.error(
                    "[SupabaseStorage] Upload failed: %s %s",
                    resp.status_code, resp.text[:300],
                )
                raise RuntimeError(
                    f"Supabase Storage upload failed (HTTP {resp.status_code}): {resp.text[:200]}"
                )

            public_url = self._public_url(bucket, file_path)
            logger.info(
                "[SupabaseStorage] Uploaded %s → %s (%d bytes)",
                original_filename, public_url, len(file_bytes),
            )

            return {
                "storage_provider": "supabase",
                "bucket":           bucket,
                "file_name":        unique_name,
                "file_path":        file_path,
                "public_url":       public_url,
                "uploaded_at":      datetime.now(timezone.utc).isoformat(),
                "file_size":        len(file_bytes),
            }

        except httpx.RequestError as exc:
            logger.error("[SupabaseStorage] Network error during upload: %s", exc)
            raise RuntimeError(
                f"Supabase Storage is unavailable (network error): {exc}"
            ) from exc

    # ── signed URL (for private buckets) ─────────────────────────────────────

    async def get_signed_url(
        self,
        bucket: str,
        file_path: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a signed URL for a private bucket object.
        For public buckets, use the public_url from the metadata directly.
        """
        if not self._ready:
            raise RuntimeError("Supabase Storage is not configured.")

        url = f"{self._storage_base()}/object/sign/{bucket}/{file_path}"
        payload = {"expiresIn": expires_in}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers())

        if resp.status_code != 200:
            raise RuntimeError(
                f"Supabase signed URL generation failed (HTTP {resp.status_code}): {resp.text[:200]}"
            )

        data = resp.json()
        signed_path = data.get("signedURL") or data.get("signedUrl") or ""
        if signed_path.startswith("/"):
            return f"{self.url}{signed_path}"
        return signed_path

    # ── download (fetch bytes for re-parsing) ─────────────────────────────────

    async def download(self, bucket: str, file_path: str) -> bytes:
        """
        Fetch raw bytes from Supabase Storage.
        Used when re-parsing a resume or streaming a recording.
        """
        if not self._ready:
            raise RuntimeError("Supabase Storage is not configured.")

        url = f"{self._storage_base()}/object/{bucket}/{file_path}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(url, headers=self._headers())

        if resp.status_code != 200:
            raise RuntimeError(
                f"Supabase Storage download failed (HTTP {resp.status_code}): "
                f"bucket={bucket}, path={file_path}"
            )
        return resp.content

    async def download_from_public_url(self, public_url: str) -> bytes:
        """Fetch bytes from a known public URL (no auth needed)."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(public_url)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch file from Supabase public URL "
                f"(HTTP {resp.status_code}): {public_url}"
            )
        return resp.content

    # ── delete ────────────────────────────────────────────────────────────────

    async def delete(self, bucket: str, file_path: str) -> bool:
        """Remove an object from the bucket. Returns True on success."""
        if not self._ready:
            return False
        url = f"{self._storage_base()}/object/{bucket}/{file_path}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(url, headers=self._headers())
        ok = resp.status_code in (200, 204)
        if not ok:
            logger.warning(
                "[SupabaseStorage] Delete failed: %s %s", resp.status_code, resp.text[:200]
            )
        return ok

    # ── health check ──────────────────────────────────────────────────────────

    async def health_check(self) -> dict:
        """Ping Supabase to verify connectivity."""
        if not self._ready:
            return {"healthy": False, "reason": "Not configured"}
        try:
            url = f"{self._storage_base()}/bucket"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=self._headers())
            return {"healthy": resp.status_code == 200, "status_code": resp.status_code}
        except Exception as exc:
            return {"healthy": False, "reason": str(exc)}


# ── Module-level singleton ────────────────────────────────────────────────────
supabase_storage = SupabaseStorageProvider()
