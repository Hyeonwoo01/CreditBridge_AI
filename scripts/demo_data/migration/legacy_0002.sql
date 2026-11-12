-- 마이그레이션 시험용 옛 데이터 1단계: 리비전 0002 스키마에 맞춘 운영 DB 모습 (0003부터 데이터 백필이 시작된다).
-- 불러오기: scripts/migration_demo.py (테스트: tests/integration/test_migrations.py). 비밀번호는 모두 demo1234 (로컬 시험 전용).
-- 각 행 옆 주석의 [0003] 같은 표시는 그 행이 시험하는 마이그레이션과 기대 결과다. 기대값은 test_migrations.py에서 확인한다.
-- id를 직접 정해 두고 마지막에 시퀀스를 맞춘다 (이후 앱이 넣는 행과 겹치지 않게).

-- ── 대학 ────────────────────────────────────────────────────────────────
INSERT INTO institutions (id, name, country, is_target, tuition_per_credit, degree_credits, created_at) VALUES
  (1, 'Legacy State University', 'US', true, 1200, 128, '2026-08-01'),   -- [0011] 졸업 학점 128 그대로 옮김
  (2, 'Second Target College', 'US', true, NULL, NULL, '2026-08-01'),     -- [0011] 비어 있으면 120·60
  (3, 'Seoul Source University (서울출신대학교)', 'KR', false, NULL, NULL, '2026-08-01'),
  (4, 'Busan Source University (부산출신대학교)', 'KR', false, NULL, NULL, '2026-08-01'),   -- [0004] 요청으로만 연결
  (5, 'Daegu Source University (대구출신대학교)', 'KR', false, NULL, NULL, '2026-08-01'),   -- [0004] 동등 과목표로만 연결
  (6, 'Incheon Source University (인천출신대학교)', 'KR', false, NULL, NULL, '2026-08-01'), -- [0004] 감사 로그로만 연결
  (7, 'Orphan Source University (고아출신대학교)', 'KR', false, NULL, NULL, '2026-08-01'); -- [0004] 어디에도 연결 없음 → 목록에 없음

INSERT INTO departments (id, institution_id, name, created_at) VALUES
  (1, 1, 'Computer Science', '2026-08-01'),
  (2, 1, 'Mathematics', '2026-08-01'),
  (3, 2, 'Computer Science', '2026-08-01');  -- [0003] 이름이 같아도 다른 대학 학과로 연결하면 안 됨

-- ── 계정 (비밀번호는 아래 UPDATE 한 줄로 모두 demo1234) ─────────────────
INSERT INTO users (id, email, password_hash, name, role, institution_id, department_id, created_at) VALUES
  (1, 'admin@legacy.example', '-', 'Legacy Admin', 'admin', 1, NULL, '2026-08-01'),
  (2, 'registrar@legacy.example', '-', 'Riley Registrar', 'evaluator', 1, NULL, '2026-08-01'),
  (3, 'cs.prof@legacy.example', '-', 'Casey Stone', 'professor', 1, 1, '2026-08-01'),
  (4, 'math.prof@legacy.example', '-', 'Morgan Hale', 'professor', 1, 2, '2026-08-01'),
  (5, 'admin@second.example', '-', 'Second Admin', 'admin', 2, NULL, '2026-08-01'),
  (6, 'cs.prof2@legacy.example', '-', 'Jordan Lee', 'professor', 1, 1, '2026-08-01'),
  (7, 'math.prof2@legacy.example', '-', 'Avery Park', 'professor', 1, 2, '2026-08-01'),
  -- 학생: 0003이 가장 최근 요청으로 출신 대학·편입 전공을 채운다
  (10, 'multi@student.example', '-', '김다중', 'student', 1, NULL, '2026-08-10'),       -- [0003] 최근 요청(102)의 서울·CS
  (11, 'preset@student.example', '-', '박기존', 'student', 1, 2, '2026-08-10'),          -- [0003] 학과가 이미 있으면 덮어쓰지 않음
  (12, 'unknownmajor@student.example', '-', '최전공', 'student', 1, NULL, '2026-08-10'), -- [0003] 없는 전공 이름 → 학과는 비움
  (13, 'norequest@student.example', '-', '정요청', 'student', 1, NULL, '2026-08-10'),    -- [0003] 요청 없음 → 그대로 비움
  (14, 't2@student.example', '-', '한둘째', 'student', 2, NULL, '2026-08-10'),           -- [0003] 같은 이름 학과 중 자기 대학 것(3)
  (15, 'closed@student.example', '-', '오삭제', 'student', 1, NULL, '2026-08-10'),       -- [0005][0006] 문서 삭제 완료 요청 보유
  (16, 'draftcopy@student.example', '-', '윤초안', 'student', 1, NULL, '2026-08-10');    -- [0007] 초안 요청에 과목 줄 복사

