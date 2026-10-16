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
| FR-10 판정 이력·감사 로그 | ✅ | `decisions`, `audit_logs` 추가 전용 + `docs/db-grants.sql`. 관리자 콘솔에 최근 감사 로그 8건(`services/stats.py::recent_audit`: 소속 기관 행위만, 로그인 제외, 처리 내용·AI 추천→판정·사유, 학생은 이름 대신 "학생"). 이의 신청 근거 자료 열람(`appeal_file.download`: 열어 본 사람 id·파일 id·이의 신청 id, 파일 이름 없음)과 계정 비활성화·다시 활성화(`account.deactivate`·`account.reactivate`)도 기록. 관리자 전체 감사 로그(`/admin/audit`)와 콘솔 카드는 모두 소속 기관 사용자의 기록만 조회(`audit_repo.recent_for_institution`, 여러 대학이 함께 쓰는 SaaS라 다른 기관 기록은 보이지 않음) | `test_decisions_table_has_no_update_path`, `test_admin_console_shows_recent_audit_without_student_names`, `test_appeal_form_with_evidence_files`, `test_audit_log_page_shows_only_own_institution` |
| FR-11 일관성 경보 | ✅ | 같은 출신 대학·과목의 과거 판정은 모두 표시(유사도 포함). 같은 대상 과목·강의계획서 유사도 0.80 이상·결과 다름일 때만 확정 전 경보(기준값은 첫 측정 후 확정). 교수 화면은 사유 선택 창 안에서 경보 확인, 심사 큐는 AI 추천과 어긋나는 건을 "일관성 경보" 필터·인라인 경보 행·"충돌 내역 확인" 버튼으로 미리 표시(`services/review.py` `QueueRow.conflicts`) | `test_consistency_alert_for_conflicting_past_decision`, `test_same_result_raises_no_alert`, `test_revised_syllabus_raises_no_alert` (TC-18), `test_queue_search_and_conflict_filter` |
| FR-12 역할 기반 접근 제어 | ✅ | `security/permissions.py`, `security/session.py` | `test_role_based_access`, `test_no_decision_without_assigned_professor` |
| FR-13 개인정보 보호 | ✅ | 성적표 마스킹 후 LLM 전달, S3 SSE 설정, 삭제 요청 흐름(학생 요청 → 심사관 처리 → 관리자 승인 시 삭제, 처리 기한·기한 초과 표시, 보완 자료·이의 신청 근거 자료 원본까지 삭제) `services/privacy.py`, [privacy.md](privacy.md). 관리자 콘솔에 마스킹 건수·삭제 요청 처리 현황·데이터 보존 및 파기 정책 카드. 교수·관리자 화면에 학생 이름을 보여 주지 않음. 접근 로그에서 쿼리 문자열(심사 큐 검색어) 제거 `logging_setup.py`. 메뉴 숫자 배지: 심사관 "삭제 요청"은 처리할 건수, 관리자 "삭제 승인"은 승인할 건수(`privacy.pending_count`) | `test_injection_and_masking.py`(`test_access_log_drops_query_string` 포함), `test_privacy_request_review_and_admin_approval`, `test_appeal_form_with_evidence_files`, `test_admin_console_shows_recent_audit_without_student_names`, `test_staff_nav_badges_count_their_own_work` |
| FR-14 숨은 지시 문구 탐지 | ✅ | `ai/injection.py` (영·한 패턴, LLM 입력에서 제외, 경고) | `test_hidden_instruction_is_flagged_and_removed_from_prompt` |

## P2 중요 (파일럿)

