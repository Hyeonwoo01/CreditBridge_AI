# CreditBridge AI

강의계획서를 분석해 편입 대학의 어떤 과목으로 학점이 인정될지 **원문 근거와 함께 추천**하고, **학과 교수가 그 근거를 보고 최종 판정**하는 편입 학점 심사 플랫폼입니다. AI는 추천만 하고 확정 권한은 사람에게만 있습니다.

- 학생(이지원): 홈 대시보드에서 요청별 예상 인정 학점·서류 준비율·할 일(메뉴에 채워야 할 서류·새 결과 배지), 편입 학점 시뮬레이션 리포트에서 예상 인정 학점·남은 학기·추가 비용, 과목별 결과(승인 완료·보완 필요·심사 중), 부족한 자료, 심사 진행 단계를 확인, 같은 대학 선배들의 과목별 인정 사례 검색, 근거 자료를 첨부한 이의 신청
- 심사관(레이첼): 검색·필터가 있는 심사 대기열, 일관성 경보 미리 보기, 학과 교수 일괄 배정, 부재 시 대리 재배정, 판정 내보내기
- 학과 교수: 근거 구절 비교 화면에서 승인·수정·반려, 반려하거나 추천과 다르게 판정하면 사유 선택 창에서 사유·소명 입력, 과거 판정과 다르면 확정 전 경보, 보완 자료 요청, 이의 신청 재판정
- 기관 관리자: 관리자 콘솔(AI 추천 수용률·학과별 처리 지표·최근 감사 로그·보존 정책), 계정·과목 CSV 가져오기와 기준 강의계획서 등록, 문서 삭제 승인, 학사정보시스템 연동 토큰, 전체 감사 로그

심사 중에 필요한 일도 앱 안에서 처리합니다: 심사관·교수의 보완 자료 요청과 학생 제출, 학생 이의 신청과 재판정, 기한이 있는 문서 삭제 요청, 화면·메일 알림, 기존 동등 과목표(CSV) 가져오기, 확정 판정 CSV·API 내보내기(`GET /api/sis/decisions`).

기준 문서: [개발 규칙](CLAUDE.md) · [기획 통합본](docs/spec.md)(페르소나·테스트 명세·기술스택·기능 명세) · [화면 디자인](docs/DESIGN.md) · [구현 현황·화면별 기능](docs/traceability.md) · [개인정보 처리](docs/privacy.md)

## AI가 판정을 추천하는 방식

1. **추출**: Claude가 강의계획서에서 학습 목표·주차별 주제·교재·선수과목·평가 방식·학점과 학문 분야를 정형 스키마로 뽑습니다. 원문에 없는 값은 비워 둡니다. 같은 문서(내용 해시가 같은 파일)는 다시 분석하지 않고 저장된 결과를 씁니다.
2. **후보 선정**: 추출한 학문 분야로 대상 대학 카탈로그를 학과 단위로 걸러 최대 30개 과목을 후보로 고릅니다. MVP는 임베딩·벡터 검색을 쓰지 않습니다.
3. **개념별 판단**: Claude가 후보 과목의 필수 개념마다 실제로 가르쳤는지(다룸/부분/없음/판단 불가), 수준이 같은지 판단하고 양쪽 원문 구절을 인용합니다.
4. **근거 검증**: 인용 구절이 원문에 그대로 있는지 코드로 확인하고, 없으면 버립니다. 근거 없이 매긴 커버리지는 40%를 넘지 못합니다.
5. **추천 계산**: 개념 커버리지, 추천 등급(직접 인정/선택 인정/불인정, 근거가 모자라면 정보 부족), 신뢰도(상·중·하)를 `backend/services/scoring.py`의 고정 규칙으로 계산합니다. 판정 확률(%)은 MVP에서 계산하지 않습니다. 같은 입력은 저장된 결과를 재사용해 반복 실행해도 결과가 같습니다.

