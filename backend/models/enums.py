from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    EVALUATOR = "evaluator"  # 학사처 심사관
    PROFESSOR = "professor"  # 학과 심사 교수 (최종 판정권자)
    ADMIN = "admin"  # 기관 관리자


class RequestStatus(StrEnum):
    DRAFT = "draft"  # 학생이 자료를 올리는 중 (사전 시뮬레이션)
    SUBMITTED = "submitted"  # 학사처에 심사 요청
    DECIDED = "decided"  # 모든 과목 판정 완료
    CLOSED = "closed"  # 문서 삭제 승인으로 종료 (더 올리거나 심사하지 않는다. 판정 기록은 남는다)


class TranscriptStatus(StrEnum):
    PROCESSING = "processing"  # 올림, 과목 목록 추출 중
    READY = "ready"
    FAILED = "failed"


class SyllabusStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETED = "deleted"


class EvaluationStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Recommendation(StrEnum):
    DIRECT = "direct"  # 직접 인정 (특정 과목 1:1 대체)
    ELECTIVE = "elective"  # 선택 인정 (Elective 학점만)
    NONE = "none"  # 불인정
    INSUFFICIENT = "insufficient"  # 정보 부족 — 확률을 내지 않는다


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DecisionAction(StrEnum):
    APPROVE = "approve"  # AI 추천 그대로 승인
    MODIFY = "modify"  # 등급 또는 대상 과목 수정
    REJECT = "reject"  # 불인정


class DecisionResult(StrEnum):
    DIRECT = "direct"
    ELECTIVE = "elective"
    NONE = "none"


class EvidenceSide(StrEnum):
    SOURCE = "source"  # 학생 강의계획서
    TARGET = "target"  # 대상 대학 기준 강의계획서


class ReasonCode(StrEnum):
    """교수 판정 선택형 사유 (FR-09)."""

    WEEKS_INSUFFICIENT = "weeks_insufficient"  # 주차 범위 부족
    LEVEL_DIFFERENCE = "level_difference"  # 수준 차이
    NO_LAB = "no_lab"  # 실험·실습 미포함
    PREREQUISITE_DIFFERENCE = "prerequisite_difference"  # 선수과목 차이
    OTHER = "other"  # 기타 (메모 필수)


class MaterialRequestStatus(StrEnum):
    OPEN = "open"  # 학생이 보완 자료를 올리기 전
    FULFILLED = "fulfilled"


class AppealStatus(StrEnum):
    SUBMITTED = "submitted"  # 학생 접수, 심사관 처리 대기
    ACCEPTED = "accepted"  # 심사관이 받아들여 교수 재판정 대기
    DISMISSED = "dismissed"  # 심사관이 기각 (사유 필수)
    REDECIDED = "redecided"  # 교수 재판정 완료


class PrivacyStatus(StrEnum):
    REQUESTED = "requested"  # 학생 요청
    REVIEWED = "reviewed"  # 심사관 처리 완료, 관리자 승인 대기
    COMPLETED = "completed"  # 관리자 승인, 삭제 완료


# 편입 학점 인정 최저 성적: C 이상(C+·C·C0)과 P·PASS·S. 성적표에서 이보다 낮은 과목(C- 이하·D·F 등)은
# 인정 대상이 아니라 교수 심사 없이 제외한다 (판정 기록은 만들지 않음)
PASSING_GRADES = frozenset({"A+", "A", "A0", "A-", "B+", "B", "B0", "B-", "C+", "C", "C0", "P", "PASS", "S"})