UPDATE users SET password_hash = '$argon2id$v=19$m=65536,t=3,p=4$86Kld8y4YoB4ksvK3YthXg$hDEaAp5VPxH5IcgM/R+WW/IUCyJpvRDDisIhIrxvPMc';  -- argon2id(demo1234)

-- ── 편입 요청 ──────────────────────────────────────────────────────────
INSERT INTO transfer_requests (id, student_id, source_institution_id, target_institution_id, major, status, submitted_at, transcript_file_key, transcript_masked_name, created_at) VALUES
  (101, 10, 4, 1, 'Mathematics', 'submitted', '2026-09-02', 'transcripts/a-old.pdf', '김**', '2026-09-01'), -- [0007] 오래된 성적표: 계정으로 옮기지 않고 그대로 남음
  (102, 10, 3, 1, 'Computer Science', 'decided', '2026-10-02', 'transcripts/a-new.pdf', '김**', '2026-10-01'), -- [0003] 최근 요청 [0007] 계정 성적표가 됨
  (103, 11, 3, 1, 'Computer Science', 'submitted', '2026-09-12', 'transcripts/b.pdf', '박**', '2026-09-11'),
  (104, 12, 3, 1, 'Underwater Basket Weaving', 'draft', NULL, NULL, NULL, '2026-09-05'),                  -- [0007] 성적표 없는 학생의 초안 → 그대로
  (105, 14, 3, 2, 'Computer Science', 'draft', NULL, 'transcripts/t2.pdf', '한**', '2026-09-06'),
  (106, 15, 3, 1, 'Computer Science', 'decided', '2026-09-11', NULL, NULL, '2026-09-10'),                  -- [0005] 문서 삭제 완료 → closed
  (107, 15, 3, 1, 'Mathematics', 'submitted', '2026-09-21', NULL, NULL, '2026-09-20'),                     -- [0005] 삭제 요청만 있음 → 그대로
  (108, 16, 3, 1, 'Computer Science', 'submitted', '2026-09-16', 'transcripts/g.pdf', '윤**', '2026-09-15'),
  (109, 16, 3, 1, 'Computer Science', 'draft', NULL, NULL, NULL, '2026-10-05'),                            -- [0007] 과목 줄 없음 → 계정 성적표에서 복사
  (110, 16, 3, 1, 'Mathematics', 'draft', NULL, NULL, NULL, '2026-10-06');                                 -- [0007] 직접 넣은 과목 줄 있음 → 복사 안 함

INSERT INTO transcript_entries (id, transfer_request_id, title, code, credits, grade, term, link_confirmed, created_at) VALUES
  (1, 101, 'Calculus I', 'MATH101', 3, 'A', '2024-1', false, '2026-09-01'),
  (2, 101, 'General Physics', 'PHY101', 3, 'B+', '2024-1', false, '2026-09-01'),
  (3, 102, 'Calculus I', 'MATH101', 3, 'A', '2024-1', true, '2026-10-01'),
  (4, 102, 'Data Structures', 'CSE204', 3, 'B', '2024-2', true, '2026-10-01'),
  (5, 102, 'C Programming', 'CSE101', 3, 'D', '2024-1', false, '2026-10-01'),
  (6, 103, 'Linear Algebra', 'MATH201', 3, 'A-', '2024-2', true, '2026-09-11'),
  (7, 105, 'Intro to Programming', 'CS100', 3, 'A', '2024-1', false, '2026-09-06'),
  (8, 108, 'Data Structures', 'CSE204', 3, 'B+', '2024-2', true, '2026-09-15'),
  (9, 108, 'Linear Algebra', 'MATH201', 3, 'C+', '2025-1', false, '2026-09-15'),
  (10, 110, 'Discrete Mathematics', 'MATH150', 3, 'B', '2025-1', false, '2026-10-06');

