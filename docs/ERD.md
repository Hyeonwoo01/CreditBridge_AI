# CreditBridge AI ERD (데이터베이스 구조)

[API 명세서](API_Spec.md)가 읽고 쓰는 데이터를 [기획 통합본](spec.md) 4장 기능 명세(FR-01~FR-27)에 맞춰 엔티티·속성·관계로 정리했다. 마지막 절에 구조 검토 결과가 있다.

- 기준: 2026-10-19 main, Alembic 0001(PostgreSQL 기준점 — MariaDB 시절 0001~0011을 하나로 합침)~0003(0002 웹 푸시, 0003 학생 출신 대학). 실행 가능한 스키마는 `db/init.sql`, 초기 데이터는 `db/data.sql`(둘 다 `scripts/export_db_sql.sh`로 생성). 실제 정의는 `backend/models/`(테이블당 1파일), 변경은 `alembic/versions/`로만.
- DB: PostgreSQL 17, 인코딩 UTF8. 시간은 모두 UTC `TIMESTAMP`(시간대 없음, 마이크로초). 기본키는 `id BIGSERIAL`(BIGINT + 시퀀스). JSON 컬럼은 `JSONB`.
- 원본 파일(강의계획서·성적표·보완 자료·이의 근거 자료)은 DB가 아니라 객체 스토리지(S3)에 두고 DB에는 파일 키만 저장한다.

## 1. 엔티티 한눈에 보기 (35개)

| 영역 | 엔티티 | 한 줄 설명 | 주요 FR |
| --- | --- | --- | --- |
| 기관·사용자 | `institutions` | 출신 대학과 대상(편입) 대학 | FR-12·15·24 |
| | `institution_sources` | 대상 대학별 ④ 출신 대학 목록 (대학마다 자기 목록만) | FR-12 |
| | `departments` | 대상 대학의 학과 (과목·교수 배정 기준) | FR-05·18 |
| | `users` | 학생·심사관·교수·관리자 계정 | FR-12·19 |
| | `courses` | 대상 대학 카탈로그 과목과 필수 개념 | FR-05 |
| | `catalog_imports` | 과목 카탈로그 가져오기 (검증 → 바뀌는 점 확인 → 게시, 출처·적용 학년도·게시자) | 리뷰 v3 P1-2 |
| | `degree_programs` | 졸업 프로그램 (학과·적용 입학연도별) | 리뷰 v3 P1-6 |
| | `graduation_requirements` | 졸업 요건 (영역·필요 학점·해당 과목 코드) | 리뷰 v3 P1-6 |
| 편입 요청·문서 | `student_transcripts` | 학생 계정의 성적표 (학생당 하나, 처음 들어오면 먼저 올림) | FR-02·13 |
| | `transfer_requests` | 편입 학점 심사 요청 (성적표의 C 이상 과목마다 하나, 예전 방식은 여러 과목 묶음) | FR-15·21 |
| | `syllabi` | 강의계획서(학생 업로드·대상 과목 기준)와 추출 결과 | FR-01·03·04·14·25 |
| | `syllabus_chunks` | 주차·개념 단위로 나눈 강의계획서 글 | FR-03 |
| | `transcript_entries` | 성적표에서 뽑은 과목과 강의계획서 연결 | FR-02 |
| AI 분석 | `course_evaluations` | 강의계획서 한 건의 AI 분석 결과(재분석마다 새 행) | FR-05~08·16 |
| | `evidence_spans` | 원문 검증을 통과한 근거 구절 위치 | FR-06·25 |
| | `evidence_feedback` | 교수가 근거 구절마다 누른 맞음·틀림 (AI 근거 정확도) | FR-06 |
| | `policy_rules` | 학칙 정책 규칙 (성적 기준·편입 상한·졸업 학점·학기당 학점, 학과·입학연도 범위, 초안·승인·끝남) | 리뷰 v3 P0-4 |
| | `credit_allocations` | 승인된 학점 배분 원장 (판정마다 출신 과목별 인정 학점 한 줄, 재판정이면 대체됨) | 리뷰 v3 P0-3 |
| | `credit_conversion_rules` | 대상 대학이 승인한 학점 환산 규칙 (출신 단위 → 대상 단위, 유효기간) | 리뷰 v3 P0-1 |
| 심사 | `assignments` | 교수 배정·대리 재배정 이력 | FR-18·19 |
| | `decisions` | 교수 최종 판정 (추가 전용) | FR-09·10·11 |
| | `material_requests` | 보완 자료 요청 | FR-22 |
| | `supplement_files` | 학생이 낸 보완 자료 원본 | FR-22 |
| | `appeals` | 이의 신청 | FR-23 |
| | `appeal_files` | 이의 신청 근거 자료 원본 | FR-23 |
| | `evaluation_notes` | 심사 건 내부 메모 (교직원만) | – |
| | `equivalencies` | 기관이 가져온 기존 동등 과목표 | FR-11·26 |
| 개인정보·운영 | `privacy_requests` | 문서 삭제 요청과 처리 단계 | FR-13 |
| | `notifications` | 화면 알림과 알림 메일·웹 푸시 | FR-19·20 |
| | `push_subscriptions` | 웹 푸시를 받는 기기(브라우저) 구독 | FR-20 |
| | `sis_syncs` | 판정의 학사정보시스템 반영 결과 (반영됨·실패·다시 보내기 대기) | FR-24, 리뷰 v3 P1-4 |
| | `sis_ack_requests` | 반영 결과 요청의 Idempotency-Key와 처음 응답 | FR-24, 리뷰 v3 P1-4 |
| | `background_jobs` | 백그라운드 분석 작업의 상태·시도·오류 코드·처리 시간 (재시도·격리·다시 처리) | 리뷰 v3 P1-3 |
| | `llm_usage` | AI 호출 사용량: 작업 시도마다 (용도, 모델)별 호출 수·입력·출력 토큰 | 리뷰 v3 13.7 (H15) |
| | `audit_logs` | 주요 행위 기록 (추가 전용) | FR-10 |

## 2. ER 다이어그램

키와 관계를 보이는 속성만 넣었다. 전체 속성은 3절.

