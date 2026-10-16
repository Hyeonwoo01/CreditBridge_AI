# P16 감사 로그

| 항목 | 내용 |
| --- | --- |
| URL | `GET /admin/audit` |
| 역할 | 기관 관리자 |
| 템플릿 | `admin/audit.html` |
| 기능 | FR-10 추가 전용 감사 기록 조회 (소속 기관 사용자가 남긴 최근 200건, 다른 대학 기록은 보이지 않음) |

## 위치

```
[global-nav: 운영 통계 · 계정·과목 (N) · 삭제 승인 (N) · 학사정보 연동 · 감사 로그(선택)]
제목 "감사 로그" + "추가 전용 기록이에요. 수정하거나 삭제할 수 없어요."
┌ 표 ────────────────────────────────────────┐
│ 시각 │ 행위 │ 대상 │ 내용(payload)           │
└────────────────────────────────────────────┘
[footer]
```

## 컴포넌트

| 영역 | 컴포넌트 | 내용 | 토큰 |
| --- | --- | --- | --- |
| 표 | 데이터 표 | 최소 폭 640px, 가로 스크롤 | 헤더 14px muted, 행 구분 `{colors.divider-soft}` (DESIGN.md: 정보 밀도가 가장 높은 곳) |
| 행위 | 텍스트 | `decision.create`, `assignment.create`, `privacy.delete_documents`, `account.deactivate`·`account.reactivate`, `appeal_file.download`(이의 신청 근거 자료를 내려받을 때마다 이의 신청·과목 id) 등 | 필요 시 `{typography.mono-code}` |
| 내용 | JSON | 식별자와 판정값만 (이름·학번·성적 없음) | muted |

## 비고

- `audit_logs`는 INSERT·SELECT만 허용(운영 DB 권한 `docs/db-grants.sql`).
- 행위자(`actor_id`)가 같은 기관 사용자인 기록만 보여 준다(`audit_repo.recent_for_institution`). 관리자 콘솔(P10) 최근 감사 로그도 같은 범위에서 로그인 기록을 빼고 보여 준다.