-- ── 강의계획서: 기준(요청 없음) 201~203 [0012] 기관 기준·확인됨 / 학생 제출 211~ [0012] 학생 제출·미확인·모름 ──
INSERT INTO syllabi (id, institution_id, transfer_request_id, owner_id, content_hash, original_filename, language, raw_text, course_code, course_title, credits, status, created_at) VALUES
  (201, 1, NULL, NULL, 'legacy-ref-cse2231', 'CSE2231.txt', 'en', 'Week 1: Abstract data types. Week 2: Linked lists. Week 3: Trees and heaps. Week 4: Hash tables. Week 5: Graph traversal.', 'CSE 2231', 'Data Structures', 3, 'ready', '2026-08-01'),
  (202, 1, NULL, NULL, 'legacy-ref-math2568', 'MATH2568.txt', 'en', 'Week 1: Systems of linear equations. Week 2: Matrix algebra. Week 3: Vector spaces. Week 4: Eigenvalues and eigenvectors.', 'MATH 2568', 'Linear Algebra', 3, 'ready', '2026-08-01'),
  (203, 1, NULL, NULL, 'legacy-ref-math1151', 'MATH1151.txt', 'en', 'Week 1: Limits. Week 2: Derivatives. Week 3: Applications of derivatives. Week 4: Integrals.', 'MATH 1151', 'Calculus I', 4, 'ready', '2026-08-01'),
  (211, 3, 102, 10, 'legacy-stu-211', 'data_structures.pdf', 'ko', '1주: 추상 자료형. 2주: 연결 리스트. 3주: 트리와 힙. 4주: 해시 테이블. 5주: 그래프 탐색.', 'CSE204', 'Data Structures', 3, 'ready', '2026-10-01'),
  (212, 3, 102, 10, 'legacy-stu-212', 'calculus.pdf', 'ko', '1주: 극한. 2주: 미분. 3주: 미분의 응용. 4주: 적분.', 'MATH101', 'Calculus I', 3, 'ready', '2026-10-01'),
  (213, 3, 106, 15, 'legacy-stu-213', 'data_structures.pdf', 'ko', '', 'CSE204', 'Data Structures', 3, 'deleted', '2026-09-10'),  -- 문서 삭제 완료(본문 지움)
  (214, 3, 107, 15, 'legacy-stu-214', 'linear_algebra.pdf', 'ko', '1주: 연립일차방정식. 2주: 행렬. 3주: 벡터공간. 4주: 고유값.', 'MATH201', 'Linear Algebra', 3, 'ready', '2026-09-20'),
  (215, 3, 103, 11, 'legacy-stu-215', 'linear_algebra_sparse.pdf', 'ko', '선형대수. 행렬을 배운다.', 'MATH201', 'Linear Algebra', 3, 'ready', '2026-09-11'),
  (216, 4, 101, 10, 'legacy-stu-216', 'calculus_busan.pdf', 'ko', '1주: 극한. 2주: 미분. 3주: 적분.', 'MATH101', 'Calculus I', 3, 'ready', '2026-09-01'),
  (217, 3, 108, 16, 'legacy-stu-217', 'data_structures.pdf', 'ko', '1주: 추상 자료형. 2주: 연결 리스트. 3주: 트리. 4주: 해시.', 'CSE204', 'Data Structures', 3, 'ready', '2026-09-15');

INSERT INTO courses (id, institution_id, code, title, credits, department_id, level, reference_syllabus_id, created_at) VALUES
  (301, 1, 'CSE 2231', 'Data Structures', 3, 1, 'intro', 201, '2026-08-01'),
  (302, 1, 'MATH 2568', 'Linear Algebra', 3, 2, 'intro', 202, '2026-08-01'),
  (303, 1, 'MATH 1151', 'Calculus I', 4, 2, 'intro', 203, '2026-08-01'),
  (304, 2, 'CS 101', 'Intro to Computing', 3, 3, 'intro', NULL, '2026-08-01');

-- ── AI 분석 결과 ───────────────────────────────────────────────────────
INSERT INTO course_evaluations (id, transfer_request_id, syllabus_id, candidate_course_id, status, recommendation, coverage, confidence, summary, prompt_version, is_latest, created_at) VALUES
  (401, 102, 211, 301, 'done', 'direct', 0.90, 'high', '', 'legacy-v1', true, '2026-10-02'),
  (402, 102, 212, 303, 'done', 'direct', 0.95, 'high', '', 'legacy-v1', true, '2026-10-02'),
  (403, 106, 213, 301, 'done', 'elective', 0.70, 'medium', '', 'legacy-v1', true, '2026-09-11'),
  (404, 107, 214, 302, 'done', 'direct', 0.85, 'high', '', 'legacy-v1', true, '2026-09-21'),
  (405, 103, 215, 302, 'done', 'insufficient', 0.30, 'low', '', 'legacy-v1', true, '2026-09-12'),
  (406, 101, 216, 303, 'done', 'direct', 0.90, 'high', '', 'legacy-v1', true, '2026-09-02'),
  (407, 108, 217, 301, 'done', 'direct', 0.88, 'high', '', 'legacy-v1', true, '2026-09-16');

