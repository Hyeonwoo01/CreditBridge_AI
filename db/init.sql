-- CreditBridge AI 스키마 (PostgreSQL). 자동 생성: sh scripts/export_db_sql.sh — 직접 고치지 말 것
-- 기준: alembic/versions (alembic upgrade head --sql). alembic_version도 함께 만들어 앱의 마이그레이션과 이어진다
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE institutions (
    name VARCHAR(200) NOT NULL, 
    country VARCHAR(2) NOT NULL, 
    is_target BOOLEAN NOT NULL, 
    tuition_per_credit INTEGER, 
    degree_credits INTEGER, 
    sis_token_hash VARCHAR(64), 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_institutions PRIMARY KEY (id)
);

CREATE TABLE departments (
    institution_id BIGINT NOT NULL, 
    name VARCHAR(50) NOT NULL, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_departments PRIMARY KEY (id), 
    CONSTRAINT fk_departments_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id), 
    CONSTRAINT uq_departments_institution_id UNIQUE (institution_id, name)
);

CREATE TABLE courses (
    institution_id BIGINT NOT NULL, 
    code VARCHAR(30) NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    credits NUMERIC(4, 1) NOT NULL, 
    department_id BIGINT NOT NULL, 
    level TEXT NOT NULL, 
    reference_syllabus_id BIGINT, 
    concepts JSONB, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_courses PRIMARY KEY (id), 
    CONSTRAINT ck_courses_credits_range CHECK (credits >= 0), 
    CONSTRAINT fk_courses_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id), 
    CONSTRAINT fk_courses_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id), 
    CONSTRAINT uq_courses_institution_id UNIQUE (institution_id, code)
);

CREATE INDEX ix_courses_department_id ON courses (department_id);

CREATE INDEX ix_courses_institution_id ON courses (institution_id);

CREATE TABLE users (
    email VARCHAR(255) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    institution_id BIGINT, 
    department_id BIGINT, 
    delegate_user_id BIGINT, 
    away_until DATE, 
    must_change_password BOOLEAN DEFAULT false NOT NULL, 
    failed_logins INTEGER DEFAULT 0 NOT NULL, 
    locked_until TIMESTAMP WITHOUT TIME ZONE, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    deactivated_at TIMESTAMP WITHOUT TIME ZONE, 
    locale VARCHAR(5), 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_users PRIMARY KEY (id), 
    CONSTRAINT ck_users_locale_valid CHECK (locale IS NULL OR locale IN ('ko', 'en')), 
    CONSTRAINT ck_users_role_valid CHECK (role IN ('student', 'evaluator', 'professor', 'admin')), 
    CONSTRAINT ck_users_failed_logins_range CHECK (failed_logins >= 0), 
    CONSTRAINT fk_users_delegate_user_id_users FOREIGN KEY(delegate_user_id) REFERENCES users (id), 
    CONSTRAINT fk_users_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (id), 
    CONSTRAINT fk_users_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id), 
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE INDEX ix_users_department_id ON users (department_id);

CREATE INDEX ix_users_role ON users (role);

CREATE TABLE audit_logs (
    actor_id BIGINT, 
    action VARCHAR(50) NOT NULL, 
    target_type VARCHAR(50) NOT NULL, 
    target_id VARCHAR(36) NOT NULL, 
    payload_json JSONB NOT NULL, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_audit_logs PRIMARY KEY (id), 
    CONSTRAINT fk_audit_logs_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)
);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_actor_action ON audit_logs (actor_id, action);

CREATE INDEX ix_audit_logs_target ON audit_logs (target_type, target_id);

