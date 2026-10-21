# AWS 프리티어 배포 (EC2 한 대 + RDS + S3)

실제 AI 분석(Claude 또는 GPT, `LLM_PROVIDER`로 선택)을 쓰는 사이트를 AWS 프리티어 범위에서 띄우는 절차다. 예시용 공개 데모(Render, 예시 AI)는 [demo-deploy.md](demo-deploy.md).

```
사용자 ─https─▶ EC2 t3.micro (Ubuntu 24.04, docker compose)
                 ├ caddy   : https 인증서 자동 발급·갱신 → web으로 전달
                 ├ web     : FastAPI (화면 + API), 시작할 때 DB 마이그레이션
                 ├ worker  : Celery (AI 분석·메일·푸시, 매일 기한 알림 beat 포함)
                 └ redis   : 작업 큐
                 ├──▶ RDS PostgreSQL 17 (db.t4g.micro, 20GB, 외부 비공개)
                 └──▶ S3 버킷 (강의계획서·이의 신청 자료 원본, 비공개, SSE-S3 암호화)
```

사용하는 파일: `docker-compose.prod.yml`, `deploy/aws/Caddyfile`, `deploy/aws/env.example`, `deploy/aws/setup-ec2.sh`, `deploy/aws/s3-policy.json`.

## 프리티어 범위와 주의

- AWS 프리티어 조건은 계정 가입 시기에 따라 다르다. **2025년 7월 15일 이후 가입**한 계정은 "무료 플랜"(최대 6개월, 크레딧 제공)이고, 그 전 계정은 12개월 무료 사용량(EC2 t2·t3.micro 750시간, RDS db.t3·t4g.micro 750시간·20GB, S3 5GB 등)이다. 조건은 바뀔 수 있으니 **콘솔에서 고를 때 "프리 티어 사용 가능(Free tier eligible)" 표시가 있는 것만** 고른다.
- 이 구성은 그 표시가 붙는 가장 작은 사양만 쓴다: EC2 t3.micro 1대, EBS 20GB, RDS db.t4g.micro 단일 AZ 20GB, S3, 리전은 서울(ap-northeast-2).
- 무료가 아닌 것: **공인 IPv4 주소**(2024년부터 시간당 과금, 12개월 무료 계정은 월 750시간 무료·무료 플랜은 크레딧에서 차감), 프리티어 범위를 넘는 사용량, 그리고 **AI API 사용료**(AWS와 별도, Claude면 Anthropic·GPT면 OpenAI에 청구).
- ElastiCache·ALB·NAT 게이트웨이·Multi-AZ는 프리티어가 아니라 쓰지 않는다 (Redis는 EC2 안에서 돌린다).
- t3.micro는 메모리가 1GB라 스왑 2GB를 켜고 웹·작업 프로세스를 하나씩만 띄운다. 사용자가 몇 명이면 충분하지만, 동시에 여러 명이 분석을 돌리면 차례로 처리된다.

## 0. 비용 안전장치 (가장 먼저)

1. 오른쪽 위 리전을 **아시아 태평양(서울) ap-northeast-2**로 바꾼다. 아래 모든 리소스를 같은 리전에 만든다.
   - 새 무료 플랜 계정은 "프로젝트"가 한 리전에 고정될 수 있다 (예: 서울로 바꾸면 "리전 사용 불가 — 프로젝트가 시드니 ap-southeast-2에 할당됨"). 그때는 **"고급 기능 활성화"(유료 전환)를 누르지 말고 할당된 리전을 그대로 쓴다.** S3·EC2·RDS를 모두 그 리전에 만들고 `.env`의 `S3_REGION`을 그 리전 코드로 적는다. 이 문서의 "서울"은 그 리전으로 읽는다.
2. **Billing and Cost Management → Budgets → 예산 생성 → 템플릿 "제로 지출 예산(Zero spend budget)"**, 받을 이메일 입력. 1센트라도 청구되면 메일이 온다.

## 1. S3 버킷

1. **S3 → 버킷 만들기**
   - 이름: 전 세계에서 유일해야 한다 (예: `creditbridge-docs-<내이름>-2026`)
   - 리전: 서울
   - **모든 퍼블릭 액세스 차단**: 켠 그대로
   - 기본 암호화: SSE-S3 (기본값)
   - 버전 관리: 사용 안 함
2. 버킷 이름을 적어 둔다 (`.env`의 `S3_BUCKET`).

