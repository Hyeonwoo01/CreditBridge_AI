"""institution data import

계정·과목 CSV 가져오기: 첫 로그인 비밀번호 변경 표시(users.must_change_password),
학과가 정한 과목별 필수 개념(courses.concepts). MySQL 8.0 호환 DDL만 사용한다.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'users', sa.Column('must_change_password', sa.Boolean(), server_default=sa.false(), nullable=False)
    )
    op.add_column('courses', sa.Column('concepts', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('courses', 'concepts')
    op.drop_column('users', 'must_change_password')
