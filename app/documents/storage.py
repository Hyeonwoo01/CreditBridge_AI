"""S3 호환 객체 스토리지 (개발 MinIO, 운영 AWS S3). 원본 문서는 DB나 로컬 디스크에 두지 않는다."""

import re
from functools import lru_cache
from typing import Any
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from app.config import Settings, get_settings


class ObjectStorage:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._bucket = settings.s3_bucket
        self._sse = settings.s3_server_side_encryption
        self._client = client or boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
            region_name=settings.s3_region,
        )

    @staticmethod
    def new_key(kind: str, filename: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)[-80:] or "file"
        return f"{kind}/{uuid4()}/{safe}"

    def put(self, key: str, data: bytes, content_type: str) -> None:
        extra: dict[str, str] = {"ContentType": content_type}
        if self._sse:
            extra["ServerSideEncryption"] = self._sse
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, **extra)

    def get(self, key: str) -> bytes:
        body: bytes = self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()
        return body

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)


@lru_cache
def get_storage() -> ObjectStorage:
    return ObjectStorage(get_settings())