CREATE TABLE equivalencies (
    target_institution_id BIGINT NOT NULL, 
    source_institution_id BIGINT NOT NULL, 
    source_course_key VARCHAR(100) NOT NULL, 
    source_course_label VARCHAR(255) NOT NULL, 
    target_course_id BIGINT, 
    result VARCHAR(10) NOT NULL, 
    decided_on DATE, 
    note TEXT NOT NULL, 
    imported_by BIGINT NOT NULL, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_equivalencies PRIMARY KEY (id), 
    CONSTRAINT ck_equivalencies_result_valid CHECK (result IN ('direct', 'elective', 'none')), 
    CONSTRAINT fk_equivalencies_imported_by_users FOREIGN KEY(imported_by) REFERENCES users (id), 
    CONSTRAINT fk_equivalencies_source_institution_id_institutions FOREIGN KEY(source_institution_id) REFERENCES institutions (id), 
    CONSTRAINT fk_equivalencies_target_course_id_courses FOREIGN KEY(target_course_id) REFERENCES courses (id), 
    CONSTRAINT fk_equivalencies_target_institution_id_institutions FOREIGN KEY(target_institution_id) REFERENCES institutions (id)
);

CREATE INDEX ix_equivalencies_pair_course ON equivalencies (target_institution_id, source_institution_id, source_course_key);

CREATE INDEX ix_equivalencies_source_course_key ON equivalencies (source_course_key);

CREATE TABLE notifications (
    user_id BIGINT NOT NULL, 
    kind VARCHAR(30) NOT NULL, 
    message VARCHAR(500) NOT NULL, 
    link VARCHAR(255) NOT NULL, 
    read_at TIMESTAMP WITHOUT TIME ZONE, 
    emailed_at TIMESTAMP WITHOUT TIME ZONE, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_notifications PRIMARY KEY (id), 
    CONSTRAINT fk_notifications_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_notifications_user_unread ON notifications (user_id, read_at);

CREATE TABLE transfer_requests (
    student_id BIGINT NOT NULL, 
    source_institution_id BIGINT NOT NULL, 
    target_institution_id BIGINT NOT NULL, 
    major VARCHAR(100) NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    submitted_at TIMESTAMP WITHOUT TIME ZONE, 
    transcript_file_key VARCHAR(255), 
    transcript_masked_name VARCHAR(100), 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_transfer_requests PRIMARY KEY (id), 
    CONSTRAINT ck_transfer_requests_status_valid CHECK (status IN ('draft', 'submitted', 'decided')), 
    CONSTRAINT fk_transfer_requests_source_institution_id_institutions FOREIGN KEY(source_institution_id) REFERENCES institutions (id), 
    CONSTRAINT fk_transfer_requests_student_id_users FOREIGN KEY(student_id) REFERENCES users (id), 
    CONSTRAINT fk_transfer_requests_target_institution_id_institutions FOREIGN KEY(target_institution_id) REFERENCES institutions (id)
);

CREATE INDEX ix_transfer_requests_status ON transfer_requests (status);

CREATE INDEX ix_transfer_requests_student_id ON transfer_requests (student_id);

CREATE INDEX ix_transfer_requests_target_institution_id ON transfer_requests (target_institution_id);

CREATE TABLE privacy_requests (
    transfer_request_id BIGINT NOT NULL, 
    student_id BIGINT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    due_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    reviewed_by BIGINT, 
    reviewed_at TIMESTAMP WITHOUT TIME ZONE, 
    approved_by BIGINT, 
    completed_at TIMESTAMP WITHOUT TIME ZONE, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_privacy_requests PRIMARY KEY (id), 
    CONSTRAINT ck_privacy_requests_status_valid CHECK (status IN ('requested', 'reviewed', 'completed')), 
    CONSTRAINT fk_privacy_requests_approved_by_users FOREIGN KEY(approved_by) REFERENCES users (id), 
    CONSTRAINT fk_privacy_requests_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id), 
    CONSTRAINT fk_privacy_requests_student_id_users FOREIGN KEY(student_id) REFERENCES users (id), 
    CONSTRAINT fk_privacy_requests_transfer_request_id_transfer_requests FOREIGN KEY(transfer_request_id) REFERENCES transfer_requests (id)
);

CREATE INDEX ix_privacy_requests_status ON privacy_requests (status);

CREATE INDEX ix_privacy_requests_transfer_request_id ON privacy_requests (transfer_request_id);

