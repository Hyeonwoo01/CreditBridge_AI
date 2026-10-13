"""환경변수 설정. 애플리케이션에서 환경변수는 이 모듈의 Settings로만 읽는다."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    database_url: str = "mysql+pymysql://creditbridge:change-me@localhost:3306/creditbridge?charset=utf8mb4"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str | None = None
    s3_bucket: str = "creditbridge-documents"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    # 운영 S3는 "AES256"(SSE-S3) 또는 "aws:kms". KMS가 없는 로컬 MinIO는 비워둔다.
    s3_server_side_encryption: str = ""

    anthropic_api_key: str = ""
    claude_model: str = ""

    session_secret: str = "change-me"
    celery_task_always_eager: bool = False

    max_upload_mb: int = 20
    max_syllabi_per_request: int = 30
    # 교수 배정 후 판정까지 예상 소요일 (학생 포털의 예상 완료일 계산용)
    review_sla_days: int = 5

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
