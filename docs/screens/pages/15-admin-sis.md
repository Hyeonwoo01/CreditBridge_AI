# P15 학사정보시스템 연동

| 항목 | 내용 |
| --- | --- |
| URL | `GET /admin/sis`, 발급·폐기 `POST /admin/sis` (`action=issue|revoke`) |
| 역할 | 대상 대학의 기관 관리자 (심사관은 403) |
| 템플릿 | `admin/sis.html` |
| 기능 | FR-24 확정 판정 내보내기용 토큰 관리 (API: `GET /api/sis/decisions`) |

## 위치

```
[global-nav: 운영 통계 · 계정·과목 (N) · 삭제 승인 (N) · 학사정보 연동(선택) · 감사 로그]
제목 "학사정보시스템 연동" + 설명(재판정은 최신만, 대체 판정 번호 함께)
(발급 직후) ┌ 새 연동 토큰 — 지금 한 번만 보여드려요 ┐
            │ cbsis_xxxxxxxx (코드)                   │
            └────────────────────────────────────────┘
┌ 상태 카드 ──────────────────────────────────────────┐
│ 상태: 토큰 발급됨 / 토큰 없음                          │
│ 요청 예시 (코드 블록)                                 │
│ 응답 필드 설명                                        │
│ [토큰 발급 / 다시 발급] [토큰 폐기]                     │
└─────────────────────────────────────────────────────┘
[footer]
```

## 컴포넌트

| 영역 | 컴포넌트 | 내용 | 토큰 |
| --- | --- | --- | --- |
| 새 토큰 | 강조 박스 | 원문 토큰(한 번만 표시, DB에는 SHA-256만 저장) | 테두리 `{colors.ink}`, 코드 `{typography.mono-code}`, `role="status"` |
| 요청 예시 | 코드 블록 | `GET /api/sis/decisions?since=...` + `Authorization: Bearer cbsis_...` | `{typography.mono-code}` 13px, 파치먼트, 가로 스크롤 |
| 발급 | `button-primary` | 다시 발급 시 기존 토큰 즉시 무효 | |
| 폐기 | `button-secondary-pill` | 토큰 있을 때만 | |

## API 응답 필드

`decision_id, replaces_decision_id, student_id, source_institution, source_course, result, target_course, credits, decided_at` (CSV 내보내기와 같음)

## 상태

| 상태 | 표시 |
| --- | --- |
| 폐기 | 플래시 "연동 토큰을 폐기했어요." |
| 토큰 없거나 틀림 | API 401 "유효한 연동 토큰이 필요해요." |
