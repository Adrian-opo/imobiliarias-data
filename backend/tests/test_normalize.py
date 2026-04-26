"""
Unit tests for normalize.py helpers.

Tests cover:
- clean_text
- normalize_price (BRL format)
- normalize_area (m² parsing)
- normalize_business_type
- normalize_property_type
- extract_bedrooms
- compute_content_hash
"""
import pytest
from app.services.normalize import (
    clean_text,
    normalize_price,
    normalize_area,
    normalize_business_type,
    normalize_property_type,
    extract_bedrooms,
    compute_content_hash,
)


class TestCleanText:
    def test_removes_extra_whitespace(self):
        assert clean_text("  Casa  com  3 quartos  ") == "Casa com 3 quartos"

    def test_removes_newlines(self):
        assert clean_text("Casa\ncom\n3\nquartos") == "Casa com 3 quartos"

    def test_returns_none_for_none(self):
        assert clean_text(None) is None

    def test_returns_none_for_empty(self):
        assert clean_text("") is None

    def test_returns_none_for_whitespace(self):
        assert clean_text("   ") is None


class TestNormalizePrice:
    def test_brazilian_format_with_cents(self):
        assert normalize_price("R$ 450.000,00") == 450000.00

    def test_brazilian_format_thousands(self):
        assert normalize_price("R$ 1.200.000,00") == 1200000.00

    def test_simple_number(self):
        assert normalize_price("450000") == 450000.0

    def test_with_currency_symbol(self):
        assert normalize_price("R$ 250.000") == 250000.0

    def test_with_text(self):
        assert normalize_price("Valor: R$ 180.000,00") == 180000.00

    def test_rental_price(self):
        assert normalize_price("R$ 2.500,00") == 2500.00

    def test_none_input(self):
        assert normalize_price(None) is None

    def test_empty_input(self):
        assert normalize_price("") is None

    def test_invalid_input(self):
        assert normalize_price("Consultar") is None

    def test_dot_decimal(self):
        assert normalize_price("1500.50") == 1500.50


class TestNormalizeArea:
    def test_with_m2_suffix(self):
        assert normalize_area("150 m²") == 150.0

    def test_with_mt_suffix(self):
        assert normalize_area("200 mt") == 200.0

    def test_with_metros_quadrados(self):
        assert normalize_area("150 metros quadrados") == 150.0

    def test_decimal_area(self):
        assert normalize_area("150,5 m²") == 150.5

    def test_bare_number(self):
        assert normalize_area("300") == 300.0

    def test_none_input(self):
        assert normalize_area(None) is None

    def test_empty_input(self):
        assert normalize_area("") is None

    def test_non_matching_text(self):
        assert normalize_area("Casa grande") is None


class TestNormalizeBusinessType:
    def test_venda(self):
        assert normalize_business_type("Venda") == "sale"

    def test_comprar(self):
        assert normalize_business_type("Comprar") == "sale"

    def test_aluguel(self):
        assert normalize_business_type("Aluguel") == "rent"

    def test_alugar(self):
        assert normalize_business_type("Alugar") == "rent"

    def test_locacao(self):
        assert normalize_business_type("Locação") == "rent"

    def test_none_input(self):
        assert normalize_business_type(None) is None

    def test_empty_input(self):
        assert normalize_business_type("") is None

    def test_unknown(self):
        assert normalize_business_type("Troca") is None


class TestNormalizePropertyType:
    def test_casa(self):
        assert normalize_property_type("Casa") == "casa"

    def test_apartamento(self):
        assert normalize_property_type("Apartamento") == "apartamento"

    def test_apto(self):
        assert normalize_property_type("Apto") == "apartamento"

    def test_terreno(self):
        assert normalize_property_type("Terreno") == "terreno"

    def test_lote(self):
        assert normalize_property_type("Lote") == "terreno"

    def test_sobrado(self):
        assert normalize_property_type("Sobrado") == "sobrado"

    def test_comercial(self):
        assert normalize_property_type("Comercial") == "comercial"

    def test_loja(self):
        assert normalize_property_type("Loja") == "comercial"

    def test_sala(self):
        assert normalize_property_type("Sala") == "sala"

    def test_barracao(self):
        assert normalize_property_type("Barracão") == "barracao"

    def test_galpao(self):
        assert normalize_property_type("Galpão") == "barracao"

    def test_chacara(self):
        assert normalize_property_type("Chácara") == "chacara"

    def test_sitio(self):
        assert normalize_property_type("Sítio") == "sitio"

    def test_fazenda(self):
        assert normalize_property_type("Fazenda") == "fazenda"

    def test_fallback_to_outro(self):
        assert normalize_property_type("Castelo") == "outro"

    def test_none_fallback(self):
        assert normalize_property_type(None) == "outro"


class TestExtractBedrooms:
    def test_extract_quartos(self):
        assert extract_bedrooms("Casa 3 quartos") == 3

    def test_extract_dormitorios(self):
        assert extract_bedrooms("Apartamento 2 dormitórios") == 2

    def test_extract_suites(self):
        assert extract_bedrooms("Casa com 2 suítes") == 2

    def test_extract_bedrooms(self):
        assert extract_bedrooms("House 4 bedrooms") == 4

    def test_none_input(self):
        assert extract_bedrooms(None) is None

    def test_no_match(self):
        assert extract_bedrooms("Casa à venda") is None

    def test_multiple_numbers(self):
        # Should pick the first match
        result = extract_bedrooms("3 quartos, 2 banheiros")
        assert result == 3


class TestComputeContentHash:
    def test_consistent_hash(self):
        h1 = compute_content_hash(100000.0, "Casa", "Desc", "Centro", 3, 2, 1, 150.0)
        h2 = compute_content_hash(100000.0, "Casa", "Desc", "Centro", 3, 2, 1, 150.0)
        assert h1 == h2
        assert isinstance(h1, str)
        assert len(h1) == 64  # SHA-256 hex

    def test_different_hash_for_different_values(self):
        h1 = compute_content_hash(100000.0, "Casa", "Desc", "Centro", 3, 2, 1, 150.0)
        h2 = compute_content_hash(200000.0, "Casa", "Desc", "Centro", 3, 2, 1, 150.0)
        assert h1 != h2

    def test_handles_none_values(self):
        h = compute_content_hash(None, None, None, None, None, None, None, None)
        assert isinstance(h, str)
        assert len(h) == 64