| 기능 | 상태 | 구현 위치 | 테스트 |
| --- | --- | --- | --- |
| FR-15 사전 시뮬레이션 | ✅ | 입학 확정(대상 대학 소속) 학생, 요청마다 전공 선택. 예상 인정 학점·남은 학기·추가 비용(인정 시 절감액) 범위 (`services/student.py::simulate`). 화면: 시뮬레이션 리포트(`student/request.html`) 다크 히어로 "예상 인정 학점: 낮음~높음 / 이수 학점 (최대 %)", 과목 필터 `?show=all\|approved\|supplement\|review`(`CourseRow.group`), 대응 교과목·판정 교수 표시 | `test_request_page_shows_simulation_and_stage`, `unit/test_simulation_and_links.py`, `test_student_report_filters_courses` |
| FR-16 수준 차이 판별 | ✅ | level=lower면 직접 인정 추천 안 함, ×0.75 | `unit/test_scoring.py` |
| FR-17 심사 큐 대시보드 | ✅ | `services/review.py::queue` → `review/queue.html`: 전체(기본)·고신뢰·저신뢰·정보 부족·일관성 경보 필터, 학과 필터, 정렬, 검색(이름·과목·출신 대학·`#요청번호`), 페이지당 20건, 지표 카드, 커버리지 원형 게이지. 화면 상단 기관 보조 바 집계(`GET /notifications/workspace`, `stats.workspace_counts`). 메뉴 "심사 큐" 숫자 배지는 교수 배정이 필요한 과목 수(`review.unassigned_count`) | `test_queue_tabs_and_department_assignment`, `test_queue_search_and_conflict_filter`, `test_staff_nav_badges_count_their_own_work` |
| FR-18 교수 자동 배정 | ✅ | 후보 과목 학과의 배정이 가장 적은 교수, 배정 알림. 심사 큐에서 행을 고르면 하단 선택 바·머리 카드 버튼으로 일괄 배정. 교수 메뉴 "배정된 심사" 숫자 배지는 판정할 건수(`views.professor_items`, 재판정 포함) | 같은 테스트, `test_notifications_for_assignment_and_delegation`, `test_staff_nav_badges_count_their_own_work` |
| FR-19 부재 시 대리 재배정 | ✅ | 대리 재배정, 대리 심사자·심사관 알림(화면 + SMTP 설정 시 메일) `services/notifications.py` | `test_away_professor_is_replaced_by_delegate`, `test_notifications_for_assignment_and_delegation` (TC-15) |
| FR-20 모바일 승인 | 🟡 | 근거 우선 모바일 화면, 모바일 메뉴(역할별 메뉴 숫자 배지 포함), 하단 고정 판정 바, 화면 폭 - 32px로 뜨는 사유 선택 창, 화면·메일 알림. 웹 푸시는 없음(서비스 워커·추가 라이브러리 필요) | 수동 확인 |
| FR-21 진행 상황 포털 | ✅ | 과목별 접수→AI 분석→교수 검토→확정, 예상 완료일, 보완 요청·이의 신청 상태. 요청 단위 "심사 진행 현황" 4단계(서류 접수 → AI 구조화·근거 추출 → 학과 교수 심사(확정 수/전체) → 최종 확정, `RequestView.analysis_done`·`decided_count`). 학생 홈 대시보드: 할 일(보완 자료 제출, 성적표·강의계획서 누락, 과목 연결 확인, 분석 실패, 준비되면 "학사처에 심사 요청하기")과 제출 전 서류 준비율(`student.readiness`), 새 판정 결과 알림. 학생 메뉴(내 편입 요청 · 이의 신청 · 인정 사례) 숫자 배지(`views.nav_badges`·`student_badges`, 기호 없이 숫자만·색으로 구분·0이면 숨김): "내 편입 요청"에 채워야 할 서류 수(앰버)와 새 판정 결과 수(파랑), "이의 신청"에 신청할 수 있는 과목 수(중립)와 새 이의 신청 결과 수(파랑). 결과 배지는 해당 화면을 열면 읽음 처리(`notifications.mark_seen`) | `test_professor_decision_rules_and_portal`, `test_student_report_filters_courses`, `test_dashboard_lists_todos_and_readiness`, `test_nav_badges_for_new_results_clear_when_viewed` |
| FR-22 보완 자료 요청 | ✅ | 심사관·배정 교수가 항목·메모 지정해 요청 → 학생 알림 → 제출 시 처리됨·요청자 알림, 재분석 결과에 교수 배정 이어짐 `services/materials.py`. 학생 리포트의 보완 필요 과목에 정보 부족 진단(요청 항목·부족 개념·필요 자료)과 "보완 서류 제출하기", 심사 큐에 "보완 요청 발송"·"보완 대기" 표시 | `test_material_request_flow_keeps_assignment`, `test_evaluator_can_request_materials_but_not_after_decision` |
| FR-23 이의 신청·근거 리포트 | ✅ | 학생 신청 → 심사관 받아들임(재판정 교수 배정)·기각(사유 필수) → 교수 재판정(새 판정 행, 원 판정 보존). 리포트에 경과 표시 `services/appeals.py`. 학생 메뉴 "이의 신청"(`/student/appeals`, `appeals.student_rows`)에서 본인 이의 신청의 상태·재판정 결과·기각 사유를 모아 보기. 같은 화면에 "이의 신청할 수 있는 과목"(`appeals.appealable`: 판정 확정, 처리 중 이의 없음), 그 수는 학생 메뉴 "이의 신청" 옆 숫자 배지로도 표시. 작성 화면 `/student/evaluations/{id}/appeal`(원 판정 요약·근거가 약한 개념·사유 20~3000자·근거 자료 PDF/JPG/PNG 최대 3개, `appeal_files` 테이블·Alembic 0005, 실패하면 적은 사유를 유지한 채 422로 다시 표시). 근거 자료는 `/appeal-files/{id}`로 학생 본인·심사관·담당 교수만 내려받기(`appeals.file_for_download`). 판정 근거 리포트에 역할별 "돌아가기"(교수 판정 화면·심사관 심사 건·학생 과목 결과)와 "PDF 내려받기"(`/evaluations/{id}/report.pdf`, `report_pdf.html` → `documents/pdf.py::html_to_pdf`, PyMuPDF Story·내장 CJK 글꼴, 시각은 UTC, 쪽 번호·"최종 판정은 학과 교수" 바닥글, 내부 메모 제외). 심사관 메뉴 "이의 신청" 숫자 배지는 접수돼 처리할 건수(`appeals.submitted_count`) | `test_appeal_accept_and_redecide_keeps_original_decision`, `test_appeal_dismiss_requires_note`, `test_student_sees_own_appeals_and_report_links_back`, `test_appeal_form_with_evidence_files`, `test_nav_badges_for_new_results_clear_when_viewed`, `test_staff_nav_badges_count_their_own_work`, `test_report_pdf_download` |
| FR-24 학사정보시스템 내보내기 | ✅ | CSV + 토큰 인증 JSON API `GET /api/sis/decisions` (관리자 발급·폐기, 재판정은 최신만 + 대체 판정 번호) `services/sis.py`. 심사 큐 "SIS CSV 내보내기", 관리자 콘솔 SIS 연동 카드(토큰 상태·확정 과목 수) | `test_sis_api_requires_admin_issued_token`, 이의 신청 테스트의 CSV 확인 |

