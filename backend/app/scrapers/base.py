"""
Abstract base scraper for real estate portals.

All source-specific scrapers should inherit from BaseScraper and implement:
- scrape_listings(): fetch list of property URLs/IDs
- scrape_detail(source_property_id, url): fetch detail page and return raw dict
- normalize(raw_data): convert raw dict to normalized property dict

Playwright fallback helpers are provided for portals that require JS rendering.
"""
from abc import ABC, abstractmethod
import asyncio
import random
from typing import Optional
from uuid import UUID

from app.config import settings


# Default HTTP headers for all scrapers
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


class BaseScraper(ABC):
    """Abstract base class for all property portal scrapers."""

    source_id: UUID
    source_name: str
    base_url: str
    platform: str  # Imobzi, Kenlo, Imonov, Apre.me, Union

    def __init__(self, source_id: UUID, base_url: str):
        self.source_id = source_id
        self.base_url = base_url.rstrip("/")

    def build_client_kwargs(self) -> dict:
        return {
            "timeout": settings.request_timeout,
            "follow_redirects": True,
            "headers": dict(DEFAULT_HEADERS),
        }

    async def polite_delay(self, *, minimum: Optional[float] = None, maximum: Optional[float] = None) -> None:
        low = settings.scrape_delay_min_seconds if minimum is None else minimum
        high = settings.scrape_delay_max_seconds if maximum is None else maximum
        if high < low:
            high = low
        await asyncio.sleep(random.uniform(low, high))

    @abstractmethod
    async def scrape_listings(self, page_offset: int = 0) -> list[dict]:
        """
        Fetch list of properties from the source portal.

        Args:
            page_offset: starting page offset for pagination rotation.
                         Each cycle should pass a different offset so that
                         different pages/routes are visited over time.

        Returns a list of dicts with at minimum:
            {"source_property_id": str, "url": str}
        """
        ...

    @abstractmethod
    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """
        Fetch detail page for a single property.

        Returns raw dict of scraped data, or None on failure.
        """
        ...

    @abstractmethod
    def normalize(self, raw_data: dict) -> Optional[dict]:
        """
        Convert raw scraped data into a normalized property dict.

        Must return a dict with keys matching the upsert_property parameters.
        Return None if data is invalid/irrelevant.
        """
        ...

    # ------------------------------------------------------------------ #
    #  Playwright fallback helpers
    # ------------------------------------------------------------------ #

    async def _fetch_with_playwright(self, url: str, timeout: int = 30000) -> Optional[str]:
        """
        Fallback: fetch a page using Playwright (Chromium headless).

        Returns the full HTML as a string, or None on failure.
        Use this when httpx fails due to JS-rendered content.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=DEFAULT_HEADERS["User-Agent"],
                    locale="pt-BR",
                )
                page = await context.new_page()
                await self.polite_delay(minimum=1.0, maximum=2.0)
                await page.goto(url, wait_until="networkidle", timeout=timeout)
                html = await page.content()
                await browser.close()
                return html
        except Exception:
            return None

    async def _batch_fetch_with_playwright(
        self, urls: list[str], max_concurrency: int = 3, timeout: int = 30000
    ) -> dict[str, Optional[str]]:
        """
        Fetch multiple URLs in parallel using Playwright.

        Returns dict mapping url -> html (or None on failure).
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {u: None for u in urls}

        results: dict[str, Optional[str]] = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=DEFAULT_HEADERS["User-Agent"],
                locale="pt-BR",
            )

            effective_concurrency = min(max_concurrency, settings.scrape_playwright_concurrency)
            for i in range(0, len(urls), effective_concurrency):
                batch = urls[i : i + effective_concurrency]
                for url in batch:
                    try:
                        page = await context.new_page()
                        await self.polite_delay(minimum=1.0, maximum=2.0)
                        await page.goto(url, wait_until="networkidle", timeout=timeout)
                        results[url] = await page.content()
                        await page.close()
                    except Exception:
                        results[url] = None

            await browser.close()

        return results

    # ------------------------------------------------------------------ #
    #  HTTP helpers
    # ------------------------------------------------------------------ #

    async def validate(self) -> bool:
        """
        Quick health check: try to reach the source base URL.
        Falls back to Playwright if httpx fails.
        """
        import httpx
        try:
            async with httpx.AsyncClient(
                timeout=10, headers=DEFAULT_HEADERS, follow_redirects=True
            ) as client:
                resp = await client.get(self.base_url)
                return resp.status_code < 500
        except Exception:
            html = await self._fetch_with_playwright(self.base_url, timeout=15000)
            return html is not None
