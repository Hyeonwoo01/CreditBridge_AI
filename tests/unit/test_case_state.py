"""상태 머신 전이 표 (리뷰 v3 P0-6)."""

from backend.services.case_state import ALLOWED, BLOCKED_MESSAGES, LABELS, CaseState


def test_every_state_has_label() -> None:
    assert set(LABELS) == set(CaseState)


def test_decide_only_while_under_review_or_appeal() -> None:
    assert ALLOWED["decide"] == {CaseState.UNDER_REVIEW, CaseState.NEEDS_INFORMATION, CaseState.APPEAL_REVIEW}
    for state in (CaseState.SUPERSEDED, CaseState.DECIDED, CaseState.APPEAL_SUBMITTED, CaseState.CLOSED):
        assert state not in ALLOWED["decide"]


def test_decided_case_is_corrected_only_through_appeal() -> None:
    for action in ("decide", "assign", "request_materials"):
        assert CaseState.DECIDED not in ALLOWED[action]
    assert ALLOWED["appeal_process"] == {CaseState.APPEAL_SUBMITTED}


def test_blocked_states_explain_why() -> None:
    for state in set(CaseState) - set().union(*ALLOWED.values()):
        assert state in BLOCKED_MESSAGES
