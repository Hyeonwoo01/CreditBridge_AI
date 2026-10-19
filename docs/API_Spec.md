# CreditBridge AI API 명세서

코드(`backend/web/routes/`, `backend/web/api/`)에서 뽑은 전체 엔드포인트 74개와, 화면 버튼·화면 데이터가 어느 API에 연결되는지 정리했다. 마지막 절에 검토 결과가 있다.

- 기준: 2026-10-19 main. 화면 번호(P00~P25)는 [화면 명세서](screens/README.md), 기능 번호(FR)는 [기획 통합본](spec.md) 4장 기능 명세.
- 데이터 구조는 [ERD.md](ERD.md).

## 1. 개요

### 1.1 구조

CreditBridge AI는 서버가 화면을 그려 보내는 앱이다 (FastAPI + Jinja2 + HTMX). 그래서 API는 다섯 종류로 나뉜다.

| 종류 | 형태 | 개수 | 설명 |
| --- | --- | --- | --- |
| 화면 조회 | `GET` → HTML | 28 | 화면 하나에 조회 API 하나. 화면에 보이는 데이터를 서버가 모아 HTML에 넣어 보낸다 (조회 함수는 5절) |
| 이동 | `GET` → 303 | 2 | `GET /`(역할별 홈으로), `GET /student/syllabi/{id}`(최신 분석으로) |
| 처리(버튼) | `POST` (폼) → 303 리다이렉트 + 플래시 | 35 | 버튼 하나가 POST 하나를 부른다. 입력 오류는 같은 화면을 422로 다시 보여 주거나 빨강 플래시 |
| 파일 내려받기 | `GET` → PDF·CSV·원본 파일 | 4 | 리포트 PDF, 원본 강의계획서, 이의 신청 근거 자료, SIS CSV |
| HTMX 조각 | `GET` → HTML 조각 | 2 | 알림 배지 숫자, 상단 보조 바 집계 칩 |
| JSON API | `GET`/`POST` → JSON | 3 | 분석 결과 조회, 판정 저장, 학사정보시스템 연동 |
| 합계 | | 74 | GET 38, POST 36 |

### 1.2 공통 규칙

| 항목 | 규칙 |
| --- | --- |
| 인증 | 로그인하면 세션 쿠키 `cb_session`(서명, HttpOnly, SameSite=Lax, 운영은 Secure, 8시간). 로그인 안 했으면 화면은 `/login`으로 303, JSON API는 401 |
| 첫 로그인 | 임시 비밀번호 계정은 비밀번호를 바꾸기 전까지 `/account/password`로 303 (JSON API는 403) |
| CSRF | 모든 POST에 필요. 폼은 `csrf_token` 필드, HTMX·JSON은 `X-CSRF-Token` 헤더. 틀리면 403 |
| 권한 | 역할(학생·심사관·교수·관리자)과 대상(본인 건·소속 기관 건·배정 건)을 함께 검사. 어긋나면 403 오류 화면 (P17) |
| 오류 | 화면: 400·403·404는 오류 화면, 입력 오류는 422로 같은 화면 또는 플래시. JSON: `{"detail": "..."}`와 401·403·404·409·422 |
| 언어 | `cb_lang` 쿠키 → 브라우저 `Accept-Language` → 한국어. 응답 문구·오류 메시지가 이 언어로 나온다 |
| 시각 | DB와 API는 UTC. 화면은 브라우저가 현지 시각으로 바꿔 보여 준다 |
| 파일 | 업로드 PDF·JPG·PNG 20MB(강의계획서·이의 근거 자료), CSV 5MB. 내려받기는 `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` |

### 1.3 역할 표기

`공개` 로그인 없이 · `로그인` 로그인한 누구나(대상 권한은 따로 검사) · `학생` · `심사관` · `교수` · `관리자` · `토큰` SIS 연동 토큰

## 2. 엔드포인트 목록

응답 표기: `HTML` 화면 · `303→경로` 처리 후 이동 · `422` 같은 화면을 오류와 함께 다시 · `파일` 내려받기 · `JSON`

### 2.1 인증·계정·공통

| # | 메서드 | 경로 | 역할 | 입력 | 응답 | 화면 | FR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | GET | `/` | 공개 | – | 303→역할별 홈 또는 `/login` | – | FR-12 |
| A2 | GET | `/login` | 공개 | – | HTML | P01 | FR-12 |
| A3 | POST | `/login` | 공개 | `email`, `password`, `csrf_token` | 303→역할별 홈·`/account/password` / 401·403·423·429 HTML | P01 | FR-12 |
| A4 | POST | `/logout` | 로그인 | `csrf_token` | 303→`/login` | P00 | – |
| A5 | POST | `/lang` | 공개 | `lang`(ko·en), `next`(같은 사이트 경로), `csrf_token` | 303→`next` (쿠키·계정 언어 저장) | P00 | NF-11 |
| A6 | GET | `/account/password` | 로그인 | – | HTML | P19 | – |
| A7 | POST | `/account/password` | 로그인 | `current`, `new`, `confirm`, `csrf_token` | 303 / 422 | P19 | – |
| A8 | GET | `/account/forgot` | 공개 | – | HTML | P20 | – |
| A9 | POST | `/account/forgot` | 공개 | `email`, `csrf_token` | HTML (계정 유무와 상관없이 같은 안내) | P20 | – |
| A10 | GET | `/account/reset` | 공개 | `token`(메일 링크) | HTML | P20 | – |
| A11 | POST | `/account/reset` | 공개 | `token`, `new`, `confirm`, `csrf_token` | 303→`/login` / 422 | P20 | – |
| A12 | GET | `/notifications` | 로그인 | – | HTML (열면 모두 읽음) | P14 | FR-19·20 |
| A13 | GET | `/notifications/count` | 로그인 | – | HTML 조각(안 읽은 수) | P00 | FR-20 |
| A14 | GET | `/notifications/workspace` | 심사관·교수·관리자 | – | HTML 조각(제출·대기·완료 칩) | P00 | FR-17 |