CREATE UNIQUE INDEX uq_privacy_requests_open_request ON privacy_requests (transfer_request_id) WHERE status <> 'completed';

CREATE TABLE syllabi (
    institution_id BIGINT NOT NULL, 
    transfer_request_id BIGINT, 
    owner_id BIGINT, 
    source_file_key VARCHAR(255), 
    content_hash VARCHAR(64) NOT NULL, 
    original_filename VARCHAR(255) NOT NULL, 
    language VARCHAR(8) NOT NULL, 
    raw_text TEXT NOT NULL, 
    page_offsets JSONB, 
    course_code VARCHAR(50) NOT NULL, 
    course_title VARCHAR(255) NOT NULL, 
    credits NUMERIC(4, 1), 
    extracted_json JSONB, 
    extraction_model VARCHAR(100), 
    quality_score NUMERIC(4, 3), 
    injection_flags JSONB, 
    status VARCHAR(20) NOT NULL, 
    error_message VARCHAR(500), 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_syllabi PRIMARY KEY (id), 
    CONSTRAINT ck_syllabi_status_valid CHECK (status IN ('uploaded', 'processing', 'ready', 'failed', 'deleted')), 
    CONSTRAINT ck_syllabi_credits_range CHECK (credits IS NULL OR credits >= 0), 
    CONSTRAINT ck_syllabi_quality_score_range CHECK (quality_score IS NULL OR quality_score BETWEEN 0 AND 1), 
    CONSTRAINT fk_syllabi_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id), 
    CONSTRAINT fk_syllabi_owner_id_users FOREIGN KEY(owner_id) REFERENCES users (id), 
    CONSTRAINT fk_syllabi_transfer_request_id_transfer_requests FOREIGN KEY(transfer_request_id) REFERENCES transfer_requests (id), 
    CONSTRAINT uq_syllabi_request_content UNIQUE (transfer_request_id, content_hash)
);

CREATE INDEX ix_syllabi_content_hash ON syllabi (content_hash);

CREATE INDEX ix_syllabi_course_code ON syllabi (course_code);

CREATE INDEX ix_syllabi_institution_id ON syllabi (institution_id);

CREATE INDEX ix_syllabi_transfer_request_id ON syllabi (transfer_request_id);

CREATE TABLE course_evaluations (
    transfer_request_id BIGINT, 
    syllabus_id BIGINT NOT NULL, 
    candidate_course_id BIGINT, 
    status VARCHAR(20) NOT NULL, 
    recommendation VARCHAR(20), 
    coverage NUMERIC(4, 3), 
    confidence VARCHAR(10), 
    level_flag VARCHAR(10), 
    coverage_json JSONB, 
    summary TEXT NOT NULL, 
    input_hash VARCHAR(64), 
    prompt_version VARCHAR(20), 
    model VARCHAR(100), 
    error_message VARCHAR(500), 
    is_latest BOOLEAN NOT NULL, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_course_evaluations PRIMARY KEY (id), 
    CONSTRAINT ck_course_evaluations_confidence_valid CHECK (confidence IS NULL OR confidence IN ('high', 'medium', 'low')), 
    CONSTRAINT ck_course_evaluations_level_flag_valid CHECK (level_flag IS NULL OR level_flag IN ('same', 'lower', 'higher')), 
    CONSTRAINT ck_course_evaluations_recommendation_valid CHECK (recommendation IS NULL OR recommendation IN ('direct', 'elective', 'none', 'insufficient')), 
    CONSTRAINT ck_course_evaluations_status_valid CHECK (status IN ('queued', 'running', 'done', 'failed')), 
    CONSTRAINT ck_course_evaluations_coverage_range CHECK (coverage IS NULL OR coverage BETWEEN 0 AND 1), 
    CONSTRAINT fk_course_evaluations_candidate_course_id_courses FOREIGN KEY(candidate_course_id) REFERENCES courses (id), 
    CONSTRAINT fk_course_evaluations_syllabus_id_syllabi FOREIGN KEY(syllabus_id) REFERENCES syllabi (id), 
    CONSTRAINT fk_course_evaluations_transfer_request_id_transfer_requests FOREIGN KEY(transfer_request_id) REFERENCES transfer_requests (id)
);

