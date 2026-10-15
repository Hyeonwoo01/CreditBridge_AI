"""login lockout

연속 로그인 실패 횟수(users.failed_logins)와 잠금 해제 시각(users.locked_until).
5번 실패하면 1분 잠금, 10번이면 비밀번호를 무효로 하고 재설정 메일. MySQL 8.0 호환 DDL만 사용한다.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-15 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('failed_logins', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column(
        'users',
        sa.Column(
            'locked_until',
            sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mariadb').with_variant(mysql.DATETIME(fsp=6), 'mysql'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_logins')
