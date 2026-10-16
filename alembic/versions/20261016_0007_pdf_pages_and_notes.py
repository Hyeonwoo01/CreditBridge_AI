"""pdf page offsets and evaluation notes

- syllabi.page_offsets: 원본 파일 페이지 위치표 (FR-25 근거 구절 → 원본 PDF 페이지). 이전 업로드는 NULL
- evaluation_notes: 심사 건 내부 메모 (심사관·담당 교수, 학생에게 보이지 않음)
MySQL 8.0 호환 DDL만 사용한다.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-16 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ID = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), 'mariadb').with_variant(mysql.BIGINT(unsigned=True), 'mysql')


def upgrade() -> None:
    op.add_column('syllabi', sa.Column('page_offsets', sa.JSON(), nullable=True))
    op.create_table(
        'evaluation_notes',
        sa.Column('syllabus_id', ID, nullable=False),
        sa.Column('course_evaluation_id', ID, nullable=False),
        sa.Column('author_id', ID, nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('id', ID, autoincrement=True, nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mariadb').with_variant(mysql.DATETIME(fsp=6), 'mysql'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['syllabus_id'], ['syllabi.id'], name=op.f('fk_evaluation_notes_syllabus_id_syllabi')),
        sa.ForeignKeyConstraint(
            ['course_evaluation_id'],
            ['course_evaluations.id'],
            name=op.f('fk_evaluation_notes_course_evaluation_id_course_evaluations'),
        ),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], name=op.f('fk_evaluation_notes_author_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluation_notes')),
    )
    op.create_index(op.f('ix_evaluation_notes_syllabus_id'), 'evaluation_notes', ['syllabus_id'], unique=False)


def downgrade() -> None:
    op.drop_table('evaluation_notes')
    op.drop_column('syllabi', 'page_offsets')
