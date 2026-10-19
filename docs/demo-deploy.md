# 예시용 공개 데모 배포 (Render · Hugging Face Spaces)

CreditBridge AI를 **예시용으로만** 공개 주소에 올리는 방법입니다. 실제 학생 자료를 다루는 운영 배포는 저장소 루트의 `Dockerfile`·`docker-compose.yml`과 README "운영 시 확인할 것"을 따르세요.

## 데모 모드가 하는 일

컨테이너 하나(`deploy/demo/Dockerfile`)에 앱과 MariaDB를 함께 띄우고, 환경변수 `DEMO_MODE=true`로 아래처럼 동작합니다.

| 항목 | 데모 모드 | 운영 |
| --- | --- | --- |
| AI 분석 | 예시 AI(`backend/ai/demo_llm.py`): Claude를 부르지 않고 강의계획서의 "Week N:" 줄과 기준 개념의 낱말 겹침으로 결과를 만든다. 비용 없음 | Claude API (`ANTHROPIC_API_KEY`) |
| 파일 저장 | 컨테이너 안 폴더(`DEMO_STORAGE_DIR`, `DiskStorage`) | S3 |
| 작업 큐 | 요청 안에서 바로 실행(`CELERY_TASK_ALWAYS_EAGER=true`), Redis·worker·beat 없음 | Celery + Redis |
| DB | 컨테이너 안 MariaDB 11.8, 시작할 때마다 새로 만듦 | 별도 MariaDB |
| 데이터 | 시작할 때 데모 계정·카탈로그(`scripts/seed_demo.py`)와 예시 시나리오(`scripts/demo_scenario.py`)를 넣음. **다시 시작하면 처음 상태로 돌아감** | 보존 |
| 화면 | 모든 화면 위에 "예시용 공개 데모" 안내, 로그인 화면에 데모 계정 4개 바로 로그인 버튼 | 없음 |
| 막는 동작 | 비밀번호 변경·관리자 비밀번호 초기화·계정 비활성화. 로그인 실패는 5번마다 1분 잠금만(비밀번호 무효화 없음) | 정상 동작 |
| 메일 | 보내지 않음 | SMTP 설정 시 발송 |

예시 시나리오: 학생 이지원의 심사 요청 1건(미적분 승인, 선형대수 보완 자료 요청, 자료구조 선택 인정 → 이의 신청, 일반물리는 Mike Brown 교수가 판정할 차례, 한국사)과 사전 시뮬레이션 초안 1건.

## Render에 올리기 (추천, 무료)

저장소 루트의 `render.yaml`(Blueprint)이 설정을 담고 있어 버튼 몇 번이면 된다. 무료(Free) 웹 서비스로 띄운다(가입·결제 정보 요구 여부는 Render 정책을 따른다).

1. https://render.com 에 **GitHub 계정으로 가입**한다(Sign up with GitHub).
2. 대시보드 오른쪽 위 **New → Blueprint**를 누른다.
3. **Connect a repository**에서 `Hyeonwoo01/CreditBridge_AI`를 고른다. 목록에 없으면 "Configure GitHub App"에서 이 저장소 접근을 허용한다(비공개 저장소도 된다).
4. Blueprint 이름을 적고(예: `creditbridge-demo`) **Deploy Blueprint**(또는 Apply)를 누른다. `render.yaml`에 적힌 대로 무료(Free) Docker 웹 서비스 `creditbridge-demo`가 만들어진다.
5. 서비스 화면의 **Logs**에서 빌드가 진행된다(처음 5~10분). `demo scenario ready`와 `Uvicorn running` 이 보이고 상태가 **Live**가 되면 화면 위쪽 `https://creditbridge-demo-xxxx.onrender.com` 주소로 열린다.

고친 뒤 다시 올리기: 변경을 main에 push한 다음 Render 서비스 화면에서 **Manual Deploy → Deploy latest commit**을 누른다(`autoDeploy: false`라 push만으로는 다시 빌드하지 않는다).

Render 무료 웹 서비스 참고:
- 15분 동안 접속이 없으면 잠든다. 다시 열면 깨어나는 데 1분 안팎 걸리고, 이때 데이터가 처음 상태로 돌아간다.
- 메모리 512MB. 데모 컨테이너는 MariaDB를 작게 띄워 250MB 안팎을 쓴다(512MB 제한으로 확인함).
- 무료 사용 시간은 한 달 단위로 정해져 있다. 데모 하나는 보통 넉넉하다.

## Hugging Face Spaces에 올리기 (대안)

같은 컨테이너를 Docker Space로도 올릴 수 있다. 다만 2026년 10월 현재 새 무료 계정에서 "cpu-basic quota limit"(403)로 Space가 켜지지 않는 사례가 많아 Render를 먼저 권한다.

1. Space를 만든다(SDK는 Docker 또는 아무거나 — 올리는 `README.md`의 `sdk: docker`가 Docker로 바꾼다).
2. 올릴 폴더를 만든다: `sh deploy/demo/prepare_space.sh` (Windows PowerShell은 저장소를 `git clone -c core.autocrlf=false`로 받은 뒤 `deploy\demo\Dockerfile`을 루트 `Dockerfile`로, `deploy\demo\SPACE_README.md`를 `README.md`로 복사)
3. Write 토큰으로 로그인하고 올린다.

   ```bash
   uvx --python 3.12 --from huggingface_hub hf auth login
   uvx --python 3.12 --from huggingface_hub hf upload <아이디>/<Space이름> <폴더> . --repo-type=space
   ```

## 알아 둘 점

- 공개 주소에 데모 계정(비밀번호 `demo1234`)이 열려 있다. 실제 학생 자료·개인정보는 올리지 않는다.
- 예시 AI는 실제 판단이 아니다. 새로 올린 강의계획서도 예시 규칙으로 결과가 나온다.
- 로컬에서 미리 확인: `docker build -f deploy/demo/Dockerfile -t creditbridge-demo . && docker run --rm -p 7860:7860 creditbridge-demo` → http://localhost:7860
- 운영 환경에서는 `DEMO_MODE`를 켜지 않는다(기본값 false).
