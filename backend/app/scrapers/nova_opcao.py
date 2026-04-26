"""
Scraper for Imobiliaria Nova Opcao (imobiliarianovaopcao.com.br).

Platform: Apre.me.
SSR-based portal. Listings at /imoveis/..., detail pages at /vende-se-... or slug URLs.
Uses httpx + Parsel for SSR content.

Observations from site analysis (Apr 2026):
- Image CDN: img.apre.me
- Listing URLs are SEO-friendly slugs: /vende-se-casa-no-bairro-terra-nova
- Property codes appear as "825 (726) 188821" format (compound code)
- Pagination via numbered page links
- Filter URLs: /imoveis/{category}/{business_type}/{detail}
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
    normalize_area,
    normalize_business_type,
    normalize_property_type,
    extract_bedrooms,
    compute_content_hash,
)

logger = logging.getLogger(__name__)

BUSINESS_URLS = [
    ("sale", "https://imobiliarianovaopcao.com.br/imoveis/venda"),
    ("rent", "https://imobiliarianovaopcao.com.br/imoveis/aluguel"),
]


@register_scraper("nova_opcao")
class NovaOpcaoScraper(BaseScraper):
    """
    Scraper for Imobiliaria Nova Opcao (Apre.me platform).

    Status: ✅ Diagnosticado — plataforma Apre.me confirmada.
    TODO: scrape_listings() e scrape_detail() precisam de implementação
    refinada após validação com scraper ao vivo (seletores Apre.me específicos).
    """

    source_name = "Nova Opcao Imoveis"
    platform = "Apre.me"

    def __init__(self, source_id: UUID, base_url: str = "https://imobiliarianovaopcao.com.br"):
        super().__init__(source_id, base_url)
        self._client_kwargs = {
            "timeout": 30,
            "follow_redirects": True,
            "headers": dict(DEFAULT_HEADERS),
        }

    async def scrape_listings(self) -> list[dict]:
        """
        Scrape property listings from Nova Opcao.

        Apre.me platform uses SSR with SEO-friendly slugs.
        We iterate through paginated business type pages.
        """
        results = []

        async with httpx.AsyncClient(**self._client_kwargs) as client:
            for business_type, base_url in BUSINESS_URLS:
                page = 1
                while page <= 50:
                    url = f"{base_url}?pagina={page}" if page > 1 else base_url
                    logger.info("NovaOpcao: fetching %s page %d", business_type, page)

                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                    except httpx.HTTPError as e:
                        logger.warning("NovaOpcao page %d error: %s", page, e)
                        break

                    sel = Selector(resp.text)

                    # Apre.me cards: links with href="/vende-se-..." or "/aluga-se-..."
                    cards = sel.css("a[href*='/vende-se'], a[href*='/aluga-se'], a[href*='/imovel']")
                    if not cards:
                        cards = sel.css("div.imovel-card a, .property-item a")

                    page_items = []
                    for card in cards:
                        href = card.attrib.get("href", "")
                        if not href:
                            continue

                        # Extract property identifier from slug
                        slug = href.strip("/").split("/")[-1] if href else ""
                        if not slug:
                            continue

                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"

                        # Try to extract a property code from the card text
                        code = slug  # fallback: use slug as ID
                        code_el = card.css(".codigo::text, .ref::text, span:contains('Código')::text").get("")
                        if code_el:
                            code_match = re.search(r'(\d+)', code_el)
                            if code_match:
                                code = code_match.group(1)

                        page_items.append({
                            "source_property_id": code,
                            "url": full_url,
                        })

                    results.extend(page_items)
                    logger.info("NovaOpcao: found %d on page %d (total %d)",
                                len(page_items), page, len(results))

                    # Check for next page
                    next_btn = sel.css("a.next, a[rel='next'], a:has(.fa-chevron-right), .pagination a:last-child")
                    has_next = False
                    if next_btn:
                        next_href = next_btn[0].attrib.get("href", "")
                        if next_href and page < int(re.search(r'pagina=(\d+)', next_href).group(1) if re.search(r'pagina=(\d+)', next_href) else "0"):
                            has_next = True
                    if not has_next and not page_items:
                        break

                    page += 1

        # Deduplicate
        seen = set()
        unique = []
        for item in results:
            if item["source_property_id"] not in seen:
                seen.add(item["source_property_id"])
                unique.append(item)

        logger.info("NovaOpcao: total unique listings: %d", len(unique))
        return unique

    async def scrape_detail(self, source_property_id: str, url: str) -> Optional[dict]:
        """Scrape a single property detail page from Nova Opcao (Apre.me)."""
        async with httpx.AsyncClient(**self._client_kwargs) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                logger.error("NovaOpcao detail error %s: %s", url, e)
                html = await self._fetch_with_playwright(url)
                if html is None:
                    return None
                sel = Selector(html)
                return self._parse_detail(sel, source_property_id, url)

        sel = Selector(resp.text)
        return self._parse_detail(sel, source_property_id, url)

    def _parse_detail(self, sel: Selector, source_property_id: str, url: str) -> dict:
        """Parse Nova Opcao detail page into raw data dict."""
        raw = {
            "source_property_id": source_property_id,
            "url": url,
        }

        title = sel.css("h1::text, .titulo-imovel::text").get("")
        raw["title"] = clean_text(title)

        price_text = sel.css(
            ".preco::text, .valor::text, .price::text, "
            "span:contains('R$')::text, [class*='preco']::text"
        ).get("")
        if not price_text:
            price_els = sel.css("*:contains('R$')::text").getall()
            for p in price_els:
                if re.search(r'R\$\s*[\d\s\.]+,\d{2}', p):
                    price_text = p
                    break
        raw["price"] = price_text

        raw["business_type"] = "venda" if "/venda" in url else ("aluguel" if "/aluguel" in url else "")

        desc = sel.css(
            ".descricao::text, .description::text, "
            "article p::text, [class*='descricao'] p::text"
        ).getall()
        raw["description"] = clean_text(" ".join(desc)) if desc else None

        neighborhood = sel.css(
            ".bairro::text, .localizacao::text, .location::text"
        ).get("")
        raw["neighborhood"] = clean_text(neighborhood) if neighborhood else None

        raw["property_type"] = title or ""

        # Apre.me feature extraction from various label/value patterns
        features = {}
        for item in sel.css("li, .detail-item, .info-item, [class*='feature']"):
            text = " ".join(item.css("::text").getall()).strip()
            if ":" in text:
                k, v = text.split(":", 1)
                features[k.strip().lower()] = v.strip()
            elif text and re.match(r'^\d+\s*(Dorm|Quart|Banh|Vaga|Suite)', text, re.IGNORECASE):
                m = re.match(r'(\d+)\s*(.+)', text)
                if m:
                    features[m.group(2).strip().lower()] = m.group(1)

        raw["features"] = features
        raw["bedrooms"] = self._extract_numeric(features, r'(quarto|dorm)')
        raw["bathrooms"] = self._extract_numeric(features, r'(banheiro|banho)')
        raw["garage_spaces"] = self._extract_numeric(features, r'(garagem|vaga)')
        raw["suites"] = self._extract_numeric(features, r'(suite)')

        # Images
        images = []
        img_tags = sel.css(
            ".gallery img::attr(src), img[src*='apre.me']::attr(src), "
            "img[src*='img.apre.me']::attr(src)"
        ).getall()
        seen = set()
        for i, src in enumerate(img_tags):
            if src and src not in seen:
                seen.add(src)
                images.append({"url": src, "position": i})
        raw["images"] = images

        return raw

    def _extract_numeric(self, features: dict, pattern: str) -> Optional[int]:
        for key, value in features.items():
            if re.search(pattern, key, re.IGNORECASE):
                nums = re.findall(r'\d+', value)
                if nums:
                    return int(nums[0])
        return None

    def normalize(self, raw_data: dict) -> Optional[dict]:
        """Convert raw Nova Opcao data into normalized property dict."""
        try:
            title = raw_data.get("title")
            business_type = normalize_business_type(raw_data.get("business_type", "")) or "sale"
            property_type = normalize_property_type(raw_data.get("property_type") or title or "")
            price = normalize_price(raw_data.get("price"))
            bedrooms = raw_data.get("bedrooms") or extract_bedrooms(title)

            content_hash = compute_content_hash(
                price=price,
                title=title,
                description=raw_data.get("description"),
                neighborhood=raw_data.get("neighborhood"),
                bedrooms=bedrooms,
                bathrooms=raw_data.get("bathrooms"),
                garage_spaces=raw_data.get("garage_spaces"),
                total_area=None,
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
                "total_area": None,
                "built_area": None,
                "land_area": None,
                "published_at_source": None,
                "images": raw_data.get("images", []),
                "content_hash": content_hash,
            }
        except Exception as e:
            logger.error("Failed to normalize NovaOpcao property: %s", e)
            return None
