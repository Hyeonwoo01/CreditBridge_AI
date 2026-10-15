"""운영 시작용: 대상 대학과 첫 기관 관리자 계정을 만든다 (데모 데이터 없이 시작할 때 한 번).

실행 예:
  uv run python -m scripts.create_admin --institution "Midwest State University" --country US \
      --email admin@msu.edu --name "학사정보처 관리자" --tuition 1350 --degree 120
Docker: docker compose --profile app exec web uv run --no-group dev python -m scripts.create_admin ...

임시 비밀번호를 한 번만 출력한다. 첫 로그인 때 새 비밀번호로 바꿔야 한다.
이후 계정·과목은 관리자 화면(/admin/data)에서 가져온다.
"""

import argparse
import sys

from backend.db.session import SessionLocal
from backend.errors import CreditBridgeError
from backend.services.institution_data import bootstrap_admin


def main() -> int:
    parser = argparse.ArgumentParser(description="대상 대학과 첫 기관 관리자 계정을 만든다")
    parser.add_argument("--institution", required=True, help="대상 대학 이름 (이미 있으면 그 대학에 추가)")
    parser.add_argument("--country", required=True, help="두 글자 국가 코드 (예: KR, US)")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--tuition", type=int, default=None, help="학점당 등록금 (시뮬레이션 기본값)")
    parser.add_argument("--degree", type=int, default=None, help="졸업 학점 (시뮬레이션 기본값)")
    args = parser.parse_args()
    with SessionLocal() as session:
        try:
            institution, admin = bootstrap_admin(
                session, args.institution, args.country, args.email, args.name, args.tuition, args.degree
            )
        except CreditBridgeError as exc:
            print(f"만들지 못했어요: {exc}", file=sys.stderr)
            return 1
    print(f"기관: {institution.name}")
    print(f"관리자: {admin.email}")
    print(f"임시 비밀번호(한 번만 표시): {admin.temporary_password}")
    print("첫 로그인 때 새 비밀번호로 바꿔야 해요. 이후 계정·과목은 /admin/data 에서 가져오세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