## 2. EC2용 IAM 역할 (S3 접근 키 없이 쓰기)

1. **IAM → 역할 → 역할 생성** → 신뢰할 엔터티: AWS 서비스, 사용 사례: **EC2** → 다음.
2. 권한 정책은 고르지 않고 다음 → 이름 `creditbridge-ec2` → 생성.
3. 만든 역할 → **권한 추가 → 인라인 정책 생성 → JSON**에 `deploy/aws/s3-policy.json` 내용을 붙여 넣고 `BUCKET_NAME` 두 곳을 1번 버킷 이름으로 바꾼다 → 이름 `creditbridge-s3` → 생성.
   (버킷 안 파일 읽기·쓰기·삭제와 목록만 허용한다. 버킷 생성·삭제 권한은 주지 않는다)

## 3. EC2 인스턴스

1. **EC2 → 인스턴스 시작**
   - 이름: `creditbridge`
   - AMI: **Ubuntu Server 24.04 LTS** (프리 티어 사용 가능), 아키텍처 64비트(x86)
   - 인스턴스 유형: **t3.micro** (프리 티어 사용 가능 표시 확인. 없으면 t2.micro)
   - 키 페어: 새로 만들기 (브라우저 접속만 쓸 거면 없어도 됨)
   - 네트워크 설정 → 보안 그룹 생성 (`creditbridge-web`):
     - SSH(22): 소스 **사용자 지정 → 접두사 목록 `com.amazonaws.<리전>.ec2-instance-connect`** (예: 시드니 `com.amazonaws.ap-southeast-2.ec2-instance-connect`). 브라우저의 EC2 Instance Connect는 AWS 주소에서 접속하므로 "내 IP"로 두면 연결이 안 되고, 0.0.0.0/0(전체 공개)은 피한다
     - HTTP(80): 위치 무관 0.0.0.0/0 (인증서 발급에 필요)
     - HTTPS(443): 위치 무관 0.0.0.0/0
   - 스토리지: **20 GiB gp3** (프리티어 30GB 안)
   - 고급 세부 정보:
     - IAM 인스턴스 프로파일: **creditbridge-ec2**
     - 메타데이터 버전: V2만(토큰 필요)
     - **메타데이터 응답 홉 제한: 2** ← 컨테이너 안의 앱이 IAM 역할로 S3에 접속하려면 필요하다
2. 시작 후 **EC2 → 탄력적 IP → 할당 → 이 인스턴스에 연결**. 인스턴스를 껐다 켜도 주소가 바뀌지 않는다 (공인 IPv4 과금 대상, 위 주의 참고).

## 4. RDS PostgreSQL

1. **RDS → 데이터베이스 생성**
   - 생성 방식: 표준 생성, 엔진: **PostgreSQL**, 버전: **17.x**
   - 템플릿: **프리 티어** (없으면 "샌드박스"/개발·테스트를 고르고 아래 값을 직접 맞춘다)
   - 배포 옵션: **단일 AZ**
   - DB 인스턴스 식별자: `creditbridge-db`
   - 마스터 사용자 이름: `creditbridge`, 비밀번호: 직접 입력 (영문·숫자로 길게, 적어 둔다)
   - 인스턴스 클래스: **db.t4g.micro** (또는 db.t3.micro)
   - 스토리지: gp2 또는 gp3 **20GiB**, **스토리지 자동 조정 끄기**
   - 연결: **EC2 컴퓨팅 리소스에 연결 → creditbridge 인스턴스 선택** (보안 그룹이 자동으로 EC2에서만 5432를 열게 만들어진다). 퍼블릭 액세스: **아니요**
   - 추가 구성 → **초기 데이터베이스 이름: `creditbridge`**
   - 자동 백업 보존 기간: **7일** (백업 저장 공간은 DB 크기까지 무료. 무료 플랜이 막으면 1일로 두고 매주 수동 스냅샷)
   - **삭제 방지 활성화** 체크 (실수로 DB를 지우지 않게)
   - 성능 개선 도우미·향상된 모니터링: 끄기
2. 생성(5~10분) 후 **연결 및 보안 → 엔드포인트**를 적어 둔다 (예: `creditbridge-db.xxxx.ap-northeast-2.rds.amazonaws.com`).

표는 만들지 않아도 된다. 앱이 처음 시작할 때 Alembic 마이그레이션으로 만든다.

## 5. 도메인 (https 인증서용)

Let's Encrypt 인증서는 IP가 아니라 도메인 이름에 발급된다.

