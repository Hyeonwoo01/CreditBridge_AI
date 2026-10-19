"""one active row rules in the database

ERD 검토(docs/ERD.md 6.2 R1) 반영. 앱이 지키던 "하나만" 규칙을 DB에서도 막는다 (동시에 두 요청이 들어온 경우).
MariaDB·MySQL에는 조건부(부분) 유니크 인덱스가 없으므로, 조건에 맞을 때만 값이 있고 아니면 NULL인
저장 생성 컬럼(STORED)을 만들고 UNIQUE를 건다. UNIQUE는 NULL끼리 겹치는 것을 허용한다.
- assignments.active_evaluation_id: 심사 건당 활성 배정 하나
- course_evaluations.latest_syllabus_id: 강의계획서당 최신 분석 하나
- appeals.open_evaluation_id: 심사 건당 처리 중(접수·수용) 이의 신청 하나
- privacy_requests.open_request_id: 편입 요청당 처리 중(완료 전) 삭제 요청 하나
이미 규칙을 어긴 행이 있으면 UNIQUE를 만들 때 실패하므로 먼저 정리해야 한다.
MySQL 8.0 호환 DDL만 사용한다 (IF 함수, GENERATED ALWAYS AS ... STORED).

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-19 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), 'mariadb').with_variant(mysql.BIGINT(unsigned=True), 'mysql')

# (테이블, 생성 컬럼, 식)
COLUMNS = [
    ('assignments', 'active_evaluation_id', 'IF(is_active, course_evaluation_id, NULL)'),
    ('course_evaluations', 'latest_syllabus_id', 'IF(is_latest, syllabus_id, NULL)'),
    ('appeals', 'open_evaluation_id', "IF(status IN ('submitted', 'accepted'), course_evaluation_id, NULL)"),
    ('privacy_requests', 'open_request_id', "IF(status <> 'completed', transfer_request_id, NULL)"),
]


def upgrade() -> None:
    for table, column, expr in COLUMNS:
        op.add_column(table, sa.Column(column, ID, sa.Computed(expr, persisted=True), nullable=True))
        op.create_unique_constraint(op.f(f'uq_{table}_{column}'), table, [column])


def downgrade() -> None:
    for table, column, _ in reversed(COLUMNS):
        op.drop_constraint(op.f(f'uq_{table}_{column}'), table, type_='unique')
        op.drop_column(table, column)
