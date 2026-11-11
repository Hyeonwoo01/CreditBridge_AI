# CreditBridge AI 화면 명세서

편입 학점 심사 자동화 SaaS **CreditBridge AI**의 화면별 명세서입니다. 화면마다 **위치(URL·영역 배치), 컴포넌트, 디자인 토큰**과, 머리 표의 **템플릿·화면 테스트**, 맨 아래 **버튼 ↔ API**(버튼이 부르는 엔드포인트 ID, [API 명세](../API_Spec.md) 2절)를 적었습니다. 화면 목록·URL·템플릿·화면 테스트는 이 폴더에만 적고 다른 문서는 여기를 링크합니다.

- 디자인 기준: `docs/DESIGN.md` (Apple 갤러리형: 단일 Action Blue `#0066cc`, 1px 헤어라인, 그림자 없음)
- 기능 기준: `docs/spec.md` 4장 기능 명세 (FR-01~FR-28)
- 구현 위치: `frontend/templates/`(화면), `frontend/static/`(CSS·JS·이미지), 라우트는 `backend/web/routes/` (Jinja2 + HTMX + Tailwind 4)
- 토큰 표기: `{colors.primary}`처럼 DESIGN.md 토큰을 쓰고, 괄호 안에 실제 Tailwind 클래스(`bg-primary`)를 함께 적었습니다.
- 문구: 명세의 화면 문구는 한국어 원문입니다. 모든 화면은 영어로도 볼 수 있으며(P00 화면 언어), 영어 문구는 `backend/locales/en.json`에 있습니다.

## 화면 목록

