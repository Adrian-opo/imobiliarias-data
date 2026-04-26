from app.tasks.celery_app import celery_app
from app.tasks.scrape_tasks import run_scrape, run_all_scrapes

__all__ = ["celery_app", "run_scrape", "run_all_scrapes"]