```mermaid
erDiagram
    institutions ||--o{ users : "소속"
    institutions ||--o{ users : "학생 출신 대학"
    institutions ||--o{ departments : "학과"
    institutions ||--o{ institution_sources : "대상 대학의 출신 대학 목록"
    institutions ||--o{ institution_sources : "목록에 오른 출신 대학"
    departments ||--o{ courses : "개설 학과"
    departments |o--o{ users : "소속 교수"
    institutions ||--o{ courses : "카탈로그"
    institutions ||--o{ transfer_requests : "출신 대학"
    institutions ||--o{ transfer_requests : "대상 대학"
    institutions ||--o{ syllabi : "작성 기관"
    institutions ||--o{ equivalencies : "대상·출신 대학"
    users |o--o{ users : "대리 심사자"
    users ||--o{ transfer_requests : "학생"
    users ||--o| student_transcripts : "계정 성적표"
    transfer_requests ||--o{ syllabi : "올린 강의계획서"
    transfer_requests ||--o{ transcript_entries : "성적표 과목"
    syllabi |o--o{ transcript_entries : "연결"
    syllabi ||--o{ syllabus_chunks : "주차·개념"
    courses |o--o| syllabi : "기준 강의계획서"
    syllabi ||--o{ course_evaluations : "분석(재분석마다)"
    courses |o--o{ course_evaluations : "1순위 후보"
    course_evaluations ||--o{ evidence_spans : "근거 구절"
    evidence_spans ||--o{ evidence_feedback : "맞음·틀림"
    users ||--o{ evidence_feedback : "누른 교수"
    course_evaluations ||--o{ assignments : "배정 이력"
    users ||--o{ assignments : "담당 교수"
    course_evaluations ||--o{ decisions : "판정(원·재판정)"
    users ||--o{ decisions : "판정 교수"
    courses |o--o{ decisions : "인정 대상 과목"
    decisions ||--o{ appeals : "이의 대상 판정"
    decisions ||--o| sis_syncs : "SIS 반영 상태"
    appeals |o--o{ decisions : "재판정"
    course_evaluations ||--o{ appeals : "이의 신청"
    appeals ||--o{ appeal_files : "근거 자료"
    course_evaluations ||--o{ material_requests : "보완 요청"
    material_requests |o--o{ supplement_files : "제출 자료"
    syllabi ||--o{ supplement_files : "덧붙인 자료"
    syllabi ||--o{ evaluation_notes : "내부 메모"
    users ||--o{ evaluation_notes : "작성자"
    transfer_requests ||--o{ privacy_requests : "삭제 요청"
    users ||--o{ notifications : "받는 사람"
    users ||--o{ push_subscriptions : "푸시 받는 기기"
    users |o--o{ audit_logs : "행위자"
    courses |o--o{ equivalencies : "인정 대상 과목"

    institutions {
        bigint id PK
        varchar name
        varchar country
        boolean is_target
        int tuition_per_credit
        int degree_credits
        varchar sis_token_hash
    }
    institution_sources {
        bigint id PK
        bigint institution_id FK "대상 대학"
        bigint source_institution_id FK "출신 대학"
    }
    departments {
        bigint id PK
        bigint institution_id FK
        varchar name "기관 안에서 UNIQUE"
    }
    users {
        bigint id PK
        varchar email UK
        varchar role
        bigint institution_id FK
        bigint department_id FK
        bigint source_institution_id FK
        bigint delegate_user_id FK
        date away_until
        boolean is_active
        varchar locale
    }
    courses {
        bigint id PK
        bigint institution_id FK
        varchar code "기관 안에서 UNIQUE"
        decimal credits
        bigint department_id FK
        jsonb concepts
        bigint reference_syllabus_id FK
    }
    transfer_requests {
        bigint id PK
        bigint student_id FK
        bigint source_institution_id FK
        bigint target_institution_id FK
        varchar status
        timestamp submitted_at
        varchar transcript_file_key
        timestamp transcript_copied_at
        varchar course_key
        boolean counted
    }
    student_transcripts {
        bigint id PK
        bigint student_id FK "UNIQUE"
        varchar file_key
        varchar masked_name
        jsonb lines
        varchar status
        timestamp uploaded_at
    }
    syllabi {
        bigint id PK
        bigint institution_id FK
        bigint transfer_request_id FK
        bigint owner_id FK
        varchar content_hash "요청 안에서 UNIQUE"
        text raw_text
        jsonb page_offsets
        jsonb extracted_json
        varchar status
    }
    syllabus_chunks {
        bigint id PK
        bigint syllabus_id FK
        int week_no
        varchar concept
    }
    transcript_entries {
        bigint id PK
        bigint transfer_request_id FK
        bigint syllabus_id FK
        varchar title
        decimal credits
        varchar grade
        boolean link_confirmed
    }
    course_evaluations {
        bigint id PK
        bigint syllabus_id FK
        bigint transfer_request_id FK
        bigint candidate_course_id FK
        varchar recommendation
        decimal coverage
        varchar confidence
        jsonb coverage_json
        varchar input_hash
        boolean is_latest
    }
    evidence_spans {
        bigint id PK
        bigint course_evaluation_id FK
        bigint syllabus_id FK
        varchar side
        int char_start
        int char_end
    }
    evidence_feedback {
        bigint id PK
        bigint evidence_span_id FK
        bigint user_id FK
        varchar verdict
    }
    assignments {
        bigint id PK
        bigint course_evaluation_id FK
        bigint reviewer_id FK
        bigint assigned_by FK
        bigint reassigned_from FK
        boolean is_active
    }
    decisions {
        bigint id PK
        bigint course_evaluation_id FK
        bigint decided_by FK
        varchar action
        varchar result
        bigint target_course_id FK
        jsonb reason_codes
        jsonb ai_recommendation_snapshot
        bigint appeal_id FK
    }
    appeals {
        bigint id PK
        bigint course_evaluation_id FK
        bigint decision_id FK
        bigint student_id FK
        varchar status
        bigint handled_by FK
    }
    appeal_files {
        bigint id PK
        bigint appeal_id FK
        varchar file_key
    }
    material_requests {
        bigint id PK
        bigint syllabus_id FK
        bigint course_evaluation_id FK
        bigint requested_by FK
        jsonb items
        varchar status
    }
    supplement_files {
        bigint id PK
        bigint syllabus_id FK
        bigint material_request_id FK
        varchar file_key
    }
    evaluation_notes {
        bigint id PK
        bigint syllabus_id FK
        bigint course_evaluation_id FK
        bigint author_id FK
        text body
    }
    equivalencies {
        bigint id PK
        bigint target_institution_id FK
        bigint source_institution_id FK
        varchar source_course_key
        bigint target_course_id FK
        varchar result
        bigint imported_by FK
    }
    privacy_requests {
        bigint id PK
        bigint transfer_request_id FK
        bigint student_id FK
        varchar status
        timestamp due_at
        bigint reviewed_by FK
        bigint approved_by FK
    }
    notifications {
        bigint id PK
        bigint user_id FK
        varchar kind
        varchar message
        timestamp read_at
        timestamp pushed_at
    }
    push_subscriptions {
        bigint id PK
        bigint user_id FK
        varchar endpoint UK
    }
    sis_syncs {
        bigint id PK
        bigint decision_id FK
        varchar status
        varchar external_reference_id
    }
    audit_logs {
        bigint id PK
        bigint actor_id FK
        varchar action
        varchar target_type
        varchar target_id
        jsonb payload_json
    }
```

## 3. 엔티티와 속성

표기: `PK` 기본키 · `FK→테이블` 외래키 · `UQ` 유일 · `IX` 인덱스 · `NN` NOT NULL · `null` 비어도 됨. 모든 테이블에 `id BIGSERIAL PK`가 있고, 따로 적지 않으면 `created_at TIMESTAMP NN`(만든 시각)도 있다.

### 3.1 기관·사용자

**institutions** — 출신 대학(학생이 다니던 곳)과 대상 대학(CreditBridge를 쓰는 편입 대학)을 한 테이블에 두고 `is_target`으로 나눈다.

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| name | VARCHAR(200) | NN | 대학 이름 (동등 과목표 CSV의 출신 대학 이름과 똑같아야 함) |
| country | VARCHAR(2) | NN | 국가 코드 (KR, US) |
| is_target | BOOLEAN | NN | 대상 대학 여부 |
| tuition_per_credit | INT | null | 학점당 등록금 (FR-15 시뮬레이션 기본값) |
| degree_credits | INT | null | 예전 졸업 학점 설정. 0011부터 쓰지 않음 — 값은 `policy_rules`(degree_credits)로 옮겼고 기관을 새로 만들 때 첫 정책을 만드는 데만 씀 |
| credit_system | VARCHAR(20) | null, CHECK | 학점 단위: kr_credit · us_semester · us_quarter · ects · other. 비우면 모름 — 환산하지 않고 예상치 보류 (P18, Alembic 0009) |
| max_transfer_credits | INT | null | 예전 편입 학점 상한 설정 (Alembic 0007). 0011부터 쓰지 않음 — 값은 `policy_rules`(transfer_cap)로 옮겼다. 상한은 학칙 정책에서 정하고, 정책이 없으면 자르지 않는다 |
| sis_token_hash | VARCHAR(64) | null | 학사정보시스템 연동 토큰의 해시 (원문은 저장하지 않음, FR-24) |

**institution_sources** — 대상 대학이 ④ 출신 대학 목록에 올린 출신 대학(Alembic 0004). `(institution_id, source_institution_id)` UNIQUE. 출신 대학 행(`institutions`, `is_target=false`)은 같은 이름이면 한 줄을 함께 쓰고, 이 표가 대학별 목록을 정한다. 계정 CSV·계정 수정·동등 과목표 CSV·학생 과목 검색은 자기 대학 목록의 출신 대학만 쓴다. 목록에서 지우면 연결만 지우고, 다른 대학도 어떤 행도 가리키지 않으면 출신 대학 행까지 지운다(그 대학 학생 계정·편입 요청·동등 과목표가 가리키면 지우지 않음).

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| institution_id | BIGINT | FK→institutions, NN | 대상 대학 |
| source_institution_id | BIGINT | FK→institutions, NN | 출신 대학 |

