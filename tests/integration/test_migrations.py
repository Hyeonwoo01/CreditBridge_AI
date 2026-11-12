"""데이터가 있는 DB에서 마이그레이션을 올려 본다 (scripts/migration_demo.py + demo_data/migration/*.sql).

빈 DB로 head까지 올리는 conftest의 migrated와 달리, 0002·0009 시점의 옛 데이터를 넣고 올려서 0003~0012의
데이터 백필이 기대대로 채우는지 확인한다. 각 기대값의 이유는 legacy_*.sql의 행 옆 주석([0003] 등)에 있다.
다른 테스트와 섞이지 않게 TEST_DATABASE_URL의 DB 이름 뒤에 _migrations를 붙인 별도 DB를 쓴다(없으면 만든다).
"""

import os
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ProgrammingError

from alembic import command
from scripts import migration_demo


@pytest.fixture(scope="module")
def legacy_url() -> str:
    base = make_url(os.environ["DATABASE_URL"])
    url = base.set(database=f"{base.database}_migrations").render_as_string(hide_password=False)
    try:
        migration_demo.ensure_database(url)
    except ProgrammingError as exc:  # CREATEDB 권한이 없는 계정
        pytest.skip(f"마이그레이션 시험용 DB를 만들 수 없음: {exc.orig}")
    return url


@pytest.fixture(scope="module")
def upgraded(legacy_url: str) -> Iterator[Engine]:
    migration_demo.build(legacy_url, "head")
    engine = create_engine(legacy_url)
    yield engine
    engine.dispose()


def rows(engine: Engine, sql: str) -> list[Any]:
    with engine.connect() as conn:
        return [tuple(r) for r in conn.execute(text(sql))]


def scalar(engine: Engine, sql: str) -> Any:
    with engine.connect() as conn:
        return conn.execute(text(sql)).scalar_one()


def test_reaches_head(upgraded: Engine, legacy_url: str) -> None:
    head = migration_demo.revision_order(migration_demo.alembic_config(legacy_url))[-1]
    assert scalar(upgraded, "SELECT version_num FROM alembic_version") == head


def test_0003_student_source_and_major(upgraded: Engine) -> None:
    got = rows(
        upgraded, "SELECT id, source_institution_id, department_id FROM users WHERE role = 'student' ORDER BY id"
    )
    assert got == [
        (10, 3, 1),  # 가장 최근 요청(102)의 서울·CS
        (11, 3, 2),  # 학과가 이미 있으면 덮어쓰지 않음
        (12, 3, None),  # 없는 전공 이름 → 학과는 비움
        (13, None, None),  # 요청 없음
        (14, 3, 3),  # 같은 이름 학과 중 자기 대학(2) 것
        (15, 3, 2),  # 최근 요청 107(Mathematics)
        (16, 3, 2),  # 최근 요청 110(Mathematics)
    ]
    # 학생이 아닌 계정은 건드리지 않음
    assert (
        scalar(upgraded, "SELECT count(*) FROM users WHERE role <> 'student' AND source_institution_id IS NOT NULL")
        == 0
    )


def test_0004_institution_sources(upgraded: Engine) -> None:
    got = rows(upgraded, "SELECT institution_id, source_institution_id FROM institution_sources ORDER BY 1, 2")
    # 1↔3 계정·요청, 1↔4 요청, 1↔5 동등 과목표, 1↔6 감사 로그(create), 2↔3 계정·요청·감사 로그(한 줄만)
    # 7(update 로그만)과 대상 대학끼리(1↔2)는 없음
    assert got == [(1, 3), (1, 4), (1, 5), (1, 6), (2, 3)]


def test_0005_closed_requests(upgraded: Engine) -> None:
    status = dict(rows(upgraded, "SELECT id, status FROM transfer_requests WHERE id IN (106, 107)"))
    assert status == {106: "closed", 107: "decided"}  # 107: 삭제 요청만 있음 (decided는 legacy_0009에서)
    active = dict(rows(upgraded, "SELECT id, is_active FROM assignments ORDER BY id"))
    assert active == {701: False, 702: True, 703: True, 704: True, 705: True}


def test_0006_closed_appeal_reason_erased(upgraded: Engine) -> None:
    reasons = dict(rows(upgraded, "SELECT id, reason FROM appeals WHERE id IN (601, 602)"))
    assert reasons[601] == ""
    assert reasons[602] != ""


