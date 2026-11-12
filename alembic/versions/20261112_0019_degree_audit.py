"""degree audit

Degree Audit 기본 기능 (리뷰 v3 P1-6). degree_programs: 대상 대학의 학과·적용 입학연도별 졸업 프로그램.
graduation_requirements: 프로그램의 요건(영역 major_required·major_elective·general_education·free_elective, 필요 학점,
요건을 채우는 대상 과목 코드, 순서). 학생 홈에서 확정 인정 학점(배분 원장)을 요건에 배정해 보여 준다. 기존 데이터는 없다.

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-12 07:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "degree_programs",
        sa.Column("institution_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("department_id", sa.BigInteger(), nullable=True),
        sa.Column("catalog_year", sa.Integer(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "catalog_year IS NULL OR catalog_year BETWEEN 1990 AND 2100",
            name=op.f("ck_degree_programs_catalog_year_range"),
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], name=op.f("fk_degree_programs_department_id_departments")
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], name=op.f("fk_degree_programs_institution_id_institutions")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_degree_programs")),
    )
    op.create_index(op.f("ix_degree_programs_institution_id"), "degree_programs", ["institution_id"], unique=False)
    op.create_table(
        "graduation_requirements",
        sa.Column("program_id", sa.BigInteger(), nullable=False),
        sa.Column("area", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("required_credits", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("course_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort", sa.Integer(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "area IN ('major_required', 'major_elective', 'general_education', 'free_elective')",
            name=op.f("ck_graduation_requirements_area_valid"),
        ),
        sa.CheckConstraint("required_credits > 0", name=op.f("ck_graduation_requirements_required_credits_positive")),
        sa.ForeignKeyConstraint(
            ["program_id"], ["degree_programs.id"], name=op.f("fk_graduation_requirements_program_id_degree_programs")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_graduation_requirements")),
    )
    op.create_index(
        op.f("ix_graduation_requirements_program_id"), "graduation_requirements", ["program_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_graduation_requirements_program_id"), table_name="graduation_requirements")
    op.drop_table("graduation_requirements")
    op.drop_index(op.f("ix_degree_programs_institution_id"), table_name="degree_programs")
    op.drop_table("degree_programs")