### 2.2 학생

| # | 메서드 | 경로 | 역할 | 입력 | 응답 | 화면 | FR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S1 | GET | `/student` | 학생 | – | HTML | P02 | FR-15·21 |
| S2 | POST | `/student/requests` | 학생 | `source_institution_id`, `major`, `csrf_token` | 303→`/student/requests/{id}` | P02 | FR-15 |
| S3 | GET | `/student/requests/{id}` | 학생(본인) | `show`(all·approved·supplement·review), `tuition`, `degree` | HTML | P03 | FR-01·02·15·21 |
| S4 | POST | `/student/requests/{id}/syllabi` | 학생(본인) | `files[]`(최대 30), `csrf_token` | 303→S3 | P03 | FR-01 |
| S5 | POST | `/student/requests/{id}/transcript` | 학생(본인) | `file`, `csrf_token` | 303→S3 | P03 | FR-02·13 |
| S6 | POST | `/student/requests/{id}/entries/{entry_id}` | 학생(본인) | `syllabus_id`(빈 값=연결 안 함), `csrf_token` | 303→S3`#transcript` | P03 | FR-02 |
| S7 | POST | `/student/requests/{id}/submit` | 학생(본인) | `csrf_token` | 303→S3 | P03 | FR-21 |
| S8 | POST | `/student/requests/{id}/delete-documents` | 학생(본인) | `csrf_token` | 303→S3 | P03 | FR-13 |
| S9 | GET | `/student/syllabi/{id}` | 학생(본인) | – | 303→그 강의계획서의 최신 분석(S10) | P03 | – |
| S10 | GET | `/student/evaluations/{id}` | 학생(본인) | – | HTML (새 결과 알림 읽음 처리) | P04 | FR-05~08·22·25 |
| S11 | POST | `/student/syllabi/{id}/supplement` | 학생(본인) | `file`, `csrf_token` | 303→S3 | P04 | FR-22 |
| S12 | GET | `/student/evaluations/{id}/appeal` | 학생(본인) | – | HTML | P22 | FR-23 |
| S13 | POST | `/student/evaluations/{id}/appeal` | 학생(본인) | `reason`(20~3000자), `files[]`(최대 3), `csrf_token` | 303→S14 / 422 | P22 | FR-23 |
| S14 | GET | `/student/appeals` | 학생 | – | HTML (새 이의 결과 읽음 처리) | P21 | FR-23 |
| S15 | GET | `/student/precedents` | 학생 | `q`, `source` | HTML | P23 | FR-26 |

### 2.3 심사관 (학사처)

| # | 메서드 | 경로 | 역할 | 입력 | 응답 | 화면 | FR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | GET | `/review` | 심사관 | `tab`(all·high·low·insufficient·conflict), `department`, `sort`(submitted·coverage·department), `q`(≤100), `page` | HTML | P05 | FR-11·17 |
| R2 | POST | `/review/assign` | 심사관 | `evaluation_ids[]`, `tab`, `csrf_token` | 303→R1 | P05 | FR-18 |
| R3 | GET | `/review/export.csv` | 심사관 | – | 파일(CSV) | P05·P10 | FR-24 |
| R4 | GET | `/review/evaluations/{id}` | 심사관(소속 기관) | – | HTML | P06 | FR-05~11·22·25 |
| R5 | POST | `/review/evaluations/{id}/materials` | 심사관 | `items[]`, `note`, `csrf_token` | 303→R4 | P06 | FR-22 |
| R13 | POST | `/review/evaluations/{id}/supplement` | 심사관(소속 기관, 판정 전·최신 분석) | `file`(PDF·JPG·PNG), `csrf_token` | 303→R1 (재분석은 작업 큐) / 오류는 303→R4`#supplement` | P06 | FR-22, 권한 매트릭스 문서 업로드 |
| R6 | GET | `/review/appeals` | 심사관 | – | HTML | P07 | FR-23 |
| R7 | POST | `/review/appeals/{id}` | 심사관 | `action`(accept·dismiss), `reviewer_id`(accept), `note`(dismiss 필수), `csrf_token` | 303→R6 | P07 | FR-23 |
| R8 | GET | `/review/privacy` | 심사관 | – | HTML | P08 | FR-13 |
| R9 | POST | `/review/privacy/{id}` | 심사관 | `csrf_token` | 303→R8 | P08 | FR-13 |
| R10 | GET | `/review/equivalencies` | 심사관 | – | HTML | P09 | FR-26 |
| R11 | POST | `/review/equivalencies` | 심사관 | `file`(CSV), `csrf_token` | 303→R10 / 422 | P09 | FR-26 |
| R12 | GET | `/review/stats` | 심사관 | – | HTML | P10 | FR-27 |

