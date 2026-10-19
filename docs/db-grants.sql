-- 운영 DB 계정 권한 (MariaDB 11.8). 테이블 단위로 부여한다.
-- decisions, audit_logs는 추가 전용이므로 앱 계정에 UPDATE·DELETE를 주지 않는다.
-- 마이그레이션(Alembic)은 DDL 권한이 있는 별도 계정으로 실행한다.
CREATE USER IF NOT EXISTS 'creditbridge_app'@'%' IDENTIFIED BY 'change-me';

GRANT SELECT, INSERT, UPDATE, DELETE ON creditbridge.institutions       TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON creditbridge.users              TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.departments        TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON creditbridge.courses            TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON creditbridge.syllabi            TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON creditbridge.syllabus_chunks    TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON creditbridge.transfer_requests  TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE ON creditbridge.transcript_entries TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.course_evaluations TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT                 ON creditbridge.evidence_spans     TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.assignments        TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT                 ON creditbridge.decisions          TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT                 ON creditbridge.audit_logs         TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.notifications      TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.material_requests  TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.supplement_files   TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.appeals            TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.appeal_files       TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT, UPDATE         ON creditbridge.privacy_requests   TO 'creditbridge_app'@'%';
GRANT SELECT, INSERT                 ON creditbridge.equivalencies      TO 'creditbridge_app'@'%';
-- 내부 메모는 고치지 않고 새로 남기며, 개인정보 삭제 승인 때만 지운다
GRANT SELECT, INSERT, DELETE         ON creditbridge.evaluation_notes   TO 'creditbridge_app'@'%';
GRANT SELECT                         ON creditbridge.alembic_version    TO 'creditbridge_app'@'%';
