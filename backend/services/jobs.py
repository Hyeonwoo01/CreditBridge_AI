"""백그라운드 작업 상태·재시도·격리 (리뷰 v3 P1-3, 13.7).

작업(workers/tasks.py)은 시작할 때 start, 끝날 때 finish를 부른다. 분석 서비스는 오류를 삼키고 화면용 상태를
남기므로, 오류가 나면 note_error로 이 작업의 오류 코드를 알려 준다(contextvar). finish는 코드를 보고

- 재시도할 수 있는 오류(AI 공급자 한도·시간 초과·연결·서버 오류, 출력 검증 실패, 작업 시간 초과)면 MAX_ATTEMPTS까지
  간격을 늘려(지수 + 무작위 지연) 다시 하고, 넘기면 격리(dead_letter)한다.
- 다시 해도 안 되는 오류(읽을 수 없는 파일, AI 설정 없음, 모델 거절)는 곧바로 실패(failed)로 둔다.

다시 처리해도 이전 분석·판정은 덮어쓰지 않는다 (분석은 새 행, 판정은 추가 전용). 로그·기록에는 오류 코드와
대상 id만 남긴다.
"""

import logging
import random
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.ai import llm_client
from backend.config import get_settings
from backend.db.base import utcnow
from backend.errors import (
    DocumentParseError,
    LLMError,
    LLMNotConfiguredError,
    LLMRefusalError,
    PermissionDeniedError,
)
from backend.i18n import N_
from backend.i18n import gettext as tr
from backend.models import BackgroundJob, LLMUsageRecord, User
from backend.models.enums import JobStatus, Role
from backend.repositories import jobs as job_repo
from backend.repositories import requests as request_repo
from backend.repositories import syllabi as syllabus_repo
from backend.repositories import users as user_repo

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 30  # 1회 실패 뒤 30초, 2회 뒤 60초 (+ 0~50% 무작위)
TASK_TIMEOUT = "task_timeout"
RETRYABLE = {"llm_rate_limit", "llm_timeout", "llm_connection", "llm_server", "llm_invalid_output", TASK_TIMEOUT}
ERROR_LABELS = {
    "llm_rate_limit": N_("AI 공급자 요청 한도"),
    "llm_timeout": N_("AI 응답 시간 초과"),
    "llm_connection": N_("AI 연결 실패"),
    "llm_server": N_("AI 공급자 서버 오류"),
    "llm_invalid_output": N_("AI 출력 형식 오류"),
    "llm_refusal": N_("AI가 요청을 거절함"),
    "llm_error": N_("AI 호출 실패"),
    "not_configured": N_("AI 설정(API 키) 없음"),
    "document_unreadable": N_("문서를 끝까지 읽지 못함"),
    TASK_TIMEOUT: N_("작업 시간 제한 초과"),
}

_error: ContextVar[str | None] = ContextVar("job_error", default=None)


def error_code(exc: BaseException) -> str:
    """예외 → 오류 코드 (문서 내용·개인정보 없이 종류만)."""
    if isinstance(exc, LLMNotConfiguredError):
        return "not_configured"
    if isinstance(exc, DocumentParseError):
        return "document_unreadable"
    if isinstance(exc, LLMRefusalError):
        return "llm_refusal"
    if isinstance(exc, LLMError):
        text = str(exc)
        for needle, code in (
            ("RateLimit", "llm_rate_limit"),
            ("Timeout", "llm_timeout"),
            ("Connection", "llm_connection"),
            ("InternalServer", "llm_server"),
            ("ServiceUnavailable", "llm_server"),
            ("Overloaded", "llm_server"),
            ("failed validation", "llm_invalid_output"),
        ):
            if needle in text:
                return code
        return "llm_error"
    return f"unexpected:{type(exc).__name__}"[:60]


def note_error(code_or_exc: str | BaseException) -> None:
    """지금 도는 작업의 오류를 알린다 (분석 서비스가 오류를 화면용 상태로 바꿀 때 부른다)."""
    _error.set(code_or_exc if isinstance(code_or_exc, str) else error_code(code_or_exc))


