"""
Scraper for Arrimo Imoveis (arrimoimoveis.com.br).

Platform: Imonov (by Si9sistemas).
SSR-based portal. Listings at /filtro/list/..., detail pages at /imovel/....
Uses httpx + Parsel.
"""
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

LISTING_URLS = [
    "https://www.arrimoimoveis.com.br/filtro/list/venda/todos/todas/todos/0-10000000/todos/todos/1",
    "https://www.arrimoimoveis.com.br/filtro/list/locacao/todos/todas/todos/0-10000000/todos/todos/1",
]
DETAIL_URL_TPL = "https://www.arrimoimoveis.com.br/imovel/{}"


@register_scraper("arrimo")
class ArrimoScraper(BaseScraper):
    """
    Scraper for Arrimo Imoveis (Imonov platform).
    """

    source_name = "Arrimo Imoveis"
    platform = "Imonov"

    def __init__(self, source_id: UUID, base_url: str = "https://arrimoimoveis.com.br"):
        super().__init__(source_id, base_url)
        self._client_kwargs = self.build_client_kwargs()
        # Imonov detail URLs: /imovel/{business_type}/{category}/{city}/{neighborhood}/{slug}/{numeric_id}
        # e.g. /imovel/venda/casa/ji-parana-ro/urupa/casa-para-venda.../824950

    async def scrape_listings(self, page_offset: int = 0) -> list[dict]:
        """
        Scrape property listings from Arrimo Imoveis (Imonov).

        Imonov uses paginated SSR pages. We iterate through pages
        extracting property cards.

        Uses page_offset to rotate which pages are visited each cycle.
        """
        results = []

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            for base_url in LISTING_URLS:
                start_page = 1 + max(0, page_offset)
                end_page = start_page + settings.scrape_page_limit - 1
                for page in range(start_page, end_page + 1):
                    # Imonov pagination: last number in URL is page
                    url = re.sub(r'/\d+$', f"/{page}", base_url)
                    logger.info("Arrimo: fetching page %d", page)

                    try:
                        await self.polite_delay()
                        resp = await client.get(url)
                        resp.raise_for_status()
                    except httpx.HTTPError as e:
                        logger.warning("Arrimo page %d error: %s", page, e)
                        if getattr(e.response, "status_code", None) == 523:
                            logger.warning("Arrimo: external block detected (523), aborting cycle early")
                        break

                    sel = Selector(resp.text)

                    # Imonov cards: look for property links
                    cards = sel.css("a[href*='/imovel/']")
                    if not cards:
                        # Try alternative: divs with links
                        cards = sel.css("div.imovel-card a, .property-card a, a[href*='imovel']")

                    page_items = []
                    for card in cards:
                        href = card.attrib.get("href", "")
                        if not href or "/imovel/" not in href:
                            continue

                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                        # Extract numeric ID from the end of URL
                        # /imovel/venda/casa/.../824950  -> 824950
                        m = re.search(r'/(\d+)/?$', href.rstrip("/"))
                        if not m:
                            # Try slug as ID
                            slug_m = re.search(r'/imovel/(.+?)(?:/|$)', href)
                            if slug_m:
                                page_items.append({
                                    "source_property_id": slug_m.group(1).split("/")[-1],
                                    "url": full_url,
                                })
                            continue

                        prop_id = m.group(1)
                        page_items.append({
                            "source_property_id": prop_id,
                            "url": full_url,
                        })

                    results.extend(page_items)
                    logger.info("Arrimo: found %d items on page %d (total %d)",
                                len(page_items), page, len(results))

                    # Check if next page exists
                    next_btn = sel.css("a.next, a[rel='next'], a:has(.fa-chevron-right)")
                    if not next_btn and not page_items:
                        break

                    page += 1

        # Deduplicate
        seen = set()
        unique = []
        for item in results:
            if item["source_property_id"] not in seen:
                seen.add(item["source_property_id"])
                unique.append(item)

        limited = unique[: settings.scrape_max_detail_pages_per_cycle]
        logger.info(
            "Arrimo: offset=%d, unique=%d, processing=%d",
            page_offset,
            len(unique),
            len(limited),
        )
        return limited

    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """Scrape a single property detail page from Arrimo (Imonov)."""
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                await self.polite_delay()
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("Arrimo detail error %s: %s", url, e)
                html = await self._fetch_with_playwright(url)
                if html is None:
                    return None
                sel = Selector(html)
                return self._parse_detail(sel, source_property_id, url)

        sel = Selector(resp.text)
        return self._parse_detail(sel, source_property_id, url)

    def _parse_detail(self, sel: Selector, source_property_id: str, url: str) -> dict:
        """Parse Arrimo detail page HTML into raw data dict."""
        raw = {
            "source_property_id": source_property_id,
            "url": url,
        }

        # Business type from URL path: /imovel/venda/... or /imovel/locacao/...
        if "/locacao/" in url:
            raw["business_type"] = "aluguel"
        elif "/venda/" in url:
            raw["business_type"] = "venda"
        else:
            raw["business_type"] = ""

        # Title - Imonov typically has it in h1 or .titulo-imovel
        title = sel.css("h1::text, .titulo-imovel::text, .property-title::text, .imovel-titulo::text").get("")
        raw["title"] = clean_text(title)

        # Price - Imonov uses .preco or .valor
        price_text = sel.css(
            ".preco::text, .valor::text, .price::text, "
            "span.preco::text, strong.preco::text, "
            "[class*='preco']::text, [class*='valor']::text"
        ).get("")
        if not price_text:
            price_els = sel.css("*:contains('R$')::text").getall()
            for p in price_els:
                if re.search(r'R\$\s*[\d\s\.]+,\d{2}', p):
                    price_text = p
                    break
        raw["price"] = price_text

        # Description
        desc = sel.css(
            ".descricao::text, .description::text, "
            ".sobre p::text, #descricao p::text, "
            "[class*='descricao'] p::text"
        ).getall()
        raw["description"] = clean_text(" ".join(desc)) if desc else None

        # Neighborhood
        neighborhood = sel.css(
            ".bairro::text, .localizacao::text, .location::text, "
            "[class*='bairro']::text, [class*='local']::text"
        ).get("")
        raw["neighborhood"] = clean_text(neighborhood) if neighborhood else None

        # Property type from the URL
        type_from_url = re.search(r'/imovel/(?:venda|locacao)/([^/]+)', url)
        raw["property_type"] = type_from_url.group(1) if type_from_url else (title or "")

        # Features - Imonov shows in characteristic tables/grids
        features = {}
        feature_items = sel.css(
            ".caracteristicas li, .features li, "
            ".detalhes li, .property-details li, "
            ".info-imovel li, [class*='characteristic'] li, "
            ".info-grid li, .info-list li"
        )
        for item in feature_items:
            text_parts = item.css("::text").getall()
            combined = " ".join(t.strip() for t in text_parts if t.strip())
            if combined and ":" in combined:
                key, val = combined.split(":", 1)
                features[key.strip().lower()] = val.strip()
            elif combined:
                features[combined.lower()] = combined

        # Try labeled divs
        labels = sel.css("span.label::text, strong.label::text, .feature-label::text")
        values = sel.css("span.value::text, .feature-value::text")
        for label, value in zip(labels, values):
            lbl = label.strip().lower()
            val = value.strip()
            if lbl and val:
                features[lbl] = val

        raw["features"] = features

        # Extract structured fields
        raw["bedrooms"] = self._extract_numeric(features, r'(quarto|dormitório|dormitorio|dorm)')
        raw["bathrooms"] = self._extract_numeric(features, r'(banheiro|banho|wc)')
        raw["garage_spaces"] = self._extract_numeric(features, r'(garagem|vaga|estacionamento)')
        raw["suites"] = self._extract_numeric(features, r'(suite|suíte)')

        # Also from page text
        page_text = " ".join(sel.css("body *::text").getall()).lower()
        if raw["bedrooms"] is None:
            m = re.search(r'(\d+)\s*(?:quarto|quartos|dormitório)', page_text)
            if m:
                raw["bedrooms"] = int(m.group(1))
        if raw["bathrooms"] is None:
            m = re.search(r'(\d+)\s*(?:banheiro|banheiros)', page_text)
            if m:
                raw["bathrooms"] = int(m.group(1))

        # Areas
        raw["total_area"] = None
        raw["built_area"] = None
        for key, val in features.items():
            if any(w in key for w in ["área total", "area total", "area"]):
                raw["total_area"] = val
            elif any(w in key for w in ["área construída", "area construida", "útil"]):
                raw["built_area"] = val

        # Also search for m² in page text
        if raw["total_area"] is None:
            m2_matches = re.findall(r'(\d+(?:[.,]\d+)?)\s*m²', page_text)
            if m2_matches:
                raw["total_area"] = m2_matches[0]

        # Images - Imonov stores on si9dados3.com.br
        # Always filter by CDN domain; also try known gallery wrappers, data-src, etc.
        images = []
        img_tags = sel.css(
            "img[src*='si9dados3']::attr(src), "
            "img[data-src*='si9dados3']::attr(data-src), "
            ".gallery img::attr(src), .carousel img::attr(src), "
            ".fotos img::attr(src), .property-images img::attr(src), "
            "#galeria img::attr(src), [class*='foto'] img::attr(src)"
        ).getall()
        seen_urls = set()
        for src in img_tags:
            src = src.strip()
            if not src or src in seen_urls:
                continue
            if "si9dados3" not in src:
                continue
            seen_urls.add(src)
            images.append({"url": src, "position": len(images)})
        raw["images"] = images

        return raw

    def _extract_numeric(self, features: dict, pattern: str) -> Optional[int]:
        """Extract numeric value from features by key regex."""
        for key, value in features.items():
            if re.search(pattern, key, re.IGNORECASE):
                nums = re.findall(r'\d+', value)
                if nums:
                    return int(nums[0])
        return None

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Convert raw Arrimo data into normalized property dict."""
        try:
            title = raw_data.get("title")
            description = raw_data.get("description")
            neighborhood = raw_data.get("neighborhood")

            business_type = normalize_business_type(raw_data.get("business_type", ""))
            if not business_type:
                business_type = "sale"

            property_type = normalize_property_type(
                raw_data.get("property_type") or title or ""
            )

            price = normalize_price(raw_data.get("price"))
            total_area = normalize_area(str(raw_data.get("total_area", ""))) if raw_data.get("total_area") else None
            built_area = normalize_area(str(raw_data.get("built_area", ""))) if raw_data.get("built_area") else None

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
                "condominium_fee": None,
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
            logger.error("Failed to normalize Arrimo property: %s", e)
            return None
