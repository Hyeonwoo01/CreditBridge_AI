"""S3 호환 객체 스토리지 (개발 SeaweedFS 등 S3 호환 저장소, 운영 AWS S3). 원본 문서는 DB나 로컬 디스크에 두지 않는다.
(예외: 공개 데모 모드의 DiskStorage — 예시 자료만 다루고 다시 시작하면 지워진다)"""

import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.config import Settings, get_settings


class ObjectStorage:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self._bucket = settings.s3_bucket
        self._sse = settings.s3_server_side_encryption
        import boto3  # 공개 데모(DiskStorage)는 boto3를 불러오지 않아 메모리를 아낀다

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
        from botocore.exceptions import ClientError

        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)


class DiskStorage(ObjectStorage):
    """공개 데모용: S3 대신 로컬 폴더에 저장한다 (Settings.demo_mode). 컨테이너를 다시 시작하면 지워진다."""

    def __init__(self, root: str) -> None:  # S3 클라이언트를 만들지 않는다
        self._root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root.resolve()):
            raise ValueError("invalid storage key")
        return path

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def ensure_bucket(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_storage() -> ObjectStorage:
    settings = get_settings()
    if settings.demo_mode:
        return DiskStorage(settings.demo_storage_dir)
    return ObjectStorage(settings)