## P3 선택

| 기능 | 상태 | 비고 |
| --- | --- | --- |
| FR-25 근거 원문 위치 이동 | ✅ | 근거 구절을 누르면 학생·기준 강의계획서 원문의 해당 위치로 이동하고 표시(`templating.highlight`). 구절 옆 "원본 N쪽 ↗"은 원본 PDF를 새 탭에서 그 쪽(`#page=N`)으로 연다: 업로드 때 페이지 위치표 `syllabi.page_offsets`(Alembic 0007, `documents/text.py::join_pages`·`page_at`, 스캔 페이지 전사 글도 원래 쪽 자리에) → `/evaluations/{id}/original/{source|target}`(`services/originals.py`, 심사 건을 볼 수 있는 사람만, `inline`·`no-store`, 학생 원본을 열면 감사 로그 `syllabus.original_view`). 이미지는 "원본 이미지", 보완 자료로 덧붙인 구절은 쪽 링크 없음. 0007 이전 업로드는 `scripts/backfill_page_offsets.py`(텍스트 PDF만, LLM 호출 없음) | `test_evidence_links_jump_to_source_positions`, `test_evidence_links_open_original_pdf_page`, `test_backfill_page_offsets_for_older_uploads`, `unit/test_pdf_pages.py` |
| FR-26 기존 동등 과목표 가져오기 | ✅ | CSV(엑셀 'CSV UTF-8', cp949도 읽음) 일괄 가져오기, 한 줄이라도 틀리면 저장 안 함. 과거 판정 이력에 "기존 동등 과목표"로 표시하되 강의계획서가 없어 경보 대상은 아님. 학생 "선배 인정 사례"(`/student/precedents`, `services/precedents.py`)에서 기관 동등 과목표만 출신 대학·과목으로 검색(같은 기준은 한 줄, 최근 판정일). 다른 학생의 CreditBridge 판정과 동등 과목표 메모는 보이지 않음 (`test_equivalency_import_shows_in_history_without_blocking`, `test_precedents_show_only_institution_equivalency_table`) |
| FR-27 운영 통계 | ✅ | 처리량, 판정 대기 과목, 평균 소요일, AI 추천 수용률(=1-AI-교수 불일치율), 학과별 처리 지표(접수·판정·처리율·평균 소요일), 승인·수정·반려 구성, 이의 신청·삭제 요청 현황, 월별 판정 (`services/stats.py`). 관리자는 "관리자 콘솔"(`/admin/stats`, 감사 로그·보존 정책 포함), 심사관은 "운영 통계"(`/review/stats`) (`test_stats_page_counts_decisions_and_disagreement`, `test_admin_console_shows_recent_audit_without_student_names`) |
| FR-28 복수 대학 비교 | ⬜ | 기능 명세상 합격 전 학생 대상이라 사업 모델 확정 후 정의 |