CREATE INDEX ix_course_evaluations_candidate_course_id ON course_evaluations (candidate_course_id);

CREATE INDEX ix_course_evaluations_confidence ON course_evaluations (confidence);

CREATE INDEX ix_course_evaluations_input_hash ON course_evaluations (input_hash);

CREATE INDEX ix_course_evaluations_is_latest ON course_evaluations (is_latest);

CREATE INDEX ix_course_evaluations_recommendation ON course_evaluations (recommendation);

CREATE INDEX ix_course_evaluations_status ON course_evaluations (status);

CREATE INDEX ix_course_evaluations_syllabus_latest ON course_evaluations (syllabus_id, is_latest);

CREATE INDEX ix_course_evaluations_transfer_request_id ON course_evaluations (transfer_request_id);

CREATE UNIQUE INDEX uq_course_evaluations_latest_syllabus ON course_evaluations (syllabus_id) WHERE is_latest;

CREATE TABLE syllabus_chunks (
    syllabus_id BIGINT NOT NULL, 
    week_no INTEGER, 
    concept VARCHAR(255) NOT NULL, 
    text TEXT NOT NULL, 
    char_start INTEGER, 
    char_end INTEGER, 
    id BIGSERIAL NOT NULL, 
    CONSTRAINT pk_syllabus_chunks PRIMARY KEY (id), 
    CONSTRAINT ck_syllabus_chunks_span_range CHECK (char_start IS NULL OR char_end IS NULL OR (char_start >= 0 AND char_start <= char_end)), 
    CONSTRAINT fk_syllabus_chunks_syllabus_id_syllabi FOREIGN KEY(syllabus_id) REFERENCES syllabi (id) ON DELETE CASCADE
);

CREATE INDEX ix_syllabus_chunks_syllabus_id ON syllabus_chunks (syllabus_id);

CREATE TABLE transcript_entries (
    transfer_request_id BIGINT NOT NULL, 
    title VARCHAR(255) NOT NULL, 
    code VARCHAR(50), 
    credits NUMERIC(4, 1), 
    grade VARCHAR(10), 
    term VARCHAR(50), 
    syllabus_id BIGINT, 
    link_score NUMERIC(4, 3), 
    link_confirmed BOOLEAN NOT NULL, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_transcript_entries PRIMARY KEY (id), 
    CONSTRAINT ck_transcript_entries_credits_range CHECK (credits IS NULL OR credits >= 0), 
    CONSTRAINT ck_transcript_entries_link_score_range CHECK (link_score IS NULL OR link_score BETWEEN 0 AND 1), 
    CONSTRAINT fk_transcript_entries_syllabus_id_syllabi FOREIGN KEY(syllabus_id) REFERENCES syllabi (id), 
    CONSTRAINT fk_transcript_entries_transfer_request_id_transfer_requests FOREIGN KEY(transfer_request_id) REFERENCES transfer_requests (id)
);

CREATE INDEX ix_transcript_entries_transfer_request_id ON transcript_entries (transfer_request_id);

CREATE TABLE assignments (
    course_evaluation_id BIGINT NOT NULL, 
    reviewer_id BIGINT NOT NULL, 
    assigned_by BIGINT, 
    assigned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    reassigned_from BIGINT, 
    is_active BOOLEAN NOT NULL, 
    id BIGSERIAL NOT NULL, 
    CONSTRAINT pk_assignments PRIMARY KEY (id), 
    CONSTRAINT fk_assignments_assigned_by_users FOREIGN KEY(assigned_by) REFERENCES users (id), 
    CONSTRAINT fk_assignments_course_evaluation_id_course_evaluations FOREIGN KEY(course_evaluation_id) REFERENCES course_evaluations (id), 
    CONSTRAINT fk_assignments_reassigned_from_users FOREIGN KEY(reassigned_from) REFERENCES users (id), 
    CONSTRAINT fk_assignments_reviewer_id_users FOREIGN KEY(reviewer_id) REFERENCES users (id)
);

