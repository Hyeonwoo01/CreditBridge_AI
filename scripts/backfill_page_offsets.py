"""0007 마이그레이션 이전에 올린 강의계획서의 원본 PDF 페이지 위치표를 채운다 (FR-25 원본 N쪽 링크).

텍스트 레이어만 있는 PDF만 채우고 LLM은 부르지 않는다. 스캔 페이지가 있는 문서는 다시 올리면 채워진다.
실행: uv run python -m scripts.backfill_page_offsets
"""

from backend.db.session import SessionLocal
from backend.documents.storage import get_storage
from backend.services.analysis import backfill_page_offsets

if __name__ == "__main__":
    with SessionLocal() as session:
        filled, skipped = backfill_page_offsets(session, get_storage())
    print(f"page offsets filled: {filled}, skipped: {skipped}")