-- 0009 이전 판정: 인정 학점 칸이 없었다 → [0010] 배분 원장에 옮기지 않음
INSERT INTO decisions (id, course_evaluation_id, decided_by, action, result, target_course_id, reason_codes, reason_memo, ai_recommendation_snapshot, conflict_acknowledged, appeal_id, decided_at) VALUES
  (501, 401, 3, 'approve', 'direct', 301, '[]', '', '{"recommendation": "direct"}', false, NULL, '2026-10-10'),
  (502, 402, 4, 'approve', 'direct', 303, '[]', '', '{"recommendation": "direct"}', false, NULL, '2026-10-10'),
  (503, 403, 3, 'modify', 'elective', 301, '["level_difference"]', '', '{"recommendation": "elective"}', false, NULL, '2026-09-25'),
  (504, 404, 4, 'approve', 'direct', 302, '[]', '', '{"recommendation": "direct"}', false, NULL, '2026-10-01');

INSERT INTO appeals (id, course_evaluation_id, decision_id, student_id, reason, status, handler_note, created_at) VALUES
  (601, 403, 503, 15, '자료구조 15주 강의 자료로 증명할 수 있어요.', 'submitted', '', '2026-09-28'), -- [0006] 종료된 요청 → 사유 지움
  (602, 404, 504, 15, '고유값 단원 시험지를 첨부했어요.', 'submitted', '', '2026-10-03');           -- [0006] 종료 안 됨 → 사유 유지

INSERT INTO assignments (id, course_evaluation_id, reviewer_id, assigned_by, assigned_at, is_active) VALUES
  (701, 403, 3, 2, '2026-09-12', true),  -- [0005] 종료된 요청 → 비활성
  (702, 404, 4, 2, '2026-09-22', true),
  (703, 406, 4, 2, '2026-09-03', true),
  (704, 401, 3, 2, '2026-10-03', true),
  (705, 407, 3, 2, '2026-09-17', true);

INSERT INTO privacy_requests (id, transfer_request_id, student_id, status, due_at, reviewed_by, reviewed_at, approved_by, completed_at, created_at) VALUES
  (801, 106, 15, 'completed', '2026-10-10', 2, '2026-09-30', 1, '2026-10-01', '2026-09-29'),
  (802, 107, 15, 'requested', '2026-11-05', NULL, NULL, NULL, NULL, '2026-10-06');

INSERT INTO equivalencies (id, target_institution_id, source_institution_id, source_course_key, source_course_label, target_course_id, result, decided_on, note, imported_by, created_at) VALUES
  (901, 1, 5, 'code:MATH101', 'Calculus I', 303, 'direct', '2025-06-01', '', 1, '2026-08-05');

INSERT INTO audit_logs (id, actor_id, action, target_type, target_id, payload_json, created_at) VALUES
  (1001, 1, 'institution.create', 'institution', '6', '{}', '2026-08-02'),  -- [0004] 대상 대학 1 ↔ 인천
  (1002, 1, 'institution.create', 'institution', '2', '{}', '2026-08-02'),  -- [0004] 대상 대학끼리는 연결 안 함
  (1003, 1, 'institution.update', 'institution', '7', '{}', '2026-08-02'),  -- [0004] create가 아니면 연결 안 함
  (1004, 5, 'institution.create', 'institution', '3', '{}', '2026-08-02');  -- [0004] 대상 대학 2 ↔ 서울 (요청과 중복, 한 줄만)

-- ── 시퀀스 맞추기 ──────────────────────────────────────────────────────
SELECT setval('institutions_id_seq', 100);
SELECT setval('departments_id_seq', 100);
SELECT setval('users_id_seq', 100);
SELECT setval('transfer_requests_id_seq', 1000);
SELECT setval('transcript_entries_id_seq', 1000);
SELECT setval('syllabi_id_seq', 1000);
SELECT setval('courses_id_seq', 1000);
SELECT setval('course_evaluations_id_seq', 1000);
SELECT setval('decisions_id_seq', 1000);
SELECT setval('appeals_id_seq', 1000);
SELECT setval('assignments_id_seq', 1000);
SELECT setval('privacy_requests_id_seq', 1000);
SELECT setval('equivalencies_id_seq', 1000);
SELECT setval('audit_logs_id_seq', 2000);