교수는 승인·수정·반려할 수 있고, 반려하거나 AI 추천과 다르게 판정할 때는 확정 전에 열리는 사유 선택 창에서 선택형 사유(주차 범위 부족·수준 차이·실험·실습 미포함·선수과목 차이·기타)를 고릅니다. '기타'만 메모(최대 500자)가 필수입니다. 같은 출신 과목·같은 대상 과목을 두고 내용이 거의 같은 강의계획서(유사도 80% 이상)에 다른 결과가 나와 있으면 확정 전에 경보를 띄웁니다. 강의계획서가 개편됐으면 이력은 보여 주되 경보는 띄우지 않습니다.

## 주요 화면

| 화면 | 주소 | 누가 | 내용 |
| --- | --- | --- | --- |
| 편입 학점 시뮬레이션 리포트 | `/student/requests/{id}` | 학생 | "예상 인정 학점: 낮음~높음 / 이수 학점" 요약, 남은 학기·추가 비용·심사 진행 카드, 과목 필터, 정보 부족 진단과 보완 서류 제출, 심사 진행 4단계 |
| 심사 대기열 | `/review` | 심사관 | 지표 카드, 이름·과목·출신 대학 검색, 신뢰도·일관성 경보·학과 필터, 커버리지 게이지, 경보 행, 행 선택 후 교수 일괄 배정, SIS CSV 내보내기 |
| 판정 화면 | `/professor/evaluations/{id}` | 학과 교수 | 좌우 근거 구절 비교, 과거 판정 이력, 하단 고정 판정 바, 불인정·판정 변경 사유 선택 창 |
| 계정·과목 관리 | `/admin/data` | 기관 관리자 | 과목 CSV(필수 개념 포함)·계정 CSV 가져오기, 새 계정 임시 비밀번호(한 번만 표시), 과목별 기준 강의계획서 올리기, 출신 대학 등록 |
| 관리자 콘솔 | `/admin/stats` | 기관 관리자 | AI 추천 수용률, 개인정보 보호·SIS 연동 상태, 학과별 처리 지표, 최근 감사 로그, 데이터 보존 및 파기 정책 (심사관은 `/review/stats`에서 감사 로그를 뺀 운영 통계) |

- 화면은 [DESIGN.md](docs/DESIGN.md)(단일 Action Blue, 1px 헤어라인, 그림자 없음)를 따릅니다. 폭은 기본 1280px이고, 정보가 많은 심사 대기열과 원문 대조 화면만 1440px입니다.
- 화면에 판정 확률(%)은 없습니다. 커버리지, 3단계 추천, 신뢰도만 보여 줍니다. 교수·관리자 화면에는 학생 이름이 나오지 않습니다.
- 모든 화면 아래에 "AI 분석 결과는 참고 자료이며 최종 인정은 학과 교수 승인으로 확정된다"는 Human-in-the-Loop 고지가 있습니다.

## 실행

### 가장 쉬운 방법: Docker로 한 번에 (내 컴퓨터에서만 접속)

