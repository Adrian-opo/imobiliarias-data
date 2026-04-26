"""Achou Imoveis Ji-Parana scraper"""
import logging
import re
from typing import Optional
from uuid import UUID

import httpx
from parsel import Selector

from app.scrapers.base import BaseScraper, DEFAULT_HEADERS
from app.scrapers.registry import register_scraper
from app.config import settings
from app.services.normalize import (
    normalize_price,
    normalize_property_type,
    normalize_business_type,
    compute_content_hash,
)

logger = logging.getLogger(__name__)


@register_scraper("achou")
class AchouScraper(BaseScraper):
    """Scraper for Achou Imoveis Ji-Parana (proprietary platform)."""

    source_name = "Achou Imoveis Ji-Parana"
    platform = "Proprio"

    def __init__(self, source_id: UUID, base_url: str = "https://www.achouimoveisjiparana.com.br"):
        super().__init__(source_id, base_url)
        self._client_kwargs = {
            "timeout": settings.request_timeout,
            "follow_redirects": True,
            "headers": dict(DEFAULT_HEADERS),
        }

    async def scrape_listings(self, page_offset: int = 0) -> list[dict]:
        """Scrape property listings from Achou."""
        results = []

        # Different filter URLs based on business type
        filter_urls = [
            f"{self.base_url}/imovel/?finalidade=venda",
            f"{self.base_url}/imovel/?finalidade=aluguel",
        ]

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            for filter_url in filter_urls:
                page = 1 + max(0, page_offset)
                url = f"{filter_url}&pagina={page}" if page > 1 else filter_url
                logger.info(f"Achou: fetching {url}")

                try:
                    await self.polite_delay()
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.warning(f"Achou listing error {url}: {e}")
                    continue

                sel = Selector(resp.text)

                # Find property links
                cards = sel.css("a[href*='/imovel/'], a[href*='imovel.php']")
                for card in cards:
                    href = card.attrib.get("href", "")
                    if not href:
                        continue

                    # Extract property ID
                    prop_id = None
                    if "id=" in href:
                        match = re.search(r"id=(\d+)", href)
                        if match:
                            prop_id = match.group(1)
                    elif href.rstrip("/").split("/")[-1].isdigit():
                        prop_id = href.rstrip("/").split("/")[-1]

                    if prop_id:
                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                        results.append({
                            "source_property_id": prop_id,
                            "url": full_url,
                        })

        # Deduplicate
        seen = set()
        unique = []
        for item in results:
            if item["source_property_id"] not in seen:
                seen.add(item["source_property_id"])
                unique.append(item)

        logger.info(f"Achou: unique listings={len(unique)}")
        return unique[: settings.scrape_max_detail_pages_per_cycle]

    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """Scrape property detail page."""
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                await self.polite_delay()
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(f"Achou detail error {url}: {e}")
                return None

        sel = Selector(resp.text)

        # Extract data from page
        title = sel.css("h1::text, .titulo::text, .property-title::text").get() or ""
        price_text = sel.css(".preco::text, .valor::text, [class*='price']::text, .property-price::text").get() or ""
        price = normalize_price(price_text)

        # Extract images
        images = []
        img_elements = sel.css("img::attr(src), img::attr(data-src)").getall()
        for src in img_elements:
            if src and len(src) > 10:
                if src.startswith("http"):
                    images.append(src)
                else:
                    images.append(f"{self.base_url}{src}")

        # Extract details
        details = {
            "title": title.strip() if title else None,
            "price": price,
            "currency": "BRL",
            "property_type": normalize_property_type(title),
            "business_type": "sale" if "venda" in url.lower() else "rent",
            "description": sel.css(".descricao::text, .property-description::text").get() or "",
            "images": images,
            "source_url": url,
        }

        return details

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Normalize raw data to standard format."""
        try:
            return {
                "title": raw_data.get("title"),
                "price": raw_data.get("price"),
                "currency": raw_data.get("currency", "BRL"),
                "business_type": normalize_business_type(raw_data.get("business_type")),
                "property_type": normalize_property_type(raw_data.get("property_type") or raw_data.get("title")),
                "description": raw_data.get("description"),
                "images": raw_data.get("images", []),
                "source_url": raw_data.get("source_url"),
            }
        except Exception as e:
            logger.error(f"Normalization error: {e}")
            return None
