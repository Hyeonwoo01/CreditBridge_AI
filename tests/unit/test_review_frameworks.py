"""분야별 심사 체크리스트 (리뷰 v3 P1-1)."""

from backend.services import review_frameworks as rf


def test_department_picks_framework() -> None:
    assert rf.for_department("Mathematics").key == "math"
    assert rf.for_department("Computer Science and Engineering").key == "computing"
    assert rf.for_department("Chemistry").key == "lab_science"
    assert rf.for_department("Physics").key == "physics"
    assert rf.for_department("Operations Management").key == "business"
    assert rf.for_department("History").key == "humanities"
    assert rf.for_department(None).key == rf.COMMON
    assert rf.for_department("Underwater Basket Weaving").key == rf.COMMON


def test_every_framework_keeps_common_items() -> None:
    common = {k for k, _ in rf.FRAMEWORKS[rf.COMMON].items}
    for framework in rf.FRAMEWORKS.values():
        keys = [k for k, _ in framework.items]
        assert common <= set(keys) and len(keys) == len(set(keys)), framework.key


def test_record_drops_unknown_and_prefers_missing() -> None:
    chem = rf.FRAMEWORKS["lab_science"]
    out = rf.record(chem, ["outcomes", "lab_hours", "made_up"], ["lab_hours", "safety", "x"])
    assert out == {
        "version": rf.VERSION,
        "framework": "lab_science",
        "checked": ["outcomes"],
        "missing_evidence": ["lab_hours", "safety"],
    }
    assert rf.label("lab_science", "lab_hours").startswith("실험실 시간")