- 도메인이 있으면: DNS에 **A 레코드 → 3번의 탄력적 IP**.
- 없으면 무료 서브도메인: https://www.duckdns.org 에 로그인 → 이름 하나 만들고(예: `creditbridge` → `creditbridge.duckdns.org`) current ip에 탄력적 IP를 넣고 update.

## 6. 서버 준비와 실행

1. **EC2 → 인스턴스 선택 → 연결 → EC2 Instance Connect → 연결** (브라우저 안 터미널. 키 파일이 있으면 `ssh -i key.pem ubuntu@<탄력적 IP>`도 된다)
2. 설치 스크립트 (Docker, 스왑 2GB, 저장소 받기):
   ```bash
   curl -fsSL https://raw.githubusercontent.com/Hyeonwoo01/CreditBridge_AI/main/deploy/aws/setup-ec2.sh | bash
   exit
   ```
   다시 연결한다 (docker 권한 적용).
3. 설정 파일 채우기:
   ```bash
   cd ~/CreditBridge_AI
   openssl rand -hex 32        # 나온 값을 SESSION_SECRET에
   nano .env
   ```
   | 항목 | 값 |
   | --- | --- |
   | `SITE_DOMAIN` | 5번 도메인 (예: `creditbridge.duckdns.org`) |
   | `APP_BASE_URL` | `https://` + 도메인 |
   | `DATABASE_URL` | `postgresql+psycopg://creditbridge:<RDS 비밀번호>@<RDS 엔드포인트>:5432/creditbridge?sslmode=require` |
   | `S3_BUCKET` | 1번 버킷 이름 (`S3_ACCESS_KEY`·`S3_SECRET_KEY`는 넣지 않는다) |
   | `ANTHROPIC_API_KEY`·`CLAUDE_MODEL` | Claude 키·모델 ID |
   | (GPT를 쓸 때) `LLM_PROVIDER=openai`, `OPENAI_API_KEY`·`OPENAI_MODEL` | GPT 키·모델 ID. 추론 모델이 아니면 `OPENAI_REASONING_EFFORT=false` |
   | `SESSION_SECRET` | 위에서 만든 값 (한 번 정하면 바꾸지 않는다) |

   저장: `Ctrl+O` → Enter → `Ctrl+X`.
4. 실행 (처음 빌드는 t3.micro에서 5~10분):
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   docker compose -f docker-compose.prod.yml logs -f web     # "Uvicorn running"이 보이면 Ctrl+C
   ```
5. 브라우저에서 `https://<도메인>/login`이 열리면 성공 (인증서 발급에 1~2분 걸릴 수 있다).

## 7. 첫 관리자 만들기

```bash
docker compose -f docker-compose.prod.yml exec web uv run --no-group dev python -m scripts.create_admin \
  --institution "NYU Stern" --country US --email admin@example.com --name "Stern Admin"
```

임시 비밀번호가 한 번만 나온다. 로그인 → 새 비밀번호로 바꾸기 → `/admin/data`에서 README "실제 데이터로 시작하기" 순서(과목 CSV → 기준 강의계획서 → 출신 대학 → 계정 CSV)로 넣는다. 데모 계정은 만들지 않는다(`SEED_DEMO=false`).

비밀번호를 잊을 때를 대비해 관리자를 하나 더 만들어 두면 서로 초기화할 수 있다.

## 8. 확인

- [ ] `https://<도메인>` 자물쇠 표시, `http://`로 들어가도 https로 바뀜
- [ ] 관리자 로그인, 과목 CSV·기준 강의계획서 업로드 → S3 버킷에 `references/...` 파일이 생김
- [ ] 학생 계정으로 강의계획서 업로드 → 분석 완료 (`docker compose -f docker-compose.prod.yml logs worker`에 오류 없음)
- [ ] 교수 판정 저장, 감사 로그에 기록
- [ ] 비용: Billing → 프리 티어 페이지에서 사용량 확인

## 운영

