-- 마이그레이션 시험용 옛 데이터 2단계: 0009(학점 단위·인정 학점 칸)까지 배포된 뒤, 0010(배분 원장) 전에 쌓인 데이터.
-- legacy_0002.sql을 넣고 0009까지 올린 DB에 넣는다. [0010] 배분 원장 백필, [0011] 학칙 정책 백필을 시험한다.

-- 관리자가 0009 화면에서 정한 값 (0009는 학점 단위를 추정하지 않는다)
UPDATE institutions SET credit_system = 'us_semester' WHERE id IN (1, 2);
UPDATE institutions SET credit_system = 'kr_credit' WHERE id IN (3, 4, 5, 6);
UPDATE institutions SET max_transfer_credits = 45 WHERE id = 1;  -- [0011] 편입 학점 상한 45 그대로 옮김 (대학 2는 비움 → 60)

INSERT INTO credit_conversion_rules (id, target_institution_id, source_system, target_system, factor, method, effective_from, approved_by, note, created_at) VALUES
  (1101, 1, 'kr_credit', 'us_semester', 1.0, 'approved_table', '2020-01-01', 1, '시험용 예시 규칙', '2026-11-01');

-- 판정은 INSERT만 한다(앱 규칙). 재판정이 가리키는 이의 신청이 먼저 있어야 하므로 순서대로 넣는다
INSERT INTO decisions (id, course_evaluation_id, decided_by, action, result, target_course_id, reason_codes, reason_memo, ai_recommendation_snapshot, conflict_acknowledged, appeal_id, decided_at, accepted_credits, credit_unit, credit_basis, source_credits, source_credit_unit, conversion_rule_id) VALUES
  -- [0010] 한 번만 판정 → active
  (505, 406, 4, 'approve', 'direct', 303, '[]', '', '{"recommendation": "direct"}', false, NULL, '2026-11-02', 3, 'us_semester', 'full', 3, 'kr_credit', 1101),
  -- [0010] 507 → 508 재판정: 507은 superseded(508이 대체), 508은 active
  (507, 407, 3, 'approve', 'direct', 301, '[]', '', '{"recommendation": "direct"}', false, NULL, '2026-11-02', 3, 'us_semester', 'full', 3, 'kr_credit', 1101),
  -- [0010] 509 → 510(불인정 0학점): 509는 superseded(510이 대체), 510은 줄을 만들지 않음
  (509, 405, 4, 'modify', 'direct', 302, '["other"]', '보완 자료 확인', '{"recommendation": "insufficient"}', false, NULL, '2026-11-02', 3, 'us_semester', 'full', 3, 'kr_credit', 1101),
  (510, 405, 7, 'reject', 'none', NULL, '["weeks_insufficient"]', '', '{"recommendation": "insufficient"}', false, NULL, '2026-11-06', 0, 'us_semester', 'not_accepted', 3, 'kr_credit', 1101);

-- 이의 신청 처리 (602: 504에 대한 이의, 603: 507에 대한 이의) — 재판정은 원 판정 교수가 아닌 교수
UPDATE appeals SET status = 'redecided', handled_by = 2, handled_at = '2026-11-04' WHERE id = 602;
INSERT INTO appeals (id, course_evaluation_id, decision_id, student_id, reason, status, handled_by, handler_note, handled_at, created_at) VALUES
  (603, 407, 507, 16, '트리·해시 과제를 첨부했어요.', 'redecided', 2, '', '2026-11-04', '2026-11-03');

INSERT INTO decisions (id, course_evaluation_id, decided_by, action, result, target_course_id, reason_codes, reason_memo, ai_recommendation_snapshot, conflict_acknowledged, appeal_id, decided_at, accepted_credits, credit_unit, credit_basis, source_credits, source_credit_unit, conversion_rule_id) VALUES
  -- [0010] 504(학점 없음, 옮기지 않음) 뒤 이의 신청 재판정 → active
  (506, 404, 7, 'modify', 'elective', 302, '["level_difference"]', '', '{"recommendation": "direct"}', false, 602, '2026-11-05', 3, 'us_semester', 'elective', 3, 'kr_credit', 1101),
  (508, 407, 6, 'modify', 'elective', 301, '["level_difference"]', '', '{"recommendation": "direct"}', false, 603, '2026-11-05', 2, 'us_semester', 'partial', 3, 'kr_credit', 1101);

UPDATE transfer_requests SET status = 'decided' WHERE id IN (101, 103, 107, 108);

SELECT setval('decisions_id_seq', 1000);
SELECT setval('appeals_id_seq', 1000);
SELECT setval('credit_conversion_rules_id_seq', 2000);
