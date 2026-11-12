"""일부러 두 곳에 둔 값이 어긋나지 않았는지 찾는 점검 쿼리 (ERD R2, open-issues H8).

권한 검사·재분석 묶기·감사에 쓰려고 같은 값을 두 테이블에 둔 곳이 있다. 값을 만드는 곳은 서비스 한 곳이지만,
운영 중 손으로 고친 SQL이나 버그로 어긋나면 권한 검사가 엉뚱한 사람을 기준으로 할 수 있다. 각 점검은 어긋난 행의
id만 돌려준다 (이름·내용 없음). 읽기만 한다.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Check:
    name: str
    table: str  # 어긋난 id가 가리키는 테이블
    description: str
    sql: str  # 어긋난 행의 id를 고르는 SELECT


CHECKS: tuple[Check, ...] = (
    Check(
        "evaluation_request",
        "course_evaluations",
        "분석의 편입 요청이 강의계획서의 편입 요청과 같다",
        """SELECT e.id FROM course_evaluations e JOIN syllabi s ON s.id = e.syllabus_id
           WHERE e.transfer_request_id IS DISTINCT FROM s.transfer_request_id""",
    ),
    Check(
        "appeal_student",
        "appeals",
        "이의 신청의 학생이 그 분석의 편입 요청 학생과 같다",
        """SELECT a.id FROM appeals a JOIN course_evaluations e ON e.id = a.course_evaluation_id
           JOIN transfer_requests r ON r.id = e.transfer_request_id WHERE a.student_id <> r.student_id""",
    ),
    Check(
        "privacy_student",
        "privacy_requests",
        "삭제 요청의 학생이 그 편입 요청의 학생과 같다",
        """SELECT p.id FROM privacy_requests p JOIN transfer_requests r ON r.id = p.transfer_request_id
           WHERE p.student_id <> r.student_id""",
    ),
    Check(
        "material_syllabus",
        "material_requests",
        "보완 자료 요청의 강의계획서가 그 분석의 강의계획서와 같다",
        """SELECT m.id FROM material_requests m JOIN course_evaluations e ON e.id = m.course_evaluation_id
           WHERE m.syllabus_id <> e.syllabus_id""",
    ),
    Check(
        "note_syllabus",
        "evaluation_notes",
        "심사 메모의 강의계획서가 그 분석의 강의계획서와 같다",
        """SELECT n.id FROM evaluation_notes n JOIN course_evaluations e ON e.id = n.course_evaluation_id
           WHERE n.syllabus_id <> e.syllabus_id""",
    ),
    Check(
        "span_source_syllabus",
        "evidence_spans",
        "학생 쪽 근거 위치가 그 분석의 강의계획서를 가리킨다",
        """SELECT sp.id FROM evidence_spans sp JOIN course_evaluations e ON e.id = sp.course_evaluation_id
           WHERE sp.side = 'source' AND sp.syllabus_id <> e.syllabus_id""",
    ),
    Check(
        "span_range",
        "evidence_spans",
        # 시작 < 끝은 DB 제약(ck_evidence_spans_span_range)이 막는다. 여기서는 원문 길이를 넘는지 본다
        "근거 위치가 원문 길이 안에 있다 (문서를 지운 강의계획서는 빼고)",
        """SELECT sp.id FROM evidence_spans sp JOIN syllabi s ON s.id = sp.syllabus_id
           WHERE s.status <> 'deleted' AND s.raw_text <> '' AND sp.char_end > char_length(s.raw_text)""",
    ),
    Check(
        "allocation_student",
        "credit_allocations",
        "배분 원장의 학생이 그 출신 과목(강의계획서) 편입 요청의 학생과 같다",
        """SELECT c.id FROM credit_allocations c JOIN syllabi s ON s.id = c.syllabus_id
           JOIN transfer_requests r ON r.id = s.transfer_request_id WHERE c.student_id <> r.student_id""",
    ),
)


def mismatched_ids(session: Session, check: Check, limit: int = 20) -> tuple[int, list[int]]:
    """(어긋난 행 수, 앞쪽 id 몇 개)."""
    count = int(session.execute(text(f"SELECT count(*) FROM ({check.sql}) AS bad")).scalar_one())
    ids = [int(i) for i in session.execute(text(f"{check.sql} ORDER BY 1 LIMIT :n"), {"n": limit}).scalars()]
    return count, ids