### 2.4 학과 교수

| # | 메서드 | 경로 | 역할 | 입력 | 응답 | 화면 | FR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | GET | `/professor` | 교수 | – | HTML | P11 | FR-18·19 |
| F2 | POST | `/professor/away` | 교수 | `days`(0=복귀), `delegate_id`, `csrf_token` | 303→F1 | P11 | FR-19 |
| F3 | GET | `/professor/evaluations/{id}` | 교수(배정·판정 건) | – | HTML | P12 | FR-05~11·16·20·25 |
| F4 | POST | `/professor/evaluations/{id}/decision` | 교수(배정 건) | `action`(approve·modify·reject), `result`, `target_course_id`, `reason_codes[]`, `reason_memo`, `acknowledge_conflict`, `csrf_token` | 303→F1 / 409(경보 확인 필요)·422 HTML | P12 | FR-09·10·11 |
| F5 | POST | `/professor/evaluations/{id}/materials` | 교수(배정 건) | `items[]`, `note`, `csrf_token` | 303→F3 | P12 | FR-22 |

### 2.5 여러 역할 공용 (심사 건)

| # | 메서드 | 경로 | 역할 | 입력 | 응답 | 화면 | FR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | GET | `/evaluations/{id}/report` | 학생(본인)·심사관·교수 | – | HTML | P13 | FR-10·23 |
| C2 | GET | `/evaluations/{id}/report.pdf` | 같음 | – | 파일(PDF, attachment) | P13 | FR-23 |
| C3 | GET | `/evaluations/{id}/original/{side}` | 같음 | `side`(source·target) | 파일(원본, inline, `#page=N`) · 학생 원본은 감사 로그 | P04·P06·P12 | FR-25 |
| C4 | POST | `/evaluations/{id}/notes` | 심사관·교수 | `body`(≤1000), `csrf_token` | 303→역할별 심사 건 화면`#notes` | P06·P12 | – |
| C5 | GET | `/appeal-files/{id}` | 학생(본인)·심사관·교수 | – | 파일(attachment) · 감사 로그 | P04·P07·P21 | FR-23 |

### 2.6 기관 관리자

| # | 메서드 | 경로 | 역할 | 입력 | 응답 | 화면 | FR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | GET | `/admin/stats` | 관리자 | – | HTML | P10 | FR-10·13·24·27 |
| M2 | GET | `/admin/data` | 관리자 | – | HTML | P18 | – |
| M3 | POST | `/admin/data/courses` | 관리자 | `file`(CSV), `csrf_token` | 303→M2`#courses` / 422 | P18 | – |
| M4 | POST | `/admin/data/courses/{id}/reference` | 관리자 | `file`, `csrf_token` | 303→M2`#courses` | P18 | FR-05 |
| M5 | POST | `/admin/data/accounts` | 관리자 | `file`(CSV), `csrf_token` | HTML(결과 카드, 임시 비밀번호는 한 번만) / 422 | P18 | FR-12 |
| M6 | POST | `/admin/data/password-reset` | 관리자 | `email`, `csrf_token` | 303 또는 HTML(임시 비밀번호 한 번만) | P18 | – |
| M7 | POST | `/admin/data/accounts/active` | 관리자 | `email`, `action`(deactivate·reactivate), `next`(선택, `/admin/accounts/{id}`만), `csrf_token` | 303→M2`#account-active` 또는 M15 | P18 | FR-12 |
| M8 | POST | `/admin/data/institutions` | 관리자 | `name`, `country`, `csrf_token` | 303→M2`#institutions` | P18 | – |
| M9 | GET | `/admin/privacy` | 관리자 | – | HTML | P08 | FR-13 |
| M10 | POST | `/admin/privacy/{id}` | 관리자 | `csrf_token` | 303→M9 | P08 | FR-13 |
| M11 | GET | `/admin/sis` | 관리자 | – | HTML | P15 | FR-24 |
| M12 | POST | `/admin/sis` | 관리자 | `action`(issue·revoke), `csrf_token` | HTML(새 토큰 한 번만) / 303 | P15 | FR-24 |
| M13 | GET | `/admin/audit` | 관리자 | `action`, `target_type`, `target_id`, `since`·`until`(UTC 날짜 YYYY-MM-DD), `page` | HTML (소속 기관 기록, 50건씩) | P16 | FR-10 |
| M14 | GET | `/admin/accounts` | 관리자 | `q`(이메일 일부), `role`, `status`(active·inactive·all), `page` | HTML (50건씩, 학생 이름 없음) | P24 | FR-12 |
| M15 | GET | `/admin/accounts/{id}` | 관리자 | – | HTML / 404(다른 기관) | P24 | FR-12·19 |
| M16 | POST | `/admin/accounts/{id}` | 관리자 | `name`(교직원), `department_id`(교수 필수·심사관 선택, 과목이 있는 학과만), `delegate_user_id`(교수), `csrf_token` | 303→M15 + 플래시 | P24 | FR-12·19 |
| M17 | GET | `/admin/assignments` | 관리자 | `show`(unassigned·all) | HTML (AI 결과 없이 접수·학생 과목·학과·담당 교수) | P25 | FR-18 |
| M18 | POST | `/admin/assignments/auto` | 관리자 | `evaluation_ids[]`, `csrf_token` | 303→M17 + 플래시 | P25 | FR-18·19 |
| M19 | POST | `/admin/assignments/{evaluation_id}` | 관리자 | `reviewer_id`, `show`, `csrf_token` | 303→M17 + 플래시 | P25 | FR-18 |