def test_0007_account_transcripts(upgraded: Engine) -> None:
    transcripts = rows(
        upgraded,
        "SELECT student_id, file_key, masked_name, status, jsonb_array_length(lines) "
        "FROM student_transcripts ORDER BY student_id",
    )
    assert transcripts == [
        (10, "transcripts/a-new.pdf", "김**", "ready", 3),  # 최근 요청 102 (101의 옛 파일은 옮기지 않음)
        (11, "transcripts/b.pdf", "박**", "ready", 1),
        (14, "transcripts/t2.pdf", "한**", "ready", 1),
        (16, "transcripts/g.pdf", "윤**", "ready", 2),
    ]
    lines = scalar(upgraded, "SELECT lines FROM student_transcripts WHERE student_id = 10")
    assert [line["code"] for line in lines] == ["MATH101", "CSE204", "CSE101"]  # 과목 줄 순서 유지
    assert lines[2] == {"title": "C Programming", "code": "CSE101", "credits": 3, "grade": "D", "term": "2024-1"}

    requests = {
        r[0]: r[1:]
        for r in rows(
            upgraded,
            "SELECT id, transcript_file_key, transcript_copied_at IS NOT NULL FROM transfer_requests ORDER BY id",
        )
    }
    assert requests[101] == ("transcripts/a-old.pdf", False)  # 오래된 성적표는 요청에 그대로
    for moved in (102, 103, 105, 108):
        assert requests[moved] == (None, True)  # 파일은 계정 소유, 요청은 복사본
    assert requests[104] == (None, False)  # 성적표 없는 학생의 초안
    assert requests[109] == (None, True)
    assert requests[110] == (None, True)

    entries = rows(
        upgraded,
        "SELECT transfer_request_id, code, grade FROM transcript_entries "
        "WHERE transfer_request_id IN (109, 110) ORDER BY id",
    )
    # 109: 과목 줄이 없어 계정 성적표(108의 줄)에서 복사 / 110: 직접 넣은 줄이 있어 복사 안 함
    assert entries == [(110, "MATH150", "B"), (109, "CSE204", "B+"), (109, "MATH201", "C+")]


def test_0010_credit_allocations(upgraded: Engine) -> None:
    got = rows(
        upgraded,
        "SELECT decision_id, student_id, syllabus_id, target_course_id, credits, credit_unit, status, "
        "superseded_by_decision_id FROM credit_allocations ORDER BY decision_id",
    )
    assert got == [
        (505, 10, 216, 303, 3.0, "us_semester", "active", None),  # 한 번만 판정
        (506, 15, 214, 302, 3.0, "us_semester", "active", None),  # 학점 없는 504 뒤 재판정
        (507, 16, 217, 301, 3.0, "us_semester", "superseded", 508),
        (508, 16, 217, 301, 2.0, "us_semester", "active", None),  # 부분 인정 2학점
        (509, 11, 215, 302, 3.0, "us_semester", "superseded", 510),  # 불인정(510)으로 대체
    ]
    # 0009 이전 판정(501~504)과 0학점 불인정(510)은 줄이 없다
    assert (
        scalar(upgraded, "SELECT count(*) FROM credit_allocations WHERE decision_id IN (501, 502, 503, 504, 510)") == 0
    )
    # 학생별 확정 인정 학점 = active 합계
    totals = dict(
        rows(upgraded, "SELECT student_id, sum(credits) FROM credit_allocations WHERE status = 'active' GROUP BY 1")
    )
    assert totals == {10: 3.0, 15: 3.0, 16: 2.0}


def test_0011_policy_rules(upgraded: Engine) -> None:
    got = rows(
        upgraded,
        "SELECT institution_id, rule_type, parameters, status FROM policy_rules ORDER BY institution_id, rule_type",
    )
    approved = "approved"
    assert got == [
        (1, "degree_credits", {"credits": 128}, approved),  # 대학 설정 그대로
        (1, "min_grade", {"min_grade": "C", "accept_pass": True}, approved),
        (1, "semester_load", {"credits": 15}, approved),
        (1, "transfer_cap", {"credits": 45}, approved),  # 0009 뒤 관리자가 정한 상한
        (2, "degree_credits", {"credits": 120}, approved),  # 비어 있으면 기본값
        (2, "min_grade", {"min_grade": "C", "accept_pass": True}, approved),
        (2, "semester_load", {"credits": 15}, approved),
        (2, "transfer_cap", {"credits": 60}, approved),
    ]
    # 출신 대학에는 정책을 만들지 않는다
    assert scalar(upgraded, "SELECT count(*) FROM policy_rules WHERE institution_id >= 3") == 0


