# P15 학사정보시스템 연동

| 항목 | 내용 |
| --- | --- |
| URL | `GET /admin/sis`, 발급·폐기 `POST /admin/sis` (`action=issue|revoke`), 다시 보내기 `POST /admin/sis/retry` |
| 역할 | 대상 대학의 기관 관리자 (심사관은 403) |
| 템플릿 | `admin/sis.html` |
| 화면 테스트 | `test_sis_api_requires_admin_issued_token`, `test_audit_log_filters_by_action_target_and_date`, `integration/test_sis_sync.py` |
| 기능 | FR-24 확정 판정 내보내기용 토큰 관리 (API: `GET /api/v1/sis/decisions`, 버전 없는 옛 경로 `/api/sis/decisions`는 폐기 예정으로 같은 응답 + `Deprecation` 헤더) |

## 위치

```
[global-nav: 운영 통계 · 계정·과목 (N) · 계정 목록 · 교수 배정 (N) · 삭제 승인 (N) · 학사정보 연동(선택) · 감사 로그]
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
반영 확인 (대사) (#reconciliation)
[지금 유효한 판정 N] [반영됨 N] [대기 N] [실패 N]
(있으면) 반영한 뒤 재판정된 판정 N건 — 판정 #12 (SIS …) → 새 판정 #31
(있으면) ☑ 판정 #32 · 실패 2회 · unknown course code
         [고른 판정 다시 보내기]
[footer]
```

## 컴포넌트

| 영역 | 컴포넌트 | 내용 | 토큰 |
| --- | --- | --- | --- |
| 새 토큰 | 강조 박스 | 원문 토큰(한 번만 표시, DB에는 SHA-256만 저장) | 테두리 `{colors.ink}`, 코드 `{typography.mono-code}`, `role="status"` |
| 요청 예시 | 코드 블록 | `GET /api/v1/sis/decisions?since=...` + `Authorization: Bearer cbsis_...` | `{typography.mono-code}` 13px, 파치먼트, 가로 스크롤 |
| 발급 | `button-primary` | 다시 발급 시 기존 토큰 즉시 무효 | |
| 폐기 | `button-secondary-pill` | 토큰 있을 때만 | |
| 반영 확인 (리뷰 v3 P1-4) | 정의 목록 4칸 + 안내 상자 + 체크 목록 | SIS가 J4로 보낸 결과로 센 지금 유효한 판정·반영됨·대기(결과 없음)·실패(`data-recon`). 반영 뒤 이의 신청으로 재판정돼 새 판정을 다시 반영해야 하는 건, 실패 목록(실패 횟수·마지막 오류, 기본 체크) | 파치먼트 타일, 실패 오류 `{colors.reject}` |
| 다시 보내기 | `button-secondary` | 고른 실패 판정을 대기로 되돌림 → SIS가 `status=unsent`로 다시 가져감. 플래시 "N건을 다시 보내기 대기로 돌렸어요…", 감사 로그 `sis.retry` | |

## API 응답 필드

`decision_id, replaces_decision_id, student_id, source_institution, source_course, result, target_course, credits, decided_at` (CSV 내보내기와 같음)

## 상태

| 상태 | 표시 |
| --- | --- |
| 폐기 | 플래시 "연동 토큰을 폐기했어요." |
| 토큰 없거나 틀림 | API 401 "유효한 연동 토큰이 필요해요." |

## 버튼 ↔ API

엔드포인트 ID(A·S·R·F·C·M·J)는 [API 명세 2절](../../API_Spec.md#2-엔드포인트-목록). `화면 안` = 서버를 부르지 않는 버튼.

| 버튼·링크 | API |
| --- | --- |
| 토큰 발급 · 토큰 다시 발급 (확인창) | M12 `action=issue` |
| 토큰 폐기 | M12 `action=revoke` |
| 반영 확인: 고른 판정 다시 보내기 | M27 |
