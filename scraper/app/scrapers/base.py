from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
import re

from app.schemas import ScrapeExecutionResult


class BaseFacturacionScraper(ABC):
    @abstractmethod
    async def run(self) -> ScrapeExecutionResult:
        """Ejecuta la extracción de cuentas y facturas desde facturacion.cl."""


def parse_clp_amount(raw: str) -> Decimal:
    """Convierte montos en formato chileno (ej. '$ 1.250.000', '1.250.000,50') a Decimal."""
    if not raw:
        return Decimal("0.00")
    cleaned = raw.strip().replace("$", "").replace("CLP", "").replace(" ", "")
    if not cleaned or cleaned == "-":
        return Decimal("0.00")
    # En formato chileno '.' es separador de miles y ',' es decimal
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "." in cleaned:
        # Si los últimos 3 dígitos van tras punto (ej. 1.250.000), quitar separadores de miles
        parts = cleaned.split(".")
        if all(len(p) == 3 for p in parts[1:]):
            cleaned = "".join(parts)
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    if not cleaned or cleaned in ("-", "."):
        return Decimal("0.00")
    return Decimal(cleaned)


def parse_chilean_date(raw: str) -> date | None:
    """Convierte fechas en formato DD-MM-YYYY, DD/MM/YYYY o YYYY-MM-DD."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
