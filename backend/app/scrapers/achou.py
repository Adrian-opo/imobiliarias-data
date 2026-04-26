"""Achou Imoveis Ji-Parana scraper"""
import json
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
        # Note: The correct URL uses query parameters, not path segments
        filter_urls = [
            f"{self.base_url}/imovel/?finalidade=venda",
            f"{self.base_url}/imovel/?finalidade=locacao",
        ]

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            for filter_url in filter_urls:
                page = 1 + max(0, page_offset)
                url = f"{filter_url}&pag={page}" if page > 1 else filter_url
                logger.info(f"Achou: fetching {url}")

                try:
                    await self.polite_delay()
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.warning(f"Achou listing error {url}: {e}")
                    continue

                sel = Selector(resp.text)

                # Find property cards with data-link attribute
                cards = sel.css("div.imovelcard[data-link]")
                for card in cards:
                    href = card.attrib.get("data-link", "")
                    if not href:
                        continue

                    # Extract property ID from URL like /imovel/4005488/lote-venda-jiparana-ro-trianon
                    # Pattern: /imovel/{id}/{slug}
                    match = re.search(r'/imovel/(\d+)/', href)
                    if match:
                        prop_id = match.group(1)
                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                        results.append({
                            "source_property_id": prop_id,
                            "url": full_url,
                        })

                # Also check for direct links inside property cards
                card_links = sel.css("div.imovelcard a[href*='/imovel/']")
                for link in card_links:
                    href = link.attrib.get("href", "")
                    if not href or href.startswith("/imovel/?"):
                        continue

                    # Extract property ID from URL
                    match = re.search(r'/imovel/(\d+)/', href)
                    if match:
                        prop_id = match.group(1)
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

        # --- Extract from JSON-LD (most reliable) ---
        json_ld_data = None
        json_ld_scripts = sel.css('script[type="application/ld+json"]::text').getall()
        for script in json_ld_scripts:
            # Look for BuyAction in the script
            if 'BuyAction' in script:
                # Find the BuyAction object by finding the opening brace and matching closing brace
                buy_pos = script.find('"BuyAction"')
                if buy_pos > 0:
                    open_pos = script.rfind('{', 0, buy_pos)
                    # Find the matching closing brace
                    brace_count = 0
                    in_string = False
                    escape = False
                    close_pos = -1
                    for j in range(open_pos, len(script)):
                        char = script[j]
                        if escape:
                            escape = False
                            continue
                        if char == '\\':
                            escape = True
                            continue
                        if char == '"':
                            in_string = not in_string
                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    close_pos = j
                                    break
                    
                    if close_pos > 0:
                        object_str = script[open_pos:close_pos + 1]
                        try:
                            json_ld_data = json.loads(object_str)
                            break
                        except (json.JSONDecodeError, TypeError):
                            pass

        # --- Title ---
        title = None
        if json_ld_data and json_ld_data.get("object", {}).get("name"):
            title = json_ld_data["object"]["name"]
        else:
            title = sel.css("h1::text, .titulo::text, .property-title::text").get() or ""
            # Clean up title if it's too long
            if title and len(title) > 200:
                title = title[:200]

        # --- Price ---
        price = None
        if json_ld_data and json_ld_data.get("price"):
            price = normalize_price(json_ld_data["price"])
        else:
            # Fallback to meta description
            meta_desc = sel.css('meta[property="og:description"]::attr(content)').get() or ""
            m = re.search(r'R\$\s*[\d\s\.]+,\d{2}', meta_desc)
            if m:
                price = normalize_price(m.group(0))

        # --- Description ---
        description = None
        if json_ld_data and json_ld_data.get("object", {}).get("description"):
            description = json_ld_data["object"]["description"]
        else:
            # Fallback to meta description or page content
            description = sel.css('meta[property="og:description"]::attr(content)').get() or ""
            if not description:
                # Try to find description in page
                desc_el = sel.css('.descricao::text, .property-description::text, .imovelcard__info__tab__content__descricao h3::text').get()
                if desc_el:
                    description = desc_el.strip()

        # --- Location (neighborhood, city) ---
        neighborhood = None
        city = "Ji-Paraná"
        if json_ld_data and json_ld_data.get("object", {}).get("address"):
            address = json_ld_data["object"]["address"]
            city = address.get("addressLocality", "Ji-Paraná")
        else:
            # Extract from meta or title
            meta_title = sel.css('meta[property="og:title"]::attr(content)').get() or ""
            if meta_title:
                m = re.search(r'bairro\s+([^-]+)', meta_title)
                if m:
                    neighborhood = m.group(1).strip()

        # --- Property type ---
        property_type = None
        if json_ld_data and json_ld_data.get("object", {}).get("name"):
            # Extract from name like "Lote para Venda, em Ji-Paraná, bairro Trianon"
            name = json_ld_data["object"]["name"]
            m = re.match(r'^([^\s,]+)', name)
            if m:
                property_type = m.group(1)
        if not property_type:
            property_type = normalize_property_type(title)

        # --- Business type ---
        business_type = "sale" if "venda" in url.lower() else "rent"

        # --- Images ---
        images = []
        img_elements = sel.css("img::attr(src), img::attr(data-src)").getall()
        seen_urls = set()
        for src in img_elements:
            if src and len(src) > 10 and src not in seen_urls:
                # Filter out logo and thumbnails
                if "logo" in src.lower() or "thumb" in src.lower():
                    continue
                seen_urls.add(src)
                if src.startswith("http"):
                    images.append(src)
                else:
                    images.append(f"{self.base_url}{src}")

        # --- Features/areas ---
        features = {}
        # Try to extract from meta description
        meta_desc = sel.css('meta[property="og:description"]::attr(content)').get() or ""
        if "m²" in meta_desc or "m&sup2;" in meta_desc:
            # Extract area from meta description
            m = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', meta_desc)
            if m:
                features["área"] = m.group(1)

        # Extract from page content
        page_text = " ".join(sel.css("body *::text").getall())
        # Look for area patterns
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]', page_text)
        if m and "área" not in features:
            features["área"] = m.group(1)

        # --- Extract structured fields ---
        bedrooms = None
        bathrooms = None
        garage_spaces = None

        # Search in page text
        m = re.search(r'(\d+)\s*(?:quarto|quartos|dorm)', page_text, re.IGNORECASE)
        if m:
            bedrooms = int(m.group(1))
        m = re.search(r'(\d+)\s*(?:banheiro|banheiros)', page_text, re.IGNORECASE)
        if m:
            bathrooms = int(m.group(1))
        m = re.search(r'(\d+)\s*(?:vaga|vagas|garagem)', page_text, re.IGNORECASE)
        if m:
            garage_spaces = int(m.group(1))

        details = {
            "title": title.strip() if title else None,
            "price": price,
            "currency": "BRL",
            "property_type": property_type,
            "business_type": business_type,
            "description": description.strip() if description else None,
            "neighborhood": neighborhood,
            "city": city,
            "features": features,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "garage_spaces": garage_spaces,
            "total_area": features.get("área"),
            "images": images,
            "source_url": url,
        }

        return details

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Normalize raw data to standard format."""
        try:
            from app.services.normalize import normalize_area, extract_bedrooms, compute_content_hash
            
            title = raw_data.get("title")
            description = raw_data.get("description")
            neighborhood = raw_data.get("neighborhood")
            
            business_type = normalize_business_type(raw_data.get("business_type")) or "sale"
            property_type = normalize_property_type(raw_data.get("property_type") or title or "")
            
            price = raw_data.get("price")
            if price is not None and isinstance(price, str):
                price = normalize_price(price)
            
            total_area = normalize_area(raw_data.get("total_area"))
            
            bedrooms = raw_data.get("bedrooms")
            if bedrooms is None:
                bedrooms = extract_bedrooms(title) or extract_bedrooms(description)
            
            bathrooms = raw_data.get("bathrooms")
            garage_spaces = raw_data.get("garage_spaces")
            suites = raw_data.get("suites")
            
            images = raw_data.get("images", [])
            
            content_hash = compute_content_hash(
                price=price,
                title=title,
                description=description,
                neighborhood=neighborhood,
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                garage_spaces=garage_spaces,
                total_area=total_area,
            )
            
            return {
                "source_property_id": raw_data.get("source_property_id", raw_data.get("source_url", "").split("/")[-1]),
                "source_url": raw_data.get("source_url"),
                "business_type": business_type,
                "property_type": property_type,
                "title": title,
                "description": description,
                "price": price,
                "condominium_fee": None,
                "iptu": None,
                "city": raw_data.get("city", "Ji-Paraná"),
                "state": "RO",
                "neighborhood": neighborhood,
                "address_text": None,
                "bedrooms": bedrooms,
                "suites": suites,
                "bathrooms": bathrooms,
                "garage_spaces": garage_spaces,
                "total_area": total_area,
                "built_area": None,
                "land_area": None,
                "published_at_source": None,
                "images": images,
                "content_hash": content_hash,
            }
        except Exception as e:
            logger.error(f"Normalization error: {e}")
            return None
