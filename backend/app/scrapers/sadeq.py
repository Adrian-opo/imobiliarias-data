"""
Scraper for Sadeq Imoveis (sadeqimoveis.com.br).

Platform: Loft (GTM Capital) - Next.js SSR-based portal.
Listings at /busca with pagination, detail pages at /imovel/{slug}-{city}-{state}-{id}.
Uses httpx + Parsel for SSR content.

Observations from site analysis (Apr 2026):
- Image CDN: Nhost (ppbxdsyojwqujdrmnxdv.storage.sa-east-1.nhost.run)
- Listing URLs: /busca with pagination (?page=X)
- Detail URLs: /imovel/{slug}-{city}-{state}-{id}
- Property codes are numeric IDs in the URL
- Uses SSR with streaming - actual content in HTML, no __NEXT_DATA__
- Image storage: cdn.vistahost.com.br for property images
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
    normalize_property_type,
    extract_bedrooms,
    compute_content_hash,
)

logger = logging.getLogger(__name__)


@register_scraper("sadeq")
class SadeqScraper(BaseScraper):
    """
    Scraper for Sadeq Imoveis (Loft platform).
    """

    source_name = "Sadeq Imoveis"
    platform = "Loft"

    def __init__(self, source_id: UUID, base_url: str = "https://sadeqimoveis.com.br"):
        super().__init__(source_id, base_url)
        self._client_kwargs = self.build_client_kwargs()

    async def scrape_listings(self, page_offset: int = 0) -> list[dict]:
        """
        Scrape property listings from Sadeq Imoveis.

        The /busca page shows properties with codes, titles, prices, and locations.
        Uses page_offset to rotate which pages are visited each cycle.
        """
        results = []

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            start_page = 1 + max(0, page_offset)
            end_page = start_page + settings.scrape_page_limit - 1

            for page in range(start_page, end_page + 1):
                url = f"{self.base_url}/busca" if page == 1 else f"{self.base_url}/busca?page={page}"
                logger.info("Sadeq: fetching page %d: %s", page, url)

                try:
                    await self.polite_delay()
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.warning("Sadeq page %d error: %s", page, e)
                    break

                sel = Selector(resp.text)

                # Find property cards/links - Sadeq uses links to /imovel/{slug}-{id}
                # Pattern: /imovel/{slug}-{city}-{state}-{id}
                cards = sel.css("a[href*='/imovel/']")
                if not cards:
                    # Alternative selector
                    cards = sel.css("a[href*='/imovel/']")

                page_items = []
                for card in cards:
                    href = card.attrib.get("href", "")
                    if not href or "/imovel/" not in href:
                        continue

                    # Extract numeric ID from URL: /imovel/casa-cafezinho-ji-parana-ro-642
                    # The ID is the last numeric segment
                    m = re.search(r'/imovel/.+-(\d+)$', href)
                    if not m:
                        continue

                    prop_id = m.group(1)
                    full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                    page_items.append({
                        "source_property_id": prop_id,
                        "url": full_url,
                    })

                results.extend(page_items)
                logger.info("Sadeq: found %d items on page %d (total %d)",
                            len(page_items), page, len(results))

                # Check for next page indicator
                next_btn = sel.css("a:has(.fa-chevron-right), a[rel='next'], a.next")
                if not next_btn and not page_items:
                    break

        # Deduplicate
        seen = set()
        unique = []
        for item in results:
            if item["source_property_id"] not in seen:
                seen.add(item["source_property_id"])
                unique.append(item)

        # Limit to max detail pages per cycle
        limited = unique[: settings.scrape_max_detail_pages_per_cycle]
        logger.info(
            "Sadeq: offset=%d, unique=%d, processing=%d",
            page_offset,
            len(unique),
            len(limited),
        )
        return limited

    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """
        Scrape a single property detail page from Sadeq Imoveis.

        The detail pages are SSR-rendered with actual content in the HTML.
        """
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                await self.polite_delay()
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("Sadeq detail error %s: %s", url, e)
                html = await self._fetch_with_playwright(url)
                if html is None:
                    return None
                sel = Selector(html)
                return self._parse_detail(sel, source_property_id, url)

        sel = Selector(resp.text)
        return self._parse_detail(sel, source_property_id, url)

    def _parse_detail(self, sel: Selector, source_property_id: str, url: str) -> dict:
        """
        Parse Sadeq detail page HTML into raw data dict.

        Sadeq uses SSR with content in HTML. We extract from:
        - Title, price, location from page content
        - Description from description section
        - Features from detail cards
        - Images from gallery
        """
        raw = {
            "source_property_id": source_property_id,
            "url": url,
        }

        # --- Title ---
        # Try meta tags first, then h1
        title = sel.css("meta[property='og:title']::attr(content)").get("")
        if not title:
            title = sel.css("h1::text").get("")
        raw["title"] = clean_text(title)

        # --- Price ---
        # Look for price in the page
        price_text = sel.css("meta[property='og:description']::attr(content)").get("")
        if price_text:
            # Extract price from description if present
            m = re.search(r'R\$\s*[\d\s\.]+,\d{2}', price_text)
            if m:
                raw["price"] = m.group(0)
        if not raw.get("price"):
            # Look for price in page content
            price_el = sel.css("span:contains('R$')::text, .price::text, [class*='price']::text").get("")
            if price_el:
                raw["price"] = price_el

        # --- Business type ---
        # From URL or title
        raw["business_type"] = self._detect_business_type(url, title)

        # --- Description ---
        desc = sel.css(
            ".description p::text, "
            "[class*='description'] p::text, "
            "article p::text, "
            ".box-description *::text"
        ).getall()
        raw["description"] = clean_text(" ".join(desc)) if desc else None

        # --- Location (neighborhood and city) ---
        # From breadcrumb or page content
        breadcrumb = sel.css(".breadcrumb *::text").getall()
        breadcrumb_text = " ".join([b.strip() for b in breadcrumb if b.strip()])
        raw["neighborhood"] = self._extract_neighborhood(breadcrumb_text, title)
        raw["city"] = self._extract_city(breadcrumb_text, url)

        # --- Property type ---
        # From title or breadcrumb
        raw["property_type"] = self._extract_property_type(breadcrumb_text, title, url)

        # --- Features ---
        # Look for feature cards or list items
        features = {}
        feature_items = sel.css(
            ".feature-item, .info-item, .detail-item, "
            ".card-info, [class*='feature'], [class*='info']"
        )
        for item in feature_items:
            text = " ".join(item.css("::text").getall()).strip()
            if ":" in text:
                k, v = text.split(":", 1)
                features[k.strip().lower()] = v.strip()
            elif text:
                # Try to match patterns like "3 quartos"
                m = re.match(r'(\d+)\s*(.+)', text)
                if m:
                    features[m.group(2).strip().lower()] = m.group(1)

        # Also look for specific feature labels
        feature_labels = sel.css(".info-label::text, .detail-label::text, .label::text").getall()
        feature_values = sel.css(".info-value::text, .detail-value::text, .value::text").getall()
        for label, value in zip(feature_labels, feature_values):
            if label and value:
                features[label.strip().lower()] = value.strip()

        raw["features"] = features

        # --- Extract structured fields ---
        raw["bedrooms"] = self._extract_numeric(features, r'(quarto|dormitório|dormitorio|dorm)')
        raw["bathrooms"] = self._extract_numeric(features, r'(banheiro|banho|wc)')
        raw["garage_spaces"] = self._extract_numeric(features, r'(garagem|vaga|estacionamento)')
        raw["suites"] = self._extract_numeric(features, r'(suite|suíte)')

        # Fallback: search in page text
        page_text = " ".join(sel.css("body *::text").getall()).lower()
        if raw["bedrooms"] is None:
            m = re.search(r'(\d+)\s*(?:quarto|quartos|dorm)', page_text)
            if m:
                raw["bedrooms"] = int(m.group(1))
        if raw["bathrooms"] is None:
            m = re.search(r'(\d+)\s*(?:banheiro|banheiros)', page_text)
            if m:
                raw["bathrooms"] = int(m.group(1))

        # --- Areas ---
        raw["total_area"] = None
        raw["built_area"] = None
        raw["land_area"] = None

        # Look for area in features or page text
        for key, value in features.items():
            if any(w in key for w in ["área total", "area total", "área", "area"]):
                raw["total_area"] = value
            elif any(w in key for w in ["área construída", "area construida", "área útil"]):
                raw["built_area"] = value
            elif any(w in key for w in ["área terreno", "area terreno", "lot", "terreno"]):
                raw["land_area"] = value

        # Also search for m² in page text
        if raw["total_area"] is None:
            m2_matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*m²', page_text)
            if m2_matches:
                raw["total_area"] = m2_matches[0]

        # --- Images ---
        images = []
        # Look for image tags in gallery
        img_tags = sel.css(
            ".gallery img::attr(src), "
            ".carousel img::attr(src), "
            "[class*='foto'] img::attr(src), "
            "[class*='photo'] img::attr(src), "
            "img[src*='cdn.vistahost.com.br']::attr(src), "
            "img[src*='vista.imobi']::attr(src)"
        ).getall()

        seen_urls = set()
        for i, src in enumerate(img_tags):
            if src and src not in seen_urls:
                seen_urls.add(src)
                # Handle relative URLs
                if src.startswith("/"):
                    src = f"{self.base_url}{src}"
                images.append({"url": src, "position": i})

        raw["images"] = images

        # --- Condominium fee ---
        raw["condominium_fee"] = None
        # Look for condomínio in features or page text
        for key, value in features.items():
            if "condomínio" in key.lower() or "condominio" in key.lower():
                raw["condominium_fee"] = value

        return raw

    # ------------------------------------------------------------------ #
    #  Parsing helpers
    # ------------------------------------------------------------------ #

    def _detect_business_type(self, url: str, title: Optional[str]) -> str:
        """Detect business type from URL or title."""
        url_lower = url.lower()
        if "/venda" in url_lower or "para venda" in (title or "").lower():
            return "venda"
        if "/aluguel" in url_lower or "para alugar" in (title or "").lower():
            return "aluguel"
        # Default to venda if not clear
        return "venda"

    def _extract_neighborhood(self, breadcrumb_text: str, title: Optional[str]) -> Optional[str]:
        """Extract neighborhood from breadcrumb or title."""
        if breadcrumb_text:
            # Try to extract neighborhood from pattern "em {neighborhood} - {city}"
            m = re.search(r'em\s+([^-]+?)\s*-', breadcrumb_text)
            if m:
                nb = m.group(1).strip()
                if nb and len(nb) > 2:
                    return nb
        if title:
            # Try from title: "Casa em {neighborhood} - {city}"
            m = re.search(r'em\s+([^-]+?)\s*-', title)
            if m:
                nb = m.group(1).strip()
                if nb and len(nb) > 2:
                    return nb
        return None

    def _extract_city(self, breadcrumb_text: str, url: str) -> str:
        """Extract city from breadcrumb or URL."""
        if breadcrumb_text:
            # Last segment after " - "
            parts = re.split(r'\s*-\s*', breadcrumb_text)
            if len(parts) >= 2:
                city = parts[-1].strip()
                if city and len(city) > 2:
                    return city
        # From URL: /imovel/{slug}-{city}-{state}-{id}
        m = re.search(r'/imovel/[^-]+-([^-]+)-([^-]+)-\d+$', url)
        if m:
            city = m.group(1).replace("-", " ")
            return city.title()
        return "Ji-Paraná"  # Default city

    def _extract_property_type(self, breadcrumb_text: str, title: Optional[str], url: str) -> str:
        """Extract property type from breadcrumb, title, or URL."""
        # From URL pattern: /imovel/{type}-{slug}-{city}-{state}-{id}
        m = re.search(r'/imovel/([^-]+)-', url)
        if m:
            type_from_url = m.group(1).replace("-", " ")
            return type_from_url

        # From breadcrumb (first meaningful word)
        if breadcrumb_text:
            parts = breadcrumb_text.split()
            if parts:
                return parts[0]

        # From title (first word)
        if title:
            parts = title.split()
            if parts:
                return parts[0]

        return ""

    def _extract_numeric(self, features: dict, pattern: str) -> Optional[int]:
        """Extract numeric value from features by key regex."""
        for key, value in features.items():
            if re.search(pattern, key, re.IGNORECASE):
                nums = re.findall(r'\d+', str(value))
                if nums:
                    return int(nums[0])
        return None

    # ------------------------------------------------------------------ #
    #  Normalize
    # ------------------------------------------------------------------ #

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Convert raw scraped data into normalized property dict."""
        try:
            title = raw_data.get("title")
            description = raw_data.get("description")
            neighborhood = raw_data.get("neighborhood")

            business_type = normalize_business_type(raw_data.get("business_type", "")) or "sale"
            property_type = normalize_property_type(raw_data.get("property_type") or title or "")

            price = normalize_price(raw_data.get("price"))
            condominium_fee = normalize_price(raw_data.get("condominium_fee"))

            total_area = normalize_area(raw_data.get("total_area"))
            built_area = normalize_area(raw_data.get("built_area"))
            land_area = normalize_area(raw_data.get("land_area"))

            bedrooms = raw_data.get("bedrooms")
            bathrooms = raw_data.get("bathrooms")
            garage_spaces = raw_data.get("garage_spaces")
            suites = raw_data.get("suites")

            if bedrooms is None:
                bedrooms = extract_bedrooms(title) or extract_bedrooms(description)

            images = raw_data.get("images", [])
            city = raw_data.get("city", "Ji-Paraná")

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
                "source_property_id": raw_data["source_property_id"],
                "source_url": raw_data["url"],
                "business_type": business_type,
                "property_type": property_type,
                "title": title,
                "description": description,
                "price": price,
                "condominium_fee": condominium_fee,
                "iptu": None,
                "city": city,
                "state": "RO",
                "neighborhood": neighborhood,
                "address_text": None,
                "bedrooms": bedrooms,
                "suites": suites,
                "bathrooms": bathrooms,
                "garage_spaces": garage_spaces,
                "total_area": total_area,
                "built_area": built_area,
                "land_area": land_area,
                "published_at_source": None,
                "images": images,
                "content_hash": content_hash,
            }
        except Exception as e:
            logger.error("Sadeq: failed to normalize property: %s", e)
            return None
