"""user active flag

계정 비활성화(users.is_active, users.deactivated_at). 졸업·퇴직한 계정은 지우지 않고(감사 기록 보존) 로그인만 막는다.
MySQL 8.0 호환 DDL만 사용한다.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-16 02:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column(
        'users',
        sa.Column(
            'deactivated_at',
            sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mariadb').with_variant(mysql.DATETIME(fsp=6), 'mysql'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'deactivated_at')
    op.drop_column('users', 'is_active')
