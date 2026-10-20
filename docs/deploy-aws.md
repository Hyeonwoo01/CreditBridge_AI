# AWS 프리티어 배포 (EC2 한 대 + RDS + S3)

실제 Claude 분석을 쓰는 사이트를 AWS 프리티어 범위에서 띄우는 절차다. 예시용 공개 데모(Render, 예시 AI)는 [demo-deploy.md](demo-deploy.md).

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
- 무료가 아닌 것: **공인 IPv4 주소**(2024년부터 시간당 과금, 12개월 무료 계정은 월 750시간 무료·무료 플랜은 크레딧에서 차감), 프리티어 범위를 넘는 사용량, 그리고 **Claude API 사용료**(AWS와 별도, Anthropic에 청구).
- ElastiCache·ALB·NAT 게이트웨이·Multi-AZ는 프리티어가 아니라 쓰지 않는다 (Redis는 EC2 안에서 돌린다).
- t3.micro는 메모리가 1GB라 스왑 2GB를 켜고 웹·작업 프로세스를 하나씩만 띄운다. 사용자가 몇 명이면 충분하지만, 동시에 여러 명이 분석을 돌리면 차례로 처리된다.

## 0. 비용 안전장치 (가장 먼저)

1. 오른쪽 위 리전을 **아시아 태평양(서울) ap-northeast-2**로 바꾼다. 아래 모든 리소스를 같은 리전에 만든다.
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
     - SSH(22): **내 IP**
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
   - 자동 백업 보존 기간: 1일 (백업 저장 공간은 DB 크기까지 무료)
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
| 상태 | `docker compose -f docker-compose.prod.yml ps` / `docker stats --no-stream` (메모리) |
| 로그 | `docker compose -f docker-compose.prod.yml logs --tail 100 web` (`worker`, `caddy`) |
| 재시작 | `docker compose -f docker-compose.prod.yml restart` (EC2가 재부팅돼도 자동으로 다시 뜬다) |
| DB 백업 | RDS 자동 백업(1일) + 필요하면 RDS 콘솔에서 수동 스냅샷 |

## 막힐 때

| 증상 | 원인·해결 |
| --- | --- |
| https가 안 열리고 caddy 로그에 인증서 오류 | 도메인이 탄력적 IP를 가리키는지(DuckDNS update), 보안 그룹에 80·443이 0.0.0.0/0으로 열려 있는지 확인 후 `restart caddy` |
| web 로그에 DB 연결 시간 초과 | RDS 보안 그룹이 EC2에서 5432를 허용하는지(4번 "EC2 컴퓨팅 리소스에 연결"), 엔드포인트·비밀번호 오타, `?sslmode=require` 확인 |
| 업로드하면 오류, 로그에 `NoCredentialsError`·`AccessDenied` | EC2에 IAM 역할 `creditbridge-ec2`가 붙었는지, **메타데이터 홉 제한이 2인지**(EC2 → 작업 → 인스턴스 설정 → 인스턴스 메타데이터 옵션 수정), 정책의 버킷 이름 확인 |
| "AI 분석 설정이 아직 없어" | `.env`의 `ANTHROPIC_API_KEY`·`CLAUDE_MODEL` 확인 후 `up -d` |
| 빌드나 분석 중 서버가 멈춤 | 메모리 부족. `swapon --show`로 스왑 확인(setup-ec2.sh), `docker stats` |
| 로그인 후 바로 다시 로그인 화면 | https가 아닌 주소로 접속함 (운영 모드는 https에서만 로그인 쿠키를 보낸다) |

## 그만 쓸 때 (과금 막기)

삭제는 되돌릴 수 없다. 필요한 데이터는 먼저 받아 둔다.

1. EC2 인스턴스 **종료(terminate)** → **탄력적 IP 릴리스** (연결 안 된 탄력적 IP도 과금된다)
2. RDS 데이터베이스 삭제 (최종 스냅샷을 만들지 고른다. 스냅샷 저장도 용량에 따라 과금될 수 있다)
3. S3 버킷 비우기 → 삭제
4. IAM 역할 `creditbridge-ec2` 삭제
