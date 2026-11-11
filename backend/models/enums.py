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


class CreditSystem(StrEnum):
    """대학의 학점 단위. 서로 다른 단위는 관리자가 승인한 환산 규칙이 있을 때만 비교한다."""

    KR_CREDIT = "kr_credit"  # 한국 학점
    US_SEMESTER = "us_semester"  # 미국 학기제 학점(semester credit hour)
    US_QUARTER = "us_quarter"  # 미국 쿼터제 학점
    ECTS = "ects"
    OTHER = "other"


class ConversionMethod(StrEnum):
    APPROVED_TABLE = "approved_table"  # 대학이 승인한 환산표
    CONTACT_HOURS = "contact_hours"  # 수업 시간 기준
    MANUAL = "manual"  # 그 밖의 명시적 규칙


class CreditBasis(StrEnum):
    """교수가 확정한 인정 학점의 근거."""

    FULL = "full"  # 대상 과목 학점 전부
    PARTIAL = "partial"  # 대상 과목 학점보다 적게 (부분 인정)
    ELECTIVE = "elective"  # 일반 선택 학점
    NOT_ACCEPTED = "not_accepted"


class AllocationStatus(StrEnum):
    ACTIVE = "active"  # 지금 유효한 배분 (확정 인정 학점에 들어감)
    SUPERSEDED = "superseded"  # 재판정으로 대체됨 (기록으로만 남음)


class PolicyRuleType(StrEnum):
    """학칙 정책 규칙 종류 (리뷰 v3 P0-4). 값은 규칙 parameters에 둔다."""

    MIN_GRADE = "min_grade"  # {"min_grade": "C", "accept_pass": true}
    TRANSFER_CAP = "transfer_cap"  # {"credits": 60}
    DEGREE_CREDITS = "degree_credits"  # {"credits": 120}
    SEMESTER_LOAD = "semester_load"  # {"credits": 15} 학기당 이수 학점 (남은 학기 계산)
    APPEAL_WINDOW = "appeal_window"  # {"days": 30} 판정 뒤 이의 신청을 받는 기간 (리뷰 v3 P1-5)
    APPEAL_REVIEW = "appeal_review"  # {"days": 14} 이의 신청 접수 뒤 학사처 처리 기한


class PolicyStatus(StrEnum):
    DRAFT = "draft"  # 판정·계산에 쓰지 않음
    APPROVED = "approved"
    RETIRED = "retired"


class SourceKind(StrEnum):
    """증거 자료를 누가 어디서 냈는지 (리뷰 v3 P0-5). 학생 제출 자료를 공식 문서처럼 표시하지 않는다."""

    STUDENT_UPLOADED = "student_uploaded"
    REGISTRAR_ISSUED = "registrar_issued"  # 출신 대학 학사처 발급
    INSTRUCTOR_CONFIRMED = "instructor_confirmed"  # 담당 교원 확인
    OFFICIAL_PORTAL = "official_portal"  # 출신 대학 공식 포털에서 직접 확인
    PUBLIC_WEB = "public_web"  # 공개 웹 자료 (참고용, 수강 분반 증명으로 자동 승격하지 않음)
    INSTITUTION_REFERENCE = "institution_reference"  # 대상 대학이 올린 기준 강의계획서
    OTHER = "other"


class Authenticity(StrEnum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    SUSPICIOUS = "suspicious"  # 자동 불인정이 아니라 판정 보류·검토
    REJECTED = "rejected"  # 심사 증거로 채택하지 않음 (새 자료 필요)


class Applicability(StrEnum):
    APPLICABLE = "applicable"  # 학생이 수강한 학기 자료
    MISMATCH = "mismatch"  # 다른 학기 자료
    UNKNOWN = "unknown"


class EvidenceSide(StrEnum):
    SOURCE = "source"  # 학생 강의계획서
    TARGET = "target"  # 대상 대학 기준 강의계획서


class EvidenceVerdict(StrEnum):
    CORRECT = "correct"  # 교수가 보기에 그 개념을 가르쳤다는 근거가 맞음
    WRONG = "wrong"  # 원문에는 있지만 그 개념의 근거가 아님


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