**departments** — 대상 대학의 학과. `(institution_id, name)` UNIQUE. 과목 CSV를 가져올 때 새 학과명이면 만들고, 계정 CSV·관리자 계정 수정은 과목이 있는 학과만 고른다. 학과명을 고치면 과목·교수가 함께 따라간다(Alembic 0011).

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| institution_id | BIGINT | FK→institutions, NN | 기관 |
| name | VARCHAR(50) | NN, UQ(기관 안) | 학과명 (예: Mathematics) |

**users** — 역할 하나와 소속 기관 하나를 가진다. 지우지 않고 비활성화한다(판정·감사 기록이 가리키므로).

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| email | VARCHAR(255) | NN, UQ | 로그인 이메일 |
| password_hash | VARCHAR(255) | NN | Argon2 해시 |
| name | VARCHAR(100) | NN | 이름 |
| role | VARCHAR(20) | NN, IX | student · evaluator · professor · admin (FR-12) |
| institution_id | BIGINT | FK→institutions, null | 소속 기관 |
| department_id | BIGINT | FK→departments, IX, null | 교수의 학과 (과목과 같은 학과 행이어야 자동 배정, FR-18). 심사관은 선택, 관리자는 비움. 학생은 편입 전공(관리자가 정함, 편입 요청의 `major`로 복사) |
| source_institution_id | BIGINT | FK→institutions, null | 학생의 출신(전적) 대학. 관리자가 계정 CSV·계정 수정에서 정하고 학생은 바꾸지 않는다. 교직원은 비움 (Alembic 0003, 기존 학생은 최근 요청 값으로 채움) |
| delegate_user_id | BIGINT | FK→users, null | 부재 시 대리 심사자 (FR-19) |
| admission_year | INT | null | 학생의 입학연도. 학칙 정책을 입학연도별로 고를 때 쓴다. 비우면 모든 입학연도 규칙만 맞음 (관리자가 계정 수정에서 정함, Alembic 0011) |
| away_until | DATE | null | 부재 종료일 (FR-19) |
| must_change_password | BOOLEAN | NN | 임시 비밀번호 → 첫 로그인 때 변경 |
| failed_logins | INT | NN | 연속 로그인 실패 수 (5회 1분 잠금, 10회 초기화) |
| locked_until | TIMESTAMP | null | 로그인 잠금 해제 시각 |
| is_active | BOOLEAN | NN | 비활성화 여부 |
| deactivated_at | TIMESTAMP | null | 비활성화 시각 |
| locale | VARCHAR(5) | null | 화면·알림·메일 언어 ko·en |

**courses** — 대상 대학 카탈로그. 기준 강의계획서가 있어야 AI 비교 후보가 된다.

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| institution_id | BIGINT | FK→institutions, NN, IX | 대상 대학 |
| code | VARCHAR(30) | NN, UQ(institution_id, code) | 과목 코드 (MATH 1151) |
| title | VARCHAR(200) | NN | 과목명 |
| credits | DECIMAL(4,1) | NN | 학점 |
| department_id | BIGINT | FK→departments, NN, IX | 학과 (후보 선정 필터·교수 배정 기준, FR-05·18) |
| level | TEXT | NN | 과목 수준 설명 (FR-16) |
| concepts | JSONB | null | 학과가 정한 필수 개념 목록 (FR-05) |
| reference_syllabus_id | BIGINT | FK→syllabi, null | 기준 강의계획서 |
| catalog_import_id | BIGINT | FK→catalog_imports, null | 이 과목 값을 마지막으로 정한 카탈로그 게시본(출처·적용 학년도·게시자·게시 시각, Alembic 0018, 리뷰 v3 P1-2). 그 전에 만든 과목은 비어 있음 |

### 3.2 편입 요청·문서

**catalog_imports** — 대상 대학 과목 카탈로그 가져오기 한 번 (Alembic 0018, 리뷰 v3 P1-2). `institution_id` FK(IX), `filename` VARCHAR(255), `file_hash` VARCHAR(64)(원본 SHA-256, 파일은 저장하지 않음), `source` TEXT(출처: 학사 편람·포털 주소), `catalog_year` INT null(적용 학년도 — 올린 날짜와 다름), `status` VARCHAR(10)(draft·published·discarded, CHECK, IX), `rows` JSONB(검증을 통과한 행), `changes` JSONB(added: 새 과목 코드, changed: 과목 코드 → 필드별 [이전, 새 값], unchanged: 그대로인 수 — 게시 직전에 다시 계산해 남김, 과목 버전 이력), `created_by` FK→users, `reviewed_by` FK→users null·`reviewed_at`(게시·버린 관리자와 시각), `created_at`. 게시 대기본은 기관마다 하나(새로 올리면 이전 대기본은 discarded). 게시 전 행은 AI 후보에 쓰이지 않는다.

**degree_programs** — 졸업 프로그램 (Alembic 0019, 리뷰 v3 P1-6). `institution_id` FK(IX), `name` VARCHAR(200), `department_id` FK→departments null(모든 학과), `catalog_year` INT null(적용 입학연도, 1990~2100 CHECK, 모든 입학연도), `created_at`. 학생에게는 편입 전공(학과)·입학연도가 맞는 것 중 가장 구체적인 프로그램을 쓰고, 없거나 같은 구체성에서 둘 이상이면 미정.

**graduation_requirements** — 졸업 요건 (Alembic 0019). `program_id` FK→degree_programs(IX), `area` VARCHAR(20)(major_required·major_elective·general_education·free_elective, CHECK), `name` VARCHAR(200), `required_credits` DECIMAL(5,1)(>0, 대상 대학 단위), `course_codes` JSONB(요건을 채우는 대상 과목 코드), `sort` INT, `created_at`. 학생 홈에서 승인된 배분 원장(credit_allocations)의 줄마다 대상 과목이 목록에 있으면 그 요건, 아니면 일반 선택에 배정하고 필요 학점을 넘는 학점은 일반 선택으로 넘긴다(같은 학점을 두 요건에 세지 않음, 계산 결과는 저장하지 않음).

**student_transcripts** — 학생 계정의 성적표 (학생당 하나, Alembic 0007). 처음 들어오면 먼저 올리고, 과목 줄을 뽑으면 성적이 C 이상인 과목마다 편입 요청을 만든다. 요청 문서를 삭제해도 계정 성적표는 남는다.

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| student_id | BIGINT | FK→users, NN, UQ | 학생 |
| file_key | VARCHAR(255) | null | 성적표 원본 파일 키 (객체 스토리지) |
| masked_name | VARCHAR(100) | null | 가린 이름 `L** J****` (FR-13) |
| lines | JSONB | null | 뽑은 과목 줄 [{title, code, credits, grade, term}] (이름·학번 없음) |
| status | VARCHAR(20) | NN, CHECK | processing · ready · failed |
| error_message | VARCHAR(500) | null | 읽지 못했을 때 화면 문구 (한국어 원문, 화면에서 번역) |
| uploaded_at | TIMESTAMP | NN | 올린 시각 |

**transfer_requests** — 편입 학점 심사 요청. 성적표의 C 이상 과목마다 하나씩 자동으로 만들고(`course_key`), 예전 방식(학생이 직접 만든 여러 과목 묶음)도 그대로 읽는다.

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| student_id | BIGINT | FK→users, NN, IX | 학생 |
| source_institution_id | BIGINT | FK→institutions, NN | 출신 대학 (만들 때 학생 계정의 값을 복사 — 나중에 계정이 바뀌어도 그대로) |
| target_institution_id | BIGINT | FK→institutions, NN, IX | 대상 대학 |
| major | VARCHAR(100) | NN | 편입 전공 (만들 때 학생 계정의 학과명을 복사) |
| status | VARCHAR(20) | NN, IX | draft(사전 시뮬레이션) · submitted · decided (FR-21) · closed(문서 삭제 승인으로 종료: 더 올리거나 심사하지 않고 심사 큐·교수 목록에서 빠짐, 판정 기록은 남음. Alembic 0005) |
| submitted_at | TIMESTAMP | null | 학사처에 심사 요청한 시각 |
| transcript_file_key | VARCHAR(255) | null | 성적표 원본 파일 키 (삭제 승인 후 null) |
| transcript_masked_name | VARCHAR(100) | null | 가린 이름 `L** J****` (FR-13) |
| transcript_copied_at | TIMESTAMP | null | 계정 성적표의 과목 줄을 이 요청에 복사한 시각 (`transcript_file_key`는 예전에 요청마다 올린 파일에만) |
| course_key | VARCHAR(300) | null | 성적표 과목 하나로 만든 요청이면 그 과목 키(`code:MATH101`, 코드가 없으면 `title:…`). 성적표를 다시 올려도 같은 과목 요청을 또 만들지 않음 |
| counted | BOOLEAN | NN, 기본 true | 편입 학점 상한을 넘을 때 졸업 학점에 넣을 과목인지 (학생이 고름) |

