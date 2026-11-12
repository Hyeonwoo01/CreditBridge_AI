"""작업 상태·자동 재시도·격리·다시 처리 (리뷰 v3 P1-3)."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.errors import LLMError, LLMNotConfiguredError
from backend.models import BackgroundJob, LLMUsageRecord
from tests.conftest import login
from tests.fakes import FakeLLM
from tests.integration.test_pipeline import new_request, upload


def jobs_of(db: Session) -> list[BackgroundJob]:
    db.expire_all()
    return list(db.scalars(select(BackgroundJob).order_by(BackgroundJob.id)))


def test_successful_analysis_is_recorded(client: TestClient, seeded: Session) -> None:
    token = login(client, "jiwon@student.example")
    upload(client, new_request(client, seeded, token), token, "calculus.txt")
    rows = [j for j in jobs_of(seeded) if j.job_type == "syllabus.process"]
    assert len(rows) == 1
    job = rows[0]
    assert job.status == "succeeded" and job.attempt_count == 1 and job.error_code == ""
    assert job.duration_ms is not None and job.institution_id is not None and job.task_args == [job.subject_id]


def test_transient_error_retries_then_dead_letters_and_admin_reprocesses(
    client: TestClient, seeded: Session, fake_llm: FakeLLM
) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    fake_llm.fail_with = LLMError("Claude API error: RateLimitError")
    upload(client, rid, token, "calculus.txt")
    job = next(j for j in jobs_of(seeded) if j.job_type == "syllabus.process")
    assert job.status == "dead_letter" and job.attempt_count == 3 and job.error_code == "llm_rate_limit"

    admin = login(client, "admin@msu.example")
    page = client.get("/admin/stats").text
    assert f'data-job="{job.id}"' in page and "AI 공급자 요청 한도" in page and "격리" in page
    fake_llm.fail_with = None  # 운영자가 원인(한도)을 해결한 뒤 다시 처리
    r = client.post(f"/admin/jobs/{job.id}/retry", data={"csrf_token": admin}, follow_redirects=False)
    assert r.status_code == 303
    job = next(j for j in jobs_of(seeded) if j.id == job.id)
    assert job.status == "succeeded" and job.attempt_count == 1  # 운영자가 다시 처리하면 새 시도 묶음
    assert f'data-job="{job.id}"' not in client.get("/admin/stats").text
    # 성공한 작업은 다시 처리할 수 없다, 다른 역할도 안 된다
    assert client.post(f"/admin/jobs/{job.id}/retry", data={"csrf_token": admin}).status_code == 403
    evaluator = login(client, "rachel@msu.example")
    assert client.post(f"/admin/jobs/{job.id}/retry", data={"csrf_token": evaluator}).status_code == 403


def test_permanent_error_fails_without_retry(client: TestClient, seeded: Session, fake_llm: FakeLLM) -> None:
    token = login(client, "jiwon@student.example")
    rid = new_request(client, seeded, token)
    fake_llm.fail_with = LLMNotConfiguredError("not configured: ANTHROPIC_API_KEY")
    upload(client, rid, token, "calculus.txt")
    job = next(j for j in jobs_of(seeded) if j.job_type == "syllabus.process")
    assert job.status == "failed" and job.attempt_count == 1 and job.error_code == "not_configured"


def test_ai_usage_is_saved_per_job_and_shown(client: TestClient, seeded: Session) -> None:
    """작업마다 AI 호출 사용량을 (용도, 모델)별로 남기고 관리자 콘솔 'AI 사용량'에 보여 준다 (리뷰 v3 13.7)."""
    token = login(client, "jiwon@student.example")
    upload(client, new_request(client, seeded, token), token, "calculus.txt")
    job = next(j for j in jobs_of(seeded) if j.job_type == "syllabus.process")
    usage = list(seeded.scalars(select(LLMUsageRecord).where(LLMUsageRecord.job_id == job.id)))
    purposes = {u.purpose for u in usage}
    assert {"SyllabusExtraction", "EvaluationOutput"} <= purposes
    assert all(u.institution_id == job.institution_id and u.model == "fake-claude" for u in usage)
    assert all(u.calls >= 1 and u.input_tokens > 0 and u.output_tokens > 0 for u in usage)

    login(client, "admin@msu.example")
    page = client.get("/admin/stats").text
    assert "data-ai-usage" in page and 'data-usage-row="EvaluationOutput"' in page and "개념 비교" in page
    assert "단가(AI_PRICE_*)를 정하면" in page  # 단가를 정하지 않으면 비용은 보이지 않는다


def test_ai_usage_cost_with_configured_price(client: TestClient, seeded: Session, monkeypatch: Any) -> None:
    from backend.config import get_settings

    token = login(client, "jiwon@student.example")
    upload(client, new_request(client, seeded, token), token, "calculus.txt")
    monkeypatch.setattr(get_settings(), "ai_price_input_per_mtok", 3.0)
    monkeypatch.setattr(get_settings(), "ai_price_output_per_mtok", 15.0)
    login(client, "admin@msu.example")
    page = client.get("/admin/stats").text
    assert 'data-usage-metric="4">$' in page and "어림한 값" in page
