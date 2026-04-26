"""
Scraper for City Imoveis (cityimoveis.imb.br).

Platform: Union (by Union Softwares).
SSR-based portal. URLs follow pattern /{business_type}/ro/ji-parana/{neighborhood}/{type}/{code}.
Uses httpx + Parsel.

Observations from site analysis (Apr 2026):
- Image CDN: cdnuso.com, cdn2.uso.com.br
- Listing URLs: /comprar/ro/ji-parana/jardim-presidencial/casa/77129890
- Business types: /comprar/ or /alugar/
- City/county: "ji-parana" in URL path
- Uses cookies consent modal
"""
import logging
import re
from typing import Optional
from uuid import UUID

import httpx
from parsel import Selector

from app.scrapers.base import BaseScraper, DEFAULT_HEADERS
from app.scrapers.registry import register_scraper
from app.services.normalize import (
    clean_text,
    normalize_price,
    normalize_business_type,
    normalize_property_type,
    extract_bedrooms,
    compute_content_hash,
)

logger = logging.getLogger(__name__)


@register_scraper("city")
class CityScraper(BaseScraper):
    """
    Scraper for City Imoveis (Union platform).
    """

    source_name = "City Imoveis"
    platform = "Union"

    def __init__(self, source_id: UUID, base_url: str = "https://cityimoveis.imb.br"):
        super().__init__(source_id, base_url)
        self._client_kwargs = {
            "timeout": 30,
            "follow_redirects": True,
            "headers": dict(DEFAULT_HEADERS),
        }

    async def scrape_listings(self) -> list[dict]:
        """
        Scrape property listings from City Imoveis (Union).

        Union uses SSR with structured URLs:
        /comprar/ro/ji-parana (all sales in Ji-Parana)
        /alugar/ro/ji-parana (all rentals in Ji-Parana)
        """
        results = []
        search_urls = [
            f"{self.base_url}/comprar/ro/ji-parana",
            f"{self.base_url}/alugar/ro/ji-parana",
        ]

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            for base_search_url in search_urls:
                page = 1
                while page <= 50:
                    url = f"{base_search_url}?pagina={page}" if page > 1 else base_search_url
                    logger.info("City: fetching page %d", page)

                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                    except httpx.HTTPError as e:
                        logger.warning("City page %d error: %s", page, e)
                        break

                    sel = Selector(resp.text)

                    # Union cards: links to /comprar/... or /alugar/... with codes
                    cards = sel.css("a[href*='/comprar/'], a[href*='/alugar/']")
                    if not cards:
                        cards = sel.css("div.imovel a, .property-item a, a[href*='/ro/ji-parana']")

                    page_items = []
                    for card in cards:
                        href = card.attrib.get("href", "")
                        if not href or "/ji-parana/" not in href:
                            continue

                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                        # Extract numeric ID from end of URL: .../77129890
                        code_match = re.search(r'/(\d+)/?$', href.rstrip("/"))
                        prop_id = code_match.group(1) if code_match else href.strip("/").split("/")[-1]

                        page_items.append({
                            "source_property_id": prop_id,
                            "url": full_url,
                        })

                    results.extend(page_items)
                    logger.info("City: found %d on page %d (total %d)",
                                len(page_items), page, len(results))

                    if not page_items:
                        break
                    page += 1

        seen = set()
        unique = []
        for item in results:
            if item["source_property_id"] not in seen:
                seen.add(item["source_property_id"])
                unique.append(item)

        logger.info("City: total unique listings: %d", len(unique))
        return unique

    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """Scrape a single property detail page from City Imoveis (Union)."""
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("City detail error %s: %s", url, e)
                html = await self._fetch_with_playwright(url)
                if html is None:
                    return None
                sel = Selector(html)
                return self._parse_detail(sel, source_property_id, url)

        sel = Selector(resp.text)
        return self._parse_detail(sel, source_property_id, url)

    def _parse_detail(self, sel: Selector, source_property_id: str, url: str) -> dict:
        """Parse City Imoveis detail page into raw data dict."""
        raw = {
            "source_property_id": source_property_id,
            "url": url,
        }

        title = sel.css("h1::text, .titulo-imovel::text").get("")
        raw["title"] = clean_text(title)

        price_text = sel.css(
            ".preco::text, .price::text, .valor::text, "
            "span:contains('R$')::text, strong:contains('R$')::text"
        ).get("")
        if not price_text:
            price_els = sel.css("*:contains('R$')::text").getall()
            for p in price_els:
                if re.search(r'R\$\s*[\d\s\.]+,\d{2}', p):
                    price_text = p
                    break
        raw["price"] = price_text

        raw["business_type"] = "venda" if "/comprar/" in url else ("aluguel" if "/alugar/" in url else "")

        desc = sel.css(
            ".descricao::text, .description::text, "
            "article p::text, #descricao p::text, "
            "[class*='descricao'] p::text"
        ).getall()
        raw["description"] = clean_text(" ".join(desc)) if desc else None

        # Extract neighborhood from breadcrumbs or URL
        neighborhood = sel.css(
            ".breadcrumb li:last-child::text, .bairro::text, "
            ".localizacao::text, [class*='bairro']::text"
        ).get("")
        if not neighborhood:
            # Try from URL: /comprar/ro/ji-parana/{neighborhood}/...
            url_parts = url.split("/")
            for i, part in enumerate(url_parts):
                if part == "ji-parana" and i + 1 < len(url_parts):
                    neighborhood = url_parts[i + 1].replace("-", " ").title()
                    break
        raw["neighborhood"] = clean_text(neighborhood) if neighborhood else None

        raw["property_type"] = title or ""

        # Extract structured fields from text blocks
        page_text = " ".join(sel.css("body *::text").getall()).lower()
        raw["bedrooms"] = None
        raw["bathrooms"] = None
        raw["garage_spaces"] = None
        raw["suites"] = None

        m = re.search(r'(\d+)\s*(?:dorm|quarto)', page_text)
        if m:
            raw["bedrooms"] = int(m.group(1))

        # Union often shows "3 Dorms." or "2 Vagas" in card text
        info_block = sel.css(".info-imovel::text, .detalhes::text, .card-text::text").getall()
        info_text = " ".join(info_block)
        if not raw["bedrooms"]:
            m = re.search(r'(\d+)\s*Dorms?', info_text, re.IGNORECASE)
            if m:
                raw["bedrooms"] = int(m.group(1))
        m = re.search(r'(\d+)\s*Vagas?', info_text, re.IGNORECASE)
        if m:
            raw["garage_spaces"] = int(m.group(1))

        # Area: "AC 200m²" or "Total: 300m²"
        area_match = re.search(r'(?:AC|Área|Area|Total)\s*:?\s*(\d+(?:[.,]\d+)?)\s*m²', page_text, re.IGNORECASE)
        if area_match:
            raw["total_area"] = area_match.group(1).replace(",", ".")

        # Images
        images = []
        img_tags = sel.css(
            ".gallery img::attr(src), img[src*='cdnuso.com']::attr(src), "
            "img[src*='cdn2.uso.com.br']::attr(src)"
        ).getall()
        seen = set()
        for i, src in enumerate(img_tags):
            if src and src not in seen:
                seen.add(src)
                images.append({"url": src, "position": i})
        raw["images"] = images

        return raw

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Convert raw City Imoveis data into normalized property dict."""
        try:
            title = raw_data.get("title")
            business_type = normalize_business_type(raw_data.get("business_type", "")) or "sale"
            property_type = normalize_property_type(raw_data.get("property_type") or title or "")
            price = normalize_price(raw_data.get("price"))
            total_area = normalize_price(raw_data.get("total_area")) if raw_data.get("total_area") else None

            total_area_float = float(total_area) if total_area else None

            bedrooms = raw_data.get("bedrooms") or extract_bedrooms(title)

            content_hash = compute_content_hash(
                price=price,
                title=title,
                description=raw_data.get("description"),
                neighborhood=raw_data.get("neighborhood"),
                bedrooms=bedrooms,
                bathrooms=raw_data.get("bathrooms"),
                garage_spaces=raw_data.get("garage_spaces"),
                total_area=total_area_float,
            )

            return {
                "source_property_id": raw_data["source_property_id"],
                "source_url": raw_data["url"],
                "business_type": business_type,
                "property_type": property_type,
                "title": title,
                "description": raw_data.get("description"),
                "price": price,
                "condominium_fee": None,
                "iptu": None,
                "neighborhood": raw_data.get("neighborhood"),
                "address_text": None,
                "bedrooms": bedrooms,
                "suites": raw_data.get("suites"),
                "bathrooms": raw_data.get("bathrooms"),
                "garage_spaces": raw_data.get("garage_spaces"),
                "total_area": total_area_float,
                "built_area": None,
                "land_area": None,
                "published_at_source": None,
                "images": raw_data.get("images", []),
                "content_hash": content_hash,
            }
        except Exception as e:
            logger.error("Failed to normalize City property: %s", e)
            return None
