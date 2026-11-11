"""학사정보시스템 내보내기 (FR-24, NF-10): 확정 판정을 CSV와 토큰 인증 JSON API로 내보낸다.

이의 신청으로 재판정된 건은 최신 판정만 내보내고, 대체한 이전 판정 번호(replaces_decision_id)를 함께 준다.

반영 확인과 대사 (리뷰 v3 P1-4): 판정마다 바뀌지 않는 idempotency_key(cb-decision-{id})를 함께 보내 SIS가
같은 판정을 두 번 반영하지 않게 하고, SIS는 반영 결과(applied·failed, 자기 쪽 기록 번호)를 돌려보낸다.
결과 요청은 Idempotency-Key로 한 번만 처리한다. 실패한 판정만 다시 가져갈 수 있고(status=failed), 관리자는
대사 화면에서 반영·실패·대기 건수와, 반영한 뒤 재판정돼 다시 보내야 하는 건을 본다.
"""

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.db.base import utcnow
from backend.errors import CreditBridgeError, DuplicateRowError, IdempotencyConflictError, PermissionDeniedError
from backend.i18n import gettext as tr
from backend.models import Decision, Institution, SisAckRequest, SisSync, User
from backend.models.enums import Role, SisSyncStatus
from backend.repositories import allocations as allocation_repo
from backend.repositories import catalog as catalog_repo
from backend.repositories import decisions as decision_repo
from backend.repositories import requests as request_repo
from backend.repositories import sis as sis_repo
from backend.repositories import syllabi as syllabus_repo
from backend.services import audit

FIELDS = [
    "decision_id",
    "replaces_decision_id",
    "student_id",
    "source_institution",
    "source_course",
    "result",
    "target_course",
    "accepted_credits",
    "credit_unit",
    "credit_basis",
    "source_credits",
    "source_credit_unit",
    "combined_source_courses",
    "decided_at",
    "idempotency_key",
    "sync_status",
    "external_reference_id",
]
SYNC_FILTERS = ("all", "pending", "failed", "applied", "unsent")  # unsent = 대기 + 실패 (아직 반영 안 됨)
MAX_ACK_ROWS = 500


def idempotency_key(decision_id: int) -> str:
    """판정마다 바뀌지 않는 키. SIS는 이 키로 같은 판정의 중복 반영을 막는다."""
    return f"cb-decision-{decision_id}"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _snapshot_target(decision: Decision) -> str | None:
    target = (decision.course_snapshot or {}).get("target")
    return str(target["code"]) if target else None


def export_rows(
    session: Session, institution_id: int, since: datetime | None = None, status: str = "all"
) -> list[dict[str, Any]]:
    """심사 건마다 현재 유효한 판정 한 줄. status로 반영 상태를 고른다 (SYNC_FILTERS)."""
    syncs = sis_repo.syncs_for(session, institution_id)
    rows = decision_repo.all_for_institution(session, institution_id)
    latest: dict[int, tuple[Decision, Any, Any]] = {}
    previous: dict[int, int] = {}
    for d, e, s in rows:  # 판정 순이므로 마지막이 현재 판정
        if e.id in latest:
            previous[e.id] = latest[e.id][0].id
        latest[e.id] = (d, e, s)
    courses = catalog_repo.courses_by_ids(
        session, [d.target_course_id for d, _, _ in latest.values() if d.target_course_id]
    )
    # 여러 출신 과목을 합쳐 인정한 판정(N:1): 원장에 남은 출신 과목들
    ledger: dict[int, list[int]] = {}
    for a in allocation_repo.for_decisions(session, [d.id for d, _, _ in latest.values()]):
        ledger.setdefault(a.decision_id, []).append(a.syllabus_id)
    combined_ids = sorted({sid for ids in ledger.values() if len(ids) > 1 for sid in ids})
    names = {x.id: x.course_code or x.course_title for x in syllabus_repo.by_ids(session, combined_ids)}
    out = []
    for d, e, s in latest.values():
        if since is not None and d.decided_at < since:
            continue
        sync = syncs.get(d.id)
        state = sync.status if sync else SisSyncStatus.PENDING
        if status == "unsent" and state == SisSyncStatus.APPLIED:
            continue
        if status not in ("all", "unsent") and state != status:
            continue
        request = request_repo.get(session, e.transfer_request_id) if e.transfer_request_id else None
        out.append(
            {
                "decision_id": d.id,
                "replaces_decision_id": previous.get(e.id, ""),
                "student_id": request.student_id if request else "",
                "source_institution": request.source_institution.name if request else "",
                "source_course": s.course_code or s.course_title,
                "result": d.result,
                # 판정 때 과목 코드 (0013 이후 판정). 그 뒤 카탈로그에서 코드가 바뀌어도 판정 때 값을 보낸다
                "target_course": _snapshot_target(d)
                or (courses[d.target_course_id].code if d.target_course_id in courses else ""),
                # 교수가 확정한 인정 학점 (0009 이전 판정은 비어 있음 — 학사처가 확인해 입력)
                "accepted_credits": d.accepted_credits if d.accepted_credits is not None else "",
                "credit_unit": d.credit_unit or "",
                "credit_basis": d.credit_basis or "",
                "source_credits": d.source_credits if d.source_credits is not None else (s.credits or ""),
                "source_credit_unit": d.source_credit_unit or "",
                "combined_source_courses": " + ".join(names.get(i, "") for i in ledger.get(d.id, []))
                if len(ledger.get(d.id, [])) > 1
                else "",
                "decided_at": d.decided_at.isoformat(timespec="seconds") + "Z",
                "idempotency_key": idempotency_key(d.id),
                "sync_status": state,
                "external_reference_id": (sync.external_reference_id if sync else None) or "",
            }
        )
    out.sort(key=lambda r: r["decision_id"])
    return out


