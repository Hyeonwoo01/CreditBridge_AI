# CreditBridge AI

강의계획서를 분석해 편입 대학의 어떤 과목으로 학점이 인정될지 **원문 근거와 함께 추천**하고, **학과 교수가 그 근거를 보고 최종 판정**하는 편입 학점 심사 플랫폼입니다. AI는 추천만 하고 확정 권한은 사람에게만 있습니다.

- 학생(이지원): 수강 신청 전에 과목별 예상 결과, 부족한 자료, 예상 인정 학점·남은 학기·추가 비용을 확인
- 심사관(레이첼): 신뢰도별 심사 큐, 학과 교수 자동 배정, 부재 시 대리 재배정, 판정 내보내기
- 학과 교수: 근거 구절 비교 화면에서 승인·수정·반려, 과거 판정과 다르면 확정 전 경보

기준 문서: [기획 통합본](docs/spec.md)(페르소나·테스트 명세·기술스택·기능 명세) · [구현 현황](docs/traceability.md) · [개인정보 처리](docs/privacy.md)

## AI가 판정을 추천하는 방식

1. **추출**: Claude가 강의계획서에서 학습 목표·주차별 주제·교재·선수과목·평가 방식·학점과 학문 분야를 정형 스키마로 뽑습니다. 원문에 없는 값은 비워 둡니다. 같은 문서(내용 해시가 같은 파일)는 다시 분석하지 않고 저장된 결과를 씁니다.
2. **후보 선정**: 추출한 학문 분야로 대상 대학 카탈로그를 학과 단위로 걸러 최대 30개 과목을 후보로 고릅니다. MVP는 임베딩·벡터 검색을 쓰지 않습니다.
3. **개념별 판단**: Claude가 후보 과목의 필수 개념마다 실제로 가르쳤는지(다룸/부분/없음/판단 불가), 수준이 같은지 판단하고 양쪽 원문 구절을 인용합니다.
4. **근거 검증**: 인용 구절이 원문에 그대로 있는지 코드로 확인하고, 없으면 버립니다. 근거 없이 매긴 커버리지는 40%를 넘지 못합니다.
5. **추천 계산**: 개념 커버리지, 추천 등급(직접 인정/선택 인정/불인정, 근거가 모자라면 정보 부족), 신뢰도(상·중·하)를 `app/services/scoring.py`의 고정 규칙으로 계산합니다. 판정 확률(%)은 MVP에서 계산하지 않습니다. 같은 입력은 저장된 결과를 재사용해 반복 실행해도 결과가 같습니다.

교수는 승인·수정·반려할 수 있고, 반려하거나 AI 추천과 다르게 판정할 때는 선택형 사유(주차 범위 부족·수준 차이·실험 미포함·선수과목 차이·기타)를 고릅니다. '기타'만 메모가 필수입니다. 같은 출신 과목·같은 대상 과목을 두고 내용이 거의 같은 강의계획서(유사도 80% 이상)에 다른 결과가 나와 있으면 확정 전에 경보를 띄웁니다. 강의계획서가 개편됐으면 이력은 보여 주되 경보는 띄우지 않습니다.

## 실행

사전 설치: Docker, [uv](https://docs.astral.sh/uv/)

```bash
uv sync                                   # Python 3.12와 의존성 설치
cp .env.example .env                      # ANTHROPIC_API_KEY, CLAUDE_MODEL 입력
docker compose up -d db redis minio       # MariaDB 11.8, Redis 7, MinIO
uv run alembic upgrade head
uv run python -m scripts.create_bucket
uv run python -m scripts.seed_demo        # 데모 카탈로그·계정
uv run fastapi dev app/main.py            # http://localhost:8000
uv run celery -A app.workers.celery_app worker --loglevel=info   # 별도 터미널
```

데모 계정 (비밀번호 모두 `demo1234`, 로컬 전용)

| 역할 | 이메일 |
| --- | --- |
| 학생 | jiwon@student.example |
| 심사관 | rachel@msu.example |
| 수학과 교수 | dkim@msu.example, lchen@msu.example |
| CS 교수 | oali@msu.example, spark@msu.example |
| 관리자 | admin@msu.example |

`scripts/demo_data/`에 페르소나의 강의계획서 PDF(미적분학, 선형대수 상세형·부실형, C프로그래밍, 자료구조, 일반물리, 일반화학, 한국사)가 있습니다. 작년에 같은 선형대수가 직접 인정된 이력도 시드되어 있어 일관성 경보를 시연할 수 있습니다.

## 품질 검사

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy app
uv run pytest tests/unit tests/integration   # 통합 테스트는 MariaDB 필요 (TEST_DATABASE_URL, 기본 creditbridge_test)
uv run pytest tests/eval -m eval             # 골든셋 평가: 실제 Claude API 호출, 비용 발생
```

테스트에서는 Claude·S3를 대역(`tests/fakes.py`)으로 바꿉니다. 대역 Claude는 일부러 원문에 없는 구절을 섞어 내보내고, 테스트는 그 구절이 저장되지 않는지 확인합니다.

## 구조

```
app/
  ai/            llm_client.py(SDK 단일 진입점) · prompts/*.md · extraction · candidates · matching · evidence · injection
  documents/     PyMuPDF 텍스트 추출(PDF·JPG·PNG), S3 저장
  services/      analysis(파이프라인) · scoring(추천 규칙) · student · review · decisions · views
  repositories/  SQL은 여기만
  models/        SQLAlchemy 2.0, 테이블당 1파일
  workers/       Celery 작업
  security/      세션·권한·CSRF·개인정보 마스킹
  web/           라우트, JSON API, Jinja2 + HTMX 템플릿, Tailwind
alembic/         마이그레이션 (MySQL 8.0 호환 문법만)
tests/           unit · integration(MariaDB) · eval(골든셋)
```

화면 CSS는 `app/web/static/css/input.css`에서 Tailwind standalone CLI로 빌드합니다(`scripts/build_css.sh`). 빌드된 `app.css`가 커밋되어 있어 CLI 없이도 실행됩니다.

## 운영 시 확인할 것

- `decisions`, `audit_logs`는 추가 전용입니다. 앱 DB 계정 권한은 [docs/db-grants.sql](docs/db-grants.sql)을 따르세요.
- 운영 S3는 `S3_SERVER_SIDE_ENCRYPTION=AES256`(또는 `aws:kms`)으로 저장 암호화를 켜세요.
- 예상 인정 학점·추가 비용은 AI 추천을 기준으로 한 예상치입니다. 화면에도 "예상치"로 표시합니다.
- 일관성 경보의 유사도 기준(`SIMILARITY_MIN = 0.80`)은 첫 측정 후 확정하는 임시값입니다.