| ID | 화면 | URL | 역할 | 주요 기능 | 파일 |
| --- | --- | --- | --- | --- | --- |
| P00 | 공통 레이아웃 | 모든 화면 | 전체 | 글로벌 내비게이션, 언어 전환(한/영), 기관 보조 바·집계 칩, 알림, Human-in-the-Loop 푸터, 화면 폭 | [00-common-layout.md](pages/00-common-layout.md) |
| P01 | 로그인 | `/login` | 비로그인 | 역할별 홈으로 이동, 비밀번호 찾기 링크, 실패 5회 1분 잠금·10회 비밀번호 초기화 | [01-login.md](pages/01-login.md) |
| P02 | 학생 홈(대시보드) | `/student` | 학생 | 성적표 C 이상 과목마다 자동으로 만든 요청 목록, 전체 합계(편입 학점 상한·졸업 학점 과목 고르기), 할 일 | [02-student-home.md](pages/02-student-home.md) |
| P03 | 편입 학점 시뮬레이션 리포트 | `/student/requests/{id}` | 학생 | FR-01·02·15·21 다크 히어로 예상치, 과목 필터, 정보 부족 진단, 심사 진행 단계 | [03-student-request.md](pages/03-student-request.md) |
| P04 | 과목 분석 결과(학생) | `/student/evaluations/{id}` | 학생 | FR-05~08 추천·근거, 버전 비교, FR-25 원본 PDF 쪽 링크, FR-22 보완 제출, FR-23 이의 신청 작성(P22)으로 이동 | [04-student-evaluation.md](pages/04-student-evaluation.md) |
| P05 | 심사 큐 | `/review` | 심사관 | FR-17 검색·신뢰도·일관성 경보·학과 필터, FR-18 일괄 배정, 커버리지 링, 경보 행 | [05-review-queue.md](pages/05-review-queue.md) |
| P06 | 심사 건 상세(심사관) | `/review/evaluations/{id}` | 심사관 | 근거 확인(원본 PDF 쪽), 내부 메모, 보완 자료 요청, 학생 대신 보완 자료 올리기, 처리 기록 | [06-review-evaluation.md](pages/06-review-evaluation.md) |
| P07 | 이의 신청 처리 | `/review/appeals` | 심사관 | FR-23 받아들임·기각, 학생 근거 자료 내려받기 | [07-review-appeals.md](pages/07-review-appeals.md) |
| P08 | 문서 삭제 요청 | `/review/privacy`, `/admin/privacy` | 심사관·관리자 | FR-13 처리·승인, 기한 관리 | [08-privacy-requests.md](pages/08-privacy-requests.md) |
| P09 | 기존 동등 과목표 | `/review/equivalencies` | 심사관 | FR-26 CSV 가져오기 | [09-review-equivalencies.md](pages/09-review-equivalencies.md) |
| P10 | 관리자 콘솔 · 운영 통계 | `/admin/stats`, `/review/stats` | 관리자·심사관 | FR-27 수용률·학과별 지표, 오늘 기한 알림 대상, 최근 감사 로그, 보존·파기 정책 | [10-stats.md](pages/10-stats.md) |
| P11 | 배정된 심사(교수 홈) | `/professor` | 교수 | 배정 목록, FR-19 부재 설정 | [11-professor-home.md](pages/11-professor-home.md) |
| P12 | 판정 화면(교수) | `/professor/evaluations/{id}` | 교수 | FR-09 판정·불인정 사유 선택 창, FR-11 일관성 경보, FR-20 모바일 승인, FR-25 원본 PDF 쪽, 내부 메모 | [12-professor-evaluation.md](pages/12-professor-evaluation.md) |
| P13 | 판정 근거 리포트 | `/evaluations/{id}/report`, `…/report.pdf` | 학생·심사관·교수 | FR-10·23 감사용 리포트, 역할별 돌아가기, PDF 내려받기 | [13-report.md](pages/13-report.md) |
| P14 | 알림 | `/notifications` | 전체 | FR-19·20 알림함, 매일 기한 알림 | [14-notifications.md](pages/14-notifications.md) |
| P15 | 학사정보 연동 | `/admin/sis` | 관리자 | FR-24 토큰 발급·폐기 | [15-admin-sis.md](pages/15-admin-sis.md) |
| P16 | 감사 로그 | `/admin/audit` | 관리자 | FR-10 추가 전용 기록(소속 기관만, 근거 자료 열람 포함), 행위·대상·기간 필터와 50건 페이지 | [16-admin-audit.md](pages/16-admin-audit.md) |
| P17 | 오류 | 모든 화면 | 전체 | 403·404·400 안내 | [17-error.md](pages/17-error.md) |
| P18 | 계정·과목 관리 | `/admin/data` | 관리자 | 단계 순서(①~④) 배치, 과목·계정 CSV, 기준 강의계획서, 출신 대학, 비밀번호 초기화(메일 링크 자동/메일 없으면 임시 비밀번호), 계정 비활성화·다시 활성화 | [18-admin-data.md](pages/18-admin-data.md) |
| P19 | 비밀번호 변경 | `/account/password` | 전체 | 첫 로그인 강제 변경 포함 | [19-account-password.md](pages/19-account-password.md) |
| P20 | 비밀번호 찾기·재설정 | `/account/forgot`, `/account/reset` | 비로그인 | 메일 링크(30분·한 번만), 메일 미설정 시 관리자 안내 | [20-account-reset.md](pages/20-account-reset.md) |
| P21 | 이의 신청(학생) | `/student/appeals` | 학생 | FR-23 이의 신청할 수 있는 과목, 본인 이의 신청 처리 상황·재판정 결과·기각 사유·근거 자료 | [21-student-appeals.md](pages/21-student-appeals.md) |
| P22 | 이의 신청 작성(학생) | `/student/evaluations/{id}/appeal` | 학생 | FR-23 원 판정 요약·근거가 약한 개념, 사유(20~3000자), 근거 자료 PDF·JPG·PNG 최대 3개 | [22-student-appeal-form.md](pages/22-student-appeal-form.md) |
| P23 | 선배 인정 사례(학생) | `/student/precedents` | 학생 | FR-26 기관 동등 과목표 검색(다른 학생의 판정은 보이지 않음) | [23-student-precedents.md](pages/23-student-precedents.md) |
| P24 | 계정 목록·계정 수정 | `/admin/accounts`, `/admin/accounts/{id}` | 관리자 | 이메일·역할·상태로 계정 찾기(학생 이름 비공개), 교직원 이름·학과·대리 심사자 수정, 비밀번호 초기화·비활성화 | [24-admin-accounts.md](pages/24-admin-accounts.md) |
| P26 | 내 성적표(학생) | `/student/transcript` | 학생 | 처음 들어오면 먼저 올리는 계정 성적표, 과목 줄·성적 기준 미달 표시, 바꿔 올리기 | [26-student-transcript.md](pages/26-student-transcript.md) |
| P25 | 교수 배정(관리자) | `/admin/assignments` | 관리자 | 판정 전 심사 건 담당 교수 자동 배정·지정·바꾸기(AI 결과 비공개) | [25-admin-assignments.md](pages/25-admin-assignments.md) |

## 역할별 흐름

```
학생    P01 → P02 대시보드(할 일) → P03 리포트 ──(과목 카드·보완 서류 제출하기)──→ P04 ──(보완 자료 제출 / 이의 신청 작성 → P22 → P21에서 처리 상황 확인)
        P21 "이의 신청할 수 있는 과목" → P22 → P21,  메뉴 "인정 사례" → P23
심사관  P01 → P05 ──(원문 대조 확인 / 충돌 내역 확인 / 보완 요청 발송)──→ P06,  P05에서 일괄 배정
        P07 이의 신청 · P08 삭제 요청 · P09 동등 과목표 · P10 운영 통계
교수    P01 → P11 → P12 ──(판정 확정 → 반려·변경·경보면 사유 선택 창)──→ 학생 P03·P04에 반영
관리자  P01 → P10 관리자 콘솔 → P18 계정·과목 · P24 계정 목록(→ 계정 수정) · P25 교수 배정 · P08 삭제 승인 · P15 연동 토큰 · P16 전체 감사 로그
새 계정  메일 O: 설정 링크 메일 → P20 → P01 / 메일 X: P01(임시 비밀번호) → P19 → 역할 홈
잊었을 때 P01 → P20 메일 링크 → 새 비밀번호 → P01   (메일 미설정: 관리자가 P18에서 재발급 → P19)
실패 잠금 P01 5번 틀림 → 1분 잠금 → 다시 5번 틀림(누적 10번) → 비밀번호 초기화 + 재설정 메일 자동 → P20 → P01
```

