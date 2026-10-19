"""환경변수 설정. 애플리케이션에서 환경변수는 이 모듈의 Settings로만 읽는다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "postgresql+psycopg://creditbridge:change-me@localhost:5432/creditbridge"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str | None = None
    s3_bucket: str = "creditbridge-documents"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    # 운영 S3는 "AES256"(SSE-S3) 또는 "aws:kms". KMS가 없는 로컬 저장소(SeaweedFS)는 비워둔다.
    s3_server_side_encryption: str = ""

    anthropic_api_key: str = ""
    claude_model: str = ""
    # 정책 거절 시 서버가 다른 모델로 다시 시도 (Claude API 전용). Bedrock·Vertex·프록시를 쓰면 false
    claude_server_fallback: bool = True

    session_secret: str = "change-me"
    celery_task_always_eager: bool = False

    max_upload_mb: int = 20
    max_syllabi_per_request: int = 30
    # 교수 배정 후 판정까지 예상 소요일 (학생 포털의 예상 완료일 계산용)
    review_sla_days: int = 5
    # 개인정보 삭제 요청 처리 기한 (FR-13)
    privacy_deletion_days: int = 30
    # 기한 알림 (매일 한 번, Celery beat): 보내는 시각(UTC, 0~23)과 기준 일수
    reminder_hour_utc: int = 13
    reminder_privacy_days: int = 3  # 삭제 요청 처리 기한이 이만큼 남으면
    reminder_material_days: int = 3  # 보완 자료 요청에 이만큼 답이 없으면
    reminder_unassigned_days: int = 2  # 교수 배정 없이 이만큼 지나면

    # 알림 메일 (비우면 화면 알림만). 메일 본문에는 개인정보를 넣지 않는다
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@creditbridge.local"
    smtp_starttls: bool = True
    # 메일 속 링크의 기준 주소
    app_base_url: str = "http://localhost:8000"
    # 브라우저 웹 푸시 (FR-20, 비우면 끔). 키는 uv run python -m scripts.generate_vapid_keys로 만든다.
    # 푸시 내용에도 개인정보를 넣지 않는다 (알림 메시지와 같은 글)
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = "mailto:admin@creditbridge.local"

    # 공개 데모(예시용 배포, deploy/demo): Claude 대신 예시 AI, S3 대신 이 폴더에 파일 저장,
    # 비밀번호 변경·초기화와 계정 비활성화를 막는다. 운영에서는 반드시 false
    demo_mode: bool = False
    demo_storage_dir: str = "/tmp/creditbridge-files"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
