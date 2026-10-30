-- 운영 DB 계정 권한 (PostgreSQL 17). 테이블 단위로 부여한다.
-- decisions, audit_logs는 추가 전용이므로 앱 계정에 UPDATE·DELETE를 주지 않는다.
-- 마이그레이션(Alembic)은 테이블 소유자(DDL 권한이 있는 별도 계정)로 실행하고, 이 파일은 그 뒤에 실행한다.
CREATE ROLE creditbridge_app LOGIN PASSWORD 'change-me';
GRANT CONNECT ON DATABASE creditbridge TO creditbridge_app;
GRANT USAGE ON SCHEMA public TO creditbridge_app;

GRANT SELECT, INSERT, UPDATE, DELETE ON institutions       TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON users              TO creditbridge_app;
-- 대학별 출신 대학 목록: 잘못 등록한 대학을 목록에서 지운다
GRANT SELECT, INSERT, DELETE         ON institution_sources TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON student_transcripts TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON departments        TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON courses            TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON syllabi            TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON syllabus_chunks    TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON transfer_requests  TO creditbridge_app;  -- DELETE: 서류 없는 빈 초안만 (student.delete_empty_request)
GRANT SELECT, INSERT, UPDATE, DELETE ON transcript_entries TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON course_evaluations TO creditbridge_app;
GRANT SELECT, INSERT                 ON evidence_spans     TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON evidence_feedback  TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON assignments        TO creditbridge_app;
GRANT SELECT, INSERT                 ON decisions          TO creditbridge_app;
GRANT SELECT, INSERT                 ON audit_logs         TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON notifications      TO creditbridge_app;
-- 푸시 구독은 기기가 끄거나 만료되면 지운다
GRANT SELECT, INSERT, UPDATE, DELETE ON push_subscriptions TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON material_requests  TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON supplement_files   TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON appeals            TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON appeal_files       TO creditbridge_app;
GRANT SELECT, INSERT, UPDATE         ON privacy_requests   TO creditbridge_app;
GRANT SELECT, INSERT                 ON equivalencies      TO creditbridge_app;
-- 내부 메모는 고치지 않고 새로 남기며, 개인정보 삭제 승인 때만 지운다
GRANT SELECT, INSERT, DELETE         ON evaluation_notes   TO creditbridge_app;
GRANT SELECT                         ON alembic_version    TO creditbridge_app;
-- INSERT로 id를 받으려면 id 시퀀스(BIGSERIAL)의 다음 값을 읽을 수 있어야 한다
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO creditbridge_app;