def issue_token(session: Session, admin: User) -> str:
    """새 연동 토큰을 발급한다. 이전 토큰은 즉시 무효가 된다. 원문은 이때 한 번만 돌려준다."""
    institution = _own_institution(session, admin)
    token = "cbsis_" + secrets.token_urlsafe(32)
    institution.sis_token_hash = _hash(token)
    audit.record(session, admin, "sis.token_issue", "institution", str(institution.id))
    session.commit()
    return token


def revoke_token(session: Session, admin: User) -> None:
    institution = _own_institution(session, admin)
    institution.sis_token_hash = None
    audit.record(session, admin, "sis.token_revoke", "institution", str(institution.id))
    session.commit()


def institution_for_token(session: Session, token: str) -> Institution | None:
    if not token.startswith("cbsis_"):
        return None
    return catalog_repo.institution_by_token_hash(session, _hash(token))


def has_token(session: Session, admin: User) -> bool:
    return _own_institution(session, admin).sis_token_hash is not None


def _own_institution(session: Session, admin: User) -> Institution:
    institution = catalog_repo.get_institution(session, admin.institution_id) if admin.institution_id else None
    if admin.role != Role.ADMIN or institution is None or not institution.is_target:
        raise PermissionDeniedError(tr("대상 대학의 기관 관리자만 연동 토큰을 관리할 수 있어요."))
    return institution


# ---------- 반영 결과와 대사 (리뷰 v3 P1-4) ----------


def _current_decisions(session: Session, institution_id: int) -> tuple[dict[int, Decision], dict[int, int]]:
    """심사 건마다 지금 유효한 판정 (판정 id → 판정)과, 대체된 판정 id → 대체한 판정 id."""
    latest: dict[int, Decision] = {}
    replaced: dict[int, int] = {}
    for d, e, _ in decision_repo.all_for_institution(session, institution_id):
        if e.id in latest:
            replaced[latest[e.id].id] = d.id
        latest[e.id] = d
    return {d.id: d for d in latest.values()}, replaced


def _ack_one(
    session: Session, institution_id: int, current: dict[int, Decision], replaced: dict[int, int], row: Any
) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"decision_id": None, "outcome": "rejected", "detail": "row must be an object"}
    decision_id, status = row.get("decision_id"), row.get("status")
    out: dict[str, Any] = {"decision_id": decision_id}
    if not isinstance(decision_id, int) or status not in (SisSyncStatus.APPLIED, SisSyncStatus.FAILED):
        return {**out, "outcome": "rejected", "detail": "decision_id (int) and status (applied|failed) are required"}
    if decision_id in replaced:
        return {**out, "outcome": "superseded", "detail": f"replaced by decision {replaced[decision_id]}"}
    if decision_id not in current:
        return {**out, "outcome": "rejected", "detail": "unknown decision for this institution"}
    reference = str(row.get("external_reference_id") or "")[:100] or None
    error = str(row.get("error") or "")[:1000]
    sync = sis_repo.sync_for_update(session, decision_id)
    now = utcnow()
    if sync is None:
        sync = sis_repo.add_sync(
            session, SisSync(decision_id=decision_id, institution_id=institution_id, status=status, attempts=0)
        )
    elif sync.status == SisSyncStatus.APPLIED:
        # 이미 반영된 판정: 같은 기록 번호면 그대로(중복 보고), 다르면 고치지 않고 대사 불일치로 알린다
        if status == SisSyncStatus.APPLIED and reference in (None, sync.external_reference_id):
            return {**out, "outcome": "duplicate", "external_reference_id": sync.external_reference_id}
        return {
            **out,
            "outcome": "conflict",
            "detail": "already applied with external_reference_id " + (sync.external_reference_id or "(none)"),
        }
    sync.status = status
    sync.acknowledged_at = sync.updated_at = now
    if status == SisSyncStatus.APPLIED:
        sync.external_reference_id = reference
        sync.last_error = ""
    else:
        sync.attempts += 1
        sync.last_error = error or "failed"
    return {**out, "outcome": "recorded", "status": status}


