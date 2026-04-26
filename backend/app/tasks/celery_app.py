"""
Celery application configuration.

Defines the Celery app instance and the periodic beat schedule.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "imobiliarias",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_soft_time_limit=600,  # 10 minutes
    task_time_limit=900,  # 15 minutes
)

# Beat schedule: run all scrapes at 12:00 and 18:00 UTC
celery_app.conf.beat_schedule = {
    "scrape-all-morning": {
        "task": "app.tasks.scrape_tasks.run_all_scrapes",
        "schedule": crontab(
            hour=settings.scrape_schedule_hour_1,
            minute=settings.scrape_schedule_minute_1,
        ),
    },
    "scrape-all-afternoon": {
        "task": "app.tasks.scrape_tasks.run_all_scrapes",
        "schedule": crontab(
            hour=settings.scrape_schedule_hour_2,
            minute=settings.scrape_schedule_minute_2,
        ),
    },
}