**syllabi** — 학생이 올린 강의계획서와, 대상 과목의 기준 강의계획서를 함께 담는다(기준은 `transfer_request_id`가 null).

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| institution_id | BIGINT | FK→institutions, NN, IX | 학생 것은 대상 대학, 기준 것은 그 과목의 대학 |
| transfer_request_id | BIGINT | FK→transfer_requests, IX, null | 속한 요청 (기준 강의계획서는 null) |
| owner_id | BIGINT | FK→users, null | 올린 학생 |
| source_file_key | VARCHAR(255) | null | 원본 파일 키 (삭제 승인 후 null) |
| content_hash | VARCHAR(64) | NN, IX, UQ(transfer_request_id, content_hash) | 원본 SHA-256. 같으면 LLM을 다시 부르지 않고 결과 재사용 |
| original_filename | VARCHAR(255) | NN | 올린 파일 이름 |
| language | VARCHAR(8) | NN | 문서 언어 |
| raw_text | TEXT | NN | 추출 글자 (보완 자료는 `[보완 자료: 이름]` 표시 뒤에 덧붙임) |
| page_offsets | JSONB | null | 원본 PDF 쪽별 글자 위치 (FR-25) |
| course_code · course_title · credits | VARCHAR(50) · VARCHAR(255) · DECIMAL(4,1) | NN·NN·null | 추출한 과목 정보 (검색용으로 JSON 밖에 둠) |
| extracted_json | JSONB | null | 6개 필드 구조화 결과 (FR-03·04) |
| extraction_model | VARCHAR(100) | null | 추출에 쓴 모델 |
| quality_score | DECIMAL(4,3) | null | 인식 품질 0~1 (FR-01) |
| injection_flags | JSONB | null | 판정 유도 의심 문구 줄 (FR-14) |
| status | VARCHAR(20) | NN | uploaded · processing · ready · failed · deleted |
| error_message | VARCHAR(500) | null | 실패 사유 (한국어 원문, 화면에서 번역) |

**syllabus_chunks** — `syllabus_id` FK→syllabi(ON DELETE CASCADE, IX), `week_no` INT null, `concept` VARCHAR(255), `text` TEXT, `char_start`·`char_end` INT null(원문 위치). `created_at` 없음.

**transcript_entries** — `transfer_request_id` FK(IX), `title` VARCHAR(255), `code` VARCHAR(50) null, `credits` DECIMAL(4,1) null, `grade` VARCHAR(10) null, `term` VARCHAR(50) null, `syllabus_id` FK→syllabi null(연결된 강의계획서), `link_score` DECIMAL(4,3) null(자동 연결 점수), `link_confirmed` BOOLEAN(학생 확인). 성적은 이 테이블에만 있고 로그·알림에는 쓰지 않는다.

### 3.3 AI 분석

**course_evaluations** — 고치지 않고 재분석마다 새 행을 만든다. 최신 행만 `is_latest`.

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| syllabus_id | BIGINT | FK→syllabi, NN, IX | 분석한 강의계획서 |
| transfer_request_id | BIGINT | FK→transfer_requests, IX, null | 속한 요청 (권한 검사용으로 함께 둠) |
| candidate_course_id | BIGINT | FK→courses, IX, null | 1순위 후보 (억지 매핑 안 하면 null, FR-05) |
| status | VARCHAR(20) | NN, IX | queued · running · done · failed |
| recommendation | VARCHAR(20) | IX, null | direct · elective · none · insufficient (FR-07·08) |
| coverage | DECIMAL(4,3) | null | 1순위 개념 커버리지 0~1 |
| confidence | VARCHAR(10) | IX, null | high · medium · low |
| level_flag | VARCHAR(10) | null | same · lower · higher (FR-16) |
| coverage_json | JSONB | null | 후보 3개·개념별 판단·근거·정보 부족 진단·경고, 한국어·영어 설명, 후보마다 분야별 확인 항목 미리 채우기 `review_items`(key·status found/not_found/unverified·원문과 일치한 인용과 위치, evaluation-v4부터) |
| summary | TEXT | NN | 요약 (한국어) |
| input_hash | VARCHAR(64) | IX, null | 프롬프트 버전·규칙 버전·모델·입력의 해시 (같으면 결과 재사용) |
| prompt_version · model | VARCHAR(20) · VARCHAR(100) | null | evaluation-v4 등 |
| error_message | VARCHAR(500) | null | 실패 사유 |
| is_latest | BOOLEAN | NN, IX | 그 강의계획서의 최신 분석 (`syllabus_id, is_latest` 복합 IX) |
| quotes_total · quotes_unmatched · quotes_non_teaching | INT · INT · INT | null | AI가 낸 인용 구절 수, 원문에 없어 버린 수, 선수과목·교재 칸이나 부정 문장이라 버린 수 (프롬프트 버전별 환각 지표, 0008). 이전 결과를 재사용한 행은 비움 |
| (부분 유니크 인덱스) | `uq_course_evaluations_latest_syllabus` | UQ | `syllabus_id` `WHERE is_latest` — 강의계획서당 최신 분석 하나 |

판정 확률(%) 컬럼은 두지 않는다 (MVP 규칙).

**evidence_spans** — `course_evaluation_id` FK(IX), `side` VARCHAR(10)(source·target), `syllabus_id` FK→syllabi, `char_start`·`char_end` INT, `concept` VARCHAR(255), `verified` BOOLEAN. 원문 문자열과 일치한 구절만 저장한다(FR-06). `created_at` 없음.

**evidence_feedback** — `evidence_span_id` FK→evidence_spans(IX), `user_id` FK→users, `verdict` VARCHAR(10)(correct·wrong, CHECK), `created_at`, `updated_at`. (`evidence_span_id`, `user_id`) UQ — 교수 한 명당 구절 하나에 한 행이고 다시 누르면 고친다(판정이 아니라 AI 근거 품질 표시). 운영 통계의 프롬프트 버전별 근거 정확도에 쓴다(0008).

### 3.4 심사

**assignments** — 배정이 바뀌면 이전 행을 `is_active=false`로 두고 새 행을 만든다(이력 보존).

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| course_evaluation_id | BIGINT | FK, NN, IX | 심사 건 |
| reviewer_id | BIGINT | FK→users, NN, IX | 담당 교수 |
| assigned_by | BIGINT | FK→users, null | 배정한 심사관 (자동 이어 붙이기는 null) |
| assigned_at | TIMESTAMP | NN | 배정 시각 (판정 기한 계산 기준) |
| reassigned_from | BIGINT | FK→users, null | 대리 재배정이면 원래 교수 (FR-19) |
| is_active | BOOLEAN | NN | 현재 배정 (`course_evaluation_id, is_active`·`reviewer_id, is_active` 복합 IX) |
| (부분 유니크 인덱스) | `uq_assignments_active_evaluation` | UQ | `course_evaluation_id` `WHERE is_active` — 심사 건당 활성 배정 하나 |