### 2.7 JSON API

| # | 메서드 | 경로 | 인증 | 설명 | FR |
| --- | --- | --- | --- | --- | --- |
| J1 | GET | `/api/evaluations/{id}` | 세션 | 분석 결과(추천)와 사람 판정 | FR-05~09 |
| J2 | POST | `/api/decisions` | 세션 + `X-CSRF-Token` | 최종 판정 저장 (F4와 같은 규칙) | FR-09·10 |
| J3 | GET | `/api/sis/decisions` | `Authorization: Bearer cbsis_...` | 확정 판정 내보내기 | FR-24 |

## 3. JSON API 상세

### J1 `GET /api/evaluations/{id}`

볼 권한은 화면과 같다 (학생 본인, 소속 기관 심사관, 배정·판정 교수).

```json
{
  "id": 6,
  "status": "done",
  "recommendation": "direct",
  "coverage": 0.9,
  "confidence": "high",
  "candidate_course": "PHYSICS 1250",
  "result": { "candidates": [ { "course_code": "PHYSICS 1250", "coverage": 0.9, "concepts": [ { "concept": "Kinematics", "status": "taught", "coverage": 0.9, "reason": "…", "reason_en": "…", "source_evidence": [ { "text": "…", "char_start": 208, "char_end": 280 } ] } ] } ], "missing_materials": [], "warnings": [] },
  "decision": { "result": "direct", "action": "approve", "reason_codes": [], "decided_at": "2026-10-13T09:00:00", "target_course": "PHYSICS 1250" }
}
```

판정 확률(%)은 MVP에서 계산·제공하지 않는다. 오류: 401 로그인 필요, 403 권한 없음, 404 없음.

### J2 `POST /api/decisions`

```json
{ "evaluation_id": 6, "action": "reject", "result": null, "target_course_id": null,
  "reason_codes": ["level_difference"], "reason_memo": "", "acknowledge_conflict": false }
```

- 201: `{"id": 31, "result": "none", "decided_by": 7}` — `decided_by`는 로그인한 교수 id로 서버가 정한다 (요청으로 받지 않음).
- 409: 같은 강의계획서 과거 판정과 결과가 달라 확인이 필요 (`acknowledge_conflict: true`로 다시).
- 422: 사유 누락(반려·추천과 다른 판정), '기타'인데 메모 없음, 정보 부족 건을 그대로 승인 등.
- 403: 배정 교수가 아님.

### J3 `GET /api/sis/decisions?since=2026-10-01T00:00:00Z`

```json
{ "institution": "Midwest State University", "count": 1,
  "decisions": [ { "decision_id": 31, "replaces_decision_id": 12, "student_id": 1,
    "source_institution": "Hankuk University (한국대학교)", "source_course": "PHY 101",
    "result": "direct", "target_course": "PHYSICS 1250", "credits": 4.0, "decided_at": "2026-10-13T09:00:00" } ] }
```

심사 건마다 현재 유효한 판정 한 줄. 이의 신청 재판정이면 `replaces_decision_id`에 대체한 판정. 이름·학번은 보내지 않고 내부 번호(`student_id`)만. 401: 토큰 없음·폐기됨.

## 4. 화면별 버튼 ↔ API 매칭

모든 버튼과 이동 링크를 템플릿에서 뽑아 엔드포인트와 맞췄다. `화면 안` = 서버를 부르지 않는 버튼.

### P00 공통 레이아웃 (모든 화면)

| 버튼·링크 | API |
| --- | --- |
| 로고 | A1 `GET /` |
| 역할별 메뉴 (학생 3·심사관 6·교수 1·관리자 7) | 각 화면 조회 API (S1·S14·S15 / R1·R6·R8·R10·R12·R3 / F1 / M1·M2·M14·M17·M9·M11·M13) |
| 알림 벨 | A12 `GET /notifications` (배지 숫자는 A13, 60초마다) |
| 이름·역할 (비밀번호 변경) | A6 `GET /account/password` |
| English / 한국어 | A5 `POST /lang` |
| 로그아웃 | A4 `POST /logout` |
| 보조 바 집계 칩 | A14 `GET /notifications/workspace` (자동) |

