"""
Scraper registry: maps source names/platforms to scraper classes.

Scrapers register themselves via the @register_scraper decorator.
"""
from typing import Optional

from app.scrapers.base import BaseScraper

_registry: dict[str, type[BaseScraper]] = {}


def register_scraper(name: str):
    """Decorator to register a scraper class."""
    def decorator(cls):
        _registry[name.lower()] = cls
        return cls
    return decorator


def get_scraper(name: str) -> Optional[type[BaseScraper]]:
    """Get scraper class by name."""
    return _registry.get(name.lower())


def get_all_scrapers() -> dict[str, type[BaseScraper]]:
    """Get all registered scraper classes."""
    return dict(_registry)
