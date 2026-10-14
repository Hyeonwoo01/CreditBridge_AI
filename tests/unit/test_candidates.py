from dataclasses import dataclass

from app.ai.candidates import MAX_CANDIDATES, matches, select


@dataclass(frozen=True)
class C:
    code: str
    department: str


CATALOG = [
    C("MATH 1151", "Mathematics"),
    C("MATH 2568", "Mathematics"),
    C("CSE 2231", "Computer Science and Engineering"),
    C("CSE 2321", "Computer Science and Engineering"),
    C("PHYSICS 1250", "Physics"),
    C("HISTORY 1151", "History"),
]


def test_discipline_matches_department_names() -> None:
    assert matches("Computer Science", "Computer Science and Engineering")
    assert matches("CS", "Computer Science and Engineering")
    assert matches("Korean History", "History")
    assert matches("Math", "Mathematics")
    assert not matches("Electrical Engineering", "Computer Science and Engineering")
    assert not matches("", "Mathematics")


def test_select_filters_by_department_in_discipline_order() -> None:
    picked = select(CATALOG, ["Mathematics", "Computer Science"])
    assert [c.code for c in picked] == ["MATH 1151", "MATH 2568", "CSE 2231", "CSE 2321"]
    assert select(CATALOG, ["Business"]) == []
    assert select(CATALOG, []) == []


def test_select_caps_candidates() -> None:
    many = [C(f"MATH {i}", "Mathematics") for i in range(50)]
    assert len(select(many, ["Mathematics"])) == MAX_CANDIDATES == 30


def test_korean_discipline_names_match_english_departments() -> None:
    assert matches("수학", "Mathematics")
    assert matches("컴퓨터공학", "Computer Science and Engineering")
    assert matches("물리학과", "Physics")
    assert matches("한국사", "History")
    assert not matches("수학", "Physics")
    assert [c.code for c in select(CATALOG, ["물리학"])] == ["PHYSICS 1250"]
