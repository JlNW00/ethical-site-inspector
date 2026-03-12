from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import boto3

from app.core.config import Settings


@dataclass(slots=True)
class StorageObject:
    relative_key: str
    absolute_path: str | None
    public_url: str


class StorageProvider(ABC):
    @abstractmethod
    def save_bytes(self, relative_key: str, payload: bytes, content_type: str) -> StorageObject:
        raise NotImplementedError

    def save_text(self, relative_key: str, payload: str, content_type: str = "text/plain; charset=utf-8") -> StorageObject:
        return self.save_bytes(relative_key, payload.encode("utf-8"), content_type)


class LocalStorageProvider(StorageProvider):
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, relative_key: str, payload: bytes, content_type: str) -> StorageObject:
        absolute_path = self.root / relative_key
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(payload)
        public_url = f"/artifacts/{relative_key.replace('\\', '/')}"
        return StorageObject(
            relative_key=relative_key.replace("\\", "/"),
            absolute_path=str(absolute_path),
            public_url=public_url,
        )


class S3StorageProvider(StorageProvider):
    def __init__(self, settings: Settings):
        self.bucket_name = settings.s3_bucket_name or ""
        self.public_base_url = settings.s3_public_base_url
        self.client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            aws_session_token=settings.aws_session_token,
        )

    def save_bytes(self, relative_key: str, payload: bytes, content_type: str) -> StorageObject:
        normalized_key = relative_key.replace("\\", "/")
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=normalized_key,
            Body=payload,
            ContentType=content_type,
        )
        public_url = (
            f"{self.public_base_url.rstrip('/')}/{normalized_key}"
            if self.public_base_url
            else f"s3://{self.bucket_name}/{normalized_key}"
        )
        return StorageObject(relative_key=normalized_key, absolute_path=None, public_url=public_url)
