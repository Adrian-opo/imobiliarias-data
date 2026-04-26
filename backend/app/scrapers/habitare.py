"""
Scraper for Habitare Ji-Paraná (habitarejipa.com.br).

Platform: Imonov (SSR-based portal).
This scraper uses httpx + parsel for SSR pages.

Listing URL pattern:
  - Sale: /filtro/venda/todos/todos/todos/0-1500000/todos/todos/{page}/1
  - Rent: /filtro/locacao/todos/todos/todos/0-20000/todos/todos/{page}/1

Property URL pattern:
  - /imovel/{business_type}/{property_type}/{city}/{neighborhood}/{slug}/{id}
  - Example: /imovel/venda/casa/ji-parana-ro/residencial-acai/imovel-3-quartos-a-venda---acai/187274

Property ID extraction: Last segment of URL path (e.g., "187274")
"""
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
    clean_text,
    normalize_price,
    normalize_area,
    normalize_business_type,
    normalize_neighborhood,
    normalize_property_type,
    extract_bedrooms,
    compute_content_hash,
)

logger = logging.getLogger(__name__)


@register_scraper("habitare")
class HabitareScraper(BaseScraper):
    """Scraper for Habitare Ji-Paraná (Imonov platform)."""

    source_name = "Habitare Ji-Paraná"
    platform = "Imonov"

    def __init__(self, source_id: UUID, base_url: str = "https://www.habitarejipa.com.br"):
        super().__init__(source_id, base_url)
        self._client_kwargs = self.build_client_kwargs()

    async def scrape_listings(self, page_offset: int = 0) -> list[dict]:
        """
        Scrape list of properties from Habitare.

        Uses page_offset to rotate which pages are visited each cycle.
        """
        results = []

        # URLs for sale and rent
        search_urls = [
            f"{self.base_url}/filtro/venda/todos/todas/todos/0-1500000/todos/todos",
            f"{self.base_url}/filtro/locacao/todos/todas/todos/0-20000/todos/todos",
        ]

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            for base_list_url in search_urls:
                start_page = 1 + max(0, page_offset)
                end_page = start_page + settings.scrape_page_limit - 1

                for page in range(start_page, end_page + 1):
                    url = f"{base_list_url}/{page}/1"
                    logger.info("Habitare: fetching page %d: %s", page, url)

                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                    except httpx.HTTPError as e:
                        logger.error("Habitare: failed to fetch page %d: %s", page, e)
                        break

                    sel = Selector(resp.text)

                    # Property cards are in div-block-62 > div-block-63 > div-block-10.detalhes
                    cards = sel.css('div.div-block-10.detalhes')
                    
                    # If no cards found, try Playwright (JS-rendered content)
                    if not cards:
                        logger.info("Habitare: no cards found with httpx, trying Playwright...")
                        html = await self._fetch_with_playwright(url)
                        if html:
                            sel = Selector(html)
                            cards = sel.css('div.div-block-10.detalhes')
                            logger.info("Habitare: Playwright found %d cards", len(cards))
                    
                    page_items = []

                    for card in cards:
                        # Get the property link
                        link = card.css('a[href*="/imovel/"]')
                        if not link:
                            continue

                        href = link[0].attrib.get('href', '')
                        if not href or '/imovel/' not in href:
                            continue

                        # Extract property ID from URL (last segment)
                        m = re.search(r'/imovel/.+/(\d+)$', href)
                        if not m:
                            continue

                        prop_id = m.group(1)
                        full_url = href if href.startswith('http') else f"{self.base_url}{href}"

                        page_items.append({
                            'source_property_id': prop_id,
                            'url': full_url,
                        })

                    results.extend(page_items)
                    logger.info("Habitare: found %d items on page %d (total %d)",
                                len(page_items), page, len(results))

                    # Check if there are items on this page
                    if not page_items:
                        break

                    # Conservative delay between pages
                    await self.polite_delay()

        # Deduplicate
        seen = set()
        unique = []
        for item in results:
            if item['source_property_id'] not in seen:
                seen.add(item['source_property_id'])
                unique.append(item)

        n_limit = settings.scrape_page_limit * 30  # Conservative limit
        limited = unique[:n_limit]

        logger.info(
            "Habitare: visited pages offset=%d, unique=%d, processing=%d",
            page_offset,
            len(unique),
            len(limited),
        )
        return limited

    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """Scrape a single property detail page."""
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                await self.polite_delay()
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("Habitare: detail error %s: %s", url, e)
                return None

        sel = Selector(resp.text)
        return self._parse_detail(sel, source_property_id, url)

    def _parse_detail(self, sel: Selector, source_property_id: str, url: str) -> dict:
        """Parse the detail page HTML into a raw data dict."""
        raw = {
            'source_property_id': source_property_id,
            'url': url,
        }

        # Get all text from the page
        all_text = sel.css('::text').getall()
        text_clean = [clean_text(t) for t in all_text if clean_text(t)]

        # Extract title (first H1 or text-block-3)
        title = sel.css('h1::text, div.text-block-3::text').get()
        if title:
            title = clean_text(title)
        raw['title'] = title

        # Extract description
        # Look for description in text blocks
        description = None
        for text in text_clean:
            if len(text) > 50 and 'R$' not in text and 'm²' not in text:
                description = text
                break
        raw['description'] = description

        # Extract price - look for R$ pattern
        price_text = None
        for text in text_clean:
            if 'R$' in text:
                # Extract just the price part (R$ XXX.XXX,XX)
                import re
                m = re.search(r'R\$[\s\d\.]+,\d{2}', text)
                if m:
                    price_text = m.group(0)
                    break
        raw['price_text'] = price_text

        # Extract area - look for m² pattern with number
        area_text = None
        for text in text_clean:
            if 'm²' in text or 'm2' in text:
                # Extract area value
                import re
                m = re.search(r'[\d\.,]+\s*m²', text, re.IGNORECASE)
                if m:
                    area_text = m.group(0)
                    break
        raw['area_text'] = area_text

        # Extract bedrooms, bathrooms, garage from features
        # Features are in div-block-12 with div-block-14 children
        features_div = sel.css('div.div-block-12')
        if features_div:
            features = features_div[0].css('div.div-block-14')
            for feat in features:
                text = feat.css('::text').get()
                img = feat.css('img::attr(src)').get()
                if img:
                    if 'car' in img:
                        raw['garage_spaces'] = int(text) if text and text.isdigit() else None
                    elif 'bed' in img:
                        raw['bedrooms'] = int(text) if text and text.isdigit() else None
                    elif 'bath' in img:
                        raw['bathrooms'] = int(text) if text and text.isdigit() else None

        # Extract location from text
        location = None
        for text in text_clean:
            if '/' in text and len(text) > 5 and 'JI PARANA' in text.upper():
                location = text
                break
        raw['location'] = location

        # Extract reference
        reference = None
        for text in text_clean:
            if 'Ref.' in text or 'Ref:' in text:
                reference = text
                break
        raw['reference'] = reference

        # Extract property type from title or first text block
        property_type = None
        if title:
            property_type = title.split()[0] if title.split() else None
        raw['property_type'] = property_type

        # Extract images
        images = []
        for img in sel.css('img::attr(src)').getall():
            if 'imonovdados' in img or self.base_url in img:
                images.append(img)
        raw['images'] = images

        # Extract business type from URL
        if '/venda/' in url:
            raw['business_type'] = 'venda'
        elif '/locacao/' in url:
            raw['business_type'] = 'locacao'
        else:
            raw['business_type'] = None

        return raw

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Convert raw scraped data into normalized property dict."""
        try:
            title = raw_data.get('title')
            description = raw_data.get('description')
            raw_neighborhood = raw_data.get('location')

            business_type = normalize_business_type(raw_data.get('business_type', ''))
            if not business_type:
                business_type = 'sale'

            property_type = normalize_property_type(raw_data.get('property_type') or title or '')

            price = raw_data.get('price_text')
            if price:
                price = normalize_price(price)
            condominium_fee = None

            area_text = raw_data.get('area_text')
            total_area = None
            if area_text:
                total_area = normalize_area(area_text)

            bedrooms = raw_data.get('bedrooms')
            bathrooms = raw_data.get('bathrooms')
            garage_spaces = raw_data.get('garage_spaces')

            # Clean neighborhood
            neighborhood = normalize_neighborhood(raw_neighborhood)
            if not neighborhood and title:
                # Try to extract from title
                m = re.search(r'em\s+([^-]+)', title, re.IGNORECASE)
                if m:
                    neighborhood = normalize_neighborhood(m.group(1).strip())

            if bedrooms is None or bedrooms == 0:
                bedrooms = extract_bedrooms(title) or extract_bedrooms(description)

            images = raw_data.get('images', [])
            city = 'Ji-Paraná'

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
                'source_property_id': raw_data['source_property_id'],
                'source_url': raw_data['url'],
                'business_type': business_type,
                'property_type': property_type,
                'title': title,
                'description': description,
                'price': price,
                'condominium_fee': condominium_fee,
                'iptu': None,
                'city': city,
                'state': 'RO',
                'neighborhood': neighborhood,
                'address_text': None,
                'bedrooms': bedrooms,
                'suites': None,
                'bathrooms': bathrooms,
                'garage_spaces': garage_spaces,
                'total_area': total_area,
                'built_area': None,
                'land_area': None,
                'published_at_source': None,
                'images': images,
                'content_hash': content_hash,
            }
        except Exception as e:
            logger.error("Habitare: failed to normalize property: %s", e)
            return None
