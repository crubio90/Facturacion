import asyncio
from datetime import date
from decimal import Decimal

from app.scrapers.base import parse_chilean_date, parse_clp_amount
from app.scrapers.mock_scraper import MockFacturacionScraper


def test_parse_clp_amount():
    assert parse_clp_amount("$ 1.250.000") == Decimal("1250000")
    assert parse_clp_amount("CLP 918.600") == Decimal("918600")
    assert parse_clp_amount("1.250.000,50") == Decimal("1250000.50")
    assert parse_clp_amount("-") == Decimal("0.00")


def test_parse_chilean_date():
    assert parse_chilean_date("15-10-2026") == date(2026, 10, 15)
    assert parse_chilean_date("05/11/2026") == date(2026, 11, 5)
    assert parse_chilean_date("2026-11-19") == date(2026, 11, 19)
    assert parse_chilean_date("") is None


def test_mock_scraper_returns_realistic_daberusa_clients():
    scraper = MockFacturacionScraper()
    result = asyncio.run(scraper.run())
    assert result.status == "SUCCESS"
    assert result.mode == "mock"
    assert len(result.clients) >= 5
    all_invoices = [inv for c in result.clients for inv in c.invoices]
    assert len(all_invoices) >= 10
    assert any(inv.fecha_vencimiento < date.today() and inv.saldo_pendiente > 0 for inv in all_invoices)
    assert any(inv.fecha_pago is not None for inv in all_invoices)