| 할 일 | 명령 (EC2, `~/CreditBridge_AI`) |
| --- | --- |
| 새 코드 반영 | `git pull && docker compose -f docker-compose.prod.yml up -d --build` (마이그레이션은 web 시작 때 자동) |
| 보안 업데이트 (한 달에 한 번) | `git pull && docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml build --pull && docker compose -f docker-compose.prod.yml up -d && docker image prune -f` (기반 이미지·Redis·Caddy를 새로 받음). 서버 OS는 `sudo apt update && sudo apt upgrade -y`, `/var/run/reboot-required`가 있으면 `sudo reboot` |
| 상태 | `docker compose -f docker-compose.prod.yml ps` / `docker stats --no-stream` (메모리) |
| 로그 | `docker compose -f docker-compose.prod.yml logs --tail 100 web` (`worker`, `caddy`) |
| 재시작 | `docker compose -f docker-compose.prod.yml restart` (EC2가 재부팅돼도 자동으로 다시 뜬다) |
| DB 백업 | RDS 자동 백업(7일) + 필요하면 RDS 콘솔에서 수동 스냅샷 (DB를 중지해 둔 동안은 자동 백업이 돌지 않는다) |
| 로그 | 컨테이너마다 10MB × 5개까지만 남는다(`docker-compose.prod.yml`의 `x-logging`) |

## 막힐 때

| 증상 | 원인·해결 |
| --- | --- |
| https가 안 열리고 caddy 로그에 인증서 오류 | 도메인이 탄력적 IP를 가리키는지(DuckDNS update), 보안 그룹에 80·443이 0.0.0.0/0으로 열려 있는지 확인 후 `restart caddy` |
| web 로그에 DB 연결 시간 초과 | RDS 보안 그룹이 EC2에서 5432를 허용하는지(4번 "EC2 컴퓨팅 리소스에 연결"), 엔드포인트·비밀번호 오타, `?sslmode=require` 확인 |
| 업로드하면 오류, 로그에 `NoCredentialsError`·`AccessDenied` | EC2에 IAM 역할 `creditbridge-ec2`가 붙었는지, **메타데이터 홉 제한이 2인지**(EC2 → 작업 → 인스턴스 설정 → 인스턴스 메타데이터 옵션 수정), 정책의 버킷 이름 확인 |
| "AI 분석 중"이 오래 그대로 | worker는 꺼질 때(`up -d`·`restart`) 하던 작업을 20초 마무리하고 못 끝낸 것은 대기열로 돌려놓는다. 서버가 갑자기 꺼진 경우는 15분 안에 다시 처리된다. 8분이 넘는 분석은 실패로 바뀌고 같은 파일을 다시 올리면 다시 분석한다. 원인은 `docker compose -f docker-compose.prod.yml logs --tail 40 worker` |
| "AI 분석 설정이 아직 없어" | `.env`의 `LLM_PROVIDER`와 그 공급자의 키·모델(`ANTHROPIC_API_KEY`·`CLAUDE_MODEL` 또는 `OPENAI_API_KEY`·`OPENAI_MODEL`) 확인 후 `up -d` |
| 빌드나 분석 중 서버가 멈춤 | 메모리 부족. `swapon --show`로 스왑 확인(setup-ec2.sh), `docker stats` |
| 로그인 후 바로 다시 로그인 화면 | https가 아닌 주소로 접속함 (운영 모드는 https에서만 로그인 쿠키를 보낸다) |
| web이 시작하자마자 꺼지고 로그에 `SESSION_SECRET must be a random value` | 운영에서는 `.env`의 `SESSION_SECRET`가 32자 이상 무작위 값이어야 한다. `openssl rand -hex 32` 결과로 바꾸고 `up -d` (바꾸면 모두 다시 로그인) |
| "로그인 시도가 너무 많아요" | 같은 IP에서 10분에 30번 넘게 틀림. 10분 기다리거나 `docker compose -f docker-compose.prod.yml restart web` |

## 보안 점검 (처음 한 번, 이후 분기마다)

앱 쪽은 코드에 들어 있다: 보안 헤더(클릭재킹·형식 추측 차단, HSTS), 운영 비밀값 검사, 같은 IP 로그인 실패 제한, 학생별 하루 업로드 횟수, PDF 60쪽·이미지 해상도·스캔 전사 20쪽 상한, CSV 수식 주입 방지, root가 아닌 컨테이너, 로그 크기 제한. 아래는 AWS 콘솔에서 할 일이다.