**decisions** — 추가 전용(INSERT만). 이의 신청 재판정도 새 행. 현재 판정은 그 심사 건의 가장 늦은 `decided_at`.

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| course_evaluation_id | BIGINT | FK, NN, IX | 심사 건 |
| decided_by | BIGINT | FK→users, NN | 판정한 교수 (사람 id 필수, FR-09) |
| action | VARCHAR(10) | NN | approve · modify · reject |
| result | VARCHAR(10) | NN | direct · elective · none |
| target_course_id | BIGINT | FK→courses, null | 직접 인정 대상 과목 |
| reason_codes | JSONB | NN | 선택형 사유 코드 목록 |
| reason_memo | TEXT | NN | 소명 메모 ('기타'면 필수) |
| ai_recommendation_snapshot | JSONB | NN | 판정 당시 AI 추천·커버리지·신뢰도·프롬프트 버전 (FR-10) |
| conflict_acknowledged | BOOLEAN | NN | 과거 판정과 다른 결과임을 확인했는지 (FR-11) |
| appeal_id | BIGINT | FK→appeals, null | 재판정이면 그 이의 신청 |
| decided_at | TIMESTAMP | NN | 판정 시각 (`created_at` 대신) |
| accepted_credits | DECIMAL(5,2) | null, ≥0 | 교수가 확정한 인정 학점 (대상 대학 단위, 0009부터. 그 전 판정은 비어 있음) |
| credit_unit · source_credit_unit | VARCHAR(20) | null, CHECK | 인정 학점·출신 학점의 단위 |
| credit_basis | VARCHAR(12) | null, CHECK | full · partial · elective · not_accepted |
| source_credits | DECIMAL(5,2) | null | 판정 때 쓴 출신 학점 (성적표 값이 먼저, 없으면 강의계획서) |
| evidence_snapshot | JSONB | null | 판정 때 증거 상태 (강의계획서 id·출처·진위·적용 학기·학기·수강 학기·파일 해시, 0012부터) |
| course_snapshot | JSONB | null | 판정 때 대상 과목(id·코드·이름·학점·학과)·출신 과목들(강의계획서 id·코드·이름·학점·파일 해시)·출신 대학·환산(출신 학점·단위·환산값·규칙 id·비율·방법·보류 이유)·추천 규칙 버전 (0013부터, 리뷰 v3 P0-8)·교수가 고른 졸업 요건(`requirement`: id·program_id·area·name, 자동이면 null, 0021부터 P1-6). 내보내기·리포트·학생 화면·API는 대상 과목 코드를 여기서 먼저 읽는다. 0013 이전 판정은 비어 있어 지금 카탈로그 값을 쓴다 |
| review_checklist | JSONB | null | 분야별 심사 체크리스트 기록: `version`·`framework`(math·computing·lab_science·physics·business·health·humanities·common)·`checked`(확인한 항목 키)·`missing_evidence`(자료가 없어 확인 못 한 항목 키) (0016부터, 리뷰 v3 P1-1). 판정을 대신하지 않는 기록, 교직원 화면에만 표시 |
| policy_snapshot | JSONB | null | 판정 때 적용한 학칙 정책 (규칙 종류 → 상태·규칙 id·값, 0011부터). 정책이 바뀌어도 그대로 |
| conversion_rule_id | BIGINT | FK→credit_conversion_rules, null | 적용한 환산 규칙 (같은 단위거나 교수가 직접 적었으면 비움) |

**syllabi 증거 상태 (0012)** — `source_kind` VARCHAR(30)(student_uploaded·registrar_issued·instructor_confirmed·official_portal·public_web·institution_reference·other), `authenticity` VARCHAR(20)(unverified·verified·partially_verified·suspicious·rejected), `applicability` VARCHAR(10)(applicable·mismatch·unknown — `academic_term`과 성적표 수강 학기 비교), `academic_term`, `verification_method`, `verification_note`(학생 비공개), `verified_by` FK→users, `verified_at`. 파일 해시가 같아도 진위·출처는 옮기지 않는다. 의심·채택 안 함이면 판정 보류(자동 불인정 아님).

**policy_rules** — `institution_id` FK(IX), `rule_type` VARCHAR(30)(min_grade·transfer_cap·degree_credits·semester_load·appeal_window·appeal_review, CHECK — 뒤의 둘은 0014), `department_id` FK→departments null(모든 학과), `admission_year` INT null(1990~2100, 모든 입학연도), `parameters` JSONB({min_grade, accept_pass}, {credits}, 이의 신청 기간·처리 기한은 {days}), `effective_from` DATE, `effective_to` DATE null, `status` VARCHAR(10)(draft·approved·retired, IX), `source` TEXT(근거 학칙), `created_by`·`approved_by` FK→users null, `approved_at`, `created_at`. 승인된 규칙 중 학생 범위에 맞고 가장 구체적인 것(학과·입학연도를 정한 수)을 쓰고, 같은 구체성에서 값이 다르면 충돌, 없으면 미정(기본값 없음). 승인한 규칙은 고치지 않고 끝낸 뒤 새로 만든다. 0011이 대상 대학마다 이전 설정(C 이상·P/PASS/S, 상한·졸업 학점, 학기당 15)을 대학 전체 승인 규칙으로 옮겼다. `institutions.max_transfer_credits`·`degree_credits`는 더 쓰지 않는다(기록용).

**credit_allocations** — `student_id` FK→users(IX), `decision_id` FK→decisions(IX), `syllabus_id` FK→syllabi(IX, 출신 과목), `target_course_id` FK→courses null(선택 학점이면 없음), `credits` DECIMAL(5,2)(>0, 대상 대학 단위), `credit_unit`, `status` VARCHAR(12)(active·superseded, IX), `superseded_by_decision_id` FK→decisions null, `requirement_id` FK→graduation_requirements null(ON DELETE SET NULL, 교수가 판정 때 고른 졸업 요건, 비우면 과목 목록 기준 자동 배정, Alembic 0021 리뷰 v3 P1-6), `created_at`. 판정이 출신 과목마다 한 줄씩 남기고 여러 과목을 합쳐 인정(N:1)하면 과목별 남은 학점에 비례해 나눈다. 학생의 확정 인정 학점은 active 줄의 합계다. 재판정하면 지우지 않고 superseded로 바꾼다. 같은 출신 과목(같은 출신 대학·과목 코드) active 합계는 환산 학점을 넘지 않고, 같은 학생의 같은 대상 과목은 다른 판정에서 다시 인정하지 않는다 — 판정 서비스가 검사(N:1은 한 판정의 여러 줄이 같은 대상을 가리켜 DB 유니크로 표현하지 않음). 0010이 0009 뒤 인정 학점이 있는 판정을 옮겼다.

**credit_conversion_rules** — `target_institution_id` FK(IX), `source_system`·`target_system` VARCHAR(20)(CHECK), `factor` DECIMAL(6,3)(>0, 출신 1학점 = factor × 대상 학점), `method` VARCHAR(20)(approved_table·contact_hours·manual), `effective_from` DATE NN, `effective_to` DATE null(≥ from), `approved_by` FK→users, `note` TEXT, `created_at`. 고치지 않고 끝내는 날을 정한 뒤 새 규칙을 추가한다(지난 판정이 쓴 규칙이 남음). 그 날짜에 유효한 규칙이 없거나 둘 이상(같은 시작일)이면 환산을 보류한다.

**material_requests** — `syllabus_id` FK(IX), `course_evaluation_id` FK, `requested_by` FK→users, `items` JSONB(요청 항목, 한국어 원문), `note` TEXT, `status` VARCHAR(20)(open·fulfilled, IX), `fulfilled_at` TIMESTAMP null.

**supplement_files** — `syllabus_id` FK(IX), `file_key` VARCHAR(255) null(삭제 후 null), `material_request_id` FK null(요청 없이 낸 사전 시뮬레이션 자료는 null).

**appeals**

| 속성 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| course_evaluation_id | BIGINT | FK, NN, IX | 심사 건 |
| decision_id | BIGINT | FK→decisions, NN | 이의를 건 판정 |
| student_id | BIGINT | FK→users, NN, IX | 신청한 학생 |
| reason | TEXT | NN | 사유 20~3000자 |
| status | VARCHAR(20) | NN, IX | submitted · accepted · dismissed · redecided |
| handled_by · handled_at · handler_note | BIGINT FK · TIMESTAMP · TEXT | null·null·NN | 처리한 심사관·시각·메모 (기각 시 필수) |
| due_at | TIMESTAMP | null | 학사처 처리 기한: 접수 + 학칙 정책 `appeal_review` 일 수 (Alembic 0014, 리뷰 v3 P1-5). 정책이 없으면 비움. 하루 안에 오거나 지나면 심사관 기한 알림 |
| (부분 유니크 인덱스) | `uq_appeals_open_evaluation` | UQ | `course_evaluation_id` `WHERE status IN ('submitted', 'accepted')` — 심사 건당 처리 중 이의 신청 하나 |

