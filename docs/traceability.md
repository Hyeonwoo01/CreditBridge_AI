# 기능 구현 현황 (기능명세서 FR ↔ 코드 ↔ 테스트)

기준: [docs/spec.md](spec.md) 4장 기능 명세, 2장 테스트 명세.

상태: ✅ 구현·테스트 / 🟡 부분 구현 / ⬜ 미구현

경로 기준: 코드는 `backend/`(예: `services/review.py` = `backend/services/review.py`), 템플릿은 `frontend/templates/`(예: `review/queue.html`), 테스트는 `tests/`.

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
| FR-09 교수 최종 판정 | ✅ | `services/decisions.py` (승인·수정·반려, 반려/추천과 다르면 선택형 `reason_codes` 1개 이상, '기타'만 `reason_memo` 필수). 화면: 반려·추천과 다른 수정·과거 판정과 다른 결과일 때 확정 전 사유 선택 창(`professor/evaluation.html` `<dialog>`, 사유 설명 `decisions.REASON_HINTS`, 메모 500자·글자 수, `app.js`), 422·409면 창을 다시 열어 오류 표시 | `test_professor_decision_rules_and_portal` (TC-17), `unit/test_decision_rules.py`, `test_reason_dialog_reopens_on_validation_error` |
| FR-10 판정 이력·감사 로그 | ✅ | `decisions`, `audit_logs` 추가 전용 + `docs/db-grants.sql`. 관리자 콘솔에 최근 감사 로그 8건(`services/stats.py::recent_audit`: 소속 기관 행위만, 로그인 제외, 처리 내용·AI 추천→판정·사유, 학생은 이름 대신 "학생") | `test_decisions_table_has_no_update_path`, `test_admin_console_shows_recent_audit_without_student_names` |
| FR-11 일관성 경보 | ✅ | 같은 출신 대학·과목의 과거 판정은 모두 표시(유사도 포함). 같은 대상 과목·강의계획서 유사도 0.80 이상·결과 다름일 때만 확정 전 경보(기준값은 첫 측정 후 확정). 교수 화면은 사유 선택 창 안에서 경보 확인, 심사 큐는 AI 추천과 어긋나는 건을 "일관성 경보" 필터·인라인 경보 행·"충돌 내역 확인" 버튼으로 미리 표시(`services/review.py` `QueueRow.conflicts`) | `test_consistency_alert_for_conflicting_past_decision`, `test_same_result_raises_no_alert`, `test_revised_syllabus_raises_no_alert` (TC-18), `test_queue_search_and_conflict_filter` |
| FR-12 역할 기반 접근 제어 | ✅ | `security/permissions.py`, `security/session.py` | `test_role_based_access`, `test_no_decision_without_assigned_professor` |
| FR-13 개인정보 보호 | ✅ | 성적표 마스킹 후 LLM 전달, S3 SSE 설정, 삭제 요청 흐름(학생 요청 → 심사관 처리 → 관리자 승인 시 삭제, 처리 기한·기한 초과 표시, 보완 자료 원본까지 삭제) `services/privacy.py`, [privacy.md](privacy.md). 관리자 콘솔에 마스킹 건수·삭제 요청 처리 현황·데이터 보존 및 파기 정책 카드. 교수·관리자 화면에 학생 이름을 보여 주지 않음. 접근 로그에서 쿼리 문자열(심사 큐 검색어) 제거 `logging_setup.py` | `test_injection_and_masking.py`(`test_access_log_drops_query_string` 포함), `test_privacy_request_review_and_admin_approval`, `test_admin_console_shows_recent_audit_without_student_names` |
| FR-14 숨은 지시 문구 탐지 | ✅ | `ai/injection.py` (영·한 패턴, LLM 입력에서 제외, 경고) | `test_hidden_instruction_is_flagged_and_removed_from_prompt` |

## P2 중요 (파일럿)

