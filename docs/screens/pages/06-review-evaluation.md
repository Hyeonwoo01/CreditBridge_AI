# P06 심사 건 상세 (심사관)

| 항목 | 내용 |
| --- | --- |
| URL | `GET /review/evaluations/{id}`, 보완 요청 `POST /review/evaluations/{id}/materials` |
| 역할 | 심사관 (소속 기관, 제출된 요청만) |
| 템플릿 | `review/evaluation.html` + 공용 `partials/evaluation.html`, `partials/history.html`, `partials/material_request_form.html` |
| 최대 폭 | 확장형 `max-w-[1440px]` (좌우 원문 대조 칸을 넓게) |
| 기능 | 근거 확인(P04와 같은 분석 결과), FR-11 과거 판정 이력, FR-22 보완 자료 요청, 처리 기록 |

## 위치

```
[global-nav: 심사 큐(선택) (2) · 이의 신청 (1) · 삭제 요청 · 동등 과목표 · 통계 · CSV 내보내기]
← 심사 큐 · 판정 근거 리포트
(P04의 분석 결과 영역과 같음: 추천 요약 → 판정 → 경고 → 근거 → 원문)
같은 과목의 과거 판정 N건 (history, `#history` — P05 "충돌 내역 확인"이 여기로 이동)
학생에게 보완 자료 요청 (`#materials`, 판정 전, 접힘. 정보 부족이면 펼침 — P05 "보완 요청 발송"이 여기로 이동)
처리 기록: 담당 교수 · 배정 시각 / 감사 로그 시간순
[footer]
```

## 컴포넌트

| 영역 | 컴포넌트 | 내용 | 토큰 |
| --- | --- | --- | --- |
| 과거 판정 | 이력 카드 | 판정일 · 결과 · 대상 과목 · 강의계획서 유사도 % · 사유. 개편된 강의계획서, 다른 대상 과목, 기존 동등 과목표(유사도 비교 불가)는 회색 보조 표시. 경보 조건을 채우는 이력이 있으면 앰버 카드 | 경보: `{colors.surface-elective-subtle}`, 아니면 `{colors.hairline}` |
| 보완 요청 | `<details>` 카드 | 자료 칩(분석이 제안한 자료가 먼저, 기본 체크) + 메모 + [요청 보내기] | 칩 `decision-option-chip`(선택 시 2px `{colors.primary-focus}`), 버튼 `button-secondary-pill` |
| 처리 기록 | 목록 | 담당 교수, 배정 시각, 감사 로그(시각 · 행위) | `section-title` 21px/600, 본문 14px muted |

## 상태

| 상태 | 표시 |
| --- | --- |
| 판정 완료 | 보완 요청 카드 숨김 |
| 보완 요청 보냄 | 플래시 "학생에게 보완 자료를 요청했어요", 분석 결과 영역에 앰버 "제출 대기" 박스 |
| 항목·메모 모두 비움 | 빨강 플래시 "요청할 자료를 하나 이상 고르거나 메모를 적어 주세요." |
