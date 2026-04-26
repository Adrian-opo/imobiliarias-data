"""
Normalization helpers for property data.

Parses raw text scraped from portals into structured values.
"""
import re
from typing import Optional


def clean_text(text: Optional[str]) -> Optional[str]:
    """Remove extra whitespace, newlines, and trim."""
    if not text:
        return None
    text = re.sub(r'\s+', ' ', text)
    stripped = text.strip()
    return stripped if stripped else None


def normalize_price(text: Optional[str]) -> Optional[float]:
    """
    Extract a numeric price from text like 'R$ 450.000,00' or '450000'.
    Returns value in BRL (float).
    """
    if not text:
        return None
    # Remove currency symbols and text
    text = text.replace('R$', '').replace('$', '').strip()
    # Remove leading non-numeric text (like "Valor:", "Preço:", etc.)
    text = re.sub(r'^[^\d]+', '', text).strip()
    if not text:
        return None
    # Handle Brazilian format: 1.234,56 -> 1234.56
    # First check if there's a comma (Brazilian centavo separator)
    if ',' in text:
        # Remove dots (thousand separators), replace comma with dot
        text = text.replace('.', '').replace(',', '.')
        try:
            return float(text)
        except (ValueError, TypeError):
            return None

    # No comma — could be US format (1234.56), or Brazilian without cents (1.234)
    # If there's a dot and more than 3 digits after it, it's a decimal
    dot_parts = text.split('.')
    if len(dot_parts) == 2 and len(dot_parts[1]) <= 2:
        # Likely a decimal like 1500.50
        text = re.sub(r'[^\d.]', '', text)
        try:
            return float(text)
        except (ValueError, TypeError):
            return None

    # Remove dots (thousands separators) entirely, parse as integer
    text = text.replace('.', '')
    text = re.sub(r'[^\d]', '', text)
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def normalize_area(text: Optional[str]) -> Optional[float]:
    """
    Extract area in m² from text like '150 m²' or '150'.
    """
    if not text:
        return None
    # Try to find number before m², m2, mt, etc.
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:m[²2]|mts?|metros?\s*quadrados?)', text, re.IGNORECASE)
    if m:
        val_str = m.group(1).replace(',', '.')
        try:
            return float(val_str)
        except ValueError:
            pass
    # Fallback: just try to extract a number
    numbers = re.findall(r'\d+(?:[.,]\d+)?', text)
    if numbers:
        try:
            return float(numbers[0].replace(',', '.'))
        except ValueError:
            pass
    return None


def normalize_business_type(text: Optional[str]) -> Optional[str]:
    """
    Normalize to 'sale' or 'rent' from Portuguese text.
    """
    if not text:
        return None
    text = text.lower().strip()
    if any(w in text for w in ['venda', 'comprar', 'vende', 'compra', 'sale']):
        return 'sale'
    if any(w in text for w in ['aluguel', 'alugar', 'locação', 'locacao', 'rent']):
        return 'rent'
    return None


def normalize_property_type(text: Optional[str]) -> str:
    """
    Map Portuguese property type strings to canonical types.

    Uses two strategies:
    1. Checks if the full text contains any known type keyword
    2. As fallback, checks if the first word of the text matches a type
    """
    if not text:
        return 'outro'
    text = text.lower().strip()

    mapping = {
        'casa': 'casa',
        'apartamento': 'apartamento',
        'apto': 'apartamento',
        'terreno': 'terreno',
        'lote': 'terreno',
        'loteamento': 'terreno',
        'sobrado': 'sobrado',
        'comercial': 'comercial',
        'ponto comercial': 'comercial',
        'loja': 'comercial',
        'sala': 'sala',
        'barracão': 'barracao',
        'barracao': 'barracao',
        'galpão': 'barracao',
        'galpao': 'barracao',
        'chácara': 'chacara',
        'chacara': 'chacara',
        'sítio': 'sitio',
        'sitio': 'sitio',
        'fazenda': 'fazenda',
    }
    # Strategy 1: full text contains keyword
    for key, val in sorted(mapping.items(), key=lambda x: -len(x[0])):
        if key in text:
            return val
    # Strategy 2: first word matches a keyword
    first_word = text.split()[0] if text.split() else ''
    if first_word in mapping:
        return mapping[first_word]
    return 'outro'


def normalize_neighborhood(text: Optional[str]) -> Optional[str]:
    """
    Clean and normalize neighborhood/location text.

    - Removes 'Bairro:' prefix
    - Removes trailing district/city info
    - Capitalizes properly (first letter uppercase, rest lowercase, 'de'/'da'/'do' lowercase)
    - Strips whitespace
    """
    if not text:
        return None
    text = text.strip()
    # Remove "Bairro:" prefix
    text = re.sub(r'^Bairro:\s*', '', text, flags=re.IGNORECASE)
    # Remove leading "em " if present
    text = re.sub(r'^em\s+', '', text, flags=re.IGNORECASE)
    # Remove leading article if followed by uppercase word
    text = re.sub(r'^[ao]\s+', '', text, flags=re.IGNORECASE)
    # Remove " - Xº Distrito" (with hyphen) OR " Xº Distrito" (without hyphen)
    text = re.sub(r'\s*-?\s*\d+[º°]\s*Distrito.*', '', text, flags=re.IGNORECASE)
    # Remove trailing " - CityName"
    text = re.sub(r'\s*-\s*[A-Za-zÀ-ÿ-]+\s*$', '', text)
    text = text.strip()
    if not text or len(text) < 3:
        return None

    # Manual title case (keep articles/prepositions lowercase)
    words = text.split()
    lower_words = {"de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos", "e", "a", "o"}
    result = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in lower_words:
            result.append(w[0].upper() + w[1:].lower() if len(w) > 1 else w.upper())
        else:
            result.append(w.lower())
    return " ".join(result)


def extract_bedrooms(text: Optional[str]) -> Optional[int]:
    """
    Extract number of bedrooms from description or title text.
    """
    if not text:
        return None
    patterns = [
        r'(\d+)\s*(?:quarto|quartos|dormitórios?|dormitorios?|suítes?|suites?|bedroom)',
        r'(\d+)\s*quartos',
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None


def compute_content_hash(
    price: Optional[float],
    title: Optional[str],
    description: Optional[str],
    neighborhood: Optional[str],
    bedrooms: Optional[int],
    bathrooms: Optional[int],
    garage_spaces: Optional[int],
    total_area: Optional[float],
) -> str:
    """Compute SHA-256 hash of key fields for change detection."""
    import hashlib
    raw = '|'.join(str(v) for v in [
        price, title, description, neighborhood,
        bedrooms, bathrooms, garage_spaces, total_area,
    ])
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()