| 기능 | 상태 | 구현 위치 | 테스트 |
| --- | --- | --- | --- |
| FR-15 사전 시뮬레이션 | ✅ | 입학 확정(대상 대학 소속) 학생, 요청마다 전공 선택. 예상 인정 학점·남은 학기·추가 비용(인정 시 절감액) 범위 (`services/student.py::simulate`). 화면: 시뮬레이션 리포트(`student/request.html`) 다크 히어로 "예상 인정 학점: 낮음~높음 / 이수 학점 (최대 %)", 과목 필터 `?show=all\|approved\|supplement\|review`(`CourseRow.group`), 대응 교과목·판정 교수 표시 | `test_request_page_shows_simulation_and_stage`, `unit/test_simulation_and_links.py`, `test_student_report_filters_courses` |
| FR-16 수준 차이 판별 | ✅ | level=lower면 직접 인정 추천 안 함, ×0.75 | `unit/test_scoring.py` |
| FR-17 심사 큐 대시보드 | ✅ | `services/review.py::queue` → `review/queue.html`: 전체(기본)·고신뢰·저신뢰·정보 부족·일관성 경보 필터, 학과 필터, 정렬, 검색(이름·과목·출신 대학·`#요청번호`), 페이지당 20건, 지표 카드, 커버리지 원형 게이지. 화면 상단 기관 보조 바 집계(`GET /notifications/workspace`, `stats.workspace_counts`) | `test_queue_tabs_and_department_assignment`, `test_queue_search_and_conflict_filter` |
| FR-18 교수 자동 배정 | ✅ | 후보 과목 학과의 배정이 가장 적은 교수, 배정 알림. 심사 큐에서 행을 고르면 하단 선택 바·머리 카드 버튼으로 일괄 배정 | 같은 테스트, `test_notifications_for_assignment_and_delegation` |
| FR-19 부재 시 대리 재배정 | ✅ | 대리 재배정, 대리 심사자·심사관 알림(화면 + SMTP 설정 시 메일) `services/notifications.py` | `test_away_professor_is_replaced_by_delegate`, `test_notifications_for_assignment_and_delegation` (TC-15) |
| FR-20 모바일 승인 | 🟡 | 근거 우선 모바일 화면, 모바일 메뉴, 하단 고정 판정 바, 화면 폭 - 32px로 뜨는 사유 선택 창, 화면·메일 알림. 웹 푸시는 없음(서비스 워커·추가 라이브러리 필요) | 수동 확인 |
| FR-21 진행 상황 포털 | ✅ | 과목별 접수→AI 분석→교수 검토→확정, 예상 완료일, 보완 요청·이의 신청 상태. 요청 단위 "심사 진행 현황" 4단계(서류 접수 → AI 구조화·근거 추출 → 학과 교수 심사(확정 수/전체) → 최종 확정, `RequestView.analysis_done`·`decided_count`) | `test_professor_decision_rules_and_portal`, `test_student_report_filters_courses` |
| FR-22 보완 자료 요청 | ✅ | 심사관·배정 교수가 항목·메모 지정해 요청 → 학생 알림 → 제출 시 처리됨·요청자 알림, 재분석 결과에 교수 배정 이어짐 `services/materials.py`. 학생 리포트의 보완 필요 과목에 정보 부족 진단(요청 항목·부족 개념·필요 자료)과 "보완 서류 제출하기", 심사 큐에 "보완 요청 발송"·"보완 대기" 표시 | `test_material_request_flow_keeps_assignment`, `test_evaluator_can_request_materials_but_not_after_decision` |
| FR-23 이의 신청·근거 리포트 | ✅ | 학생 신청 → 심사관 받아들임(재판정 교수 배정)·기각(사유 필수) → 교수 재판정(새 판정 행, 원 판정 보존). 리포트에 경과 표시 `services/appeals.py` | `test_appeal_accept_and_redecide_keeps_original_decision`, `test_appeal_dismiss_requires_note` |
| FR-24 학사정보시스템 내보내기 | ✅ | CSV + 토큰 인증 JSON API `GET /api/sis/decisions` (관리자 발급·폐기, 재판정은 최신만 + 대체 판정 번호) `services/sis.py`. 심사 큐 "SIS CSV 내보내기", 관리자 콘솔 SIS 연동 카드(토큰 상태·확정 과목 수) | `test_sis_api_requires_admin_issued_token`, 이의 신청 테스트의 CSV 확인 |

## P3 선택

