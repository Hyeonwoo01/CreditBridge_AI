"""composite indexes and check constraints

ERD 검토(docs/ERD.md 6절) 반영.
- R3: 자주 쓰는 조회에 맞춘 복합 인덱스. 앞 컬럼이 같은 단일 인덱스는 복합 인덱스가 대신하므로 지운다
- E3: 상태·코드 값 허용 목록 CHECK
- E4: 점수(0~1)·위치·학점·크기 범위 CHECK
(E2 JSON 유효성은 MariaDB가 JSON 컬럼마다 JSON_VALID CHECK를 자동으로 붙이고 MySQL 8.0은 JSON 형식이 검사하므로 따로 두지 않는다)
허용 목록은 이 시점 값으로 고정한다 (backend/models/enums.py가 바뀌면 새 마이그레이션으로 바꾼다).
MySQL 8.0.16+ 호환 DDL만 사용한다.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-19 09:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (테이블, 새 복합 인덱스, 컬럼, 대신하는 단일 인덱스, 그 컬럼)
INDEXES = [
    ('audit_logs', 'ix_audit_logs_target', ['target_type', 'target_id'], None, None),
    ('audit_logs', 'ix_audit_logs_actor_action', ['actor_id', 'action'], 'ix_audit_logs_actor_id', 'actor_id'),
    ('notifications', 'ix_notifications_user_unread', ['user_id', 'read_at'], 'ix_notifications_user_id', 'user_id'),
    (
        'assignments',
        'ix_assignments_evaluation_active',
        ['course_evaluation_id', 'is_active'],
        'ix_assignments_course_evaluation_id',
        'course_evaluation_id',
    ),
    ('assignments', 'ix_assignments_reviewer_active', ['reviewer_id', 'is_active'], 'ix_assignments_reviewer_id', 'reviewer_id'),
    (
        'course_evaluations',
        'ix_course_evaluations_syllabus_latest',
        ['syllabus_id', 'is_latest'],
        'ix_course_evaluations_syllabus_id',
        'syllabus_id',
    ),
    (
        'equivalencies',
        'ix_equivalencies_pair_course',
        ['target_institution_id', 'source_institution_id', 'source_course_key'],
        'ix_equivalencies_target_institution_id',
        'target_institution_id',
    ),
]


def _in(column: str, values: tuple[str, ...], nullable: bool = False) -> str:
    listed = f"{column} IN ({', '.join(repr(v) for v in values)})"
    return f'{column} IS NULL OR {listed}' if nullable else listed


def _ratio(column: str) -> str:
    return f'{column} IS NULL OR {column} BETWEEN 0 AND 1'


RESULTS = ('direct', 'elective', 'none')

# (테이블, 제약 이름, 조건)
CHECKS = [
    ('users', 'ck_users_role_valid', _in('role', ('student', 'evaluator', 'professor', 'admin'))),
    ('users', 'ck_users_locale_valid', _in('locale', ('ko', 'en'), nullable=True)),
    ('users', 'ck_users_failed_logins_range', 'failed_logins >= 0'),
    ('transfer_requests', 'ck_transfer_requests_status_valid', _in('status', ('draft', 'submitted', 'decided'))),
    (
        'syllabi',
        'ck_syllabi_status_valid',
        _in('status', ('uploaded', 'processing', 'ready', 'failed', 'deleted')),
    ),
    ('syllabi', 'ck_syllabi_quality_score_range', _ratio('quality_score')),
    ('syllabi', 'ck_syllabi_credits_range', 'credits IS NULL OR credits >= 0'),
    ('courses', 'ck_courses_credits_range', 'credits >= 0'),
    (
        'course_evaluations',
        'ck_course_evaluations_status_valid',
        _in('status', ('queued', 'running', 'done', 'failed')),
    ),
    (
        'course_evaluations',
        'ck_course_evaluations_recommendation_valid',
        _in('recommendation', ('direct', 'elective', 'none', 'insufficient'), nullable=True),
    ),
    (
        'course_evaluations',
        'ck_course_evaluations_confidence_valid',
        _in('confidence', ('high', 'medium', 'low'), nullable=True),
    ),
    (
        'course_evaluations',
        'ck_course_evaluations_level_flag_valid',
        _in('level_flag', ('same', 'lower', 'higher'), nullable=True),
    ),
    ('course_evaluations', 'ck_course_evaluations_coverage_range', _ratio('coverage')),
    ('decisions', 'ck_decisions_action_valid', _in('action', ('approve', 'modify', 'reject'))),
    ('decisions', 'ck_decisions_result_valid', _in('result', RESULTS)),
    ('evidence_spans', 'ck_evidence_spans_side_valid', _in('side', ('source', 'target'))),
    ('evidence_spans', 'ck_evidence_spans_span_range', 'char_start >= 0 AND char_start < char_end'),
    (
        'syllabus_chunks',
        'ck_syllabus_chunks_span_range',
        'char_start IS NULL OR char_end IS NULL OR (char_start >= 0 AND char_start <= char_end)',
    ),
    ('transcript_entries', 'ck_transcript_entries_link_score_range', _ratio('link_score')),
    ('transcript_entries', 'ck_transcript_entries_credits_range', 'credits IS NULL OR credits >= 0'),
    ('material_requests', 'ck_material_requests_status_valid', _in('status', ('open', 'fulfilled'))),
    ('equivalencies', 'ck_equivalencies_result_valid', _in('result', RESULTS)),
    ('appeal_files', 'ck_appeal_files_size_range', 'size >= 0'),
    (
        'appeals',
        'ck_appeals_status_valid',
        _in('status', ('submitted', 'accepted', 'dismissed', 'redecided')),
    ),
    ('privacy_requests', 'ck_privacy_requests_status_valid', _in('status', ('requested', 'reviewed', 'completed'))),
]


def upgrade() -> None:
    for table, name, columns, replaces, _ in INDEXES:
        op.create_index(op.f(name), table, columns, unique=False)
        if replaces:
            # 외래키가 쓰던 인덱스라도 같은 컬럼으로 시작하는 복합 인덱스가 먼저 생겼으므로 지울 수 있다
            op.drop_index(op.f(replaces), table_name=table)
    for table, name, condition in CHECKS:
        op.create_check_constraint(op.f(name), table, condition)


def downgrade() -> None:
    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(op.f(name), table, type_='check')
    for table, name, _, replaces, column in reversed(INDEXES):
        if replaces:
            op.create_index(op.f(replaces), table, [column], unique=False)
        op.drop_index(op.f(name), table_name=table)
