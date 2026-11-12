"""catalog imports

카탈로그 출처·검증·승인 (리뷰 v3 P1-2). 과목 CSV를 올리면 검증을 통과한 행과 바뀌는 점(새 과목·바뀌는 필드의
이전·새 값·그대로인 과목 수)을 catalog_imports에 게시 대기본으로 남기고, 관리자가 게시해야 courses에 반영한다.
과목마다 마지막으로 값을 정한 게시본(courses.catalog_import_id: 출처·적용 학년도·게시자·게시 시각)을 남긴다.
기존 과목은 출처 기록이 없다(비움).

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-12 06:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_imports",
        sa.Column("institution_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("catalog_year", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("rows", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'discarded')", name=op.f("ck_catalog_imports_status_valid")
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_catalog_imports_created_by_users")),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name=op.f("fk_catalog_imports_institution_id_institutions")
        ),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name=op.f("fk_catalog_imports_reviewed_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalog_imports")),
    )
    op.create_index(op.f("ix_catalog_imports_institution_id"), "catalog_imports", ["institution_id"], unique=False)
    op.create_index(op.f("ix_catalog_imports_status"), "catalog_imports", ["status"], unique=False)
    op.add_column("courses", sa.Column("catalog_import_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_courses_catalog_import_id_catalog_imports"), "courses", "catalog_imports", ["catalog_import_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_courses_catalog_import_id_catalog_imports"), "courses", type_="foreignkey")
    op.drop_column("courses", "catalog_import_id")
    op.drop_index(op.f("ix_catalog_imports_status"), table_name="catalog_imports")
    op.drop_index(op.f("ix_catalog_imports_institution_id"), table_name="catalog_imports")
    op.drop_table("catalog_imports")
