# 기능 구현 현황 (기능명세서 FR ↔ 코드 ↔ 테스트)

기준: [docs/spec.md](spec.md) 4장 기능 명세, 2장 테스트 명세.

상태: ✅ 구현·테스트 / 🟡 부분 구현 / ⬜ 미구현

## P1 필수 (MVP)

| 기능 | 상태 | 구현 위치 | 테스트 |
| --- | --- | --- | --- |
| FR-01 문서 업로드·OCR | ✅ | `documents/text.py` (PDF·JPG·PNG만, 파일당 20MB·강의계획서 30건, PyMuPDF 텍스트 레이어, 스캔 페이지·이미지 → Claude 전사), 품질 점수 `syllabi.quality_score` | `unit/test_documents.py`, `integration/test_pipeline.py::test_upload_rejections_have_reasons` |
| FR-02 성적표 파싱·과목 연결 | ✅ | `services/analysis.py::process_transcript, relink_transcript` (불확실하면 학생 확인) | `test_transcript_is_masked_before_llm_and_linked` |
| FR-03 구조화 추출 | ✅ | `ai/extraction.py`, `prompts/extraction.md`(학문 분야 포함), `schemas/extraction.py`. 같은 content_hash 문서는 추출 재사용 | 파이프라인 테스트 전반 |
| FR-04 미기재 정보 처리 | ✅ | `SyllabusExtraction.missing_fields`, 화면 "기재 없음" | `test_sparse_syllabus_is_insufficient_with_guidance` |
| FR-05 매핑·커버리지 | ✅ | `ai/candidates.py` (학과 필터, 최대 30개) → `ai/matching.py` + `prompts/evaluation.md` 개념별 비교 → `services/scoring.py`. 임베딩 없음 | `test_calculus_maps_to_math1151...`, `test_no_equivalent_course_is_not_forced`, `test_course_outside_catalog_departments_gets_no_candidates`, `unit/test_candidates.py` |
| FR-06 근거 하이라이트 | ✅ | `ai/evidence.py` 원문 검증, `evidence_spans`, 좌우 병치 화면 | 근거 환각 0건 검증 (`test_calculus...`) |
| FR-07 판정 추천·신뢰도 | ✅ | 3단계 추천·신뢰도(상·중·하), 신뢰도 하는 정보 부족으로 전환. 확률(%)은 계산하지 않음. 같은 content_hash·같은 규칙 버전이면 LLM 재호출 없이 저장된 판정·근거 반환 | `unit/test_scoring.py`, `test_reupload_reuses_stored_result_without_llm` (TC-12) |
| FR-08 정보 부족 진단 | ✅ | 추천 대신 정보 부족, 부족 개념·필요 자료, 보완 자료 재분석(이전 결과 보존) | `test_supplement_reanalyzes_and_keeps_history` |
| FR-09 교수 최종 판정 | ✅ | `services/decisions.py` (승인·수정·반려, 반려/추천과 다르면 선택형 `reason_codes` 1개 이상, '기타'만 `reason_memo` 필수) | `test_professor_decision_rules_and_portal` (TC-17), `unit/test_decision_rules.py` |
| FR-10 판정 이력·감사 로그 | ✅ | `decisions`, `audit_logs` 추가 전용 + `docs/db-grants.sql` | `test_decisions_table_has_no_update_path` |
| FR-11 일관성 경보 | ✅ | 같은 출신 대학·과목의 과거 판정은 모두 표시(유사도 포함). 같은 대상 과목·강의계획서 유사도 0.80 이상·결과 다름일 때만 확정 전 경보(기준값은 첫 측정 후 확정) | `test_consistency_alert_for_conflicting_past_decision`, `test_same_result_raises_no_alert`, `test_revised_syllabus_raises_no_alert` (TC-18) |
| FR-12 역할 기반 접근 제어 | ✅ | `security/permissions.py`, `security/session.py` | `test_role_based_access`, `test_no_decision_without_assigned_professor` |
| FR-13 개인정보 보호 | 🟡 | 성적표 마스킹 후 LLM 전달, S3 SSE 설정, 문서 삭제 요청, [privacy.md](privacy.md) | `test_injection_and_masking.py`, `test_privacy_delete_removes_files_and_text` — 기관별 학습 제외 설정 UI 없음(Anthropic API는 기본적으로 API 데이터를 학습에 쓰지 않음), 삭제 기한 관리 없음 |
| FR-14 숨은 지시 문구 탐지 | ✅ | `ai/injection.py` (영·한 패턴, LLM 입력에서 제외, 경고) | `test_hidden_instruction_is_flagged_and_removed_from_prompt` |

## P2 중요 (파일럿)

| 기능 | 상태 | 비고 |
| --- | --- | --- |
| FR-15 사전 시뮬레이션 | ✅ | 입학 확정(대상 대학 소속) 학생, 요청마다 전공 선택. 예상 인정 학점·남은 학기·추가 비용 범위 (`services/student.py::simulate`) |
| FR-16 수준 차이 판별 | ✅ | level=lower면 직접 인정 추천 안 함, ×0.75 |
| FR-17 심사 큐 대시보드 | ✅ | 고신뢰/저신뢰/정보 부족 탭, 학과 필터, 정렬 |
| FR-18 교수 자동 배정 | ✅ | 후보 과목 학과의 배정이 가장 적은 교수 |
| FR-19 부재 시 대리 재배정 | 🟡 | 대리 재배정·큐 표시. 이메일 알림 없음 |
| FR-20 모바일 승인 | 🟡 | 근거 우선 모바일 화면. 푸시 알림 없음 |
| FR-21 진행 상황 포털 | ✅ | 접수→AI 분석→교수 검토→확정, 예상 완료일 |
| FR-22 보완 자료 요청 | ⬜ | 학생 쪽 보완 업로드는 있음, 심사관의 요청 발송은 없음 |
| FR-23 이의 신청·근거 리포트 | 🟡 | 판정 근거 리포트 있음, 이의 신청 접수 흐름 없음 |
| FR-24 학사정보시스템 내보내기 | 🟡 | 확정 판정 CSV(모의 SIS). API 연동 없음 |

## P3 선택

FR-25(근거 원문 위치 이동: 위치는 저장, 화면 이동 없음), FR-26, FR-27, FR-28 ⬜

## 테스트 명세 대비 아직 측정하지 않은 것

- AI 품질 지표(오인정률, 판정 일치도, 언어 간 격차; ECE는 확률을 도입하는 파일럿에서): `tests/eval`에 골든셋 평가 틀만 있음. 전문가 라벨 골든셋(D1)이 필요하다.
- 한국어 스캔본 인식 정확도(TC-01), 성능·부하(NF-08, NF-09): 실제 데이터와 API 키로 측정해야 한다.
