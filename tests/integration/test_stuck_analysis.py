"""분석이 '분석 중'에 멈추지 않게: 시간 제한에 걸리면 실패로 표시하고, 같은 파일을 다시 올리면 다시 분석한다.
worker 재시작으로 다시 넘어온 작업은 끊긴 이전 분석 행을 닫는다."""

from typing import Any

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import CourseEvaluation, Syllabus
from backend.repositories import evaluations as evaluation_repo
from backend.services import analysis
from backend.workers import tasks
from tests.conftest import login
from tests.fakes import FakeLLM
from tests.integration.test_pipeline import latest, new_request, upload


def syllabus_of(db: Session, request_id: int, name: str = "calculus.pdf") -> Syllabus:
    db.expire_all()
    stmt = select(Syllabus).where(Syllabus.transfer_request_id == request_id, Syllabus.original_filename == name)
    return db.scalars(stmt).one()


def test_extraction_timeout_fails_and_reupload_retries(client: TestClient, seeded: Session, fake_llm: FakeLLM) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    fake_llm.fail_with = SoftTimeLimitExceeded()
    upload(client, rid, token, "calculus.txt")
    syllabus = syllabus_of(seeded, rid)
    assert syllabus.status == "failed" and syllabus.error_message == analysis.TIMED_OUT
    assert "분석이 너무 오래 걸려 멈췄어요" in client.get(f"/student/requests/{rid}").text

    # 같은 파일을 다시 올리면 '이미 올린 문서'로 건너뛰지 않고 다시 분석한다
    fake_llm.fail_with = None
    page = upload(client, rid, token, "calculus.txt")
    assert "분석하지 못했던 문서를 다시 분석해요: calculus.pdf" in page
    assert syllabus_of(seeded, rid).status == "ready" and latest(seeded, "calculus.txt", rid).status == "done"
    # 이미 분석된 문서는 그대로 저장된 결과를 쓴다
    assert "이미 올린 문서라 저장된 분석 결과를 그대로 보여드려요" in upload(client, rid, token, "calculus.txt")


def test_evaluation_timeout_fails_and_reupload_reevaluates(
    client: TestClient, seeded: Session, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = fake_llm.parse

    def slow_comparison(prompt: str, output_model: type[BaseModel], **kwargs: Any) -> Any:
        if output_model.__name__ == "EvaluationOutput":
            raise SoftTimeLimitExceeded()
        return original(prompt, output_model, **kwargs)

    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    monkeypatch.setattr(fake_llm, "parse", slow_comparison)
    upload(client, rid, token, "calculus.txt")
    timed_out = latest(seeded, "calculus.txt", rid)
    assert syllabus_of(seeded, rid).status == "ready"  # 글자 읽기는 끝났고 AI 비교만 멈췄다
    assert timed_out.status == "failed" and timed_out.error_message == analysis.TIMED_OUT

    monkeypatch.setattr(fake_llm, "parse", original)
    calls = len(fake_llm.prompts("SyllabusExtraction"))
    assert "다시 분석해요" in upload(client, rid, token, "calculus.txt")
    again = latest(seeded, "calculus.txt", rid)
    assert again.id != timed_out.id and again.status == "done"
    assert len(fake_llm.prompts("SyllabusExtraction")) == calls  # 비교만 다시 했다


def test_redelivered_task_closes_interrupted_evaluation(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    syllabus = syllabus_of(seeded, rid)
    # worker가 비교 도중 꺼져 '분석 중'으로 남은 행
    stuck = CourseEvaluation(
        transfer_request_id=rid, syllabus_id=syllabus.id, status="running", input_hash="x", prompt_version="v"
    )
    evaluation_repo.add(seeded, stuck)
    seeded.commit()
    tasks.evaluate_syllabus.delay(syllabus.id)  # 대기열로 돌아온 작업이 다시 실행됨
    seeded.expire_all()
    seeded.refresh(stuck)
    assert stuck.status == "failed" and stuck.error_message == analysis.INTERRUPTED
    assert latest(seeded, "calculus.txt", rid).status == "done"
