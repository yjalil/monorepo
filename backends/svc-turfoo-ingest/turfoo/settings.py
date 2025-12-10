"""Application settings for Turfoo."""

import logging

from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Turfoo application settings."""

    # Turfoo RSS feeds
    turfoo_program_feed_url: HttpUrl
    turfoo_news_feed_url: HttpUrl
    turfoo_results_feed_url: HttpUrl

    # Logging
    log_level: int = logging.INFO
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_date_format: str = "%Y-%m-%d %H:%M:%S"

    # Redis cache
    cache_redis_host: str
    cache_redis_port: int = 6379
    cache_redis_username: str = "default"
    cache_redis_password: str

    # S3/MinIO
    s3_endpoint_url: HttpUrl
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_turfoo_bucket_name: str

    # Celery
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        return f"redis://{self.cache_redis_username}:{self.cache_redis_password}@{self.cache_redis_host}:{self.cache_redis_port}"

    @property
    def s3_endpoint(self) -> str:
        """Convert HttpUrl to string for boto3."""
        return str(self.s3_endpoint_url)

    def model_post_init(self, __context) -> None:
        """Set Celery URLs from Redis if not explicitly set."""
        if self.celery_broker_url is None:
            self.celery_broker_url = f"{self.redis_url}/1"
        if self.celery_result_backend is None:
            self.celery_result_backend = f"{self.redis_url}/1"


settings = Settings()

