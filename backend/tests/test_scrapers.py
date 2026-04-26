"""
Test scraper registry and base scraper structure.

Verifies that all registered scrapers have the correct interface.
"""
from app.scrapers.registry import get_all_scrapers, get_scraper
from app.scrapers.base import BaseScraper


def test_all_scrapers_registered():
    """All 6 scrapers should be in the registry."""
    scrapers = get_all_scrapers()
    expected = {"jardins", "porto_real", "arrimo", "nova_opcao", "city"}
    registered = set(scrapers.keys())
    assert expected.issubset(registered), f"Missing scrapers: {expected - registered}"


def test_each_scraper_has_correct_interface():
    """Each scraper should be a BaseScraper subclass with required attributes."""
    scrapers = get_all_scrapers()
    for name, cls in scrapers.items():
        assert issubclass(cls, BaseScraper), f"{name} is not a BaseScraper subclass"
        assert hasattr(cls, 'source_name'), f"{name} missing source_name"
        assert hasattr(cls, 'platform'), f"{name} missing platform"
        assert cls.source_name, f"{name} has empty source_name"
        assert cls.platform, f"{name} has empty platform"


def test_platforms_are_known():
    """All platforms should be one of the known ones."""
    known_platforms = {"Imobzi", "Kenlo", "Imonov", "Apre.me", "Union"}
    scrapers = get_all_scrapers()
    for name, cls in scrapers.items():
        assert cls.platform in known_platforms, (
            f"{name} has unknown platform: {cls.platform}"
        )


def test_scraper_registry_lookup():
    """Test that get_scraper finds registered scrapers."""
    assert get_scraper("jardins") is not None
    assert get_scraper("porto_real") is not None
    assert get_scraper("arrimo") is not None
    assert get_scraper("nova_opcao") is not None
    assert get_scraper("city") is not None
    assert get_scraper("nonexistent") is None


def test_jardins_platform():
    """Jardins should be Imobzi."""
    cls = get_scraper("jardins")
    assert cls.platform == "Imobzi"


def test_porto_real_platform():
    """Porto Real should be Kenlo."""
    cls = get_scraper("porto_real")
    assert cls.platform == "Kenlo"


def test_arrimo_platform():
    """Arrimo should be Imonov."""
    cls = get_scraper("arrimo")
    assert cls.platform == "Imonov"


def test_nova_opcao_platform():
    """Nova Opcao should be Apre.me."""
    cls = get_scraper("nova_opcao")
    assert cls.platform == "Apre.me"


def test_city_platform():
    """City Imoveis should be Union."""
    cls = get_scraper("city")
    assert cls.platform == "Union"
