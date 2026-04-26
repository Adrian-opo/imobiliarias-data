"""
Scraper for Imobiliaria Nogueira (imobiliarianogueira.com.br).

Platform: Imobzi (Angular 21.2.6) - SSR with client hydration.
Listing page: /buscar with query parameters.
Detail pages: /imovel/{slug}-code-{id}
Uses httpx + Parsel for SSR content.

Observations from site analysis (Apr 2026):
- Platform: Imobzi (Angular 21.2.6)
- Account ID: ac-uiod201113b5s0
- API Base: https://api2.imobzi.app/v1/ac-uiod201113b5s0/site2/
- Image CDN: lh3.googleusercontent.com (Google Photos)
- Property ID format: code-XXXX (e.g., code-1428)
- Listing page: /buscar (with filters via query params)
- Detail URL: /imovel/{slug}-code-{id}
- Embedded state: <script id="ng-state"> contains preloaded API responses
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


@register_scraper("nogueira")
class NogueiraScraper(BaseScraper):
    """
    Scraper for Imobiliaria Nogueira (Imobzi platform).
    """

    source_name = "Imobiliaria Nogueira"
    platform = "Imobzi"

    def __init__(self, source_id: UUID, base_url: str = "https://www.imobiliarianogueira.com.br"):
        super().__init__(source_id, base_url)
        self._client_kwargs = self.build_client_kwargs()

    async def scrape_listings(self, page_offset: int = 0) -> list[dict]:
        """
        Scrape property listings from Imobiliaria Nogueira.

        The /buscar page shows properties with ng-state embedded data.
        Uses page_offset to rotate which pages are visited each cycle.
        """
        results = []

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            start_page = 1 + max(0, page_offset)
            end_page = start_page + settings.scrape_page_limit - 1

            for page in range(start_page, end_page + 1):
                url = f"{self.base_url}/buscar?page={page}" if page > 1 else f"{self.base_url}/buscar"
                logger.info("Nogueira: fetching page %d: %s", page, url)

                try:
                    await self.polite_delay()
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.warning("Nogueira page %d error: %s", page, e)
                    break

                sel = Selector(resp.text)

                # Extract ng-state JSON blob
                ng_state = self._extract_ng_state(sel)
                if ng_state:
                    # Extract property listings from ng-state
                    items_from_state = self._extract_listings_from_ng_state(ng_state)
                    if items_from_state:
                        results.extend(items_from_state)
                        logger.info("Nogueira: found %d items from ng-state (total %d)",
                                    len(items_from_state), len(results))
                        continue

                # Fallback: scrape links from HTML
                cards = sel.css("a[href*='/imovel/']")
                page_items = []
                for card in cards:
                    href = card.attrib.get("href", "")
                    if not href or "/imovel/" not in href:
                        continue

                    # Extract property ID from URL: /imovel/{slug}-code-{id}
                    m = re.search(r'/imovel/.+-code-(\d+)$', href)
                    if not m:
                        continue

                    prop_id = f"code-{m.group(1)}"
                    full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                    page_items.append({
                        "source_property_id": prop_id,
                        "url": full_url,
                    })

                results.extend(page_items)
                logger.info("Nogueira: found %d items on page %d (total %d)",
                            len(page_items), page, len(results))

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
            "Nogueira: offset=%d, unique=%d, processing=%d",
            page_offset,
            len(unique),
            len(limited),
        )
        return limited

    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """
        Scrape a single property detail page from Imobiliaria Nogueira.

        The detail pages are SSR-rendered with ng-state embedded data.
        """
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                await self.polite_delay()
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("Nogueira detail error %s: %s", url, e)
                html = await self._fetch_with_playwright(url)
                if html is None:
                    return None
                sel = Selector(html)
                return self._parse_detail(sel, source_property_id, url)

        sel = Selector(resp.text)
        return self._parse_detail(sel, source_property_id, url)

    def _parse_detail(self, sel: Selector, source_property_id: str, url: str) -> dict:
        """
        Parse Nogueira detail page HTML into raw data dict.

        The ng-state JSON blob contains preloaded API data with full property details.
        """
        raw = {
            "source_property_id": source_property_id,
            "url": url,
        }

        # --- Extract ng-state data ---
        ng_state = self._extract_ng_state(sel)
        if ng_state:
            # Try to extract property detail from ng-state
            property_data = self._extract_property_from_ng_state(ng_state, source_property_id)
            if property_data:
                raw.update(property_data)

        # --- Fallback: scrape from HTML ---
        if not raw.get("title"):
            # Title from meta or h1
            title = sel.css("meta[property='og:title']::attr(content)").get("")
            if not title:
                title = sel.css("h1::text, .property-title::text").get("")
            raw["title"] = clean_text(title)

        if not raw.get("price"):
            # Price from meta or page content
            price_text = sel.css("meta[property='og:description']::attr(content)").get("")
            if price_text:
                m = re.search(r'R\$\s*[\d\s\.]+,\d{2}', price_text)
                if m:
                    raw["price"] = m.group(0)
            if not raw.get("price"):
                price_el = sel.css("span:contains('R$')::text, .price::text").get("")
                if price_el:
                    raw["price"] = price_el

        if not raw.get("description"):
            # Description from meta or page
            desc = sel.css(
                "meta[property='og:description']::attr(content), "
                ".description p::text, "
                "[class*='descricao'] p::text"
            ).getall()
            raw["description"] = clean_text(" ".join(desc)) if desc else None

        if not raw.get("neighborhood"):
            # Neighborhood from meta or page
            raw["neighborhood"] = self._extract_neighborhood_from_html(sel, url)

        if not raw.get("city"):
            raw["city"] = "Ji-Paraná"

        if not raw.get("property_type"):
            raw["property_type"] = self._extract_property_type_from_html(sel, url)

        # --- Business type from URL ---
        raw["business_type"] = self._detect_business_type(url)

        # --- Features ---
        features = {}
        feature_items = sel.css(
            ".property-features li, "
            ".features-list li, "
            "[class*='feature'] li, "
            "imobzi-property-features li"
        )
        for item in feature_items:
            text = " ".join(item.css("::text").getall()).strip()
            if ":" in text:
                k, v = text.split(":", 1)
                features[k.strip().lower()] = v.strip()
            elif text:
                m = re.match(r'(\d+)\s*(.+)', text)
                if m:
                    features[m.group(2).strip().lower()] = m.group(1)

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

        for key, value in features.items():
            if any(w in key for w in ["área total", "area total", "área", "area"]):
                raw["total_area"] = value
            elif any(w in key for w in ["área construída", "area construida", "área útil"]):
                raw["built_area"] = value
            elif any(w in key for w in ["área terreno", "area terreno", "lot", "terreno"]):
                raw["land_area"] = value

        if raw["total_area"] is None:
            m2_matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*m²', page_text)
            if m2_matches:
                raw["total_area"] = m2_matches[0]

        # --- Images ---
        images = []
        img_tags = sel.css(
            ".gallery img::attr(src), "
            ".carousel img::attr(src), "
            "[class*='foto'] img::attr(src), "
            "[class*='photo'] img::attr(src), "
            "img[src*='lh3.googleusercontent.com']::attr(src), "
            "img[src*='googleusercontent.com']::attr(src)"
        ).getall()

        seen_urls = set()
        for i, src in enumerate(img_tags):
            if src and src not in seen_urls:
                seen_urls.add(src)
                images.append({"url": src, "position": i})

        raw["images"] = images

        # --- Condominium fee ---
        raw["condominium_fee"] = None
        for key, value in features.items():
            if "condomínio" in key.lower() or "condominio" in key.lower():
                raw["condominium_fee"] = value

        return raw

    # ------------------------------------------------------------------ #
    #  ng-state extraction helpers
    # ------------------------------------------------------------------ #

    def _extract_ng_state(self, sel: Selector) -> Optional[dict]:
        """Extract the ng-state JSON blob from the page."""
        ng_state_script = sel.css("script#ng-state::text").get()
        if ng_state_script:
            try:
                return json.loads(ng_state_script)
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def _extract_listings_from_ng_state(self, ng_state: dict) -> list[dict]:
        """
        Extract property listings from ng-state JSON.

        The ng-state contains preloaded API responses with property data.
        """
        results = []

        # ng-state structure: {hash: {b: [...], u: url, s: status}}
        for key, value in ng_state.items():
            if isinstance(value, dict) and "b" in value:
                data = value["b"]
                # Data could be a list of properties or a dict with properties
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            prop_id = item.get("code") or item.get("id")
                            if prop_id:
                                # Convert to format code-XXXX if numeric
                                if isinstance(prop_id, int) or (isinstance(prop_id, str) and prop_id.isdigit()):
                                    prop_id_str = f"code-{prop_id}" if isinstance(prop_id, int) else f"code-{prop_id}"
                                else:
                                    prop_id_str = str(prop_id)

                                # Get URL if available
                                url = item.get("url") or item.get("link")
                                if url:
                                    if not url.startswith("http"):
                                        url = f"{self.base_url}{url}"
                                else:
                                    # Build URL from slug if available
                                    slug = item.get("slug") or item.get("url_slug")
                                    if slug:
                                        url = f"{self.base_url}/imovel/{slug}-code-{prop_id}"
                                    else:
                                        url = None

                                if url:
                                    results.append({
                                        "source_property_id": prop_id_str,
                                        "url": url,
                                    })

                elif isinstance(data, dict):
                    # Sometimes data is wrapped in a dict
                    for key2, value2 in data.items():
                        if isinstance(value2, dict):
                            prop_id = value2.get("code") or value2.get("id")
                            if prop_id:
                                prop_id_str = f"code-{prop_id}" if isinstance(prop_id, int) else f"code-{prop_id}"
                                url = value2.get("url") or value2.get("link")
                                if url:
                                    if not url.startswith("http"):
                                        url = f"{self.base_url}{url}"
                                if url:
                                    results.append({
                                        "source_property_id": prop_id_str,
                                        "url": url,
                                    })

        return results

    def _extract_property_from_ng_state(self, ng_state: dict, source_property_id: str) -> Optional[dict]:
        """
        Extract property detail from ng-state JSON.

        Looks for property data matching the source_property_id.
        """
        for key, value in ng_state.items():
            if isinstance(value, dict) and "b" in value:
                data = value["b"]

                # Handle list of properties
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            prop_id = item.get("code") or item.get("id")
                            if prop_id:
                                prop_id_str = f"code-{prop_id}" if isinstance(prop_id, int) else f"code-{prop_id}"
                                if prop_id_str == source_property_id:
                                    return self._map_ng_state_property(item)

                # Handle single property dict
                elif isinstance(data, dict):
                    prop_id = data.get("code") or data.get("id")
                    if prop_id:
                        prop_id_str = f"code-{prop_id}" if isinstance(prop_id, int) else f"code-{prop_id}"
                        if prop_id_str == source_property_id:
                            return self._map_ng_state_property(data)

        return None

    def _map_ng_state_property(self, item: dict) -> dict:
        """Map ng-state property data to raw format."""
        raw = {}

        # Title
        raw["title"] = item.get("title") or item.get("name")

        # Price
        price = item.get("price") or item.get("valor")
        if price:
            if isinstance(price, (int, float)):
                raw["price"] = f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                raw["price"] = str(price)

        # Description
        raw["description"] = item.get("description") or item.get("descricao")

        # Location
        raw["neighborhood"] = item.get("neighborhood") or item.get("bairro")
        raw["city"] = item.get("city") or item.get("cidade") or "Ji-Paraná"

        # Property type
        raw["property_type"] = item.get("property_type") or item.get("tipo")

        # Business type
        raw["business_type"] = item.get("business_type") or item.get("finalidade")

        # Features
        features = item.get("features") or item.get("caracteristicas") or {}
        if isinstance(features, list):
            # Convert list to dict
            features_dict = {}
            for f in features:
                if isinstance(f, dict):
                    key = f.get("name") or f.get("nome")
                    value = f.get("value") or f.get("valor")
                    if key and value:
                        features_dict[key.lower()] = str(value)
            features = features_dict
        raw["features"] = features

        # Extract structured fields
        raw["bedrooms"] = self._extract_numeric(features, r'(quarto|dormitório|dormitorio|dorm)')
        raw["bathrooms"] = self._extract_numeric(features, r'(banheiro|banho|wc)')
        raw["garage_spaces"] = self._extract_numeric(features, r'(garagem|vaga|estacionamento)')
        raw["suites"] = self._extract_numeric(features, r'(suite|suíte)')

        # Areas
        raw["total_area"] = None
        raw["built_area"] = None
        raw["land_area"] = None

        for key, value in features.items():
            if any(w in key for w in ["área total", "area total", "área", "area"]):
                raw["total_area"] = value
            elif any(w in key for w in ["área construída", "area construida"]):
                raw["built_area"] = value
            elif any(w in key for w in ["área terreno", "area terreno"]):
                raw["land_area"] = value

        # Images
        images = []
        img_list = item.get("images") or item.get("fotos") or []
        for i, img in enumerate(img_list):
            if isinstance(img, dict):
                url = img.get("url") or img.get("src")
                if url:
                    images.append({"url": url, "position": i})
            elif isinstance(img, str):
                images.append({"url": img, "position": i})
        raw["images"] = images

        return raw

    # ------------------------------------------------------------------ #
    #  HTML parsing helpers
    # ------------------------------------------------------------------ #

    def _extract_neighborhood_from_html(self, sel: Selector, url: str) -> Optional[str]:
        """Extract neighborhood from HTML."""
        # From meta tags
        title = sel.css("meta[property='og:title']::attr(content)").get("")
        if title:
            m = re.search(r'em\s+([^-]+?)\s*-', title)
            if m:
                return m.group(1).strip()

        # From URL
        m = re.search(r'/imovel/([^-]+)-', url)
        if m:
            return m.group(1).replace("-", " ").title()

        return None

    def _extract_property_type_from_html(self, sel: Selector, url: str) -> str:
        """Extract property type from HTML or URL."""
        # From URL
        m = re.search(r'/imovel/([^-]+)-', url)
        if m:
            return m.group(1).replace("-", " ")

        # From title
        title = sel.css("meta[property='og:title']::attr(content)").get("")
        if title:
            parts = title.split()
            if parts:
                return parts[0]

        return ""

    def _detect_business_type(self, url: str) -> str:
        """Detect business type from URL."""
        url_lower = url.lower()
        if "/venda" in url_lower or "venda" in url_lower:
            return "venda"
        if "/aluguel" in url_lower or "aluguel" in url_lower:
            return "aluguel"
        return "venda"

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
            logger.error("Nogueira: failed to normalize property: %s", e)
            return None