| 기능 | 상태 | 비고 |
| --- | --- | --- |
| FR-25 근거 원문 위치 이동 | 🟡 | 근거 구절을 누르면 학생·기준 강의계획서 원문의 해당 위치로 이동하고 표시(`templating.highlight`). 원본 PDF의 페이지 번호로 이동은 아직 없음 (`test_evidence_links_jump_to_source_positions`) |
| FR-26 기존 동등 과목표 가져오기 | ✅ | CSV(엑셀 'CSV UTF-8', cp949도 읽음) 일괄 가져오기, 한 줄이라도 틀리면 저장 안 함. 과거 판정 이력에 "기존 동등 과목표"로 표시하되 강의계획서가 없어 경보 대상은 아님 (`test_equivalency_import_shows_in_history_without_blocking`) |
| FR-27 운영 통계 | ✅ | 처리량, 판정 대기 과목, 평균 소요일, AI 추천 수용률(=1-AI-교수 불일치율), 학과별 처리 지표(접수·판정·처리율·평균 소요일), 승인·수정·반려 구성, 이의 신청·삭제 요청 현황, 월별 판정 (`services/stats.py`). 관리자는 "관리자 콘솔"(`/admin/stats`, 감사 로그·보존 정책 포함), 심사관은 "운영 통계"(`/review/stats`) (`test_stats_page_counts_decisions_and_disagreement`, `test_admin_console_shows_recent_audit_without_student_names`) |
| FR-28 복수 대학 비교 | ⬜ | 기능 명세상 합격 전 학생 대상이라 사업 모델 확정 후 정의 |

## 운영 데이터 준비 (기능 명세 밖, 실제 운영에 필요)

| 기능 | 상태 | 구현 위치 | 테스트 |
| --- | --- | --- | --- |
| 첫 기관·관리자 생성 | ✅ | `scripts/create_admin.py` → `services/institution_data.py::bootstrap_admin` (임시 비밀번호 한 번 출력) | `test_bootstrap_admin_starts_without_demo_data` |
| 계정 CSV 가져오기 | ✅ | `institution_data.import_accounts` (역할·학과 검증, 이미 있는 이메일 건너뜀, 한 줄이라도 틀리면 저장 안 함, 임시 비밀번호 한 번만 표시·해시만 저장) | `test_account_import_gives_one_time_passwords_and_forces_change`, `test_account_import_rejects_bad_rows_without_saving` |
| 첫 로그인 비밀번호 변경 | ✅ | `users.must_change_password`, `security/session.py::PasswordChangeRequired`, `/account/password`(`services/auth.py::change_password`, 10자 이상) | 같은 테스트 |
| 비밀번호 재설정 | ✅ | 메일 링크: `/account/forgot`·`/account/reset`, `services/auth.py`(itsdangerous 서명 토큰 30분·비밀번호 지문으로 한 번만, 5분 재요청 제한, 계정 존재 여부 비공개), Celery `auth.password_reset_email`(종류 reset·lockout·admin·welcome). 관리자 초기화 `/admin/data/password-reset`와 계정 CSV는 메일 발송이 있으면 72시간짜리 설정 링크를 자동 발송, 없으면 임시 비밀번호 한 번 표시. 비밀번호가 바뀌면 다른 세션 종료(`security/session.py::password_fingerprint`) | `test_password_reset.py` 전체 |
| 로그인 실패 잠금 | ✅ | 연속 5번 실패 → 1분 잠금, 연속 10번 → 비밀번호 무효화 + 재설정 메일 자동 발송(메일 미설정 시 관리자 재발급 안내), 성공·재설정 시 초기화. `users.failed_logins`·`locked_until`(Alembic 0004), `services/auth.py::login_attempt`, `repositories/users.py::add_failed_login` | `test_login_lockout.py` 전체 |
| 과목 CSV 가져오기 | ✅ | `institution_data.import_courses` (과목 코드 기준 생성·수정, 학과가 정한 필수 개념 `courses.concepts` → AI 비교 프롬프트에 사용) | `test_course_import_and_reference_upload_feed_ai_comparison` |
| 과목별 기준 강의계획서 | ✅ | `institution_data.upload_reference` → Celery `reference.process`(스캔은 Claude 전사, 실패 시 이전 것 유지). 없으면 AI 비교 후보에서 빠짐 | 같은 테스트 |
| 출신 대학 등록 | ✅ | `institution_data.add_source_institution` | `test_source_institution_registration` |
| CSV 공통 처리 | ✅ | `services/csv_import.py` (UTF-8·cp949, 5MB, 실제 줄 번호) — 동등 과목표 가져오기도 사용 | `unit/test_institution_data_units.py` |

