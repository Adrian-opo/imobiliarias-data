"""
Scraper for Jardins Imobiliaria (jardinsimobiliaria.com.br).

Platform: Imobzi (SSR + client-side rendering).
This scraper uses httpx + parsel for SSR pages, extracting data from:
  - Breadcrumb: property type, business type, neighborhood, city
  - JSON-LD: bedrooms, bathrooms, images, description, city
  - H1 title: fallback for all fields
  - Playwright: fallback if httpx returns a client-rendered page

Conservative scraping policy:
  - Max 3 listing pages per cycle (60 items)
  - Respectful delays between requests (1-3s)
  - No parallelism on detail pages (sequential)
  - Respects robots.txt conventions

Reuses shared DEFAULT_HEADERS from base.py.
"""
import json
import logging
import re
from typing import Optional
from uuid import UUID

import httpx
from parsel import Selector

from app.scrapers.base import BaseScraper, DEFAULT_HEADERS
from app.config import settings
from app.scrapers.registry import register_scraper
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

LISTING_URL = "https://www.jardinsimobiliaria.com.br/imoveis"


@register_scraper("jardins")
class JardinsScraper(BaseScraper):
    """Scraper for Jardins Imobiliaria (Imobzi platform)."""

    source_name = "Jardins Imobiliaria"
    platform = "Imobzi"

    def __init__(self, source_id: UUID, base_url: str = "https://www.jardinsimobiliaria.com.br"):
        super().__init__(source_id, base_url)
        self._client_kwargs = self.build_client_kwargs()

    async def scrape_listings(self) -> list[dict]:
        """
        Scrape list of properties from Jardins Imobiliaria.

        Conservative approach: few pages per cycle and polite delays.
        """
        results = []

        search_urls = [
            f"{self.base_url}/buscar?order=neighborhood&availability=buy",
            f"{self.base_url}/buscar?order=neighborhood&availability=rent",
        ]

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            for base_list_url in search_urls:
                page = 1
                while page <= settings.scrape_page_limit:
                    url = f"{base_list_url}&pagina={page}" if page > 1 else base_list_url
                    logger.info("Jardins: fetching page %d: %s", page, url)

                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                    except httpx.HTTPError as e:
                        logger.error("Jardins: failed to fetch page %d: %s", page, e)
                        break

                    sel = Selector(resp.text)

                    items = sel.css("a[href*='/imovel/']")
                    page_items = []
                    for item in items:
                        href = item.attrib.get("href", "")
                        if not href or "/imovel/" not in href:
                            continue
                        m = re.search(r'/imovel/([^/]+)', href)
                        if not m:
                            continue
                        prop_id = m.group(1)
                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                        page_items.append({
                            "source_property_id": prop_id,
                            "url": full_url,
                        })

                    results.extend(page_items)
                    logger.info("Jardins: found %d items on page %d (total %d)",
                                len(page_items), page, len(results))

                    # Next page detection
                    next_btn = sel.css("a.next, a:has(.fa-chevron-right), a[rel='next']")
                    if not next_btn and (not page_items or not sel.css("a:has(.fa-chevron-left), a:has(.fa-chevron-right)")):
                        break

                    page += 1

                    # Conservative delay between pages
                    await self.polite_delay()

        # Deduplicate across search URLs
        seen = set()
        unique = []
        for item in results:
            if item["source_property_id"] not in seen:
                seen.add(item["source_property_id"])
                unique.append(item)

        limited = unique[: settings.scrape_max_detail_pages_per_cycle]
        logger.info(
            "Jardins: total unique listings=%d, processing this cycle=%d",
            len(unique),
            len(limited),
        )
        return limited

    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """Scrape a single property detail page using httpx + JSON-LD + breadcrumb."""

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                await self.polite_delay()
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("Jardins: detail error %s: %s", url, e)
                html = await self._fetch_with_playwright(url)
                if html is None:
                    return None
                sel = Selector(html)
                return self._parse_detail(sel, source_property_id, url)

        sel = Selector(resp.text)
        return self._parse_detail(sel, source_property_id, url)

    def _parse_detail(self, sel: Selector, source_property_id: str, url: str) -> dict:
        """Parse the detail page HTML into a raw data dict.

        Sources ranked by reliability:
          1. JSON-LD (structured data)
          2. Breadcrumb (parsed text)
          3. H1 title (fallback)
        """
        raw = {
            "source_property_id": source_property_id,
            "url": url,
        }

        # --- Source 1: JSON-LD ---
        ld = self._extract_json_ld(sel)

        # --- Source 2: Breadcrumb ---
        breadcrumb_text = self._get_breadcrumb(sel)

        # --- Source 3: H1 title ---
        h1 = clean_text(sel.css("h1::text").get(""))

        # --- Extract property type ---
        # Priority: breadcrumb first word > H1 first word > JSON-LD @type
        if breadcrumb_text:
            raw["property_type"] = breadcrumb_text.split()[0] if breadcrumb_text.split() else ""
        elif h1:
            raw["property_type"] = h1.split()[0] if h1.split() else ""
        else:
            raw["property_type"] = ld.get("name", "")

        # --- Extract business type ---
        # JSON-LD description has "Alugue" or "Compre", breadcrumb has "à venda" or "para locação"
        bt = None
        if breadcrumb_text:
            bt = self._parse_business_from_breadcrumb(breadcrumb_text)
        if not bt and ld.get("description"):
            bt = self._parse_business_from_description(ld["description"])
        raw["business_type"] = bt or ""

        # --- Extract neighborhood ---
        nb = None
        if breadcrumb_text:
            nb = self._parse_neighborhood_from_breadcrumb(breadcrumb_text)
        if not nb and h1:
            nb = self._parse_neighborhood_from_title(h1)
        if not nb and ld.get("name"):
            nb = self._parse_neighborhood_from_title(ld["name"])
        raw["neighborhood"] = nb

        # --- Extract city ---
        city = None
        if ld.get("address", {}).get("addressLocality"):
            city = ld["address"]["addressLocality"]
        if not city and breadcrumb_text:
            city = self._parse_city_from_breadcrumb(breadcrumb_text)
        raw["city"] = city or "Ji-Paraná"  # default city

        # --- Title ---
        raw["title"] = clean_text(ld.get("name")) or h1 or ""

        # --- Description ---
        raw["description"] = clean_text(ld.get("description"))

        # --- Price from JSON-LD offers ---
        price = None
        offers = ld.get("offers", {})
        if offers.get("price") and float(offers["price"]) > 0:
            price = float(offers["price"])
        if not price and ld.get("description"):
            # Try to extract "R$ X" from description text
            m = re.search(r'R\$\s*([\d\s\.]+,\d{2})', ld["description"])
            if m:
                price = normalize_price(f"R$ {m.group(1)}")
        raw["price"] = price

        # --- Bedrooms and bathrooms from JSON-LD ---
        raw["bedrooms"] = ld.get("numberOfBedrooms")
        raw["bathrooms"] = ld.get("numberOfBathroomsTotal")
        raw["suites"] = None
        raw["garage_spaces"] = None

        # --- Areas from JSON-LD ---
        raw["total_area"] = ld.get("floorSize", {}).get("value")
        raw["built_area"] = None
        raw["land_area"] = ld.get("lotSize", {}).get("value")

        # --- Images from JSON-LD ---
        images = []
        img_urls = ld.get("image", [])
        if isinstance(img_urls, str):
            img_urls = [img_urls]
        for i, src in enumerate(img_urls):
            if src and not src.endswith(("svg", "placeholder")):
                images.append({"url": src, "position": i})
        raw["images"] = images

        # --- Condominium fee (not available in SSR) ---
        raw["condominium_fee"] = None

        # --- Features (not available in SSR — requires client-side) ---
        raw["features"] = {}

        return raw

    # ------------------------------------------------------------------ #
    #  Parsing helpers
    # ------------------------------------------------------------------ #

    def _extract_json_ld(self, sel: Selector) -> dict:
        """Extract structured data from JSON-LD script tag."""
        for script in sel.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, ValueError):
                continue
        return {}

    def _get_breadcrumb(self, sel: Selector) -> Optional[str]:
        """
        Extract the property description from the breadcrumb.
        
        Imobzi breadcrumb format:
          Home > imoveis > {Property Description} > Cód: {code}
        We want the description (second-to-last meaningful item).
        """
        parts = sel.css(".breadcrumb *::text").getall()
        parts = [p.strip() for p in parts if p.strip() and p.strip() not in ("chevron_right", "Home", "imoveis")]
        # Filter out "Cód:" items
        parts = [p for p in parts if not p.startswith("Cód:") and not p.startswith("Cód :")]
        if parts:
            return parts[-1]
        return None

    def _parse_business_from_breadcrumb(self, text: str) -> Optional[str]:
        """Extract business type from breadcrumb text like 'à venda' or 'para locação'."""
        text_lower = text.lower()
        if "à venda" in text_lower or "venda" in text_lower:
            return "venda"
        if "para locação" in text_lower or "locação" in text_lower or "alugar" in text_lower or "aluguel" in text_lower or "locacao" in text_lower:
            return "aluguel"
        return None

    def _parse_business_from_description(self, desc: str) -> Optional[str]:
        """Extract business type from description like 'Alugue ...' or 'Compre ...'."""
        desc_lower = desc.lower()
        if any(w in desc_lower for w in ["alugue", "alugar", "locação"]):
            return "aluguel"
        if any(w in desc_lower for w in ["compre", "comprar", "venda"]):
            return "venda"
        return None

    def _parse_neighborhood_from_breadcrumb(self, text: str) -> Optional[str]:
        """
        Extract neighborhood from breadcrumb like:
          'Fazenda à venda em Zona Rural - Ouro Preto do Oeste'
          'Apartamento para locação em Jardim Aurélio Bernardi - 1º Distrito - Ji-paraná'
        
        Strategy: take text after 'em ' and before the next ' - '.
        """
        # Remove business type prefix (type + "à venda" / "para locação" / etc.)
        m = re.search(r'\bem\s+(.+)', text, re.IGNORECASE)
        if not m:
            return None
        after_em = m.group(1).strip()

        # Extract only up to the first " - " (removes district/city)
        m2 = re.split(r'\s*-\s*', after_em)
        if m2:
            nb = m2[0].strip()
            return nb if nb else None
        return after_em if after_em else None

    def _parse_neighborhood_from_title(self, title: str) -> Optional[str]:
        """
        Extract neighborhood from H1 title like:
          'Apartamento em Jardim Aurélio Bernardi - 1º Distrito - Ji-paraná'
          'Fazenda em Zona Rural - Ji-Paraná'
        """
        m = re.search(r'\bem\s+(.+)', title, re.IGNORECASE)
        if not m:
            return None
        after_em = m.group(1).strip()
        # Take everything before the first " - "
        parts = re.split(r'\s*-\s*', after_em)
        nb = parts[0].strip() if parts else after_em
        return nb if nb else None

    def _parse_city_from_breadcrumb(self, text: str) -> Optional[str]:
        """
        Extract city from breadcrumb — the last segment after ' - '.
        E.g. 'Fazenda à venda em Zona Rural - Ouro Preto do Oeste' → 'Ouro Preto do Oeste'
        """
        parts = re.split(r'\s*-\s*', text)
        if len(parts) >= 2:
            return parts[-1].strip()
        return None

    # ------------------------------------------------------------------ #
    #  Normalize
    # ------------------------------------------------------------------ #

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Convert raw scraped data into normalized property dict."""
        try:
            title = raw_data.get("title")
            description = raw_data.get("description")
            raw_neighborhood = raw_data.get("neighborhood")

            business_type = normalize_business_type(raw_data.get("business_type", ""))
            if not business_type:
                business_type = "sale"

            property_type = normalize_property_type(raw_data.get("property_type") or title or "")

            price = raw_data.get("price")
            if price is not None:
                price = float(price)
            condominium_fee = raw_data.get("condominium_fee")

            total_area = raw_data.get("total_area")
            if total_area is not None:
                total_area = float(total_area) if total_area > 0 else None
            land_area = raw_data.get("land_area")
            if land_area is not None:
                land_area = float(land_area) if land_area > 0 else None

            bedrooms = raw_data.get("bedrooms")
            bathrooms = raw_data.get("bathrooms")
            garage_spaces = raw_data.get("garage_spaces")
            suites = raw_data.get("suites")

            # Clean neighborhood
            neighborhood = normalize_neighborhood(raw_neighborhood)
            if not neighborhood and title:
                neighborhood = normalize_neighborhood(
                    self._parse_neighborhood_from_title(title)
                )

            if bedrooms is None or bedrooms == 0:
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
                "built_area": None,
                "land_area": land_area,
                "published_at_source": None,
                "images": images,
                "content_hash": content_hash,
            }
        except Exception as e:
            logger.error("Jardins: failed to normalize property: %s", e)
            return None