**appeal_files** — `appeal_id` FK(IX), `file_key` VARCHAR(255) null, `original_filename` VARCHAR(255), `content_type` VARCHAR(100), `size` INT.

**evaluation_notes** — `syllabus_id` FK(IX, 재분석해도 이어지게 강의계획서 단위), `course_evaluation_id` FK(쓴 분석 회차), `author_id` FK→users, `body` TEXT(1000자). 고치지 않고 새로 남기며 삭제 승인 때만 지운다.

**equivalencies** — `target_institution_id` FK(`target_institution_id, source_institution_id, source_course_key` 복합 IX), `source_institution_id` FK, `source_course_key` VARCHAR(100)(IX, 비교용 정규화 키), `source_course_label` VARCHAR(255), `target_course_id` FK→courses null, `result` VARCHAR(10), `decided_on` DATE null, `note` TEXT(기관 내부 메모, 학생에게 안 보임), `imported_by` FK→users.

### 3.5 개인정보·운영

**privacy_requests** — `transfer_request_id` FK(IX), `student_id` FK→users, `status` VARCHAR(20)(requested·reviewed·completed, IX), `due_at` TIMESTAMP(처리 기한), `reviewed_by`·`reviewed_at`(심사관 처리), `approved_by`·`completed_at`(관리자 승인·삭제 완료), 부분 유니크 인덱스 `uq_privacy_requests_open_request`(`transfer_request_id` `WHERE status <> 'completed'` — 요청당 처리 중 삭제 요청 하나).

**notifications** — `user_id` FK(`user_id, read_at` 복합 IX), `kind` VARCHAR(30)(assignment.created 등), `message` VARCHAR(500)(한국어 원문, 화면·메일에서 받는 사람 언어로), `link` VARCHAR(255), `read_at` null, `emailed_at` null, `pushed_at` null(웹 푸시를 보낸 시각, Alembic 0002).

**push_subscriptions** — 웹 푸시 구독(FR-20, Alembic 0002). `user_id` FK(IX), `endpoint` VARCHAR(1000) UQ(브라우저 푸시 서비스 주소, 기기마다 다름), `p256dh` VARCHAR(200)·`auth` VARCHAR(100)(내용 암호화 키, RFC 8291), `last_sent_at` null. 같은 브라우저에서 다른 계정으로 구독하면 그 계정으로 옮기고, 푸시 서비스가 만료(404·410)를 알리거나 사용자가 끄면 행을 지운다. 알림보다 나중에 구독한 기기에는 그 알림을 보내지 않는다.

**sis_syncs** — 판정 하나가 학사정보시스템에 반영됐는지 (Alembic 0015, 리뷰 v3 P1-4). `decision_id` FK→decisions UQ(`uq_sis_syncs_decision`, 판정당 한 행), `institution_id` FK(IX), `status` VARCHAR(10)(pending·applied·failed, CHECK, IX — 행이 없으면 대기), `external_reference_id` VARCHAR(100) null(SIS 쪽 기록 번호), `attempts` INT(실패로 보고된 횟수), `last_error` TEXT, `acknowledged_at`(마지막 결과를 받은 시각), `created_at`, `updated_at`. 판정은 추가 전용이라 반영 상태는 이 표에 둔다. 이미 반영된 판정에 다른 번호가 오면 고치지 않고 대사 불일치로 알린다.

**sis_ack_requests** — 반영 결과 요청의 Idempotency-Key (Alembic 0015). `institution_id` FK, `idempotency_key` VARCHAR(100), (`institution_id`, `idempotency_key`) UQ, `request_hash` VARCHAR(64)(같은 키에 다른 내용이면 409), `response` JSONB(처음 응답 — 같은 키로 다시 오면 그대로 돌려줌), `created_at`.

**background_jobs** — 백그라운드 분석 작업 하나 (Alembic 0017, 리뷰 v3 P1-3). `institution_id` FK null(`institution_id, created_at` 복합 IX), `job_type` VARCHAR(40)(syllabus.process·syllabus.supplement·syllabus.evaluate·transcript.process_student·reference.process), `subject_type` VARCHAR(20)(syllabus·student)·`subject_id`(대상 id, 외래키 없음), `status` VARCHAR(12)(queued·running·succeeded·retry_wait·failed·dead_letter, CHECK, IX), `attempt_count`, `error_code` VARCHAR(60)(llm_rate_limit·llm_timeout·llm_connection·llm_server·llm_invalid_output·llm_refusal·llm_error·not_configured·document_unreadable·task_timeout·unexpected:예외 이름), `started_at`·`completed_at`, `duration_ms`(마지막 시도), `task_args` JSONB(다시 처리할 인자: id·파일 키만), `created_at`. 일시 오류는 최대 3번 지수 간격으로 다시 하고 넘기면 격리, 다시 해도 안 되는 오류는 곧바로 실패. 문서 내용·이름은 넣지 않는다.

**llm_usage** — AI 호출 사용량 (Alembic 0020, 리뷰 v3 13.7 비용 지표). `institution_id` FK null(`institution_id, created_at` 복합 IX), `job_id` FK→background_jobs null(IX, 작업 시도마다 한 묶음), `purpose` VARCHAR(60)(출력 모델 이름: SyllabusExtraction·EvaluationOutput·PageTranscription·TranscriptExtraction), `model` VARCHAR(100)(응답이 알려 준 모델), `calls` INT, `input_tokens` INT(캐시 쓰기·읽기 포함), `output_tokens` INT, `created_at`. 검증 실패로 다시 부른 호출도 센다. 비용은 저장하지 않고 화면에서 설정 단가(`AI_PRICE_*`)로 어림한다. 문서 내용·이름은 넣지 않는다.

**audit_logs** — 추가 전용(INSERT만). `actor_id` FK→users null(시스템 행위는 null, `actor_id, action` 복합 IX), `action` VARCHAR(50)(IX), `target_type` VARCHAR(50)·`target_id` VARCHAR(36)(대상, 외래키 없음, `target_type, target_id` 복합 IX), `payload_json` JSONB(id·판정값만, 이름·학번·성적 없음).

## 4. 관계

