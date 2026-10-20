"""request closed status

편입 요청 상태에 closed(문서 삭제 승인으로 종료)를 더한다. 승인하면 요청이 끝나 학생 화면에서 종료로 보이고,
심사 큐·교수 목록에서 빠진다. 이미 문서를 삭제한 요청도 closed로 바꾼다.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-20 08:00:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_transfer_requests_status_valid"), "transfer_requests", type_="check")
    op.create_check_constraint(
        op.f("ck_transfer_requests_status_valid"),
        "transfer_requests",
        "status IN ('draft', 'submitted', 'decided', 'closed')",
    )
    op.execute(
        """
        UPDATE transfer_requests SET status = 'closed'
        WHERE id IN (SELECT transfer_request_id FROM privacy_requests WHERE status = 'completed')
        """
    )
    op.execute(
        """
        UPDATE assignments SET is_active = false
        WHERE is_active AND course_evaluation_id IN (
            SELECT e.id FROM course_evaluations AS e
            JOIN transfer_requests AS r ON r.id = e.transfer_request_id
            WHERE r.status = 'closed'
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE transfer_requests SET status = CASE
            WHEN submitted_at IS NULL THEN 'draft' ELSE 'submitted' END
        WHERE status = 'closed'
        """
    )
    op.drop_constraint(op.f("ck_transfer_requests_status_valid"), "transfer_requests", type_="check")
    op.create_check_constraint(
        op.f("ck_transfer_requests_status_valid"), "transfer_requests", "status IN ('draft', 'submitted', 'decided')"
    )
