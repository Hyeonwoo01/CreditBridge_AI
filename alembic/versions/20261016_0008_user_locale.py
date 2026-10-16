"""user locale

users.locale: 화면·알림·메일 언어(ko/en). NULL이면 다음 로그인 때 그때 화면 언어로 정한다.
MySQL 8.0 호환 DDL만 사용한다.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-16 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('users', sa.Column('locale', sa.String(length=5), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'locale')
