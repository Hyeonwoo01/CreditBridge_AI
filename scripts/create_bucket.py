"""로컬 S3 호환 저장소(SeaweedFS)에 문서 버킷을 만든다. 실행: uv run python -m scripts.create_bucket"""

from backend.documents.storage import get_storage

if __name__ == "__main__":
    get_storage().ensure_bucket()
    print("bucket ready")
