"""추천 등급 기준값 보정 도구 (services/calibration.py)."""

import pytest

from backend.services import calibration, scoring
from backend.services.calibration import Sample
from scripts.calibrate_scoring import render


def test_predict_follows_scoring_rules() -> None:
    d, e = scoring.DIRECT_MIN, scoring.ELECTIVE_MIN
    assert calibration.predict(Sample(0.80, "same", "direct"), d, e) == "direct"
    assert calibration.predict(Sample(0.80, "lower", "direct"), d, e) == "elective"  # 수준이 낮으면 직접 인정 안 함
    assert calibration.predict(Sample(0.50, None, "none"), d, e) == "elective"
    assert calibration.predict(Sample(0.20, "same", "none"), d, e) == "none"


def test_suggest_moves_threshold_to_cut_over_recognition() -> None:
    # 교수들은 커버리지 0.85 이상만 직접 인정, 0.5 미만은 불인정으로 판정해 왔다
    samples = (
        [Sample(0.90, "same", "direct")] * 30
        + [Sample(0.78, "same", "elective")] * 30  # 지금 기준(0.75)이면 AI가 직접 인정으로 과하게 추천
        + [Sample(0.60, "same", "elective")] * 20
        + [Sample(0.45, "same", "none")] * 20  # 지금 기준(0.40)이면 선택 인정으로 과하게 추천
    )
    report = calibration.suggest(samples, max_over=0.0)
    assert report.current.over_rate == pytest.approx(0.5)
    suggested = report.suggested
    assert suggested is not None and suggested.over_rate == 0 and suggested.agreement == 1
    assert 0.78 < suggested.direct_min <= 0.90 and 0.45 < suggested.elective_min <= 0.60
    assert report.enough_samples
    text = render(report)
    assert "제안 기준값" in text and "오인정률" in text and "RULES_VERSION" in text


def test_suggest_keeps_current_values_when_they_already_fit() -> None:
    samples = [Sample(0.95, "same", "direct")] * 5 + [Sample(0.10, "same", "none")] * 5
    report = calibration.suggest(samples)
    assert report.suggested is not None
    assert (report.suggested.direct_min, report.suggested.elective_min) == (scoring.DIRECT_MIN, scoring.ELECTIVE_MIN)
    assert not report.enough_samples and "참고로만" in render(report)


def test_empty_and_csv_samples() -> None:
    assert "표본이 없어요" in render(calibration.suggest([]))
    rows = calibration.samples_from_csv("﻿coverage,level,result\n0.8,same,direct\n0.3,,NONE\n")
    assert rows == [Sample(0.8, "same", "direct"), Sample(0.3, None, "none")]
    with pytest.raises(ValueError, match="line 2"):
        calibration.samples_from_csv("coverage,result\n1.4,direct\n")
    with pytest.raises(ValueError, match="missing columns"):
        calibration.samples_from_csv("score,result\n0.4,none\n")
