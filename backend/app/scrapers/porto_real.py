"""
Scraper for Porto Real Imoveis (porto-real.com).

Platform: Kenlo.
SSR-based portal with listing pages at /imoveis/a-venda/... and detail pages
at /imovel/... Uses httpx + Parsel; falls back to Playwright if needed.
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


@register_scraper("porto_real")
class PortoRealScraper(BaseScraper):
    """
    Scraper for Porto Real Imoveis (Kenlo platform).
    """

    source_name = "Porto Real Imoveis"
    platform = "Kenlo"
    SALE_PATHS = [
        "/imoveis/a-venda/ji-parana",
        "/imoveis/a-venda/casa/ji-parana",
        "/imoveis/a-venda/apartamento/ji-parana",
        "/imoveis/a-venda/terreno/ji-parana",
        "/imoveis/a-venda/sobrado/ji-parana",
        "/imoveis/a-venda/chacara/ji-parana",
        "/imoveis/a-venda/area/ji-parana",
        "/imoveis/a-venda/galpao/ji-parana",
        "/imoveis/a-venda/barracao/ji-parana",
        "/imoveis/a-venda/loja/ji-parana",
        "/imoveis/a-venda/sala/ji-parana",
        "/imoveis/a-venda/salao/ji-parana",
        "/imoveis/a-venda/predio/ji-parana",
    ]
    RENT_PATHS = [
        "/imoveis/para-alugar/ji-parana",
        "/imoveis/para-alugar/casa/ji-parana",
        "/imoveis/para-alugar/apartamento/ji-parana",
        "/imoveis/para-alugar/galpao/ji-parana",
        "/imoveis/para-alugar/barracao/ji-parana",
        "/imoveis/para-alugar/predio/ji-parana",
        "/imoveis/para-alugar/ponto/ji-parana",
        "/imoveis/para-alugar/sala/ji-parana",
        "/imoveis/para-alugar/salao/ji-parana",
        "/imoveis/para-alugar/chacara/ji-parana",
        "/imoveis/para-alugar/andar-corporativo/ji-parana",
    ]

    def __init__(self, source_id: UUID, base_url: str = "https://porto-real.com"):
        super().__init__(source_id, base_url)
        self._client_kwargs = self.build_client_kwargs()

    async def scrape_listings(self) -> list[dict]:
        """
        Scrape property listings from Porto Real.

        Kenlo exposes SSR cards on multiple filter URLs. The generic city page only
        shows a subset, so we fan out through the real type-specific routes and keep
        the crawl conservative via the shared page limit and polite delays.
        """
        results = []
        # Interleave SALE and RENT routes so both categories are visited each cycle.
        # SALE_PATHS + RENT_PATHS concatenated would bias toward SALE (13 vs 9 routes).
        max_routes = settings.scrape_max_listing_routes_per_cycle
        half = max(max_routes // 2, 1)
        sale_selected = self.SALE_PATHS[:half]
        rent_selected = self.RENT_PATHS[:max(max_routes - half, 1)]
        # Interleave: SALE[0], RENT[0], SALE[1], RENT[1], ...
        interleaved = []
        i = 0
        while len(interleaved) < max_routes and (i < len(sale_selected) or i < len(rent_selected)):
            if i < len(sale_selected):
                interleaved.append(sale_selected[i])
            if i < len(rent_selected) and len(interleaved) < max_routes:
                interleaved.append(rent_selected[i])
            i += 1
        search_urls = [f"{self.base_url}{path}" for path in interleaved]

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            for url in search_urls:
                logger.info("PortoReal: fetching listings: %s", url)

                try:
                    await self.polite_delay()
                    resp = await client.get(url)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    logger.warning("PortoReal listing error for %s: %s", url, e)
                    continue

                sel = Selector(resp.text)

                # Detect business type from the listing URL path
                url_lower = url.lower()
                if "/a-venda/" in url_lower or "/venda/" in url_lower:
                    inferred_business = "venda"
                elif "/para-alugar/" in url_lower or "/alugar/" in url_lower or "/locacao/" in url_lower:
                    inferred_business = "aluguel"
                else:
                    inferred_business = None

                page_items = []
                for href in sel.css("a[href*='/imovel/']::attr(href)").getall():
                    if not href or "/imovel/" not in href:
                        continue
                    full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                    source_property_id = href.rstrip("/").split("/")[-1]
                    if not source_property_id:
                        continue
                    page_items.append(
                        {
                            "source_property_id": source_property_id,
                            "url": full_url,
                            "business_type_hint": inferred_business,
                        }
                    )

                results.extend(page_items)
                logger.info(
                    "PortoReal: found %d items for %s (total %d)",
                    len(page_items),
                    url,
                    len(results),
                )

        # Deduplicate by source_property_id (keep first occurrence which has matching hint)
        seen = set()
        unique = []
        for item in results:
            if item["source_property_id"] not in seen:
                seen.add(item["source_property_id"])
                unique.append(item)

        limited = unique[: settings.scrape_max_detail_pages_per_cycle]
        logger.info(
            "PortoReal: total unique listings=%d, selected routes=%d, processing this cycle=%d",
            len(unique),
            len(search_urls),
            len(limited),
        )
        return limited

    async def scrape_detail(self, source_property_id: str, url: str, **kwargs) -> Optional[dict]:
        """Scrape a single property detail page from Porto Real (Kenlo)."""
        import httpx

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                await self.polite_delay()
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("PortoReal detail error %s: %s", url, e)
                # Try Playwright fallback
                html = await self._fetch_with_playwright(url)
                if html is None:
                    return None
                sel = Selector(html)
                return self._parse_detail(sel, source_property_id, url, **kwargs)

        sel = Selector(resp.text)
        return self._parse_detail(sel, source_property_id, url, **kwargs)

    def _parse_detail(self, sel: Selector, source_property_id: str, url: str, **kwargs) -> dict:
        """Parse Porto Real detail page HTML into raw data dict."""
        raw = {
            "source_property_id": source_property_id,
            "url": url,
        }
        product_ld = self._extract_product_json_ld(sel)
        detail_map = self._extract_detail_map(sel)

        title = clean_text(product_ld.get("name")) or clean_text(
            sel.css("meta[property='og:title']::attr(content), title::text").get("")
        )
        raw["title"] = title

        offers = product_ld.get("offers") or []
        if isinstance(offers, dict):
            offers = [offers]
        price_text = offers[0].get("price", "") if offers else ""
        if not price_text:
            price_text = sel.css(".price-value--full::text, .price::text").get("")
        raw["price"] = price_text

        # Business type: 1) hint from listing page, 2) page content, 3) URL fallback
        raw["business_type"] = self._detect_business_type(url, title, product_ld, sel, kwargs.get("business_type_hint"))

        desc = sel.css(".box-description *::text").getall()
        raw["description"] = clean_text(" ".join(desc)) or clean_text(product_ld.get("description"))

        raw["neighborhood"] = self._extract_neighborhood(title, url)

        raw["property_type"] = self._extract_property_type(url)

        features = detail_map.copy()
        amenities = [clean_text(text) for text in sel.css(".box-amenities p::text").getall()]
        amenities = [item for item in amenities if item]
        if amenities:
            features["amenidades"] = amenities

        raw["features"] = features

        # Extract structured fields
        raw["bedrooms"] = self._extract_feature(features, r'(quarto|dormitório|dormitorio)')
        raw["bathrooms"] = self._extract_feature(features, r'(banheiro|wc|banho)')
        raw["garage_spaces"] = self._extract_feature(features, r'(garagem|vaga|estacionamento)')
        raw["suites"] = self._extract_feature(features, r'(suite|suíte)')

        page_text = " ".join(sel.css("body *::text").getall())
        if raw["bedrooms"] is None:
            m = re.search(r'(\d+)\s*(?:quarto|quartos|dorm)', page_text, re.IGNORECASE)
            if m:
                raw["bedrooms"] = int(m.group(1))
        if raw["bathrooms"] is None:
            m = re.search(r'(\d+)\s*(?:banheiro|wc)', page_text, re.IGNORECASE)
            if m:
                raw["bathrooms"] = int(m.group(1))

        raw["total_area"] = self._get_detail_value(
            detail_map,
            ["área do terreno", "area do terreno", "área total", "area total"],
        )
        raw["built_area"] = self._get_detail_value(
            detail_map,
            ["área construída", "area construída", "area construida", "área útil", "area util"],
        )

        raw["condominium_fee"] = None

        images = []
        img_tags = sel.css(
            ".cards_digital_carousel img::attr(src), .gallery img::attr(src), .carousel img::attr(src), "
            ".slider img::attr(src), [class*='photo'] img::attr(src), "
            "[class*='foto'] img::attr(src), .property-images img::attr(src)"
        ).getall()
        seen_urls = set()
        for i, src in enumerate(img_tags):
            if src and src not in seen_urls and not src.endswith(("svg", "placeholder", "kenlo.svg")):
                seen_urls.add(src)
                if src.startswith("/"):
                    src = f"{self.base_url}{src}"
                images.append({"url": src, "position": i})
        raw["images"] = images

        return raw

    def _detect_business_type(
        self,
        url: str,
        title: Optional[str],
        product_ld: dict,
        sel: Selector,
        hint: Optional[str] = None,
    ) -> str:
        """
        Detect business type (venda/aluguel) from multiple signals.

        Priority (page content over hint, because hint comes from listing URL
        which may cross-list):
          1. Title / JSON-LD name (most reliable)
          2. Page content text (main body area, excluding footer/neighborhoods)
          3. Price pattern: "R$ X/mês" indicates rent, high values without /mês indicate sale
          4. Hint from listing page context (suggestion, not absolute)
          5. URL fallback (/a-venda/, /para-alugar/)
        """
        # 1. Title / JSON-LD name
        check_texts = [title or "", product_ld.get("name", "")]
        for t in check_texts:
            tl = t.lower()
            if "para alugar" in tl or "aluguel" in tl or "locação" in tl or "locacao" in tl:
                return "aluguel"
            if "à venda" in tl or "a venda" in tl:
                return "venda"

        # 2. Page content — description block (excludes footer noise)
        desc_text = " ".join(sel.css(".box-description *::text").getall()).lower()
        rent_score = sum(1 for w in ["para alugar", "aluguel", "alugar", "locação", "locacao"] if w in desc_text)
        sale_score = sum(1 for w in ["à venda", "a venda", "comprar", "vende-se"] if w in desc_text)
        if rent_score > sale_score:
            return "aluguel"
        if sale_score > rent_score:
            return "venda"

        # 3. Price pattern: "/mês" in title indicates rent

        # 3. Price pattern: "/mês" in title indicates rent
        full_title = title or ""
        if "r$" in full_title.lower():
            if "/mês" in full_title.lower() or "/mes" in full_title.lower():
                return "aluguel"

        # 4. Hint from listing page (suggestion, never overrides page signals).
        #    Only used when the opposing type has ZERO signals in the page text.
        if hint:
            if hint == "venda" and rent_score == 0:
                return "venda"
            if hint == "aluguel" and sale_score == 0:
                return "aluguel"

        # 4. URL fallback
        url_lower = url.lower()
        if "/a-venda/" in url_lower or "/venda/" in url_lower or "/comprar/" in url_lower:
            return "venda"
        if "/para-alugar/" in url_lower or "/alugar/" in url_lower or "/locacao/" in url_lower:
            return "aluguel"

        return ""

    def _extract_feature(self, features: dict, pattern: str) -> Optional[int]:
        """Extract numeric value from a feature by regex pattern on key."""
        for key, value in features.items():
            if isinstance(value, list):
                value = " ".join(value)
            if re.search(pattern, key, re.IGNORECASE):
                nums = re.findall(r'\d+', str(value))
                if nums:
                    return int(nums[0])
        return None

    def _extract_product_json_ld(self, sel: Selector) -> dict:
        for script in sel.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            if isinstance(data, dict) and data.get("@type") == "Product":
                return data
        return {}

    def _extract_detail_map(self, sel: Selector) -> dict[str, str]:
        labels = [clean_text(text) for text in sel.css(".item-info-title::text").getall()]
        values = [clean_text(text) for text in sel.css(".item-info-value::text").getall()]
        detail_map = {}
        for label, value in zip(labels, values):
            if label and value:
                detail_map[label.lower()] = value
        return detail_map

    def _get_detail_value(self, detail_map: dict[str, str], candidates: list[str]) -> Optional[str]:
        for candidate in candidates:
            value = detail_map.get(candidate)
            if value:
                return value
        return None

    def _extract_property_type(self, url: str) -> str:
        match = re.search(r'/imovel/([a-z-]+)-ji-parana', url)
        if not match:
            return ""
        return match.group(1).replace("-", " ")

    def _extract_neighborhood(self, title: Optional[str], url: str) -> Optional[str]:
        """
        Extract neighborhood from Kenlo title.

        Kenlo title formats:
          A) "{Type} {business}, {details} - {Neighborhood} - {City}/RO"
             Ex: "Salão para alugar, 115 m² por R$ 2.300 - Nova Brasília - Ji-Paraná/RO"
          B) "{Type} {other} - Bairro {Neighborhood} - {City}"
             Ex: "Terreno à venda, 1244 m² - Bairro Centro - Ji-Paraná"
          C) No neighborhood — just type + city:
             Ex: "Terreno de 40.000 m² Anel Viário - Ji-Paraná, à venda"
        """
        if not title:
            return None

        parts = title.split(" - ")
        if len(parts) < 2:
            return None

        # Candidate is the second segment (after first " - ")
        candidate = parts[1].strip()

        # "Bairro Centro" → "Centro"
        if candidate.lower().startswith("bairro "):
            return candidate[7:].strip()

        # Known city names or "city, price" patterns — not neighborhoods
        cand_lower = candidate.lower().strip(" ,./")

        # Reject if it starts with a known city name
        for city in ["ji-paraná", "ji-parana", "ji paraná", "ji parana",
                      "ouro preto do oeste", "vilhena", "pimenta bueno",
                      "cacoal", "presidente médici", "rolim de moura",
                      "porto velho"]:
            if cand_lower.startswith(city):
                return None

        # Reject if it contains price indicators (R$, à venda, por)
        if any(w in cand_lower for w in ["r$", "à venda", "a venda", "por r$"]):
            return None

        # Reject if very short
        if len(candidate) <= 3:
            return None

        return candidate

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Convert raw Porto Real data into normalized property dict."""
        try:
            title = raw_data.get("title")
            description = raw_data.get("description")
            neighborhood = normalize_neighborhood(raw_data.get("neighborhood"))

            business_type = raw_data.get("business_type", "")
            business_type = normalize_business_type(business_type) or "sale"

            property_type = normalize_property_type(
                raw_data.get("property_type") or title or ""
            )

            price = normalize_price(raw_data.get("price"))
            condominium_fee = normalize_price(raw_data.get("condominium_fee"))

            total_area = normalize_area(raw_data.get("total_area"))
            built_area = normalize_area(raw_data.get("built_area"))

            bedrooms = raw_data.get("bedrooms")
            bathrooms = raw_data.get("bathrooms")
            garage_spaces = raw_data.get("garage_spaces")
            suites = raw_data.get("suites")

            if bedrooms is None:
                bedrooms = extract_bedrooms(title) or extract_bedrooms(description)

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
                "source_property_id": raw_data["source_property_id"],
                "source_url": raw_data["url"],
                "business_type": business_type,
                "property_type": property_type,
                "title": title,
                "description": description,
                "price": price,
                "condominium_fee": condominium_fee,
                "iptu": None,
                "neighborhood": neighborhood,
                "address_text": None,
                "bedrooms": bedrooms,
                "suites": suites,
                "bathrooms": bathrooms,
                "garage_spaces": garage_spaces,
                "total_area": total_area,
                "built_area": built_area,
                "land_area": None,
                "published_at_source": None,
                "images": images,
                "content_hash": content_hash,
            }
        except Exception as e:
            logger.error("Failed to normalize PortoReal property: %s", e)
            return None