## 화면 ↔ 기능

화면 디자인 기준은 [DESIGN.md](DESIGN.md) 1.1.0. 폭은 기본 1280px, 심사 큐·원문 대조 화면만 1440px(`frontend/templates/base.html` `{% block width %}`). 템플릿 열의 경로는 `frontend/templates/` 기준.

| 화면 | URL | 템플릿 | 기능 | 화면 테스트 |
| --- | --- | --- | --- | --- |
| 공통 레이아웃 | 모든 화면 | `base.html` (기관 보조 바·집계 칩, Human-in-the-Loop 푸터) | FR-12, FR-19 알림 | `test_queue_search_and_conflict_filter`(집계 칩, 학생에게 숨김) |
| 학생 홈 | `/student` | `student/index.html` | FR-15 요청 만들기 | `test_request_needs_affiliated_student_and_valid_major` |
| 편입 학점 시뮬레이션 리포트 | `/student/requests/{id}` | `student/request.html`, `partials/course_list.html` | FR-01·02·15·21·22, FR-13 삭제 요청 | `test_request_page_shows_simulation_and_stage`, `test_student_report_filters_courses` |
| 과목 분석 결과(학생) | `/student/evaluations/{id}` | `student/evaluation.html`, `partials/evaluation.html` | FR-05~08·22·23·25 | `test_material_request_flow_keeps_assignment`, `test_evidence_links_jump_to_source_positions` |
| 심사 큐 | `/review` | `review/queue.html` | FR-11·17·18·24 | `test_queue_tabs_and_department_assignment`, `test_queue_search_and_conflict_filter` |
| 심사 건 상세 | `/review/evaluations/{id}` | `review/evaluation.html`, `partials/history.html`(`#history`), `partials/material_request_form.html`(`#materials`) | FR-11·22 | `test_evaluator_can_request_materials_but_not_after_decision` |
| 이의 신청·삭제 요청·동등 과목표 | `/review/appeals`, `/review/privacy`, `/admin/privacy`, `/review/equivalencies` | `review/appeals.html`, `privacy.html`, `review/equivalencies.html` | FR-23·13·26 | 각 기능 테스트 |
| 관리자 콘솔 · 운영 통계 | `/admin/stats`, `/review/stats` | `stats.html` | FR-27·10·13·24 | `test_stats_page_counts_decisions_and_disagreement`, `test_admin_console_shows_recent_audit_without_student_names` |
| 교수 판정 화면 | `/professor/evaluations/{id}` | `professor/evaluation.html` (사유 선택 창, 하단 판정 바) | FR-09·11·20·22·23 | `test_professor_decision_rules_and_portal`, `test_reason_dialog_reopens_on_validation_error` |
| 판정 근거 리포트 | `/evaluations/{id}/report` | `report.html` | FR-10·23 | `test_consistency_alert_for_conflicting_past_decision` |
| 계정·과목 관리 | `/admin/data`, `/account/password`, `/account/forgot`, `/account/reset` | `admin/data.html`, `account/password.html`, `account/forgot.html`, `account/reset.html` | 운영 데이터 준비 | `test_institution_data.py` 전체 |
| 학사정보 연동·감사 로그 | `/admin/sis`, `/admin/audit` | `admin/sis.html`, `admin/audit.html` | FR-24·10 | `test_sis_api_requires_admin_issued_token` |

화면에 넣지 않은 것: 판정 확률(%), 실제 데이터가 없는 인증 배지·전주 대비 증감·해시 체인·상담 담당자 카드, 교수·관리자 화면의 학생 이름.

## 테스트 명세 대비 아직 측정하지 않은 것

- AI 품질 지표(오인정률, 판정 일치도, 언어 간 격차; ECE는 확률을 도입하는 파일럿에서): `tests/eval`에 골든셋 평가 틀만 있음. 전문가 라벨 골든셋(D1)이 필요하다.
- 한국어 스캔본 인식 정확도(TC-01), 성능·부하(NF-08, NF-09): 실제 데이터와 API 키로 측정해야 한다.
