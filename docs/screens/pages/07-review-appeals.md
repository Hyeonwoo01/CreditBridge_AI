# P07 이의 신청 처리

| 항목 | 내용 |
| --- | --- |
| URL | `GET /review/appeals`, 처리 `POST /review/appeals/{id}` (`action=accept|dismiss`) |
| 역할 | 심사관 |
| 템플릿 | `review/appeals.html` |
| 화면 테스트 | `test_appeal_accept_and_redecide_keeps_original_decision`, `test_appeal_form_with_evidence_files`, `test_privacy_request_review_and_admin_approval`, `test_equivalency_import_shows_in_history_without_blocking` |
| 기능 | FR-23 이의 신청 접수·처리 |

## 위치

```
[global-nav: 심사 큐 (2) · 이의 신청(선택) (1) · 삭제 요청 · 동등 과목표 · 통계 · CSV 내보내기]
제목 "이의 신청" + 설명(원 판정은 지워지지 않음)
┌ 이의 신청 카드 (접수된 것 먼저, 최신순) ─────────────────────────┐
│ 과목(링크 → P06)                                 [접수됨]       │
│ 출신 대학 · 신청 시각 · 판정 근거 리포트                          │
│ ┌ 학생 이의 사유 (파치먼트 인용) ┐                               │
│ 근거 자료  (강의노트.pdf) (시험지.png)          ← 첨부가 있을 때 │
│ 재판정 교수 ▾ │ 메모 입력 │ [받아들이고 재판정 배정] [기각]        │
└──────────────────────────────────────────────────────────────┘
[footer]
```

## 컴포넌트

| 영역 | 컴포넌트 | 내용 | 토큰 |
| --- | --- | --- | --- |
| 카드 | `evaluation-utility-card` | 이의 신청 한 건 | `{rounded.lg}`, `{colors.hairline}` |
| 상태 배지 | `confidence-badge-pill` | 접수됨(빨강 글자)·재판정 중·기각·재판정 완료 | 중립 `{colors.surface-pearl}` |
| 사유 | 인용 블록 | 학생이 쓴 사유, 줄바꿈 유지 | `{colors.canvas-parchment}`, `{rounded.sm}` |
| 근거 자료 | 파일 캡슐 | 학생이 첨부한 PDF·JPG·PNG(최대 3개). 누르면 `GET /appeal-files/{id}`로 내려받기(학생 본인·소속 심사관·담당 교수만, `no-store`). 개인정보 삭제 후 "(삭제됨)" | 흰 배경 + `{colors.hairline}` 1px 캡슐, 14px, hover `{colors.primary}` |
| 재판정 교수 | select | 판정한 대상 과목 학과의 교수 중 원 판정 교수를 뺀 목록(리뷰 v3 P0-6: 이의 신청은 다른 교수가 다시 본다). 원 판정 교수가 부재면 대리 심사자를 기본 선택, "(원 판정 교수의 대리)" 표시. 아래에 "원 판정 교수는 고를 수 없어요", 고를 교수가 없으면 "같은 학과에 원 판정 교수 말고 다른 교수가 없어요…" | 높이 44px |
| 메모 | input | 기각 시 필수, 학생에게 전달 | |
| 받아들임 | `button-primary` | 교수 배정 + 교수·학생 알림 | |
| 기각 | `button-secondary-pill` | 사유와 함께 학생 알림 | |

## 상태

| 상태 | 표시 |
| --- | --- |
| 없음 | "접수된 이의 신청이 없어요." |
| 처리된 건 | 폼 없이 상태 배지와 처리 메모만 |
| 문서 삭제로 종료된 요청의 이의 신청 | 목록과 메뉴 배지에서 빠짐 |
| 기각 메모 비움 | 빨강 플래시 "기각할 때는 학생에게 전할 사유를 적어 주세요." |
| 원 판정 교수를 골라 보냄 | 빨강 플래시 "재판정할 학과 교수를 선택해 주세요." |
| 다른 심사관이 먼저 처리 | 심사 건 행을 잠근 뒤 다시 읽어 빨강 플래시 "이미 처리한 이의 신청이에요." |

## 버튼 ↔ API

엔드포인트 ID(A·S·R·F·C·M·J)는 [API 명세 2절](../../API_Spec.md#2-엔드포인트-목록). `화면 안` = 서버를 부르지 않는 버튼.

| 버튼·링크 | API |
| --- | --- |
| 받아들이고 재판정 배정 · 기각 | R7 (`action=accept` · `action=dismiss`) |
| 심사 건 · 판정 근거 리포트 · 근거 자료 | R4 · C1 · C5 |