def _institution_of(session: Session, subject_type: str, subject_id: int) -> int | None:
    if subject_type == "syllabus":
        syllabus = syllabus_repo.get(session, subject_id)
        if syllabus is None:
            return None
        request = request_repo.get(session, syllabus.transfer_request_id) if syllabus.transfer_request_id else None
        return request.target_institution_id if request else syllabus.institution_id
    user = user_repo.get_by_id(session, subject_id)
    return user.institution_id if user else None


def start(
    session: Session, job_type: str, subject_type: str, subject_id: int, job_id: int | None, args: list[Any]
) -> BackgroundJob:
    """작업 시작 기록. job_id가 있으면 같은 작업의 다음 시도. 이 시도의 AI 사용량을 모으기 시작한다."""
    _error.set(None)
    llm_client.start_usage()
    job = job_repo.get(session, job_id) if job_id else None
    if job is None:
        job = job_repo.add(
            session,
            BackgroundJob(
                institution_id=_institution_of(session, subject_type, subject_id),
                job_type=job_type,
                subject_type=subject_type,
                subject_id=subject_id,
                status=JobStatus.QUEUED,
                task_args=args,
            ),
        )
    job.status = JobStatus.RUNNING
    job.attempt_count += 1
    job.started_at = utcnow()
    job.completed_at = None
    session.commit()
    return job


def finish(session: Session, job: BackgroundJob, timed_out: bool = False) -> int | None:
    """작업 끝 기록. 다시 해야 하면 기다릴 초를 돌려준다 (호출한 쪽이 같은 job_id로 다시 넣는다)."""
    session.rollback()  # 작업이 남긴 미완료 트랜잭션과 섞지 않는다
    job = job_repo.get(session, job.id) or job
    code = TASK_TIMEOUT if timed_out else _error.get()
    now = utcnow()
    job.completed_at = now
    if job.started_at is not None:
        job.duration_ms = int((now - job.started_at).total_seconds() * 1000)
    delay: int | None = None
    if code is None:
        job.status, job.error_code = JobStatus.SUCCEEDED, ""
    elif code in RETRYABLE and job.attempt_count < MAX_ATTEMPTS:
        job.status, job.error_code = JobStatus.RETRY_WAIT, code
        base = BACKOFF_BASE_SECONDS * 2 ** (job.attempt_count - 1)
        delay = int(base + random.uniform(0, base / 2))  # 재시도 간격 흩뜨리기 (보안 용도 아님)
    elif code in RETRYABLE:
        job.status, job.error_code = JobStatus.DEAD_LETTER, code
    else:
        job.status, job.error_code = JobStatus.FAILED, code
    _save_usage(session, job)
    session.commit()
    if code is not None:
        logger.warning(
            "background job failed",
            extra={"job_id": job.id, "job_type": job.job_type, "error_code": code, "attempt": job.attempt_count},
        )
    _error.set(None)
    return delay


def _save_usage(session: Session, job: BackgroundJob) -> None:
    """이 시도에서 모은 AI 사용량을 (용도, 모델)별로 합쳐 남긴다 (리뷰 v3 13.7 비용 지표)."""
    totals: dict[tuple[str, str], list[int]] = {}
    for u in llm_client.take_usage():
        row = totals.setdefault((u.purpose, u.model), [0, 0, 0])
        row[0] += 1
        row[1] += u.input_tokens
        row[2] += u.output_tokens
    if totals:
        job_repo.add_usage(
            session,
            [
                LLMUsageRecord(
                    institution_id=job.institution_id,
                    job_id=job.id,
                    purpose=purpose,
                    model=model[:100],
                    calls=calls,
                    input_tokens=tokens_in,
                    output_tokens=tokens_out,
                )
                for (purpose, model), (calls, tokens_in, tokens_out) in totals.items()
            ],
        )


