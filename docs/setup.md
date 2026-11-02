# 실행·배포 자세히

README의 [실행](../README.md#실행)에서 옮긴 내용이에요. 빠른 시작과 데모 계정은 README에 있어요.

## 가장 쉬운 방법: Docker로 한 번에 (내 컴퓨터에서만 접속)

사전 설치: [Docker Desktop](https://www.docker.com/products/docker-desktop/), Git

Docker Desktop을 먼저 실행하고, 창 왼쪽 아래에 **Engine running**이 보일 때까지 기다린 뒤 터미널(Windows는 PowerShell)에서 한 줄씩 실행합니다.

```bash
git clone https://github.com/Hyeonwoo01/CreditBridge_AI.git
cd CreditBridge_AI
cp .env.example .env                      # (선택) Windows PowerShell: copy .env.example .env
# .env에 ANTHROPIC_API_KEY만 넣으면 실제 AI 분석(CLAUDE_MODEL은 예시 값이 들어 있음. GPT는 LLM_PROVIDER=openai, OPENAI_API_KEY, OPENAI_MODEL). .env가 없어도 실행은 되고, AI 분석만 "AI 분석 설정(API 키)이 아직 없어 분석하지 못했어요"로 실패 표시
docker compose up -d --build              # 프론트엔드·백엔드·DB·작업 큐·파일 저장소를 한 번에
```

`docker-compose.yml` 하나에 서비스 6개가 들어 있습니다: `web`(FastAPI 백엔드가 `frontend/` 화면까지 함께 그려 보냄, :8000), `worker`(AI 분석 등 오래 걸리는 작업), `beat`(매일 기한 알림), `db`(PostgreSQL 17), `redis`(작업 큐), `s3`(파일 저장소). 모두 `restart: unless-stopped`라 PC를 다시 켜도 Docker Desktop만 실행하면 직접 끄지 않은 서비스는 다시 켜집니다.

처음에는 이미지 내려받기와 빌드에 몇 분 걸립니다. DB(PostgreSQL 17)는 볼륨이 비어 있을 때 `db/init.sql`(테이블)과 `db/data.sql`(데모 계정·과목 초기 데이터)로 한 번 초기화되고, 웹 컨테이너가 시작하면서 문서 버킷을 만듭니다.
브라우저에서 http://localhost:8000 을 엽니다. 모든 포트를 127.0.0.1에만 열어 같은 네트워크의 다른 기기에서는 접속할 수 없습니다.

- 로그인: 아래 [데모 계정](../README.md#데모-계정) 중 하나로 들어갑니다(비밀번호 `demo1234`).
- 끄기: `docker compose down` (데이터는 남음, 모두 지우려면 `down -v`)
- 다시 켜기: Docker Desktop을 켜면 자동으로 다시 켜짐(`docker compose down`으로 끈 뒤에는 `docker compose up -d`) / 코드를 새로 받은 뒤(`git pull`)에는 `docker compose up -d --build`
- 예전 명령 `docker compose --profile app ...`도 그대로 동작합니다(이제 프로필 없이 전부 뜸).
- 상태·로그 보기: `docker compose ps`, `docker compose logs -f web worker`
- 파일 저장소는 S3 호환 SeaweedFS 컨테이너(`s3`)를 씁니다. 운영에서는 AWS S3로 바꿉니다.

### 내 이메일로 계정 만들기

회원가입 화면은 없습니다. 기관 관리자가 명단으로 계정을 만들어 주는 방식입니다.

1. 관리자(`admin@msu.example`)로 로그인 → **계정·과목** → **③ 계정 CSV**에서 "예시 파일 받기"
2. `email,name,role,department,source_institution` 형식으로 적고 엑셀에서 "다른 이름으로 저장 → CSV UTF-8"로 저장 (role은 student·evaluator·professor·admin, 교수는 과목에 있는 학과명 필수, 학생은 department에 편입 전공·source_institution에 출신 대학)
3. 올리면 새 계정마다 임시 비밀번호가 화면에 한 번만 나옵니다. 그 비밀번호로 로그인하면 새 비밀번호로 바꾸는 화면이 먼저 나옵니다.

메일 발송(`SMTP_HOST`)을 설정하지 않았으면 메일은 보내지 않으므로 실제로 없는 주소여도 됩니다. 이미 만든 계정의 이메일은 바꿀 수 없고(교직원은 이름·학과, 학생은 편입 전공·출신 대학만 수정), 바꾸려면 새 계정을 만들고 이전 계정을 비활성화합니다.

### 막힐 때

| 증상 | 원인과 해결 |
| --- | --- |
| `failed to connect to the docker API ... dockerDesktopLinuxEngine` | Docker Desktop이 꺼져 있습니다. 실행하고 Engine running이 보이면 다시 실행하세요. `docker info`에 `Server:` 정보가 나오면 준비된 것입니다 |
| `fatal: not a git repository`, `no configuration file provided` | 저장소 폴더 밖에서 실행했습니다. `cd CreditBridge_AI`로 들어가서 실행하세요 |
| 브라우저에 "localhost 연결을 거부했습니다" | 아직 빌드·시작 중이거나 웹 컨테이너가 멈췄습니다. `up` 명령이 끝날 때까지 기다린 뒤 `docker compose ps`로 `web`이 실행 중인지 보고, 아니면 `docker compose logs web --tail 40`으로 오류를 확인하세요 |
| 예전(MariaDB) 버전으로 띄운 적이 있고 DB가 시작되지 않음 | 이전 DB 볼륨이 남아 있습니다. `docker compose down -v`로 지우고 다시 `up -d --build` 하세요 (데이터도 지워짐) |
| WSL 관련 오류로 Docker Desktop이 켜지지 않음 | 관리자 PowerShell에서 `wsl --update` 후 Docker Desktop을 다시 실행하세요 |
| "AI 분석 중"이 몇 분 넘게 그대로 | 서버를 다시 띄운 직후라면 작업이 대기열로 돌아가 곧 다시 처리됩니다(최대 15분). 8분이 넘는 분석은 "너무 오래 걸려 멈췄어요"로 바뀌고, 같은 파일을 다시 올리면 다시 분석합니다. `docker compose logs --tail 40 worker`로 오류를 확인하세요 |
| 강의계획서를 올리면 "AI 분석 설정(API 키)이 아직 없어 분석하지 못했어요" | `.env`에 쓰는 AI의 키·모델이 없습니다. Claude면 `ANTHROPIC_API_KEY`·`CLAUDE_MODEL`, GPT면 `LLM_PROVIDER=openai`와 `OPENAI_API_KEY`·`OPENAI_MODEL`을 넣고 `docker compose up -d`를 다시 실행하세요 |
| 학생으로 로그인하면 "내 성적표" 화면만 나옴 | 정상이에요. 학생은 성적표를 먼저 올려야 해요(데모는 `scripts/demo_data/transcript.pdf`). 올리면 내 편입 요청으로 넘어가요 |
| 성적표를 올렸는데 과목 카드가 안 생김 | ① 내 성적표 화면이 "읽지 못함"이면 AI 설정(API 키)·파일 상태를 확인하고 다시 올리세요. ② 학생 계정에 출신 대학·편입 전공이 없으면 요청을 만들 수 없어요. 관리자가 계정 목록에서 정한 뒤 성적표를 다시 올리세요. ③ 성적이 모두 C 미만이면 만들 과목이 없어요 |
| 파일(강의계획서·기준 강의계획서)을 올리면 `Internal Server Error` | 파일 저장소 키가 비어 있던 예전 설정입니다. `git pull` 후 `docker compose up -d`를 다시 실행하세요 (지금은 `.env`에 `S3_ACCESS_KEY`가 없어도 기본값으로 동작) |

## 실제 서비스로 올리기 (AWS 프리티어)

EC2 한 대(docker compose + Caddy https) + RDS PostgreSQL 17 + S3로 실제 AI 분석(Claude 또는 GPT)을 쓰는 사이트를 띄워요. `docker-compose.prod.yml`과 `deploy/aws/`를 쓰고, AWS 콘솔에서 누를 순서와 프리티어 설정은 [docs/deploy-aws.md](deploy-aws.md)에 있어요.

## 예시용 공개 데모로 올리기 (Render 무료)

지금 운영 중인 공개 데모는 없어요. 필요할 때 아래 방법으로 다시 올릴 수 있어요.

컨테이너 하나에 앱과 PostgreSQL을 넣고 예시 AI(실제 AI API 미사용, 비용 없음)로 돌리는 데모 모드(`DEMO_MODE=true`)가 있어요. Render 무료 웹 서비스에 올리면(`render.yaml`) 누구나 데모 계정 버튼으로 둘러볼 수 있고, 다시 시작하면 처음 상태로 돌아가요. 방법은 [docs/demo-deploy.md](demo-deploy.md).

## 개발용: 인프라만 Docker, 앱은 uv로

사전 설치: Docker, [uv](https://docs.astral.sh/uv/)

```bash
uv sync                                   # Python 3.12와 의존성 설치
cp .env.example .env                      # ANTHROPIC_API_KEY 입력(CLAUDE_MODEL은 예시 값 있음. GPT면 LLM_PROVIDER=openai, OPENAI_API_KEY, OPENAI_MODEL)
docker compose up -d db redis s3          # PostgreSQL 17(db/init.sql·data.sql로 초기화), Redis 7, S3 호환 저장소(SeaweedFS)
uv run alembic upgrade head               # init.sql로 이미 최신이면 아무것도 안 함
uv run python -m scripts.create_bucket
uv run python -m scripts.seed_demo        # 데모 카탈로그·계정 (data.sql로 이미 있으면 건너뜀)
uv run fastapi dev backend/main.py        # http://localhost:8000
uv run celery -A backend.workers.celery_app worker --loglevel=info   # 별도 터미널 (Windows는 --pool=solo 추가)
uv run celery -A backend.workers.celery_app beat --loglevel=info     # 별도 터미널: 매일 기한 알림 (하나만 띄움)
```