CREATE INDEX ix_assignments_evaluation_active ON assignments (course_evaluation_id, is_active);

CREATE INDEX ix_assignments_reviewer_active ON assignments (reviewer_id, is_active);

CREATE UNIQUE INDEX uq_assignments_active_evaluation ON assignments (course_evaluation_id) WHERE is_active;

CREATE TABLE decisions (
    course_evaluation_id BIGINT NOT NULL, 
    decided_by BIGINT NOT NULL, 
    action VARCHAR(10) NOT NULL, 
    result VARCHAR(10) NOT NULL, 
    target_course_id BIGINT, 
    reason_codes JSONB NOT NULL, 
    reason_memo TEXT NOT NULL, 
    ai_recommendation_snapshot JSONB NOT NULL, 
    conflict_acknowledged BOOLEAN NOT NULL, 
    appeal_id BIGINT, 
    decided_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    id BIGSERIAL NOT NULL, 
    CONSTRAINT pk_decisions PRIMARY KEY (id), 
    CONSTRAINT ck_decisions_action_valid CHECK (action IN ('approve', 'modify', 'reject')), 
    CONSTRAINT ck_decisions_result_valid CHECK (result IN ('direct', 'elective', 'none')), 
    CONSTRAINT fk_decisions_course_evaluation_id_course_evaluations FOREIGN KEY(course_evaluation_id) REFERENCES course_evaluations (id), 
    CONSTRAINT fk_decisions_decided_by_users FOREIGN KEY(decided_by) REFERENCES users (id), 
    CONSTRAINT fk_decisions_target_course_id_courses FOREIGN KEY(target_course_id) REFERENCES courses (id)
);

CREATE INDEX ix_decisions_course_evaluation_id ON decisions (course_evaluation_id);

CREATE TABLE evaluation_notes (
    syllabus_id BIGINT NOT NULL, 
    course_evaluation_id BIGINT NOT NULL, 
    author_id BIGINT NOT NULL, 
    body TEXT NOT NULL, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_evaluation_notes PRIMARY KEY (id), 
    CONSTRAINT fk_evaluation_notes_author_id_users FOREIGN KEY(author_id) REFERENCES users (id), 
    CONSTRAINT fk_evaluation_notes_course_evaluation_id_course_evaluations FOREIGN KEY(course_evaluation_id) REFERENCES course_evaluations (id), 
    CONSTRAINT fk_evaluation_notes_syllabus_id_syllabi FOREIGN KEY(syllabus_id) REFERENCES syllabi (id)
);

CREATE INDEX ix_evaluation_notes_syllabus_id ON evaluation_notes (syllabus_id);

CREATE TABLE evidence_spans (
    course_evaluation_id BIGINT NOT NULL, 
    side VARCHAR(10) NOT NULL, 
    syllabus_id BIGINT NOT NULL, 
    char_start INTEGER NOT NULL, 
    char_end INTEGER NOT NULL, 
    concept VARCHAR(255) NOT NULL, 
    verified BOOLEAN NOT NULL, 
    id BIGSERIAL NOT NULL, 
    CONSTRAINT pk_evidence_spans PRIMARY KEY (id), 
    CONSTRAINT ck_evidence_spans_side_valid CHECK (side IN ('source', 'target')), 
    CONSTRAINT ck_evidence_spans_span_range CHECK (char_start >= 0 AND char_start < char_end), 
    CONSTRAINT fk_evidence_spans_course_evaluation_id_course_evaluations FOREIGN KEY(course_evaluation_id) REFERENCES course_evaluations (id), 
    CONSTRAINT fk_evidence_spans_syllabus_id_syllabi FOREIGN KEY(syllabus_id) REFERENCES syllabi (id)
);

CREATE INDEX ix_evidence_spans_course_evaluation_id ON evidence_spans (course_evaluation_id);

