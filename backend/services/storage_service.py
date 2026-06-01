import os
import uuid
import shutil
from pathlib import Path

class CloudStorageService:
    def __init__(self):
        # AWS S3 Configurations
        self.s3_bucket = os.getenv("AWS_S3_BUCKET")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        # Supabase Storage Configurations
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase_bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "interviews")
        
        # Local public fallback configuration
        self.local_upload_dir = Path("uploads/recordings")
        self.local_upload_dir.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file_path: str, filename: str) -> str:
        """
        Uploads a local file to the configured cloud storage (S3 or Supabase),
        or falls back to local storage serving with a generated URL.
        """
        # 1. AWS S3 Upload
        if self.aws_access_key and self.aws_secret_key and self.s3_bucket:
            try:
                import boto3
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                s3_key = f"recordings/{uuid.uuid4()}-{filename}"
                # Run standard blocking S3 call in executor to keep backend non-blocking
                import asyncio
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    s3_client.upload_file,
                    file_path,
                    self.s3_bucket,
                    s3_key
                )
                return f"https://{self.s3_bucket}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            except Exception as e:
                print(f"[StorageService] AWS S3 Upload failed: {e}")

        # 2. Supabase Storage Upload
        if self.supabase_url and self.supabase_key:
            try:
                import httpx
                supabase_url_clean = self.supabase_url.rstrip('/')
                s_filename = f"{uuid.uuid4()}-{filename}"
                upload_url = f"{supabase_url_clean}/storage/v1/object/{self.supabase_bucket}/recordings/{s_filename}"
                headers = {
                    "Authorization": f"Bearer {self.supabase_key}",
                    "apikey": self.supabase_key,
                    "Content-Type": "audio/webm"
                }
                with open(file_path, "rb") as f:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(upload_url, content=f.read(), headers=headers)
                        if response.status_code == 200:
                            return f"{supabase_url_clean}/storage/v1/object/public/{self.supabase_bucket}/recordings/{s_filename}"
            except Exception as e:
                print(f"[StorageService] Supabase Upload failed: {e}")

        # 3. Local Fallback Emulator (Production-Grade Local Path)
        dest_filename = f"{uuid.uuid4()}-{filename}"
        dest_path = self.local_upload_dir / dest_filename
        shutil.copy2(file_path, dest_path)
        
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        return f"{backend_url}/uploads/recordings/{dest_filename}"

storage_service = CloudStorageService()