def acknowledge(session: Session, institution: Institution, key: str, body: Any) -> tuple[dict[str, Any], bool]:
    """SIS가 보낸 반영 결과를 기록한다. (응답, 이전 요청을 다시 돌려준 것인지).

    같은 Idempotency-Key로 같은 내용을 다시 보내면 처음 응답을 그대로 돌려주고 아무것도 바꾸지 않는다.
    같은 키에 다른 내용이면 CreditBridgeError (API는 409)."""
    key = key.strip()
    if not key or len(key) > 100:
        raise CreditBridgeError(tr("Idempotency-Key 헤더(100자 이하)가 필요해요."))
    rows = body.get("results") if isinstance(body, dict) else None
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ACK_ROWS:
        raise CreditBridgeError(tr("results는 1~{n}개 항목의 목록이어야 해요.", n=MAX_ACK_ROWS))
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    previous = sis_repo.ack_request(session, institution.id, key)
    if previous is not None:
        if previous.request_hash != digest:
            raise IdempotencyConflictError(tr("같은 Idempotency-Key로 다른 내용을 보냈어요. 새 키를 쓰세요."))
        return previous.response, True
    current, replaced = _current_decisions(session, institution.id)
    results = [_ack_one(session, institution.id, current, replaced, row) for row in rows]
    response = {"idempotency_key": key, "results": results}
    try:
        sis_repo.add_ack_request(
            session,
            SisAckRequest(institution_id=institution.id, idempotency_key=key, request_hash=digest, response=response),
        )
    except DuplicateRowError:
        # 같은 키의 요청이 동시에 들어와 다른 쪽이 먼저 처리했다: 이쪽 변경은 버리고 그 응답을 돌려준다
        session.rollback()
        winner = sis_repo.ack_request(session, institution.id, key)
        if winner is None or winner.request_hash != digest:
            raise IdempotencyConflictError(tr("같은 Idempotency-Key로 다른 내용을 보냈어요. 새 키를 쓰세요.")) from None
        return winner.response, True
    counts = {o: sum(r["outcome"] == o for r in results) for o in {r["outcome"] for r in results}}
    audit.record(session, None, "sis.ack", "institution", str(institution.id), **counts)
    session.commit()
    return response, False


@dataclass
class Reconciliation:
    """관리자 대사 화면: 지금 유효한 판정의 반영 상태별 건수와 손볼 판정."""

    applied: int = 0
    pending: int = 0
    failed: list[tuple[Decision, SisSync]] = field(default_factory=list)
    # 반영된 판정이 이의 신청 재판정으로 바뀌어 새 판정을 다시 보내야 함: (반영된 옛 판정 동기화, 새 판정)
    resend: list[tuple[SisSync, Decision]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.applied + self.pending + len(self.failed)


def reconciliation(session: Session, admin: User) -> Reconciliation:
    institution = _own_institution(session, admin)
    current, replaced = _current_decisions(session, institution.id)
    syncs = sis_repo.syncs_for(session, institution.id)
    out = Reconciliation()
    for decision_id, decision in sorted(current.items()):
        sync = syncs.get(decision_id)
        if sync is None or sync.status == SisSyncStatus.PENDING:
            out.pending += 1
        elif sync.status == SisSyncStatus.APPLIED:
            out.applied += 1
        else:
            out.failed.append((decision, sync))
    seen: set[int] = set()
    for old_id, new_id in sorted(replaced.items()):
        old = syncs.get(old_id)
        newest = new_id
        while newest in replaced:
            newest = replaced[newest]
        new_sync = syncs.get(newest)
        stale = old is not None and old.status == SisSyncStatus.APPLIED and newest in current
        if stale and (new_sync is None or new_sync.status != SisSyncStatus.APPLIED) and newest not in seen:
            assert old is not None
            seen.add(newest)
            out.resend.append((old, current[newest]))
    return out


def retry(session: Session, admin: User, decision_ids: list[int]) -> int:
    """실패한 판정을 '대기'로 되돌려 SIS가 다시 가져가게 한다 (status=unsent·pending에 다시 나옴)."""
    institution = _own_institution(session, admin)
    syncs = sis_repo.syncs_for(session, institution.id)
    count = 0
    for decision_id in set(decision_ids):
        sync = syncs.get(decision_id)
        if sync is not None and sync.status == SisSyncStatus.FAILED:
            sync.status = SisSyncStatus.PENDING
            sync.updated_at = utcnow()
            count += 1
    if count:
        audit.record(session, admin, "sis.retry", "institution", str(institution.id), decisions=count)
    session.commit()
    return count
