"""allocation requirement

판정 때 졸업 요건 고르기 (리뷰 v3 P1-6). credit_allocations.requirement_id: 교수가 고른 졸업 요건
(graduation_requirements, 지우면 NULL로 돌아가 자동 배정). 비어 있으면 지금처럼 과목 목록 기준으로 배정한다.
기존 행은 모두 비어 있다(자동).

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-12 09:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("credit_allocations", sa.Column("requirement_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_credit_allocations_requirement_id_graduation_requirements"),
        "credit_allocations",
        "graduation_requirements",
        ["requirement_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_credit_allocations_requirement_id_graduation_requirements"), "credit_allocations", type_="foreignkey"
    )
    op.drop_column("credit_allocations", "requirement_id")
