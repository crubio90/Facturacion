from datetime import date, datetime, timezone
from decimal import Decimal
import json
import logging
from pathlib import Path
import re

from app.config import ScraperSettings
from app.schemas import ScrapedClient, ScrapedInvoice, ScrapeExecutionResult
from app.scrapers.base import (
    BaseFacturacionScraper,
    parse_chilean_date,
    parse_clp_amount,
)

logger = logging.getLogger(__name__)


class FacturacionClPlaywrightScraper(BaseFacturacionScraper):
    """Scraper Playwright configurable para el portal de facturacion.cl.

    Los selectores CSS/XPath se cargan desde `selectors.json` (o `selectors.example.json`)
    para facilitar su adaptación al módulo/sistema específico contratado en facturacion.cl.
    """

    def __init__(self, settings: ScraperSettings) -> None:
        self.settings = settings
        selectors_path = settings.resolve_selectors_file()
        with selectors_path.open("r", encoding="utf-8") as fh:
            self.selectors = json.load(fh)

    def _format_url(self, template: str) -> str:
        return template.format(
            base_url=self.settings.FACTURACION_BASE_URL.rstrip("/"),
            system_slug=self.settings.FACTURACION_SYSTEM_SLUG.strip("/"),
        )

    async def _capture_debug_screenshot(self, page, label: str) -> str | None:
        try:
            out_dir = Path(self.settings.DEBUG_SCREENSHOTS_DIR)
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = out_dir / f"{ts}_{label}.png"
            await page.screenshot(path=str(path), full_page=True)
            return str(path)
        except Exception:
            return None

    async def _detect_captcha_or_block(self, page) -> bool:
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            "iframe[src*='turnstile']",
            ".g-recaptcha",
            "#captcha",
        ]
        for sel in captcha_selectors:
            if await page.locator(sel).count() > 0:
                return True
        return False

    async def run(self) -> ScrapeExecutionResult:
        if not self.settings.FACTURACION_USERNAME or not self.settings.FACTURACION_PASSWORD:
            return ScrapeExecutionResult(
                mode="playwright",
                status="FAILED",
                log_summary="Credenciales de facturacion.cl no configuradas.",
                error_message=(
                    "Debes definir FACTURACION_USERNAME y FACTURACION_PASSWORD en .env "
                    "para ejecutar el modo playwright, o usar SCRAPER_MODE=mock para pruebas."
                ),
            )

        login_cfg = self.selectors["login"]
        ar_cfg = self.selectors["accounts_receivable"]
        login_url = self._format_url(login_cfg["url_template"])
        ar_url = self._format_url(ar_cfg["navigate_url_template"])

        clients_by_rut: dict[str, ScrapedClient] = {}
        pages_scraped = 0

        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.settings.FACTURACION_HEADLESS)
                context = await browser.new_context(
                    locale="es-CL",
                    timezone_id=self.settings.SCRAPE_TIMEZONE,
                )
                page = await context.new_page()
                page.set_default_timeout(self.settings.FACTURACION_TIMEOUT_MS)

                logger.info("Abriendo portal facturacion.cl: %s", login_url)
                await page.goto(login_url, wait_until="domcontentloaded")

                if await self._detect_captcha_or_block(page):
                    await self._capture_debug_screenshot(page, "captcha_detected")
                    await browser.close()
                    return ScrapeExecutionResult(
                        mode="playwright",
                        status="FAILED",
                        log_summary="Scraping detenido por verificación CAPTCHA en facturacion.cl.",
                        error_message=(
                            "Se detectó un desafío CAPTCHA o verificación anti-bot en el inicio de sesión "
                            "de facturacion.cl. Se abortó el proceso automáticamente."
                        ),
                    )

                await page.locator(login_cfg["username_selector"]).first.fill(
                    self.settings.FACTURACION_USERNAME
                )
                await page.locator(login_cfg["password_selector"]).first.fill(
                    self.settings.FACTURACION_PASSWORD
                )
                await page.locator(login_cfg["submit_selector"]).first.click()

                try:
                    await page.wait_for_selector(
                        login_cfg["logged_in_indicator"],
                        timeout=self.settings.FACTURACION_TIMEOUT_MS,
                    )
                except PlaywrightTimeoutError:
                    shot = await self._capture_debug_screenshot(page, "login_failed")
                    await browser.close()
                    return ScrapeExecutionResult(
                        mode="playwright",
                        status="FAILED",
                        log_summary="No se pudo confirmar inicio de sesión en facturacion.cl.",
                        error_message=(
                            "Tiempo de espera agotado tras enviar credenciales en facturacion.cl. "
                            f"Verifica usuario/clave y selectores. Captura: {shot or 'no disponible'}"
                        ),
                    )

                logger.info("Navegando a módulo Cuentas Corrientes / Por Cobrar: %s", ar_url)
                await page.goto(ar_url, wait_until="networkidle")

                max_pages = 50
                while pages_scraped < max_pages:
                    pages_scraped += 1
                    frame_selector = ar_cfg.get("frame_selector")
                    scope = page.frame_locator(frame_selector) if frame_selector else page
                    rows = scope.locator(ar_cfg["table_row_selector"])
                    row_count = await rows.count()

                    col_map = ar_cfg["columns"]
                    for idx in range(row_count):
                        cells = rows.nth(idx).locator("td")
                        cell_count = await cells.count()
                        if cell_count < 6:
                            continue

                        async def cell_text(col_key: str) -> str:
                            pos = col_map.get(col_key)
                            if pos is None or pos >= cell_count:
                                return ""
                            return (await cells.nth(pos).inner_text()).strip()

                        rut = (await cell_text("rut")).upper()
                        razon_social = await cell_text("razon_social")
                        folio_raw = re.sub(r"[^0-9]", "", await cell_text("folio"))
                        if not rut or not folio_raw:
                            continue

                        folio = int(folio_raw)
                        tipo_nombre = (await cell_text("tipo_dte_nombre")) or "Factura Electrónica"
                        tipo_dte = "34" if "exenta" in tipo_nombre.lower() else "33"

                        fecha_emision = parse_chilean_date(await cell_text("fecha_emision")) or date.today()
                        fecha_venc = parse_chilean_date(await cell_text("fecha_vencimiento")) or fecha_emision
                        monto_total = parse_clp_amount(await cell_text("monto_total"))
                        monto_pagado = parse_clp_amount(await cell_text("monto_pagado"))
                        saldo_raw = await cell_text("saldo_pendiente")
                        saldo = (
                            parse_clp_amount(saldo_raw)
                            if saldo_raw
                            else max(Decimal("0.00"), monto_total - monto_pagado)
                        )
                        estado_raw = (await cell_text("estado")).upper()

                        status = None
                        fecha_pago = None
                        if "PAGAD" in estado_raw or saldo == Decimal("0"):
                            status = "PAGADA"
                            fecha_pago = date.today()
                        elif "ANULAD" in estado_raw:
                            status = "ANULADA"

                        monto_neto = (monto_total / Decimal("1.19")).quantize(Decimal("1"))
                        monto_iva = monto_total - monto_neto

                        inv = ScrapedInvoice(
                            external_id=f"DTE-{tipo_dte}-{folio}",
                            tipo_dte=tipo_dte,
                            tipo_dte_nombre=tipo_nombre,
                            folio=folio,
                            fecha_emision=fecha_emision,
                            fecha_vencimiento=fecha_venc,
                            fecha_pago=fecha_pago,
                            monto_neto=monto_neto,
                            monto_iva=monto_iva,
                            monto_total=monto_total,
                            monto_pagado=monto_pagado,
                            saldo_pendiente=saldo,
                            status=status,
                            source_url=ar_url,
                            raw_metadata={"estado_portal": estado_raw},
                        )

                        if rut not in clients_by_rut:
                            clients_by_rut[rut] = ScrapedClient(
                                rut=rut,
                                razon_social=razon_social or rut,
                                invoices=[],
                            )
                        clients_by_rut[rut].invoices.append(inv)

                    next_sel = ar_cfg.get("next_page_selector")
                    if not next_sel:
                        break
                    next_btn = scope.locator(next_sel).first
                    if await next_btn.count() == 0 or not await next_btn.is_visible() or not await next_btn.is_enabled():
                        break
                    await next_btn.click()
                    await page.wait_for_load_state("networkidle")

                await browser.close()

            clients = list(clients_by_rut.values())
            total_inv = sum(len(c.invoices) for c in clients)
            return ScrapeExecutionResult(
                mode="playwright",
                status="SUCCESS",
                log_summary=(
                    f"Scraping facturacion.cl completado en {pages_scraped} página(s): "
                    f"{len(clients)} clientes y {total_inv} documentos extraídos."
                ),
                clients=clients,
            )

        except Exception as exc:
            logger.exception("Error ejecutando scraper Playwright en facturacion.cl: %s", exc)
            return ScrapeExecutionResult(
                mode="playwright",
                status="FAILED",
                log_summary="Error durante ejecución Playwright en facturacion.cl.",
                error_message=str(exc),
            )