## 운영 데이터 준비 (기능 명세 밖, 실제 운영에 필요)

| 기능 | 상태 | 구현 위치 | 테스트 |
| --- | --- | --- | --- |
| 첫 기관·관리자 생성 | ✅ | `scripts/create_admin.py` → `services/institution_data.py::bootstrap_admin` (임시 비밀번호 한 번 출력) | `test_bootstrap_admin_starts_without_demo_data` |
| 계정 CSV 가져오기 | ✅ | `institution_data.import_accounts` (역할·학과 검증, 이미 있는 이메일 건너뜀, 한 줄이라도 틀리면 저장 안 함, 임시 비밀번호 한 번만 표시·해시만 저장) | `test_account_import_gives_one_time_passwords_and_forces_change`, `test_account_import_rejects_bad_rows_without_saving` |
| 첫 로그인 비밀번호 변경 | ✅ | `users.must_change_password`, `security/session.py::PasswordChangeRequired`, `/account/password`(`services/auth.py::change_password`, 10자 이상) | 같은 테스트 |
| 비밀번호 재설정 | ✅ | 메일 링크: `/account/forgot`·`/account/reset`, `services/auth.py`(itsdangerous 서명 토큰 30분·비밀번호 지문으로 한 번만, 5분 재요청 제한, 계정 존재 여부 비공개), Celery `auth.password_reset_email`(종류 reset·lockout·admin·welcome). 관리자 초기화 `/admin/data/password-reset`와 계정 CSV는 메일 발송이 있으면 72시간짜리 설정 링크를 자동 발송, 없으면 임시 비밀번호 한 번 표시. 비밀번호가 바뀌면 다른 세션 종료(`security/session.py::password_fingerprint`) | `test_password_reset.py` 전체 |
| 기한 알림 자동 발송 | ✅ | 매일 한 번 Celery beat(`celery_app.beat_schedule` "daily-reminders", `REMINDER_HOUR_UTC` 기본 13시 UTC) → 작업 `reminders.daily` → `services/reminders.py`. 교수: 판정 기한(배정 + `REVIEW_SLA_DAYS`)이 지났거나 하루 남은 심사 · 심사관: 기한 지난 심사, 교수 배정 없이 `REMINDER_UNASSIGNED_DAYS`일 지난 과목, 처리 기한 `REMINDER_PRIVACY_DAYS`일 이내 삭제 요청 · 관리자: 승인 기한 임박 삭제 요청 · 학생: `REMINDER_MATERIAL_DAYS`일째 답 없는 보완 자료 요청. 같은 사람·같은 종류는 20시간에 한 번, 비활성 계정 제외, 메일 설정 시 바로 메일. 운영 통계·관리자 콘솔에 "기한 알림" 카드(오늘 대상 건수). docker compose `beat` 서비스 | `test_reminders.py` 전체 |
| 계정 비활성화 | ✅ | 졸업·퇴직한 계정을 지우지 않고(감사 기록 보존) 막기: `users.is_active`·`deactivated_at`(Alembic 0006), `/admin/data/accounts/active`(`institution_data.set_active`). 로그인(비밀번호가 맞을 때만 비활성 안내, 실패로 세지 않음)·남은 세션·비밀번호 재설정·알림 메일·교수 배정·대리 심사자·심사관 알림 대상·계정 수에서 제외. 교수는 진행 중 심사를 같은 학과 다른 교수에게 넘기고(`review.pick_reviewer`), 없으면 배정을 비우고 심사관에게 알림. 본인 계정은 불가, 다시 활성화하면 이전 비밀번호로 로그인 | `test_account_active.py` 전체 |
| 심사 건 내부 메모 | ✅ | 심사관·담당 교수가 심사 건마다 남기는 메모(예: "학과장 확인 중"). `evaluation_notes`(Alembic 0007, 강의계획서 단위로 모아 재분석해도 이어짐), `POST /evaluations/{id}/notes`(`services/notes.py`, 1000자, 고치지 않고 새로 남김). 학생 화면·판정 근거 리포트(화면·PDF)에는 나오지 않음. 감사 로그 `note.create`는 id만(내용 없음). 개인정보 삭제 승인 때 함께 삭제. DB 권한 SELECT·INSERT·DELETE(`docs/db-grants.sql`) | `test_internal_notes_for_staff_only` |
| 로그인 실패 잠금 | ✅ | 연속 5번 실패 → 1분 잠금, 연속 10번 → 비밀번호 무효화 + 재설정 메일 자동 발송(메일 미설정 시 관리자 재발급 안내), 성공·재설정 시 초기화. `users.failed_logins`·`locked_until`(Alembic 0004), `services/auth.py::login_attempt`, `repositories/users.py::add_failed_login` | `test_login_lockout.py` 전체 |
| 과목 CSV 가져오기 | ✅ | `institution_data.import_courses` (과목 코드 기준 생성·수정, 학과가 정한 필수 개념 `courses.concepts` → AI 비교 프롬프트에 사용) | `test_course_import_and_reference_upload_feed_ai_comparison` |
| 과목별 기준 강의계획서 | ✅ | `institution_data.upload_reference` → Celery `reference.process`(스캔은 Claude 전사, 실패 시 이전 것 유지). 없으면 AI 비교 후보에서 빠짐 | 같은 테스트 |
| 출신 대학 등록 | ✅ | `institution_data.add_source_institution` | `test_source_institution_registration` |
| CSV 공통 처리 | ✅ | `services/csv_import.py` (UTF-8·cp949, 5MB, 실제 줄 번호) — 동등 과목표 가져오기도 사용 | `unit/test_institution_data_units.py` |