### P01 로그인 · P19 비밀번호 변경 · P20 찾기·재설정

| 화면 | 버튼·링크 | API |
| --- | --- | --- |
| P01 | 로그인 | A3 `POST /login` |
| P01 | 비밀번호를 잊으셨나요? | A8 `GET /account/forgot` |
| P19 | 비밀번호 바꾸기 | A7 `POST /account/password` |
| P19 | 로그아웃 (첫 로그인 강제 변경 중) | A4 |
| P20 | 재설정 링크 받기 | A9 `POST /account/forgot` |
| P20 | 비밀번호 바꾸기 (메일 링크로 연 화면) | A11 `POST /account/reset` |
| P20 | 재설정 링크 다시 받기 · 로그인으로 돌아가기 | A8 · A2 |

### 학생 화면

| 화면 | 버튼·링크 | API |
| --- | --- | --- |
| P02 | 새 요청 만들기 | S2 `POST /student/requests` |
| P02 | 요청 카드 · 할 일 항목 | S3 (할 일은 S3 `#upload`·`#transcript`·`#submit` 또는 S10) |
| P02 | 새 판정 결과 확인 | A12 |
| P03 | 분석 시작 (강의계획서 업로드) | S4 |
| P03 | 성적표 등록 | S5 |
| P03 | 성적표 과목 연결 [확인] | S6 |
| P03 | 학사처에 심사 요청 | S7 |
| P03 | 내 문서 삭제 요청 (확인창) | S8 |
| P03 | 과목 필터 4개 · 다시 계산 | S3 `?show=` · S3 `?tuition=&degree=` |
| P03 | 과목 카드 · 보완 서류 제출하기 | S9 → S10 |
| P04 | 보완 자료 제출 | S11 |
| P04 | 이의 신청 작성 | S12 |
| P04 | 원본 N쪽 ↗ · 원본 파일 ↗ | C3 |
| P04 | 근거 자료 파일 | C5 |
| P04 | 근거 구절 (원문 위치로 이동) | 화면 안 (같은 화면의 원문으로 스크롤) |
| P04 | 이전 분석 기록 | S10 (이전 분석 id) |
| P04 | 판정 근거 리포트 (P13 링크는 리포트 안) | C1 |
| P21 | 이의 신청 작성 · 과목 결과 보기 · 판정 근거 리포트 · 근거 자료 | S12 · S10 · C1 · C5 |
| P22 | 이의 신청 제출 | S13 |
| P22 | 과목 결과 · 이의 신청 목록 · 분석 결과와 근거 · 판정 근거 리포트 · 처리 상황 보기 · 취소 | S10 · S14 · S10 · C1 · S14 · S10 |
| P23 | 찾기 | S15 `?q=` |

### 심사관 화면

| 화면 | 버튼·링크 | API |
| --- | --- | --- |
| P05 | 검색 · 탭 5개 · 학과 칩 · 정렬 · 페이지 | R1 (`q`·`tab`·`department`·`sort`·`page`) |
| P05 | 행 선택 → 담당 교수 일괄 배정 · 선택 항목 교수 일괄 배정 | R2 `POST /review/assign` |
| P05 | SIS CSV 내보내기 | R3 |
| P05 | 원문 대조 확인 → · 충돌 내역 확인 · 보완 요청 발송 · 과거 판례 N건 보기 | R4 (각각 `#history`·`#materials` 위치) |
| P05 | 이 페이지 전체 선택 | 화면 안 |
| P06 | 학생에게 보완 자료 요청 [요청 보내기] | R5 |
| P06 | 학생 대신 보완 자료 올리기 [올리고 다시 분석] (확인창) | R13 |
| P06 | 메모 남기기 | C4 |
| P06 | 원본 N쪽 ↗ · 근거 자료 · 판정 근거 리포트 · ← 심사 큐 | C3 · C5 · C1 · R1 |
| P07 | 받아들이고 재판정 배정 · 기각 | R7 (`action=accept` · `action=dismiss`) |
| P07 | 심사 건 · 판정 근거 리포트 · 근거 자료 | R4 · C1 · C5 |
| P08 | 처리 완료 (심사관) | R9 |
| P08 | 승인·삭제 (관리자, 확인창) | M10 |
| P09 | 가져오기 (CSV) · 예시 파일 | R11 · 정적 파일 |
| P10 | 학사정보 연동 · 연동 설정 보기 · 전체 감사 로그 · 전체 보기 · 삭제 승인 화면 (관리자) | M11 · M11 · M13 · M13 · M9 |
| P10 | SIS CSV 내보내기 (심사관) | R3 |

### 교수 화면