| # | 관계 | 카디널리티 | 외래키 | 근거 (기능 명세) |
| --- | --- | --- | --- | --- |
| 1 | 기관 – 사용자 | 1 : N (사용자 쪽 0..1) | users.institution_id | FR-12 소속 기관 건만 접근 |
| 2 | 사용자 – 대리 심사자 (자기 참조) | 0..1 : N | users.delegate_user_id | FR-19 |
| 3 | 대상 대학 – 과목 | 1 : N | courses.institution_id | FR-05 카탈로그 |
| 3a | 대상 대학 – 학과 | 1 : N | departments.institution_id | FR-18 |
| 3d | 대상 대학 – 출신 대학 목록 – 출신 대학 | N : M | institution_sources.institution_id·source_institution_id | FR-12 대학별 목록 |
| 3b | 학과 – 과목 | 1 : N | courses.department_id | FR-05 후보 필터 |
| 3c | 학과 – 교수 | 0..1 : N | users.department_id | FR-18 자동 배정, FR-19 같은 학과 대리 |
| 4 | 과목 – 기준 강의계획서 | 0..1 : 0..1 | courses.reference_syllabus_id | FR-05 개념 비교 기준 |
| 5 | 학생 – 편입 요청 | 1 : N | transfer_requests.student_id | FR-15 |
| 6 | 출신·대상 대학 – 편입 요청 | 1 : N (두 번) | source_institution_id, target_institution_id | FR-15 |
| 7 | 편입 요청 – 강의계획서 | 1 : N (요청당 최대 30) | syllabi.transfer_request_id | FR-01 |
| 8 | 편입 요청 – 성적표 과목 | 1 : N | transcript_entries.transfer_request_id | FR-02 |
| 9 | 성적표 과목 – 강의계획서 | N : 0..1 | transcript_entries.syllabus_id | FR-02 자동 연결·학생 확인 |
| 10 | 강의계획서 – 청크 | 1 : N (함께 삭제) | syllabus_chunks.syllabus_id | FR-03 |
| 11 | 강의계획서 – 분석 | 1 : N (최신 1개 is_latest) | course_evaluations.syllabus_id | FR-05 재분석 이력, FR-22 |
| 12 | 과목 – 분석 (1순위 후보) | 0..1 : N | course_evaluations.candidate_course_id | FR-05 |
| 13 | 분석 – 근거 구절 | 1 : N | evidence_spans.course_evaluation_id | FR-06 |
| 13a | 근거 구절 – 교수 확인 | 1 : N (교수당 1개) | evidence_feedback.evidence_span_id, user_id | FR-06 근거 정확도 |
| 14 | 분석 – 배정 | 1 : N (활성 1개) | assignments.course_evaluation_id | FR-18 |
| 15 | 교수 – 배정 | 1 : N | assignments.reviewer_id, reassigned_from | FR-18·19 |
| 16 | 분석 – 판정 | 1 : N (원 판정 + 재판정) | decisions.course_evaluation_id | FR-09·10 |
| 17 | 교수 – 판정 | 1 : N | decisions.decided_by | FR-09 사람만 확정 |
| 18 | 판정 – 이의 신청 | 1 : N (처리 중 1개) | appeals.decision_id | FR-23 |
| 19 | 이의 신청 – 재판정 | 0..1 : N | decisions.appeal_id | FR-23 재판정도 새 행 |
| 20 | 이의 신청 – 근거 자료 | 1 : N (최대 3) | appeal_files.appeal_id | FR-23 |
| 21 | 분석 – 보완 요청 | 1 : N | material_requests.course_evaluation_id (+ syllabus_id) | FR-22 |
| 22 | 보완 요청 – 보완 자료 | 0..1 : N | supplement_files.material_request_id | FR-22 |
| 23 | 강의계획서 – 내부 메모 | 1 : N | evaluation_notes.syllabus_id | 운영 |
| 24 | 편입 요청 – 삭제 요청 | 1 : N (처리 중 1개) | privacy_requests.transfer_request_id | FR-13 |
| 25 | 사용자 – 알림 | 1 : N | notifications.user_id | FR-19·20 |
| 25-1 | 사용자 – 푸시 구독 | 1 : N (기기마다) | push_subscriptions.user_id | FR-20 |
| 26 | 사용자 – 감사 로그 | 0..1 : N | audit_logs.actor_id | FR-10 |
| 27 | 대상·출신 대학, 과목 – 동등 과목표 | 1 : N | equivalencies.* | FR-11·26 |
| 29 | 판정 – 배분 – 출신 과목 | 1 : N · 1 : N | credit_allocations.decision_id, syllabus_id | 리뷰 v3 P0-3 (N:1 합쳐 인정) |
| 28 | 대상 대학 – 환산 규칙 – 판정 | 1 : N · 0..1 : N | credit_conversion_rules.target_institution_id, decisions.conversion_rule_id | 리뷰 v3 P0-1·2 |
| 30 | 판정 – SIS 반영 상태 | 1 : 0..1 | sis_syncs.decision_id | 리뷰 v3 P1-4 |

### 4.1 API가 쓰는 데이터 (API_Spec.md 연결)

| 엔티티 | 만드는 API | 바꾸는 API | 읽는 화면(조회 API) |
| --- | --- | --- | --- |
| institutions | M8, 첫 관리자 스크립트 | M12(토큰), M21(쓰는 곳이 없으면 삭제) | S1·S15·M11 |
| institution_sources | M8 | M21(삭제) | M2·M15·S15, M5·R11(이름 확인) |
| users | M5, 첫 관리자 스크립트 | A3(실패 수·언어), A5, A7, A11, F2, M6, M7, M16(이름·department_id·대리 심사자) | 대부분 (권한·이름) |
| departments | M3(새 학과명), M5 | – | M2·M14·M15·R1·M1(학과별 지표) |
| courses | M3 | M3, M4 | R1·S10·R4·F3·M2 |
| transfer_requests | S2 | S5, S7, S8, 판정 완료 시 | S1·S3·R1 |
| syllabi | S4, M4 | S11, 작업 큐(추출·분석), M10(삭제) | S3·S10·R4·F3·C3 |
| transcript_entries | S5(작업 큐) | S6 | S3 |
| course_evaluations · evidence_spans | 작업 큐(분석) | 재분석 시 is_latest | S3·S10·R1·R4·F1·F3·C1·J1·M1·R12(인용 수) |
| evidence_feedback | F6 | F6(다시 누르면 고침) | F3(내가 누른 값)·M1·R12(근거 정확도) |
| assignments | R2, R7(재판정), F2(대리), M7(비활성화 인계), M18·M19(관리자 배정) | 같은 API | R1·F1·F3·M17 |
| decisions | F4, J2 | – (추가 전용) | S3·S10·R4·F3·C1·M1·J1·J3·R3 |
| appeals · appeal_files | S13 | R7 | S14·R6·S10·C5 |
| material_requests · supplement_files | R5, F5 · S11, R13(심사관 대신 올리기) | S11, R13 | S3·S10·R4·F3 |
| evaluation_notes | C4 | – | R4·F3 |
| equivalencies | R11 | – | R10·S15·R4·F3(과거 이력) |
| privacy_requests | S8 | R9, M10 | S3·R8·M9·M1 |
| notifications | 여러 처리 API, 기한 알림 작업 | A12·S10·S14(읽음), 알림 발송 작업(메일·푸시 시각) | A12·A13 |
| push_subscriptions | A15 | A15(다른 계정으로 옮김), A16·발송 작업(삭제) | A12(기기 수) |
| audit_logs | 거의 모든 처리 API, C3·C5 열람 | – (추가 전용) | M13(조건별·50건씩)·M1·C1·R4 |

## 5. 설계 규칙

| 규칙 | 적용 |
| --- | --- |
| 추가 전용 | `decisions`, `audit_logs`는 INSERT만. 앱 DB 계정에 UPDATE·DELETE 권한을 주지 않는다 (`docs/db-grants.sql`). 판정을 바꾸면 새 행 |
| 이력 보존 | `course_evaluations`(재분석), `assignments`(재배정), `evaluation_notes`는 고치지 않고 새 행 |
| 지우지 않는 삭제 | 개인정보 삭제는 파일 키를 null로, 글을 비우고 상태를 deleted로. 판정·감사 기록이 가리키는 행은 남긴다. 계정은 비활성화 |
| DB 검사 | 상태·코드 컬럼은 허용 목록 CHECK(`ck_<테이블>_<컬럼>_valid`), 0~1 점수·근거 위치·학점·파일 크기는 범위 CHECK. 허용 목록은 `backend/models/enums.py`와 같고, 값을 늘리면 모델과 새 마이그레이션을 함께 고친다 |
| JSON 사용 | `JSONB`라 형식은 DB가 검사한다. 구조 검증은 Pydantic, 검색 조건에 쓰는 값은 JSON 밖 일반 컬럼으로 (`course_code`, `recommendation`, `coverage` 등) |
| 결과 재사용 | `syllabi.content_hash`(같은 문서), `course_evaluations.input_hash`(같은 비교 입력)로 LLM 재호출을 막는다 |
| 개인정보 | 이름은 `users.name`, 성적은 `transcript_entries`에만. 알림·감사 로그·AI 입력에는 넣지 않는다 (성적표는 가린 뒤 AI에) |
| 다국어 | 저장하는 안내 글은 한국어 원문, 화면에서 번역. AI 설명은 `coverage_json`에 한국어·영어(`*_en`) 두 벌 |

## 6. 검토 결과

### 6.1 저장되는 데이터 구조 (엔티티·속성)