## 공통 원칙 (DESIGN.md 요약)

- 클릭할 수 있는 요소(버튼·링크·포커스·선택 칩)는 `{colors.primary}` 하나만 쓴다. 판정 의미 색은 배지·게이지·하이라이트에만 쓴다.
- 카드·버튼·배지에 그림자를 넣지 않는다. 영역 구분은 흰 카드 + `1px {colors.hairline}`으로 한다.
- 본문 17px(행간 1.47), 굵기는 300·400·600만 쓴다(500 금지). 숫자에는 `tabular-nums`를 쓴다.
- AI 추천은 항상 "추천이며 확정이 아님"을 함께 보여 주고, 최종 판정 버튼은 교수 화면에만 있다.
- 화면 폭은 기본 1280px, 정보가 빽빽한 심사 큐(P05)와 원문 대조 화면(P06·P12)만 1440px.
- 목록 필터 칩은 선택 시 잉크(검정) 채움, 판정 칩은 파란 2px 테두리로 구분한다.
- 실제 데이터가 없는 장식(인증 배지, 전주 대비 증감, 판정 확률 %, 해시 체인, 상담 담당자 카드)은 넣지 않는다. 교수·관리자 화면에 학생 이름을 보여 주지 않는다.
- 비밀번호·재설정 링크처럼 한 번만 보여 주는 값은 화면을 캐시하지 않고(`no-store`) 서버에 원문을 남기지 않는다.

## 변경 이력

화면이 새로 생기거나 없어졌을 때, 화면 배치나 흐름이 크게 바뀌었을 때만 한 줄씩 남깁니다. 문구·버튼 하나 같은 작은 변경은 커밋 기록에서 보세요: `git log -- docs/screens frontend/templates`.

| 날짜 | 내용 |
| --- | --- |
| 2026-11-11 | 문서 구성: 화면 테스트를 각 페이지 머리 표로, "버튼 ↔ API"를 각 페이지 맨 아래로 옮김 (추적표·API 명세에서 이동, `scripts/docs_check.py`가 확인) |
| 2026-11-11 | 판정 신뢰성(리뷰 v3 P0-4~7): P18 "학칙 정책" 카드(편입 학점 상한 카드를 대신함), P06 "증거 상태" 카드, P06·P12 머리에 심사 상태 칩, P07 재판정 교수에서 원 판정 교수 제외 |
| 2026-11-10 | 학점 계산(리뷰 v3 P0-1~3): P18 "학점 단위와 환산 규칙" 카드, P12 판정 폼에 인정 학점 입력과 "함께 인정할 출신 과목"(N:1) |
| 2026-11-02 | P11 교수 홈에 "최근 판정한 심사" 목록 |
| 2026-10-30 | AI 근거 품질: P12 근거 구절마다 맞음·틀림, P10 "AI 근거 품질" 표 |
| 2026-10-21 | 성적표 먼저 흐름: P26 내 성적표 추가(처음 들어오면 이 화면), 성적표 과목마다 요청 자동 생성, P02 맨 위 "전체 합계"와 종료된 요청 접기 |
| 2026-10-20 | P06 "담당 교수 배정" 카드, P18 출신 대학 목록을 대학별로 |
| 2026-10-19 | P24 계정 목록·계정 수정, P25 교수 배정(관리자) 추가, P14 웹 푸시 카드, 공개 데모 모드(P00·P01) |
| 2026-10-16 | P00 한국어·영어 전환, P04·P06·P12 강의계획서 버전 비교 카드와 원본 PDF 쪽 링크, P10 "기한 알림" 카드 |
| 2026-10-15 | 역할별 메뉴와 숫자 배지(P00), P02 학생 홈 대시보드, P21·P22 학생 이의 신청 목록·작성, P23 선배 인정 사례, P18 계정·과목 관리, P19·P20 비밀번호 변경·찾기 추가 |
| 2026-10-14 | 화면 목업 반영: P00 기관 보조 바·푸터·화면 폭, P03 시뮬레이션 리포트, P05 심사 대기열, P10 관리자 콘솔 |