사전 설치: [Docker Desktop](https://www.docker.com/products/docker-desktop/), Git

```bash
git clone https://github.com/Hyeonwoo01/CreditBridge_AI.git
cd CreditBridge_AI
cp .env.example .env                      # Windows PowerShell: copy .env.example .env
# .env를 열어 ANTHROPIC_API_KEY에 Claude API 키를 넣는다 (없으면 화면은 열리지만 AI 분석이 실패함)
docker compose --profile app up -d --build
```

처음에는 이미지 내려받기와 빌드에 몇 분 걸립니다. 웹 컨테이너가 시작하면서 DB 테이블, 문서 버킷, 데모 계정을 자동으로 만듭니다.
브라우저에서 http://localhost:8000 을 엽니다. 모든 포트를 127.0.0.1에만 열어 같은 네트워크의 다른 기기에서는 접속할 수 없습니다.

- 끄기: `docker compose --profile app down` (데이터는 남음, 모두 지우려면 `down -v`)
- 로그 보기: `docker compose --profile app logs -f web worker`

### 개발용: 인프라만 Docker, 앱은 uv로

사전 설치: Docker, [uv](https://docs.astral.sh/uv/)

```bash
uv sync                                   # Python 3.12와 의존성 설치
cp .env.example .env                      # ANTHROPIC_API_KEY, CLAUDE_MODEL 입력
docker compose up -d db redis minio       # MariaDB 11.8, Redis 7, MinIO
uv run alembic upgrade head
uv run python -m scripts.create_bucket
uv run python -m scripts.seed_demo        # 데모 카탈로그·계정
uv run fastapi dev backend/main.py        # http://localhost:8000
uv run celery -A backend.workers.celery_app worker --loglevel=info   # 별도 터미널 (Windows는 --pool=solo 추가)
```

데모 계정 (비밀번호 모두 `demo1234`, 로컬 전용)

| 역할 | 이메일 |
| --- | --- |
| 학생 | jiwon@student.example |
| 심사관 | rachel@msu.example |
| 수학과 교수 | dkim@msu.example, lchen@msu.example |
| CS 교수 | oali@msu.example, spark@msu.example |
| 관리자 | admin@msu.example |
| 물리·화학·영어·역사 교수 | mbrown@msu.example, ewong@msu.example, alopez@msu.example, jreed@msu.example, twhite@msu.example |

로그인하면 역할별 첫 화면으로 갑니다: 학생은 내 편입 요청 목록(요청을 누르면 시뮬레이션 리포트), 심사관은 심사 대기열, 교수(예: mbrown)는 배정된 심사, 관리자는 관리자 콘솔입니다.

`scripts/demo_data/`에 페르소나의 강의계획서 PDF(미적분학, 선형대수 상세형·부실형, C프로그래밍, 자료구조, 일반물리, 일반화학, 한국사)가 있습니다. 작년에 같은 선형대수가 직접 인정된 이력도 시드되어 있어 일관성 경보를 시연할 수 있습니다.

## 개발 규칙 (CLAUDE.md)

코드를 고치기 전에 [CLAUDE.md](CLAUDE.md)를 먼저 읽어 주세요. 사람과 Claude Code가 함께 따르는 규칙이며, Claude Code는 이 파일을 자동으로 읽습니다. 핵심만 옮기면:

- **고정 스택**: Python 3.12·uv, FastAPI(`def` 엔드포인트), Pydantic 2, SQLAlchemy 2.0, MariaDB + PyMySQL, Alembic, Celery + Redis, Anthropic 공식 SDK, PyMuPDF, Jinja2 + HTMX + Tailwind. 목록 밖 라이브러리는 추가하기 전에 먼저 물어봅니다.
- **구조**: web → services → repositories → models. SQL은 `backend/repositories`에만, LLM 호출은 `backend/ai/llm_client.py`로만, 프롬프트는 `backend/ai/prompts/*.md`(바꾸면 버전 올림), 추천 규칙은 `backend/services/scoring.py` 한 곳(바꾸면 `RULES_VERSION` 올림).
- **사람이 최종 판정**: AI는 추천만 합니다. 판정 확률(%)은 계산·표시하지 않고, 확정 판정에는 `decided_by`가 필수이며, `decisions`·`audit_logs`는 INSERT만 합니다(재판정도 새 행).
- **개인정보·보안**: 로그·예외·알림에 이름·학번·성적을 쓰지 않습니다. 문서 안 지시 문구는 데이터로만 다루고, 상태를 바꾸는 POST는 CSRF 토큰을 검증합니다.
- **작업 완료 전**: 아래 품질 검사를 모두 통과시키고, 스키마를 바꾸면 Alembic 마이그레이션을, 새 Tailwind 클래스를 쓰면 `app.css` 재빌드를 함께 커밋합니다.

## 실제 데이터로 시작하기

데모 데이터 없이(`SEED_DEMO=false`) 실제 기관에서 쓸 때의 순서입니다.

1. **첫 관리자 만들기** (서버에서 한 번):
   ```bash
   uv run python -m scripts.create_admin --institution "대학 이름" --country KR \
       --email admin@univ.ac.kr --name "학사정보처 관리자" --tuition 1350 --degree 130
   # Docker: docker compose --profile app exec web uv run --no-group dev python -m scripts.create_admin ...
   ```
   임시 비밀번호가 한 번만 출력됩니다. 첫 로그인 때 새 비밀번호(10자 이상)로 바꿔야 다른 화면을 쓸 수 있습니다.
2. **과목 CSV** (`/admin/data`): `code,title,credits,department,level,concepts`. `concepts`는 학과가 정한 필수 개념을 `;`로 구분해 적습니다. 과목 코드가 이미 있으면 새 값으로 고칩니다.
3. **과목별 기준 강의계획서**: 같은 화면의 과목 목록에서 PDF·JPG·PNG를 올립니다. **기준 강의계획서가 없는 과목은 AI 비교 후보에서 빠집니다.**
4. **계정 CSV**: `email,name,role,department`. role은 student·evaluator·professor·admin(또는 학생·심사관·교수·관리자). 교수의 department는 과목 CSV의 학과명과 똑같아야 그 학과 과목이 배정됩니다. 메일 발송이 설정돼 있으면 새 계정마다 본인 메일로 비밀번호 설정 링크(72시간)를 자동으로 보내고, 없으면 임시 비밀번호를 만들어 가져온 직후 한 번만 보여 줍니다(CSV로 받기 가능, 저장하지 않음). 이미 있는 이메일은 건너뜁니다.
5. **출신 대학 등록**: 학생이 편입 요청을 만들 때 고르는 목록입니다.

비밀번호를 잊은 사용자는 로그인 화면의 "비밀번호를 잊으셨나요?"에서 메일로 재설정 링크(30분 동안, 한 번만 사용)를 받습니다. 관리자가 `/admin/data`의 "비밀번호 초기화"를 쓰면 사용자 메일로 설정 링크(72시간)가 자동으로 갑니다. 메일 발송(`SMTP_HOST`)이 설정되지 않은 서버에서는 대신 임시 비밀번호를 화면에 한 번만 보여 줍니다. **운영에서는 메일 발송을 설정하는 것을 권장합니다.** 그래야 관리자 없이 계정 만들기·비밀번호 찾기·잠금 해제가 모두 메일로 처리됩니다. 비밀번호가 바뀌면 다른 기기의 로그인은 끊깁니다.

비밀번호를 연속 5번 틀리면 1분 동안 로그인할 수 없고, 그 뒤로도 틀려 연속 10번이 되면 비밀번호가 초기화되어 메일로 받은 재설정 링크(메일 미설정 시 관리자 재발급)로만 새 비밀번호를 정할 수 있습니다. 관리자 화면에 이렇게 초기화된 계정 수가 표시됩니다.

CSV는 엑셀에서 "다른 이름으로 저장 → CSV UTF-8"로 저장합니다(한국어 엑셀 기본 CSV도 읽습니다). 한 줄이라도 틀리면 아무것도 저장하지 않고 틀린 행 번호와 이유를 보여 줍니다. 예시 파일은 화면의 "예시 파일 받기" 또는 `frontend/static/samples/`에 있습니다.

## 품질 검사

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy backend
uv run pytest tests/unit tests/integration   # 통합 테스트는 MariaDB 필요 (TEST_DATABASE_URL, 기본 creditbridge_test)
uv run pytest tests/eval -m eval             # 골든셋 평가: 실제 Claude API 호출, 비용 발생
```

테스트에서는 Claude·S3를 대역(`tests/fakes.py`)으로 바꿉니다. 대역 Claude는 일부러 원문에 없는 구절을 섞어 내보내고, 테스트는 그 구절이 저장되지 않는지 확인합니다.

## 구조

```
backend/         ← 백엔드 (Python, import 이름도 backend)
  main.py        FastAPI 앱, /static 마운트(frontend/static)
  ai/            llm_client.py(SDK 단일 진입점) · prompts/*.md · extraction · candidates · matching · evidence · injection
  documents/     PyMuPDF 텍스트 추출(PDF·JPG·PNG), S3 저장
  services/      analysis(파이프라인) · scoring(추천 규칙) · student · review(심사 대기열) · decisions(판정·경보)
                 materials · appeals · privacy · notifications · sis · equivalencies · stats(통계·관리자 콘솔) · views(화면 조회)
                 institution_data(계정·과목 CSV, 기준 강의계획서, 출신 대학, 첫 관리자) · csv_import(CSV 공통)
  repositories/  SQL은 여기만
  models/        SQLAlchemy 2.0, 테이블당 1파일
  workers/       Celery 작업
  security/      세션·권한·CSRF·개인정보 마스킹
  web/           라우트(routes/), JSON API(api/), 템플릿 렌더링(templating.py: frontend/templates 사용)
frontend/        ← 프론트엔드 (서버가 그려 보내는 화면 파일)
  templates/     Jinja2 + HTMX 템플릿: base · student · review · professor · admin · partials · stats · report
  static/        css/app.css(빌드 결과) · js/app.js · img/(로고·아이콘) · samples/(CSV 예시)
  tailwind/      input.css (DESIGN.md 토큰, Tailwind 4 입력)
alembic/         마이그레이션 (MySQL 8.0 호환 문법만)
scripts/         start.sh · build_css.sh · create_admin(첫 관리자) · seed_demo · create_bucket · demo_data/
tests/           unit · integration(MariaDB) · eval(골든셋)
```

백엔드와 프론트엔드는 폴더만 나뉘어 있고 하나의 앱으로 함께 실행됩니다. FastAPI가 `frontend/templates`로 HTML을 그려 보내고 `frontend/static`을 `/static`으로 내보냅니다.

화면 CSS는 `frontend/tailwind/input.css`(DESIGN.md 토큰)에서 Tailwind standalone CLI로 빌드합니다(`scripts/build_css.sh`). 빌드된 `frontend/static/css/app.css`가 커밋되어 있어 CLI 없이도 실행됩니다. 템플릿에 새 Tailwind 클래스를 쓰면 `scripts/build_css.sh`로 다시 빌드해 함께 커밋하세요.

## 운영 시 확인할 것

- 운영에서는 `SEED_DEMO=false`로 두세요. 데모 계정(비밀번호 `demo1234`)이 만들어지지 않게 합니다. 첫 관리자는 `scripts/create_admin.py`로 만듭니다.
- `decisions`, `audit_logs`는 추가 전용입니다. 앱 DB 계정 권한은 [docs/db-grants.sql](docs/db-grants.sql)을 따르세요.
- 운영 S3는 `S3_SERVER_SIDE_ENCRYPTION=AES256`(또는 `aws:kms`)으로 저장 암호화를 켜세요.
- 예상 인정 학점·추가 비용은 AI 추천을 기준으로 한 예상치입니다. 화면에도 "예상치"로 표시합니다.
- 알림 메일과 비밀번호 재설정 메일을 보내려면 `SMTP_HOST` 등과 `APP_BASE_URL`(메일 속 링크 주소)을 설정하세요. 비워 두면 화면 알림만 쓰고, 비밀번호는 관리자가 초기화합니다.
- `SESSION_SECRET`은 길고 무작위인 값으로 정하고 바꾸지 마세요. 바꾸면 모든 로그인과 아직 쓰지 않은 재설정 링크가 무효가 됩니다.
- 웹 서버 접근 로그는 쿼리 문자열을 지우고 경로만 남깁니다(심사 대기열 검색어에 학생 이름이 들어갈 수 있음). 앞에 리버스 프록시를 둘 때도 접근 로그에서 쿼리 문자열을 빼세요.
- 관리자 콘솔의 "데이터 보존 및 파기 정책" 카드는 [docs/privacy.md](docs/privacy.md)를 요약한 것입니다. 삭제 처리 기한은 `PRIVACY_DELETION_DAYS`(기본 30일)로 바꿉니다.
- 일관성 경보의 유사도 기준(`SIMILARITY_MIN = 0.80`)은 첫 측정 후 확정하는 임시값입니다.