| 점검 | 결과 |
| --- | --- |
| 기능 명세의 데이터가 모두 저장되는가 | ✅ FR-01~FR-27의 입력·출력이 모두 엔티티에 있다 (1절 주요 FR). FR-27 통계, FR-17 큐, FR-11 유사도는 저장하지 않고 조회할 때 계산. FR-28(복수 대학 비교)은 범위 밖이라 없음 |
| API가 쓰는 데이터가 모두 엔티티에 있는가 | ✅ 4.1절. 엔티티 21개 모두 만드는 API와 읽는 화면이 있다 |
| 판정 확률 컬럼이 없는가 | ✅ 없음 (MVP 규칙) |
| 원본 파일을 DB에 넣지 않는가 | ✅ 파일 키만 |

고칠 만한 점:

| # | 항목 | 내용 | 권장 |
| --- | --- | --- | --- |
| E1 | 학과가 글자 ✅ 반영 (0011) | `users.department`와 `courses.department`가 자유 글자다. 철자가 다르면 자동 배정이 안 된다 (화면이 "교수 없는 학과"로 경고만 함). 기능 명세 권한표의 "학과 설정"을 담을 곳도 없다 | `departments`(institution_id, name, UQ) 엔티티를 만들고 두 컬럼을 `department_id` FK로. (2026-10-19 반영: Alembic 0011이 기존 글자 값으로 학과 행을 만들고 id로 옮긴 뒤 글자 컬럼을 지웠다. 학생의 편입 전공 `transfer_requests.major`는 요청 당시 이름을 남기는 기록이라 글자로 둔다) |
| E2 | JSON 유효성 검사 ✅ 문제 아님 (확인) | `syllabi.extracted_json`에만 `JSON_VALID` CHECK가 있다. MariaDB의 JSON은 LONGTEXT라 나머지 JSON 컬럼(`courses.concepts`, `decisions.reason_codes`·`ai_recommendation_snapshot`, `course_evaluations.coverage_json`, `material_requests.items`, `audit_logs.payload_json`, `syllabi.page_offsets`·`injection_flags`)에는 잘못된 값이 들어갈 수 있다 (DB 규칙 위반) | 다시 확인해 보니 MariaDB가 `JSON`으로 만든 컬럼마다 `CHECK (json_valid(col))`를 자동으로 붙인다(`SHOW CREATE TABLE`로 확인). MySQL 8.0은 JSON 형식 자체가 검사한다. 추가할 것 없음. (PostgreSQL 전환 뒤에는 모든 JSON 컬럼이 `JSONB`라 형식 검사가 기본) |
| E3 | 상태·코드 값 검사 ✅ 반영 (0009) | `role`, `status`, `recommendation`, `result`, `action`, `side` 등이 VARCHAR이고 허용 값 검사가 앱에만 있다 | `CHECK (status IN (...))` 추가 (PostgreSQL 기준점 0001에 그대로 들어 있음) |
| E4 | 값 범위 검사 ✅ 반영 (0009) | `coverage`·`quality_score`·`link_score`(0~1), `evidence_spans.char_start < char_end`가 DB에서 검사되지 않는다 | CHECK 추가 |
| E5 | 사유 코드가 JSON 배열 | `decisions.reason_codes`라 "사유별 반려 건수" 같은 통계를 SQL로 못 내고 앱에서 센다 | 지금 규모에서는 그대로. 사유 통계가 필요해지면 `decision_reasons(decision_id, code)` |
| E6 | `syllabi.institution_id`의 뜻이 둘 | 학생 강의계획서는 대상 대학, 기준 강의계획서는 과목의 대학이다. 출신 대학이 아니라서 헷갈린다 | 컬럼 설명을 문서에 고정하거나, 학생 것은 `transfer_request`에서 얻고 이 컬럼은 기준 강의계획서 전용으로 |

### 6.2 데이터 간 관계

| 점검 | 결과 |
| --- | --- |
| 기능 명세의 관계가 모두 외래키로 있는가 | ✅ 4절 27개. 재분석·재배정·재판정 이력이 1:N으로 남는다 |
| 판정이 사람과 연결되는가 | ✅ `decisions.decided_by` NN FK (FR-09) |
| 이의 신청과 재판정 | ✅ 판정→이의(`appeals.decision_id`), 이의→재판정(`decisions.appeal_id`). 서로 참조하는 고리지만 둘 다 이전 행을 가리켜 넣는 순서 문제는 없다 |

고칠 만한 점:

| # | 항목 | 내용 | 권장 |
| --- | --- | --- | --- |
| R1 | "하나만" 규칙이 DB에 없다 ✅ 반영 (0010) | 심사 건당 활성 배정 1개, 처리 중 이의 신청 1개, 요청당 처리 중 삭제 요청 1개, 강의계획서당 `is_latest` 1개를 앱이 지킨다. 동시에 두 요청이 들어오면 둘 다 들어갈 수 있다 | MariaDB 때는 부분 유니크 인덱스가 없어 생성 컬럼(`IF(is_active, course_evaluation_id, NULL)`에 UNIQUE)으로 막았고, PostgreSQL로 옮기며 부분 유니크 인덱스(`... WHERE is_active`)로 바꿨다 |
| R2 | 같은 값을 두 곳에 둔다 | `course_evaluations.transfer_request_id`(강의계획서에서 얻을 수 있음), `appeals.student_id`·`privacy_requests.student_id`(요청에서), `material_requests.syllabus_id`·`evaluation_notes.syllabus_id`(분석에서), `evidence_spans`(= `coverage_json`의 근거 위치) | 권한 검사·재분석 묶기·감사에 쓰려고 일부러 둔 것이다. 값이 어긋나지 않도록 만드는 곳을 서비스 한 곳으로 두고, 정합성 점검 쿼리를 테스트에 넣는다 ✅ 반영 (2026-11-12, `repositories/integrity.py`·`scripts/integrity_check.py`·`test_integrity.py`, 배분 원장 학생 점검 포함) |
| R3 | 자주 쓰는 조회에 맞는 복합 인덱스가 없다 ✅ 반영 (0009, 앞 컬럼이 같은 단일 인덱스는 지움) | `audit_logs(target_type, target_id)` — 심사 건 처리 기록·리포트가 매번 전체를 훑는다 · `notifications(user_id, read_at)` — 60초마다 안 읽은 수 · `assignments(course_evaluation_id, is_active)`, `assignments(reviewer_id, is_active)` · `course_evaluations(syllabus_id, is_latest)` · `equivalencies(target_institution_id, source_institution_id, source_course_key)` | Alembic 마이그레이션으로 추가. 특히 `audit_logs`는 계속 쌓이는 테이블이라 먼저 |
| R4 | 감사 로그 대상에 외래키가 없다 | `audit_logs.target_type`·`target_id`는 여러 테이블을 가리키는 다형 참조라 FK가 없다 | 대상 행이 지워져도 기록이 남아야 하므로 의도한 설계. 그대로 둔다 |
| R5 | 지울 때 동작 | `syllabus_chunks`만 CASCADE, 나머지는 기본(RESTRICT). 앱은 행을 지우지 않고 키를 비우는 방식이라 맞다 | 그대로. 운영자가 SQL로 직접 지우지 않도록 `db-grants.sql`을 유지 |

### 6.3 권장 순서

1. **R3 인덱스** — 데이터가 쌓이면 바로 느려지는 곳. 동작은 바뀌지 않는다.
2. **E2·E3·E4 CHECK 제약** — DB 규칙(JSON_VALID)과 맞추고 잘못된 값을 막는다.
3. **R1 "하나만" 유니크** — 동시 요청 대비.
4. **E1 학과 엔티티** — 관리자 계정 수정 API(API_Spec 6.3)와 함께.

1~3은 반영했다 (2026-10-19, 당시 Alembic 0009·0010 — 지금은 PostgreSQL 기준점 0001에 포함, 테스트 `tests/integration/test_db_rules.py`). 동시에 들어온 두 번째 이의 신청·삭제 요청은 DB 유니크에 걸리면 "이미 처리 중" 안내로 바꿔 보여 준다(`DuplicateRowError`). 4(E1 학과 엔티티)도 반영했다 (당시 Alembic 0011).
