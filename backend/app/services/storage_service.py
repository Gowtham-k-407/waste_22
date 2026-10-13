import os
import shutil
import logging
from abc import ABC, abstractmethod
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("wastedash.storage")

class BaseStorageService(ABC):
    @abstractmethod
    def save_file(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        """Saves bytes to storage and returns the access URL or key."""
        pass

    @abstractmethod
    def get_file(self, key: str) -> Optional[bytes]:
        """Retrieves file bytes by key."""
        pass

    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """Deletes file by key."""
        pass

    @abstractmethod
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Returns direct or presigned URL for the given key."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Checks if key exists."""
        pass


class LocalStorageService(BaseStorageService):
    def __init__(self, base_dir: str = settings.MEDIA_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _resolve_path(self, key: str) -> str:
        # Sanitize key to prevent path traversal
        clean_key = key.lstrip("/\\").replace("..", "")
        return os.path.join(self.base_dir, clean_key)

    def save_file(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        dest_path = self._resolve_path(key)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)
        # Return web accessible path
        clean_key = key.lstrip("/\\")
        return f"/uploads/{clean_key}"

    def get_file(self, key: str) -> Optional[bytes]:
        path = self._resolve_path(key)
        if os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    def delete_file(self, key: str) -> bool:
        path = self._resolve_path(key)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception as e:
                logger.error(f"Failed to delete local file {path}: {e}")
                return False
        return False

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        clean_key = key.lstrip("/\\")
        return f"/uploads/{clean_key}"

    def exists(self, key: str) -> bool:
        return os.path.exists(self._resolve_path(key))


class S3StorageService(BaseStorageService):
    def __init__(self):
        import boto3
        from botocore.config import Config

        session_kwargs = {
            "aws_access_key_id": settings.STORAGE_ACCESS_KEY,
            "aws_secret_access_key": settings.STORAGE_SECRET_KEY,
            "region_name": settings.STORAGE_REGION,
        }
        
        client_kwargs = {
            "config": Config(signature_version="s3v4")
        }
        if settings.STORAGE_ENDPOINT:
            client_kwargs["endpoint_url"] = settings.STORAGE_ENDPOINT

        self.bucket = settings.STORAGE_BUCKET
        self.s3_client = boto3.client("s3", **session_kwargs, **client_kwargs)

    def save_file(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        clean_key = key.lstrip("/\\")
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=clean_key,
            Body=data,
            ContentType=content_type
        )
        return self.get_url(clean_key)

    def get_file(self, key: str) -> Optional[bytes]:
        clean_key = key.lstrip("/\\")
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=clean_key)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"S3 get_object failed for key {clean_key}: {e}")
            return None

    def delete_file(self, key: str) -> bool:
        clean_key = key.lstrip("/\\")
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=clean_key)
            return True
        except Exception as e:
            logger.error(f"S3 delete_object failed for key {clean_key}: {e}")
            return False

    def get_url(self, key: str, expires_in: int = 3600) -> str:
        clean_key = key.lstrip("/\\")
        try:
            # Generate pre-signed URL for secure access
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": clean_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {clean_key}: {e}")
            return f"https://{self.bucket}.s3.{settings.STORAGE_REGION}.amazonaws.com/{clean_key}"

    def exists(self, key: str) -> bool:
        clean_key = key.lstrip("/\\")
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=clean_key)
            return True
        except Exception:
            return False


def get_storage_service() -> BaseStorageService:
    """Returns configured storage provider with automatic fallback to local storage."""
    if settings.STORAGE_PROVIDER == "s3" and settings.STORAGE_ACCESS_KEY:
        try:
            return S3StorageService()
        except Exception as e:
            logger.warning(f"Failed to initialize S3 storage provider ({e}). Falling back to LocalStorageService.")
    return LocalStorageService()

# Global default instance
storage_service = get_storage_service()
