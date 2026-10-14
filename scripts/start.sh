#!/bin/sh
# 웹 컨테이너 시작: DB 마이그레이션 → 문서 버킷 준비 → (선택) 데모 데이터 → 서버 실행
set -e
uv run --no-group dev alembic upgrade head
# 파일 저장소가 막 뜨는 중이면 잠시 기다렸다 다시 시도한다
for i in 1 2 3 4 5 6 7 8 9 10; do
  if uv run --no-group dev python -m scripts.create_bucket; then break; fi
  echo "waiting for object storage ($i)"; sleep 3
done
if [ "${SEED_DEMO:-false}" = "true" ]; then
  uv run --no-group dev python -m scripts.seed_demo
fi
exec uv run --no-group dev fastapi run app/main.py --host 0.0.0.0 --port 8000