def requeue(session: Session, admin: User, job_id: int) -> BackgroundJob:
    """운영자가 격리·실패 작업을 다시 처리한다. 같은 작업 기록에 시도를 더한다 (이전 결과는 그대로)."""
    job = job_repo.get(session, job_id)
    if admin.role != Role.ADMIN or job is None or job.institution_id != admin.institution_id:
        raise PermissionDeniedError(tr("소속 기관의 작업만 다시 처리할 수 있어요."))
    if job.status not in (JobStatus.DEAD_LETTER, JobStatus.FAILED):
        raise PermissionDeniedError(tr("격리되거나 실패한 작업만 다시 처리할 수 있어요."))
    job.status = JobStatus.QUEUED
    job.attempt_count = 0  # 운영자가 원인을 고친 뒤의 새 재시도 묶음
    job.error_code = ""
    session.commit()
    return job


@dataclass
class Health:
    """관리자 콘솔 '작업 처리 현황' (최근 기간)."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0  # 실패 + 격리
    retried: int = 0  # 두 번 이상 시도한 작업
    running: int = 0  # 대기·실행·재시도 대기
    p50_ms: int | None = None
    p95_ms: int | None = None
    attention: list[BackgroundJob] = field(default_factory=list)
    usage: list["UsageRow"] = field(default_factory=list)  # AI 사용량 (용도·모델별)
    usage_jobs: int = 0  # AI를 부른 작업 수

    @property
    def input_tokens(self) -> int:
        return sum(u.input_tokens for u in self.usage)

    @property
    def output_tokens(self) -> int:
        return sum(u.output_tokens for u in self.usage)

    @property
    def tokens_per_job(self) -> int | None:
        return round((self.input_tokens + self.output_tokens) / self.usage_jobs) if self.usage_jobs else None

    @property
    def cost(self) -> float | None:
        """설정한 단가(1백만 토큰당 USD)로 어림한 비용. 단가를 정하지 않았으면 None."""
        return _cost(self.input_tokens, self.output_tokens)

    @property
    def success_rate(self) -> float | None:
        done = self.succeeded + self.failed
        return self.succeeded / done if done else None


# 용도(출력 모델 이름) → 화면 이름
USAGE_PURPOSES = {
    "SyllabusExtraction": N_("강의계획서 정보 추출"),
    "EvaluationOutput": N_("개념 비교"),
    "PageTranscription": N_("스캔 쪽 글자 옮기기"),
    "TranscriptExtraction": N_("성적표 읽기"),
}


@dataclass
class UsageRow:
    purpose: str
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    jobs: int

    @property
    def label(self) -> str:
        return USAGE_PURPOSES.get(self.purpose, self.purpose)

    @property
    def cost(self) -> float | None:
        return _cost(self.input_tokens, self.output_tokens)


def _cost(tokens_in: int, tokens_out: int) -> float | None:
    settings = get_settings()
    price_in, price_out = settings.ai_price_input_per_mtok, settings.ai_price_output_per_mtok
    if price_in is None or price_out is None:
        return None
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000


def _percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]


def health(session: Session, institution_id: int, days: int = 7, now: datetime | None = None) -> Health:
    rows = job_repo.since(session, institution_id, (now or utcnow()) - timedelta(days=days))
    out = Health(total=len(rows))
    durations = []
    for job in rows:
        if job.status == JobStatus.SUCCEEDED:
            out.succeeded += 1
            if job.duration_ms is not None:
                durations.append(job.duration_ms)
        elif job.status in (JobStatus.FAILED, JobStatus.DEAD_LETTER):
            out.failed += 1
        else:
            out.running += 1
        if job.attempt_count > 1:
            out.retried += 1
    out.p50_ms, out.p95_ms = _percentile(durations, 0.5), _percentile(durations, 0.95)
    out.attention = job_repo.needing_attention(session, institution_id)
    start = (now or utcnow()) - timedelta(days=days)
    out.usage = [UsageRow(*row) for row in job_repo.usage_since(session, institution_id, start)]
    out.usage_jobs = job_repo.usage_job_count(session, institution_id, start)
    return out