| 화면 | 버튼·링크 | API |
| --- | --- | --- |
| P11 | 심사 건 행 | F3 |
| P11 | 부재 설정 [저장] | F2 |
| P12 | 판정 칩(승인·수정·반려) · 등급·대상 과목 선택 | 화면 안 (F4 입력값) |
| P12 | 판정 확정 · 하단 바 판정 확정 · 재판정 확정 | F4 |
| P12 | 사유 선택 창 [사유 저장 및 판정 확정] | F4 (같은 폼) |
| P12 | 사유 선택 창 [취소 / 판정 변경] · 닫기 · 과거 판정 이력 보기 | 화면 안 |
| P12 | 보완 자료 요청 (하단 바) → [요청 보내기] | F5 |
| P12 | 메모 남기기 | C4 |
| P12 | ← 배정된 심사 · 판정 근거 리포트 · 원본 N쪽 ↗ | F1 · C1 · C3 |
| P13 | PDF 내려받기 | C2 |
| P13 | 인쇄 | 화면 안 (브라우저 인쇄) |
| P13 | ← 돌아가기 | S10 · R4 · F3 (역할별) |

### 관리자 화면

| 화면 | 버튼·링크 | API |
| --- | --- | --- |
| P15 | 토큰 발급 · 토큰 다시 발급 (확인창) | M12 `action=issue` |
| P15 | 토큰 폐기 | M12 `action=revoke` |
| P18 | 과목 가져오기 | M3 |
| P18 | 기준 강의계획서 올리기·바꾸기 | M4 |
| P18 | 계정 가져오기 | M5 |
| P18 | 설정 링크 메일 보내기 / 임시 비밀번호 발급 (확인창) | M6 |
| P18 | 비활성화 (확인창) · 다시 활성화 | M7 `action=deactivate` · `action=reactivate` |
| P18 | 출신 대학 추가 | M8 |
| P18 | 이메일을 모르면 계정 목록에서 찾기 | M14 |
| P18 | 단계 바로가기 4개 · 예시 파일 받기 · 임시 비밀번호 CSV 받기 | 화면 안 (같은 화면 위치) · 정적 파일 · 화면 안 (data URI) |
| P16 | 찾기 (행위·대상 종류·대상 번호·기간) · 초기화 · 대상 링크(그 대상만) · 이전·다음 페이지 | M13 (조건을 쿼리로) |
| P24 목록 | 찾기 (이메일·역할) · 상태 칩 (활성·비활성·전체) · 이전·다음 페이지 | M14 |
| P24 목록 | 수정 | M15 |
| P24 수정 | ‹ 계정 목록 | M14 |
| P24 수정 | 저장 | M16 |
| P24 수정 | 설정 링크 메일 보내기 / 임시 비밀번호 발급 (확인창) | M6 (결과는 P18) |
| P24 수정 | 비활성화 (확인창) · 다시 활성화 | M7 + `next` (처리 뒤 이 화면으로) |
| P25 | 미배정 · 전체 (보기 칩) | M17 `show` |
| P25 | 고른 건 학과 교수에게 자동 배정 | M18 |
| P25 | 배정 · 바꾸기 (행마다) | M19 |
| P14·P17 | (버튼 없음 · 알림 행의 링크는 해당 화면 조회 API · 오류 화면 "처음으로"는 A1) | – |

## 5. 화면 데이터 ↔ 조회 API

화면마다 조회 API 하나가 그 화면의 모든 데이터를 모아 보낸다. 조회 함수는 `backend/services/`.

