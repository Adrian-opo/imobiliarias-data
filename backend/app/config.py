from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    app_name: str = "Imobiliarias Data"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql://imobiliarias:imobiliarias_secret@postgres:5432/imobiliarias"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # CORS
    cors_origins: str = '["*"]'

    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.cors_origins)

    # Celery Beat schedule times (UTC)
    scrape_schedule_hour_1: int = 12
    scrape_schedule_minute_1: int = 0
    scrape_schedule_hour_2: int = 18
    scrape_schedule_minute_2: int = 0

    # Scraping
    request_timeout: int = 30
    max_retries: int = 3
    scrape_interval_days: int = 7  # how many days without seeing = removed
    scrape_page_limit: int = 3
    scrape_delay_min_seconds: float = 2.5
    scrape_delay_max_seconds: float = 5.0
    scrape_playwright_concurrency: int = 1
    scrape_max_detail_pages_per_cycle: int = 10
    scrape_max_listing_routes_per_cycle: int = 4

    # Playwright
    playwright_headless: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