CREATE TABLE material_requests (
    syllabus_id BIGINT NOT NULL, 
    course_evaluation_id BIGINT NOT NULL, 
    requested_by BIGINT NOT NULL, 
    items JSONB NOT NULL, 
    note TEXT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    fulfilled_at TIMESTAMP WITHOUT TIME ZONE, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_material_requests PRIMARY KEY (id), 
    CONSTRAINT ck_material_requests_status_valid CHECK (status IN ('open', 'fulfilled')), 
    CONSTRAINT fk_material_requests_course_evaluation_id_course_evaluations FOREIGN KEY(course_evaluation_id) REFERENCES course_evaluations (id), 
    CONSTRAINT fk_material_requests_requested_by_users FOREIGN KEY(requested_by) REFERENCES users (id), 
    CONSTRAINT fk_material_requests_syllabus_id_syllabi FOREIGN KEY(syllabus_id) REFERENCES syllabi (id)
);

CREATE INDEX ix_material_requests_status ON material_requests (status);

CREATE INDEX ix_material_requests_syllabus_id ON material_requests (syllabus_id);

CREATE TABLE appeals (
    course_evaluation_id BIGINT NOT NULL, 
    decision_id BIGINT NOT NULL, 
    student_id BIGINT NOT NULL, 
    reason TEXT NOT NULL, 
    status VARCHAR(20) NOT NULL, 
    handled_by BIGINT, 
    handler_note TEXT NOT NULL, 
    handled_at TIMESTAMP WITHOUT TIME ZONE, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_appeals PRIMARY KEY (id), 
    CONSTRAINT ck_appeals_status_valid CHECK (status IN ('submitted', 'accepted', 'dismissed', 'redecided')), 
    CONSTRAINT fk_appeals_course_evaluation_id_course_evaluations FOREIGN KEY(course_evaluation_id) REFERENCES course_evaluations (id), 
    CONSTRAINT fk_appeals_decision_id_decisions FOREIGN KEY(decision_id) REFERENCES decisions (id), 
    CONSTRAINT fk_appeals_handled_by_users FOREIGN KEY(handled_by) REFERENCES users (id), 
    CONSTRAINT fk_appeals_student_id_users FOREIGN KEY(student_id) REFERENCES users (id)
);

CREATE INDEX ix_appeals_course_evaluation_id ON appeals (course_evaluation_id);

CREATE INDEX ix_appeals_status ON appeals (status);

CREATE INDEX ix_appeals_student_id ON appeals (student_id);

CREATE UNIQUE INDEX uq_appeals_open_evaluation ON appeals (course_evaluation_id) WHERE status IN ('submitted', 'accepted');

CREATE TABLE supplement_files (
    syllabus_id BIGINT NOT NULL, 
    file_key VARCHAR(255), 
    material_request_id BIGINT, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_supplement_files PRIMARY KEY (id), 
    CONSTRAINT fk_supplement_files_material_request_id_material_requests FOREIGN KEY(material_request_id) REFERENCES material_requests (id), 
    CONSTRAINT fk_supplement_files_syllabus_id_syllabi FOREIGN KEY(syllabus_id) REFERENCES syllabi (id)
);

CREATE INDEX ix_supplement_files_syllabus_id ON supplement_files (syllabus_id);

CREATE TABLE appeal_files (
    appeal_id BIGINT NOT NULL, 
    file_key VARCHAR(255), 
    original_filename VARCHAR(255) NOT NULL, 
    content_type VARCHAR(100) NOT NULL, 
    size INTEGER NOT NULL, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_appeal_files PRIMARY KEY (id), 
    CONSTRAINT ck_appeal_files_size_range CHECK (size >= 0), 
    CONSTRAINT fk_appeal_files_appeal_id_appeals FOREIGN KEY(appeal_id) REFERENCES appeals (id)
);

CREATE INDEX ix_appeal_files_appeal_id ON appeal_files (appeal_id);

