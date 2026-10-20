#!/bin/sh
# 웹 컨테이너 시작: DB 마이그레이션 → (로컬) 문서 버킷 준비 → (선택) 데모 데이터 → 서버 실행
set -e
uv run --no-group dev alembic upgrade head
# 로컬 S3 호환 저장소(S3_ENDPOINT_URL 지정)만 버킷을 만든다. 막 뜨는 중이면 잠시 기다렸다 다시 시도한다.
# AWS S3(운영)는 버킷을 콘솔에서 미리 만들고, 앱 권한(IAM 역할)에는 버킷 생성 권한을 주지 않는다
if [ -n "${S3_ENDPOINT_URL:-}" ]; then
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if uv run --no-group dev python -m scripts.create_bucket; then break; fi
    echo "waiting for object storage ($i)"; sleep 3
  done
fi
if [ "${SEED_DEMO:-false}" = "true" ]; then
  uv run --no-group dev python -m scripts.seed_demo
fi
exec uv run --no-group dev fastapi run backend/main.py --host 0.0.0.0 --port 8000
