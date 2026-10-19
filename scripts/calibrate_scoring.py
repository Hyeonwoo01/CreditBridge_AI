"""추천 등급 기준값 보정 보고서 (open-issues B2). 기준값을 바꾸지 않고 제안만 출력한다.

실행 예:
  # 교수의 확정 판정을 정답으로 (운영·파일럿 DB)
  uv run python -m scripts.calibrate_scoring --institution "Midwest State University"
  # 전문가 라벨 골든셋 CSV (열: coverage, level, result)
  uv run python -m scripts.calibrate_scoring --csv golden.csv --max-over 0.03
Docker: docker compose --profile app exec web uv run --no-group dev python -m scripts.calibrate_scoring ...

제안값을 쓰려면 backend/services/scoring.py의 DIRECT_MIN·ELECTIVE_MIN을 고치고 RULES_VERSION을 올린다.
"""

import argparse
import sys
from pathlib import Path

from backend.db.session import SessionLocal
from backend.repositories import catalog as catalog_repo
from backend.services import calibration, scoring
from backend.services.calibration import Metrics, Report

LABELS = {"direct": "직접 인정", "elective": "선택 인정", "none": "불인정"}


def _metrics(title: str, m: Metrics) -> list[str]:
    lines = [
        f"{title}: DIRECT_MIN={m.direct_min:.2f}, ELECTIVE_MIN={m.elective_min:.2f}",
        f"  일치율 {m.agreement:.1%} · 오인정률(AI가 더 높게) {m.over_rate:.1%} · 과소 추천률 {m.under_rate:.1%}",
        "  AI 추천 \\ 사람 판정   " + "  ".join(f"{LABELS[h]:>6}" for h in calibration.RESULTS),
    ]
    for ai in calibration.RESULTS:
        counts = "  ".join(f"{m.confusion[(ai, h)]:>6}" for h in calibration.RESULTS)
        lines.append(f"  {LABELS[ai]:<14}       {counts}")
    return lines


def render(report: Report) -> str:
    lines = [f"표본 {report.current.n}건 (정보 부족 추천 제외), 목표 오인정률 ≤ {report.max_over:.0%}", ""]
    if report.current.n == 0:
        return "\n".join([*lines, "표본이 없어요. 확정 판정이 쌓이거나 골든셋 CSV가 있어야 계산할 수 있어요."])
    lines += _metrics(f"지금 기준값 ({scoring.RULES_VERSION})", report.current)
    lines.append("")
    if report.suggested is None:
        lines.append("목표 오인정률을 지키는 기준값 조합이 없어요. --max-over를 높이거나 표본을 늘려 주세요.")
    else:
        lines += _metrics("제안 기준값", report.suggested)
    if not report.enough_samples:
        lines += ["", f"주의: 표본이 {calibration.MIN_SAMPLES}건보다 적어 제안값은 참고로만 보세요."]
    lines += [
        "",
        "바꾸려면 backend/services/scoring.py의 값을 고치고 RULES_VERSION을 올리세요 (자동으로 바꾸지 않아요).",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="추천 등급 기준값 보정 보고서")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--institution", help="대상 대학 이름: 그 대학 교수의 확정 판정을 정답으로 쓴다")
    source.add_argument("--csv", type=Path, help="전문가 라벨 골든셋 CSV (coverage, level, result)")
    parser.add_argument("--max-over", type=float, default=calibration.DEFAULT_MAX_OVER, help="허용할 오인정률 (0~1)")
    parser.add_argument("--step", type=float, default=0.01, help="기준값을 훑는 간격")
    args = parser.parse_args()
    if args.csv:
        try:
            samples = calibration.samples_from_csv(args.csv.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            print(f"CSV를 읽지 못했어요: {exc}", file=sys.stderr)
            return 1
    else:
        with SessionLocal() as session:
            institution = catalog_repo.target_institution_by_name(session, args.institution)
            if institution is None:
                print("등록된 대상 대학이 아니에요.", file=sys.stderr)
                return 1
            samples = calibration.samples_from_decisions(session, institution.id)
    print(render(calibration.suggest(samples, max_over=args.max_over, step=args.step)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