## 화면 ↔ 기능

화면 디자인 기준은 [DESIGN.md](DESIGN.md) 1.1.0. 폭은 기본 1280px, 심사 큐·원문 대조 화면만 1440px(`frontend/templates/base.html` `{% block width %}`). 템플릿 열의 경로는 `frontend/templates/` 기준.

| 화면 | URL | 템플릿 | 기능 | 화면 테스트 |
| --- | --- | --- | --- | --- |
| 로그인 | `/login` | `login.html` (실패 5번 1분 잠금·10번 초기화 안내) | FR-12, 운영 데이터 준비 | `test_five_failures_lock_login_for_a_minute`, `test_lockout_without_mail_sends_user_to_admin` |
| 공통 레이아웃 | 모든 화면 | `base.html` (기관 보조 바·집계 칩, Human-in-the-Loop 푸터), 역할별 메뉴 `*/_nav.html`·`partials/macros.html::nav_link`. 역할별 메뉴 숫자 배지(`views.nav_badges`, `web/nav.py`가 그릴 때 한 번 계산, 숫자만·0이면 숨김). 학생 "내 편입 요청 · 이의 신청 · 인정 사례": 채워야 할 서류 수(앰버)·이의 신청할 수 있는 과목 수(중립)·새 결과 수(파랑). 심사관: 심사 큐에 교수 배정이 필요한 과목 수, 이의 신청에 처리할(접수됨) 건수, 삭제 요청에 처리할 건수. 교수: 배정된 심사에 판정할 건수(재판정 포함). 관리자: 계정·과목에 준비가 필요한 항목(기준 강의계획서 없는 과목 + 교수가 없는 학과), 삭제 승인에 승인할 건수. 교직원 배지는 모두 앰버(처리할 일)이고 기관 전체 집계는 보조 바 칩이 맡음. 함께 쓰는 화면(알림·판정 근거 리포트·비밀번호 변경)에도 같은 배지, 모바일은 햄버거 메뉴 안. 첫 로그인 비밀번호 강제 변경 중과 오류 화면에는 역할 메뉴·배지 없음 | FR-12, FR-17·18·19·20·21, FR-13·23 | `test_queue_search_and_conflict_filter`(집계 칩, 학생에게 숨김), `test_dashboard_lists_todos_and_readiness`(숫자만 표시), `test_nav_badges_for_new_results_clear_when_viewed`, `test_staff_nav_badges_count_their_own_work` |
| 학생 홈(대시보드) | `/student` | `student/index.html` | FR-15 요청 만들기·요청별 예상 인정 학점·판정 확정 수·남은 학기, FR-21 할 일·서류 준비율 | `test_request_needs_affiliated_student_and_valid_major`, `test_dashboard_lists_todos_and_readiness` |
| 선배 인정 사례(학생) | `/student/precedents` | `student/precedents.html` | FR-26 기관 동등 과목표 검색 | `test_precedents_show_only_institution_equivalency_table` |
| 편입 학점 시뮬레이션 리포트 | `/student/requests/{id}` | `student/request.html`, `partials/course_list.html` | FR-01·02·15·21·22, FR-13 삭제 요청 | `test_request_page_shows_simulation_and_stage`, `test_student_report_filters_courses` |
| 이의 신청(학생) | `/student/appeals` | `student/appeals.html` | FR-23 | `test_student_sees_own_appeals_and_report_links_back` |
| 이의 신청 작성(학생) | `/student/evaluations/{id}/appeal` | `student/appeal_form.html` | FR-23 | `test_appeal_form_with_evidence_files` |
| 과목 분석 결과(학생) | `/student/evaluations/{id}` | `student/evaluation.html`, `partials/evaluation.html` | FR-05~08·22·23·25 | `test_material_request_flow_keeps_assignment`, `test_evidence_links_jump_to_source_positions` |
| 심사 큐 | `/review` | `review/queue.html` (메뉴 숫자: 교수 배정이 필요한 과목) | FR-11·17·18·24 | `test_queue_tabs_and_department_assignment`, `test_queue_search_and_conflict_filter` |
| 심사 건 상세 | `/review/evaluations/{id}` | `review/evaluation.html`, `partials/history.html`(`#history`), `partials/notes.html`(`#notes` 내부 메모), `partials/material_request_form.html`(`#materials`) | FR-11·22·25 | `test_evaluator_can_request_materials_but_not_after_decision`, `test_internal_notes_for_staff_only` |
| 이의 신청 처리(근거 자료 내려받기)·삭제 요청·동등 과목표 | `/review/appeals`, `/appeal-files/{id}`, `/review/privacy`, `/admin/privacy`, `/review/equivalencies` | `review/appeals.html`, `privacy.html`, `review/equivalencies.html` | FR-23·13·26 | `test_appeal_accept_and_redecide_keeps_original_decision`, `test_appeal_form_with_evidence_files`, `test_privacy_request_review_and_admin_approval`, `test_equivalency_import_shows_in_history_without_blocking` |
| 관리자 콘솔 · 운영 통계 | `/admin/stats`, `/review/stats` | `stats.html` | FR-27·10·13·24 | `test_stats_page_counts_decisions_and_disagreement`, `test_admin_console_shows_recent_audit_without_student_names` |
| 교수 홈(배정된 심사) | `/professor` | `professor/index.html` (배정 목록·이의 신청 재판정·부재 설정, 메뉴 숫자: 판정할 건수) | FR-18·19·23 | `test_away_professor_is_replaced_by_delegate` |
| 교수 판정 화면 | `/professor/evaluations/{id}`, `/evaluations/{id}/original/{side}` | `professor/evaluation.html` (사유 선택 창, 하단 판정 바, 근거 구절 "원본 N쪽" 링크, 내부 메모 `partials/notes.html`) | FR-09·11·20·22·23·25 | `test_professor_decision_rules_and_portal`, `test_reason_dialog_reopens_on_validation_error`, `test_evidence_links_open_original_pdf_page` |
| 판정 근거 리포트 | `/evaluations/{id}/report`, `/evaluations/{id}/report.pdf` | `report.html` (역할별 메뉴·숫자 배지·돌아가기·PDF 내려받기·근거 구절 원본 쪽), `report_pdf.html`(PDF용) | FR-10·23·25 | `test_consistency_alert_for_conflicting_past_decision`, `test_student_sees_own_appeals_and_report_links_back`, `test_report_pdf_download` |
| 알림 | `/notifications` | `notifications.html` (역할별 메뉴·숫자 배지, 열면 모두 읽음) | FR-19·20·22·23 | `test_notifications_for_assignment_and_delegation` |
| 계정·과목 관리 | `/admin/data`, `/account/password`, `/account/forgot`, `/account/reset` | `admin/data.html`, `account/password.html`, `account/forgot.html`, `account/reset.html` (메뉴 숫자: 기준 강의계획서 없는 과목 + 교수가 없는 학과) — 비밀번호 변경 화면은 역할별 메뉴·숫자 배지가 있고 첫 로그인 강제 변경이면 숨김 | 운영 데이터 준비 | `test_institution_data.py` 전체 |
| 학사정보 연동·감사 로그 | `/admin/sis`, `/admin/audit` | `admin/sis.html`, `admin/audit.html` | FR-24·10 | `test_sis_api_requires_admin_issued_token` |
| 오류 | 모든 화면 | `error.html` (400·403·404, 역할 메뉴·숫자 배지 없이 "이전 화면으로·처음으로" 링크) | FR-12 | `test_role_based_access` |

