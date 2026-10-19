# 예시용 공개 데모 배포 (Hugging Face Spaces)

CreditBridge AI를 **예시용으로만** 공개 주소에 올리는 방법입니다. 실제 학생 자료를 다루는 운영 배포는 저장소 루트의 `Dockerfile`·`docker-compose.yml`과 README "운영 시 확인할 것"을 따르세요.

## 데모 모드가 하는 일

컨테이너 하나(`deploy/huggingface/Dockerfile`)에 앱과 MariaDB를 함께 띄우고, 환경변수 `DEMO_MODE=true`로 아래처럼 동작합니다.

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

## 올리기 (처음 한 번)

1. https://huggingface.co 에 가입하고 **New Space**를 만든다.
   - Space name: 예) `creditbridge-demo`
   - SDK: **Docker** → Blank
   - Hardware: 무료 CPU (CPU basic)
   - 공개(Public)로 두면 누구나 볼 수 있다
2. 쓰기 권한 토큰을 만든다: Settings → Access Tokens → New token(Write).
3. 저장소에서 Space에 올릴 폴더를 만든다 (지금 커밋된 내용 기준).

   ```bash
   sh deploy/huggingface/prepare_space.sh            # ../creditbridge-space 폴더가 생긴다
   ```

4. 올린다. 처음 한 번 `hf auth login`으로 2번의 토큰을 넣는다.

   ```bash
   uvx --from huggingface_hub hf auth login
   uvx --from huggingface_hub hf upload <허깅페이스아이디>/creditbridge-demo ../creditbridge-space . --repo-type=space
   ```

   `uvx`는 이 프로젝트 의존성에 추가하지 않고 Hugging Face 업로드 도구만 잠깐 실행한다. PDF·이미지 같은 파일도 이 도구가 알아서 올린다(웹 화면 끌어다 놓기로 올려도 된다).

5. Space 화면의 **Building** 이 끝나면(처음 5분 안팎) `https://<아이디>-creditbridge-demo.hf.space` 주소로 열린다.

## 고친 뒤 다시 올리기

변경을 커밋한 뒤 3·4번을 다시 하면 Space가 새로 빌드된다.

## 알아 둘 점

- 무료 Space는 한동안 접속이 없으면 잠든다. 다시 열면 깨어나는 데 몇 분 걸리고, 이때 데이터가 처음 상태로 돌아간다.
- 공개 주소에 데모 계정(비밀번호 `demo1234`)이 열려 있다. 실제 학생 자료·개인정보는 올리지 않는다.
- 예시 AI는 실제 판단이 아니다. 새로 올린 강의계획서도 예시 규칙으로 결과가 나온다.
- 로컬에서 미리 확인: `docker build -f deploy/huggingface/Dockerfile -t creditbridge-demo . && docker run --rm -p 7860:7860 creditbridge-demo` → http://localhost:7860
- 운영 환경에서는 `DEMO_MODE`를 켜지 않는다(기본값 false).