ALTER TABLE courses ADD CONSTRAINT fk_courses_reference_syllabus_id_syllabi FOREIGN KEY(reference_syllabus_id) REFERENCES syllabi (id);

ALTER TABLE decisions ADD CONSTRAINT fk_decisions_appeal_id_appeals FOREIGN KEY(appeal_id) REFERENCES appeals (id);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

CREATE TABLE push_subscriptions (
    user_id BIGINT NOT NULL, 
    endpoint VARCHAR(1000) NOT NULL, 
    p256dh VARCHAR(200) NOT NULL, 
    auth VARCHAR(100) NOT NULL, 
    last_sent_at TIMESTAMP WITHOUT TIME ZONE, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_push_subscriptions PRIMARY KEY (id), 
    CONSTRAINT fk_push_subscriptions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), 
    CONSTRAINT uq_push_subscriptions_endpoint UNIQUE (endpoint)
);

CREATE INDEX ix_push_subscriptions_user_id ON push_subscriptions (user_id);

ALTER TABLE notifications ADD COLUMN pushed_at TIMESTAMP WITHOUT TIME ZONE;

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

-- Running upgrade 0002 -> 0003

ALTER TABLE users ADD COLUMN source_institution_id BIGINT;

ALTER TABLE users ADD CONSTRAINT fk_users_source_institution_id_institutions FOREIGN KEY(source_institution_id) REFERENCES institutions (id);

UPDATE users AS u
        SET source_institution_id = latest.source_institution_id
        FROM (
            SELECT DISTINCT ON (student_id) student_id, source_institution_id
            FROM transfer_requests ORDER BY student_id, created_at DESC, id DESC
        ) AS latest
        WHERE u.id = latest.student_id AND u.role = 'student' AND u.source_institution_id IS NULL;

UPDATE users AS u
        SET department_id = d.id
        FROM (
            SELECT DISTINCT ON (student_id) student_id, major
            FROM transfer_requests ORDER BY student_id, created_at DESC, id DESC
        ) AS latest
        JOIN departments AS d ON d.name = latest.major
        WHERE u.id = latest.student_id AND u.role = 'student' AND u.department_id IS NULL
          AND d.institution_id = u.institution_id;

UPDATE alembic_version SET version_num='0003' WHERE alembic_version.version_num = '0002';

-- Running upgrade 0003 -> 0004

CREATE TABLE institution_sources (
    institution_id BIGINT NOT NULL, 
    source_institution_id BIGINT NOT NULL, 
    id BIGSERIAL NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    CONSTRAINT pk_institution_sources PRIMARY KEY (id), 
    CONSTRAINT fk_institution_sources_institution_id_institutions FOREIGN KEY(institution_id) REFERENCES institutions (id), 
    CONSTRAINT fk_institution_sources_source_institution_id_institutions FOREIGN KEY(source_institution_id) REFERENCES institutions (id), 
    CONSTRAINT uq_institution_sources_institution_id UNIQUE (institution_id, source_institution_id)
);

INSERT INTO institution_sources (institution_id, source_institution_id, created_at)
        SELECT DISTINCT pair.target_id, pair.source_id, now() AT TIME ZONE 'utc'
        FROM (
            SELECT institution_id AS target_id, source_institution_id AS source_id FROM users
            WHERE institution_id IS NOT NULL AND source_institution_id IS NOT NULL
            UNION SELECT target_institution_id, source_institution_id FROM transfer_requests
            UNION SELECT target_institution_id, source_institution_id FROM equivalencies
            UNION SELECT actor.institution_id, src.id FROM audit_logs AS a
                JOIN users AS actor ON actor.id = a.actor_id
                JOIN institutions AS src ON src.id::text = a.target_id
            WHERE a.action = 'institution.create' AND actor.institution_id IS NOT NULL
        ) AS pair
        JOIN institutions AS t ON t.id = pair.target_id AND t.is_target
        JOIN institutions AS s ON s.id = pair.source_id AND NOT s.is_target;

UPDATE alembic_version SET version_num='0004' WHERE alembic_version.version_num = '0003';

COMMIT;

