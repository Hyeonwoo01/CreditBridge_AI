"""오래 걸리는 AI 처리. 작업당 DB 세션 하나."""

import logging

from app.ai.embedding import get_embedder
from app.ai.llm_client import get_llm
from app.db.session import SessionLocal
from app.documents.storage import get_storage
from app.errors import LLMError
from app.services import analysis
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="syllabus.process")  # type: ignore[untyped-decorator]
def process_syllabus(syllabus_id: int) -> None:
    with SessionLocal() as session:
        analysis.process_syllabus(session, syllabus_id, llm=get_llm(), embedder=get_embedder(), storage=get_storage())


@celery_app.task(name="syllabus.supplement")  # type: ignore[untyped-decorator]
def add_supplement(syllabus_id: int, file_key: str) -> None:
    with SessionLocal() as session:
        analysis.add_supplement(
            session, syllabus_id, file_key, llm=get_llm(), embedder=get_embedder(), storage=get_storage()
        )


@celery_app.task(name="syllabus.evaluate")  # type: ignore[untyped-decorator]
def evaluate_syllabus(syllabus_id: int) -> None:
    with SessionLocal() as session:
        analysis.evaluate_syllabus(session, syllabus_id, llm=get_llm())


@celery_app.task(name="transcript.process")  # type: ignore[untyped-decorator]
def process_transcript(request_id: int) -> None:
    with SessionLocal() as session:
        try:
            analysis.process_transcript(session, request_id, llm=get_llm(), storage=get_storage())
        except LLMError as exc:
            logger.warning(
                "transcript processing failed", extra={"request_id": request_id, "error": type(exc).__name__}
            )