| 화면 | 조회 API | 조회 함수 | 화면에 보이는 데이터 |
| --- | --- | --- | --- |
| P00 | A13 · A14 · 각 화면 | `notifications.unread_count`, `stats.workspace_counts`, `views.nav_badges` | 안 읽은 알림 수, 기관 집계 칩, 메뉴 숫자 배지 |
| P01·P19·P20 | A2 · A6 · A8 · A10 | – | 폼만 (P20 재설정은 토큰 유효성) |
| P02 | S1 | `views.student_home` | 할 일, 요청 목록, 요청별 예상 인정 학점·판정 확정 수·남은 학기·서류 준비율, 소속 대학·출신 대학·전공 선택지 |
| P03 | S3 | `views.request_view` (+ `student.simulate`) | 예상 학점·학기·비용, 과목 카드(추천·커버리지·대응 과목·판정 교수·담당 교수·심사 단계·보완 요청), 성적표 과목 연결, 진행 단계, 삭제 요청 상태 |
| P04·P06·P12 | S10 · R4 · F3 | `views.evaluation_view` | 추천·신뢰도·커버리지·후보 과목, 판정·이의 신청·보완 요청 경과, 이전 분석과 비교, 경고, 정보 부족 진단, 개념별 근거(원본 쪽), 원문, 추출 정보, 과거 판정 이력, 내부 메모(교직원), 처리 기록(심사관), 대상 과목 목록(교수) |
| P05 | R1 | `review.queue`, `stats.institution_stats` | 지표 카드 4개, 탭·학과별 건수, 행(접수 번호·학생·출신 대학·과목·후보·커버리지·추천·신뢰도·담당 교수·상태·경보), 페이지 |
| P07 | R6 | `appeals.rows` | 접수된 이의 신청(과목·출신 대학·신청 시각·사유·근거 자료·원 판정, 학생 이름은 없음), 재판정 교수 후보 |
| P08 | R8 · M9 | `privacy.rows` | 삭제 요청(요청 #·학생 이메일·기한·상태·기한 초과) |
| P09 | R10 | `equivalencies.recent` | 최근 가져온 동등 과목표 |
| P10 | M1 · R12 | `stats.institution_stats`, `stats.recent_audit`(관리자), `views.reminder_preview` | 수용률·불일치율, 개인정보, SIS 상태, 처리 현황, 기한 알림, 학과별 지표, 월별 판정, 판정 구성, 최근 감사 로그 8건(관리자), 보존 정책 |
| P11 | F1 | `views.professor_items`, `views.colleagues` | 배정된 심사(재판정·대리 표시), 부재 설정·대리 교수 후보 |
| P13 | C1 · C2 | `views.evaluation_view(with_audit=True)` | 사람 판정·당시 AI 추천, 경과, AI 추천, 개념별 근거, 과거 판정, 감사 로그 |
| P14 | A12 | `notifications.inbox` | 알림 50건 (저장된 한국어 원문을 화면 언어로) |
| P15 | M11 | `sis.has_token` | 토큰 상태 (발급 직후에만 원문) |
| P16 | M13 | `stats.audit_page` | 소속 기관 감사 로그(조건별, 50건씩)·행위자 역할·필터 선택지(그 기관 기록에 나온 행위·대상 종류) |
| P18 | M2 | `institution_data.overview` | 과목 수·계정 수(역할별, 비활성 제외)·첫 비밀번호 대기·출신 대학, 교수 없는 학과, 과목별 기준 강의계획서 상태, 출신 대학 목록 |
| P21 | S14 | `appeals.appealable`, `appeals.student_rows` | 이의 신청할 수 있는 과목, 낸 이의 신청·처리 경과 |
| P22 | S12 | `views.evaluation_view` | 원 판정 요약, 근거가 약한 개념, 처리 중 이의 신청 여부 |
| P23 | S15 | `precedents.search` | 소속 대학, 동등 과목표 검색 결과 |
| P24 목록 | M14 | `accounts.list_accounts` | 계정(이메일·교직원 이름·역할·학과·대리 심사자·상태), 건수·페이지 |
| P25 | M17 | `review.assignment_board` | 판정 전 심사 건(접수 번호·제출일·학생 과목·출신 대학·배정 학과·담당 교수·배정일·대리 여부), 교수 선택지, 미배정·전체 건수 |
| P24 수정 | M15 | `accounts.account_form` | 계정 정보, 학과 선택지(과목 학과명), 대리 심사자 후보(같은 기관 다른 활성 교수) |

## 6. 검토 결과

### 6.1 버튼 ↔ API 매칭 (요청 1)

점검 방법: 템플릿 43개에서 폼 44개·링크 61개·HTMX 호출 3개(모두 108개)를 뽑아 엔드포인트 74개와 경로·메서드로 맞췄다. 메뉴 링크(`nav_link`)와 할 일 링크처럼 코드가 만드는 주소는 따로 확인했다.

| 항목 | 결과 |
| --- | --- |
| 서버를 부르는 버튼이 엔드포인트와 연결되는가 | ✅ 모두 연결. 연결되지 않는 버튼 0개 (보완 자료 요청 폼은 역할에 따라 R5·F5로 나뉨) |
| 처리 API(POST 35개)마다 버튼이 있는가 | ✅ 35개 모두 화면 버튼이 있음. JSON J2만 화면 버튼 없음 (아래) |
| 화면 안에서만 동작하는 버튼 | 인쇄, 사유 창 닫기·취소, 판정 칩, 전체 선택, 단계 바로가기, 근거 구절 이동 — 서버 API가 필요 없음 |
| 버튼 없이 쓰는 API | A1(로고·첫 진입), A10(메일 링크), A13·A14(자동 갱신), S9(과목 카드 → 최신 분석으로 이동), J1·J2(화면에서 안 씀), J3(외부 시스템) |

1:1이 아닌 곳 (한 API에 버튼 여러 개):

| API | 버튼 | 판단 |
| --- | --- | --- |
| R7 `POST /review/appeals/{id}` | 받아들이고 재판정 배정 / 기각 | `action`으로 구분. 같은 이의 신청의 상태 변경이라 하나로 두어도 됨. 엄격한 1:1이 필요하면 `/accept`·`/dismiss`로 나눈다 |
| M7 `POST /admin/data/accounts/active` | 비활성화 / 다시 활성화 | 위와 같음 (`/deactivate`·`/reactivate`) |
| M12 `POST /admin/sis` | 토큰 발급 / 폐기 | 위와 같음 (`/token`·`/token/revoke`) |
| F4 `POST /professor/evaluations/{id}/decision` | 판정 확정(본문·하단 바) · 사유 창 확정 | 같은 폼의 제출 버튼 3개. 1:1 문제 아님 |
| R3 `GET /review/export.csv` | 메뉴·심사 큐·통계 3곳 | 같은 기능의 진입점이 여러 곳. 문제 아님 |

같은 일을 하는 API가 둘인 곳: J2 `POST /api/decisions`는 F4와 같은 판정 저장이다. 화면에서는 F4만 쓴다. J1·J2를 외부(모바일 앱 등)용으로 둘지, 지울지 정해야 한다.

### 6.2 화면 데이터 조회 API (요청 2)

| 항목 | 결과 |
| --- | --- |
| 화면마다 데이터를 조회하는 API가 있는가 | ✅ 화면 26개(P00~P25) 모두 조회 API가 있음 (5절). 템플릿 43개 중 화면 템플릿은 모두 조회 라우트가 그리고, 나머지는 포함용 조각 |
| 화면 데이터를 JSON으로 받을 수 있는가 | ⚠️ 심사 건 하나(J1)와 SIS 판정(J3)만. 나머지 화면 데이터는 HTML로만 나온다. 서버 렌더링 구조라 지금은 문제없지만, 모바일 앱이나 별도 프론트엔드를 만들면 화면마다 JSON 조회 API가 필요하다 |

조회 범위가 모자란 곳:

| 화면 | 문제 | 권장 |
| --- | --- | --- |
| P18 계정·과목 ✅ 반영 | 계정 **목록**을 조회하는 API가 없었다. 역할별 개수만 보여서, 비활성화·비밀번호 초기화할 때 이메일을 직접 알아야 했다 | M14 `GET /admin/accounts?q=&role=&status=&page=` 추가 (P24) |
| P16 감사 로그 ✅ 반영 | 최근 200건만, 기간·행위·대상 필터와 페이지가 없었다 | M13에 `action`·`target_type`·`target_id`·`since`·`until`·`page` 추가 (50건씩) |
| P14 알림 | 최근 50건만, 페이지 없음 | 페이지 추가 (우선순위 낮음) |
| P09 동등 과목표 | 최근 가져온 것만 보이고 전체 검색이 없다 | `GET /review/equivalencies?q=&page=` |

### 6.3 기능 명세·권한 매트릭스 대비 빠진 API

[기획 통합본](spec.md) 4장 "역할별 권한 매트릭스"에는 있는데 API가 없는 권한:

| 권한 (매트릭스) | 현재 | 영향 |
| --- | --- | --- |
| 교수 배정·재배정 — **관리자 가능** ✅ 반영 | 배정 API(R2)가 심사관 전용이었다 | 코드를 매트릭스에 맞춤: 관리자용 P25와 M17~M19 추가(학과 자동 배정·교수 지정·바꾸기). 관리자는 AI 결과를 보지 않는다는 매트릭스 규칙에 따라 추천·커버리지 없이 학과·담당 교수만 보여 준다 |
| 사용자·학과·대리자 설정 — **관리자 가능** ✅ 반영 | 교수의 학과·대리자를 고치는 API가 없었다 | M16 `POST /admin/accounts/{id}` 추가: 교직원 이름, 교수·심사관 학과(과목 학과명만), 교수 대리 심사자. 역할은 기록이 묶여 있어 바꾸지 않는다(새 계정 + 비활성화) |
| 문서 업로드 — **심사관 소속 기관 전체** ✅ 반영 | 심사관은 보완 자료 **요청**(R5)만 할 수 있었다 | 코드를 매트릭스에 맞춤: R13 `POST /review/evaluations/{id}/supplement`로 심사관이 학생 대신 보완 자료를 올린다(메일·종이로 받은 자료, 판정 전·최신 분석만, 다시 분석). 새 강의계획서 추가는 학생 업로드로 둔다 |
| FR-20 모바일 승인의 알림 | 화면·메일 알림만 (웹 푸시 없음) | 추적표에 🟡로 이미 기록 |

### 6.4 설계상 확인할 점

| 항목 | 내용 | 권장 |
| --- | --- | --- |
| GET이 상태를 바꾼다 | A12(알림 모두 읽음), S10·S14(새 결과 배지 읽음 처리)는 조회하면서 읽음 시각을 남긴다 | 같은 요청을 여러 번 해도 결과가 같아(멱등) 실제 문제는 없다. REST 원칙을 지키려면 `POST /notifications/read`로 분리 |
| 코드 설명이 옛 동작 | S15 라우트 설명에 "확정 판정 건수"가 남아 있지만 지금은 기관 동등 과목표만 보여 준다 | 수정함 (기관 동등 과목표 기준으로 설명 변경) |
| 버전 표기 | 경로에 버전(`/api/v1`)이 없다 | 외부 연동(J3)을 공개하기 전에 `/api/v1/sis/decisions`로 정한다 |

### 6.5 권장 조치 (우선순위)

1. ~~계정 목록·수정 API~~ (6.2·6.3) — 반영 (M14~M16, P24, 2026-10-19).
2. ~~감사 로그 필터·페이지~~ (6.2) — 반영 (M13, P16, 2026-10-19).
3. ~~권한 매트릭스 정리~~ (6.3) — 코드를 매트릭스에 맞춤 (관리자 배정 P25·M17~M19, 심사관 대신 업로드 R13, 2026-10-19).
4. J1·J2를 외부용으로 둘지 결정하고, 둔다면 `/api/v1`과 JSON 조회 API 범위를 정한다.
