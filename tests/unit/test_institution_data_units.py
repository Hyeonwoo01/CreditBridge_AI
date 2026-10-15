import pytest

from backend.errors import CreditBridgeError
from backend.services import csv_import
from backend.services.auth import temporary_password


def test_temporary_password_avoids_confusable_characters() -> None:
    passwords = {temporary_password() for _ in range(50)}
    assert len(passwords) == 50
    for p in passwords:
        assert len(p) == 12 and not set(p) & set("0O1lI")


def test_read_rows_handles_excel_korean_csv_and_limits() -> None:
    data = "email,name\n\na@b.co,김교수\n".encode("cp949")
    assert list(csv_import.read_rows("x.csv", data, ["email", "name"], ["email"], 10)) == [
        (3, {"email": "a@b.co", "name": "김교수"})
    ]
    with pytest.raises(CreditBridgeError, match="CSV 파일만"):
        list(csv_import.read_rows("x.xlsx", data, ["email"], ["email"], 10))
    with pytest.raises(CreditBridgeError, match="2줄까지만"):
        list(csv_import.read_rows("x.csv", b"email\na\nb\nc\n", ["email"], ["email"], 2))