화면에 넣지 않은 것: 판정 확률(%), 실제 데이터가 없는 인증 배지·전주 대비 증감·해시 체인·상담 담당자 카드, 교수·관리자 화면의 학생 이름.

학생 화면 참고안(사이드바형 정보 구조)에서 검토했지만 넣지 않은 것:

| 항목 | 이유 |
| --- | --- |
| 사이드바, 목표 대학 전환·복수 대학 비교 | DESIGN.md는 상단 메뉴. 복수 대학 비교는 FR-28(P3, 사업 모델 확정 후 정의)이고 MVP 학생 계정은 입학이 확정된 대학 한 곳에 소속 |
| 졸업 요건 감사(Degree Audit)·상위 과정·거주 학점 | 테스트 명세 범위에서 제외. 남은 학기 예상(FR-15)까지만 |
| 4.0 GPA·WES/ECE 환산 | 명세에 없음. 성적은 민감 정보이고 공인 평가를 대신 계산하지 않음 |
| 국문 강의계획서 영문 번역 | FR-01 "번역 없이 인식". 근거 구절은 원문과 일치할 때만 저장 |
| 교양(Gen-Ed) 인정 단계 | 추천은 3단계로 고정(`services/scoring.py`). 바꾸려면 규칙 버전과 대학별 교양 과목 데이터 필요 |
| 청원서·커버레터 생성기 | 이의 신청은 같은 기관 안에서 처리하고 근거 비교는 판정 근거 리포트가 맡음. AI는 추천만 |
| 다른 학생의 판정 사례 | FR-12(학생은 본인 건만). 선배 인정 사례는 기관 동등 과목표만 보여 줌 |

## 테스트 명세 대비 아직 측정하지 않은 것

- AI 품질 지표(오인정률, 판정 일치도, 언어 간 격차; ECE는 확률을 도입하는 파일럿에서): `tests/eval`에 골든셋 평가 틀만 있음. 전문가 라벨 골든셋(D1)이 필요하다.
- 한국어 스캔본 인식 정확도(TC-01), 성능·부하(NF-08, NF-09): 실제 데이터와 API 키로 측정해야 한다.
