"""AI 키·모델이 없는 서버: 분석이 "분석 중"에 멈추지 않고 실패와 설정 안내를 보여 준다."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai.llm_client import LLMClient
from backend.config import Settings
from backend.models import Syllabus
from backend.models.enums import SyllabusStatus
from backend.workers import tasks
from tests.conftest import login
from tests.integration.test_pipeline import new_request, upload


def test_upload_without_claude_settings_fails_with_guidance(
    client: TestClient, seeded: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    unconfigured = LLMClient(Settings(llm_provider="anthropic", claude_model="", anthropic_api_key=""))
    monkeypatch.setattr(tasks, "get_llm", lambda: unconfigured)
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    upload(client, rid, token, "calculus.txt")
    seeded.expire_all()
    syllabus = seeded.scalars(select(Syllabus).where(Syllabus.transfer_request_id == rid)).one()
    assert syllabus.status == SyllabusStatus.FAILED
    assert syllabus.error_message is not None and "API 키" in syllabus.error_message
    assert "AI 분석 설정(API 키)이 아직 없어" in client.get(f"/student/requests/{rid}").text  # 학생 화면 안내
