"""appeal files

이의 신청 근거 자료(appeal_files). 개인정보 삭제 때 파일을 지우고 file_key를 비운다. MySQL 8.0 호환 DDL만 사용한다.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-15 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), 'mariadb').with_variant(mysql.BIGINT(unsigned=True), 'mysql')


def upgrade() -> None:
    op.create_table(
        'appeal_files',
        sa.Column('appeal_id', ID, nullable=False),
        sa.Column('file_key', sa.String(length=255), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('id', ID, autoincrement=True, nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mariadb').with_variant(mysql.DATETIME(fsp=6), 'mysql'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['appeal_id'], ['appeals.id'], name=op.f('fk_appeal_files_appeal_id_appeals')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_appeal_files')),
    )
    op.create_index(op.f('ix_appeal_files_appeal_id'), 'appeal_files', ['appeal_id'], unique=False)


def downgrade() -> None:
    op.drop_table('appeal_files')