def test_0012_evidence_status(upgraded: Engine) -> None:
    got = rows(
        upgraded,
        "SELECT source_kind, authenticity, applicability, count(*) FROM syllabi GROUP BY 1, 2, 3 ORDER BY 1",
    )
    assert got == [
        ("institution_reference", "verified", "unknown", 3),  # 201~203 기준 강의계획서
        ("student_uploaded", "unverified", "unknown", 7),  # 211~217
    ]


def test_append_only_tables_untouched(upgraded: Engine) -> None:
    """판정·감사 로그는 마이그레이션이 고치거나 지우지 않는다 (INSERT만 규칙)."""
    assert rows(upgraded, "SELECT id FROM decisions ORDER BY id") == [(i,) for i in range(501, 511)]
    assert scalar(upgraded, "SELECT count(*) FROM audit_logs") == 4
    # 0009 이전 판정은 인정 학점 칸이 비어 있다 (추정해서 채우지 않음)
    assert scalar(upgraded, "SELECT count(*) FROM decisions WHERE id <= 504 AND accepted_credits IS NOT NULL") == 0


# 아래 세 테스트는 같은 DB를 다시 만든다. upgraded를 쓰는 테스트보다 뒤에 두어야 한다(파일 순서대로 실행)


def test_stop_at_intermediate_revision(legacy_url: str) -> None:
    """--to로 중간에서 멈추면 그 뒤 단계의 옛 데이터(legacy_0009)는 넣지 않는다."""
    migration_demo.build(legacy_url, "0006")
    engine = create_engine(legacy_url)
    try:
        assert scalar(engine, "SELECT version_num FROM alembic_version") == "0006"
        assert scalar(engine, "SELECT count(*) FROM decisions") == 4
        assert scalar(engine, "SELECT status FROM transfer_requests WHERE id = 106") == "closed"
    finally:
        engine.dispose()


def test_rejects_bad_target_before_dropping(legacy_url: str) -> None:
    cfg = migration_demo.alembic_config(legacy_url)
    with pytest.raises(SystemExit):
        migration_demo.check_target(cfg, "9999")
    with pytest.raises(SystemExit):
        migration_demo.check_target(cfg, "0001")  # 0002 데이터를 넣을 수 없는 리비전


def test_refuses_app_database() -> None:
    app = "postgresql+psycopg://u:p@localhost:5432/creditbridge"
    with pytest.raises(SystemExit):
        migration_demo.refuse_app_database(make_url("postgresql+psycopg://x:y@localhost/creditbridge"), app)
    migration_demo.refuse_app_database(make_url("postgresql+psycopg://u:p@localhost:5432/cb_migration"), app)


def test_downgrade_to_0002_and_back(legacy_url: str) -> None:
    """데이터가 있는 채로 head → 0002 → head가 실패 없이 지나가는지 (되돌리기 안전망).

    되돌리면 사라지는 값(인정 학점·배분 원장·closed 상태 등)은 되돌릴 수 없는 게 맞다. 여기서는 핵심 행이 남는지만 본다.
    """
    migration_demo.build(legacy_url, "head")
    cfg = migration_demo.alembic_config(legacy_url)
    engine = create_engine(legacy_url)
    try:
        command.downgrade(cfg, "0002")
        assert scalar(engine, "SELECT version_num FROM alembic_version") == "0002"
        assert scalar(engine, "SELECT count(*) FROM users") == 14
        assert scalar(engine, "SELECT count(*) FROM transfer_requests") == 10
        assert scalar(engine, "SELECT count(*) FROM decisions") == 10
        # [0005 되돌리기] closed는 제출 여부로 되돌린다 (원래 decided였는지는 알 수 없음)
        assert scalar(engine, "SELECT status FROM transfer_requests WHERE id = 106") == "submitted"
        # [0007 되돌리기] 계정 성적표 파일이 학생의 요청 하나로 돌아간다
        assert scalar(engine, "SELECT count(*) FROM transfer_requests WHERE transcript_file_key IS NOT NULL") == 5
        # 원래 파일이 있던 요청(108)은 알 수 없어 그 학생의 가장 최근 복사 요청(초안 110)으로 간다 (0007 downgrade 주석)
        assert (
            scalar(engine, "SELECT id FROM transfer_requests WHERE student_id = 16 AND transcript_file_key IS NOT NULL")
            == 110
        )

        command.upgrade(cfg, "head")
        assert scalar(engine, "SELECT count(*) FROM student_transcripts") == 4
        assert scalar(engine, "SELECT count(*) FROM policy_rules") == 8
    finally:
        engine.dispose()