| 할 일 | 위치 | 왜 |
| --- | --- | --- |
| 루트 계정 MFA 켜기, 루트 액세스 키 삭제 | 오른쪽 위 계정 이름 → 보안 자격 증명 → MFA 디바이스 할당 | 계정을 뺏기면 모든 데이터·비용이 넘어간다 |
| SSH(22)를 EC2 Instance Connect 주소로만 | EC2 → 보안 그룹 → `creditbridge-web` → 인바운드 규칙 편집 → SSH 소스를 접두사 목록 `com.amazonaws.<리전>.ec2-instance-connect`로 | 0.0.0.0/0이면 전 세계에서 접속을 시도한다 |
| 메타데이터 IMDSv2 필수 | EC2 → 인스턴스 → 작업 → 인스턴스 설정 → 인스턴스 메타데이터 옵션 수정 → IMDSv2 **필수**, 홉 제한 2 | 위조 요청으로 IAM 역할 자격 증명을 빼가는 것을 막는다 |
| RDS 공개 안 함·암호화 확인, 삭제 방지 | RDS → creditbridge-db → 연결 및 보안: 퍼블릭 액세스 **아니요**, 보안 그룹 5432는 EC2 보안 그룹에서만 / 구성: 암호화 **활성화됨** / 수정: 삭제 방지 | DB가 인터넷에 열리지 않게 |
| S3 퍼블릭 차단·https만 | 버킷 → 권한: 퍼블릭 액세스 차단 4개 모두 켜짐, 객체 소유권 ACL 비활성화 / 버킷 정책에 아래 "https만" 정책 추가 | 성적표·강의계획서가 공개되지 않게 |
| AI API 키 범위·한도 | OpenAI: 프로젝트 키(모델 호출 권한만) + Settings → Limits 월 예산 / Anthropic: 워크스페이스 키 + 지출 한도 | 키가 새도 피해를 한도 안으로 |
| 도메인 계정 2단계 인증 | DuckDNS에 로그인하는 GitHub·Google 계정 | 그 계정을 뺏기면 도메인을 다른 곳으로 돌릴 수 있다 |
| 비용 알림 | Billing → 예산(제로 지출 예산) + 결제 기본 설정 → 프리 티어 사용 알림 | 이상한 사용을 빨리 안다 |
| Lambda 로그 보존 | CloudWatch → 로그 그룹 → `/aws/lambda/creditbridge-rds-autostop` → 보존 기간 14일 | 기본은 영구 보관 |

S3 "https만" 버킷 정책 (`<버킷>`을 바꾼다):

```json
{"Version": "2012-10-17", "Statement": [{"Sid": "HttpsOnly", "Effect": "Deny", "Principal": "*", "Action": "s3:*",
  "Resource": ["arn:aws:s3:::<버킷>", "arn:aws:s3:::<버킷>/*"], "Condition": {"Bool": {"aws:SecureTransport": "false"}}}]}
```

### (선택) 앱 전용 DB 계정 쓰기

지금은 앱이 RDS 마스터 계정으로 접속한다. [db-grants.sql](db-grants.sql)의 앱 계정(`creditbridge_app`)을 쓰면 `decisions`·`audit_logs`를 DB 권한으로도 추가 전용으로 막을 수 있다.

1. `docs/db-grants.sql` 4줄의 `'change-me'`를 새 비밀번호로 바꾼 사본을 EC2에 만든다(저장소에 올리지 않는다).
2. EC2에서: `docker run --rm -i postgres:17 psql "host=<RDS 엔드포인트> user=creditbridge dbname=creditbridge sslmode=require" < db-grants-edited.sql` (마스터 비밀번호 입력)
3. `.env`의 `DATABASE_URL`을 `creditbridge_app:<새 비밀번호>@…`로 바꾸고 `docker compose -f docker-compose.prod.yml up -d`.
4. 이후 새 마이그레이션이 있는 코드를 받으면 web이 권한 부족으로 시작하지 못한다. 그때는 마스터 계정으로 한 번 실행한다: `docker compose -f docker-compose.prod.yml run --rm -e DATABASE_URL='<마스터 계정 URL>' web uv run --no-group dev alembic upgrade head` → 새 테이블이 있으면 db-grants.sql에 GRANT를 더해 다시 실행 → `up -d`.

## 그만 쓸 때 (과금 막기)

삭제는 되돌릴 수 없다. 필요한 데이터는 먼저 받아 둔다.

1. EC2 인스턴스 **종료(terminate)** → **탄력적 IP 릴리스** (연결 안 된 탄력적 IP도 과금된다)
2. RDS 데이터베이스 삭제 (최종 스냅샷을 만들지 고른다. 스냅샷 저장도 용량에 따라 과금될 수 있다)
3. S3 버킷 비우기 → 삭제
4. IAM 역할 `creditbridge-ec2` 삭제
