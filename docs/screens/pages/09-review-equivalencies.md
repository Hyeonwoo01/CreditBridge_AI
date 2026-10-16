# P09 기존 동등 과목표

| 항목 | 내용 |
| --- | --- |
| URL | `GET /review/equivalencies`, 가져오기 `POST /review/equivalencies` (multipart) |
| 역할 | 심사관 |
| 템플릿 | `review/equivalencies.html` |
| 기능 | FR-26 엑셀(CSV) 판정 이력 일괄 가져오기 |

## 위치

```
[global-nav: 심사 큐 (2) · 이의 신청 (1) · 삭제 요청 · 동등 과목표(선택) · 통계 · CSV 내보내기]
제목 "기존 동등 과목표" + 설명(과거 판정 이력에 참고로 표시, 경보는 띄우지 않음)
┌ CSV 업로드 드롭존 ───────────────────────────────────┐
│ CSV 파일 올리기                                       │
│ 'CSV UTF-8'로 저장 안내 · 첫 줄 열 이름(코드 표기)       │
│ 값 규칙 안내 · 한 줄이라도 틀리면 저장 안 함              │
│ [파일 선택] [가져오기]                                 │
└─────────────────────────────────────────────────────┘
(오류 시) 빨강 박스: 고칠 행 목록 (최대 50개 + 외 N건)
최근 가져온 이력 표: 출신 과목 │ 판정 │ 판정일 │ 메모
[footer]
```

## 컴포넌트

| 영역 | 컴포넌트 | 내용 | 토큰 |
| --- | --- | --- | --- |
| 업로드 | `upload-dropzone-card` | `.csv`만, 5MB, 5,000행 이하 | 점선 `{colors.ink-muted-48}`, `{rounded.lg}` |
| 열 이름 | 코드 태그 | `source_institution,source_course,target_course,result,decided_on,note` | `{typography.mono-code}`, 배경 파치먼트 |
| 가져오기 | `button-primary` | | |
| 오류 목록 | 경고 박스 | "N행: 등록되지 않은 출신 대학, 판정은 direct·elective·none 중 하나 …" | `{colors.surface-reject-subtle}` + `{colors.status-reject}`, `role="alert"` |
| 이력 표 | 데이터 표 | 최근 200건, 판정은 "직접 인정·선택 인정·불인정"으로 표시 | 최소 폭 600px |

## 입력 규칙

| 열 | 필수 | 규칙 |
| --- | --- | --- |
| source_institution | 예 | 등록된 출신 대학 이름 그대로 |
| source_course | 예 | 과목 코드 또는 이름 |
| target_course | 직접 인정이면 예 | 대상 대학 카탈로그 코드 |
| result | 예 | direct·elective·none 또는 직접 인정·선택 인정·불인정 |
| decided_on | 아니오 | YYYY-MM-DD |
| note | 아니오 | 메모 |

인코딩은 UTF-8(BOM 포함)과 cp949(한국어 엑셀 기본)를 모두 읽는다.

## 상태

| 상태 | 표시 |
| --- | --- |
| 성공 | 플래시 "동등 과목표 N건을 가져왔어요." |
| 행 오류 | HTTP 422 + 오류 목록, 아무것도 저장하지 않음 |
| 파일 오류 | 빨강 플래시 (CSV 아님, 빈 파일, 5MB 초과, 필수 열 없음, 인코딩) |
