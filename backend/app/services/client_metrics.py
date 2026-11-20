from datetime import date
from decimal import Decimal

from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.client import ClientSummary
from app.schemas.invoice import InvoiceRead


def compute_invoice_days_overdue(invoice: Invoice, today: date | None = None) -> int:
    ref = today or date.today()
    if invoice.status == InvoiceStatus.PAGADA.value or invoice.status == InvoiceStatus.ANULADA.value:
        return 0
    if invoice.saldo_pendiente <= Decimal("0"):
        return 0
    delta = (ref - invoice.fecha_vencimiento).days
    return max(0, delta)


def refresh_invoice_status(invoice: Invoice, today: date | None = None) -> str:
    ref = today or date.today()
    if invoice.status == InvoiceStatus.ANULADA.value:
        return InvoiceStatus.ANULADA.value
    if invoice.saldo_pendiente <= Decimal("0") or invoice.fecha_pago is not None:
        invoice.saldo_pendiente = Decimal("0.00")
        invoice.status = InvoiceStatus.PAGADA.value
    elif invoice.fecha_vencimiento < ref:
        invoice.status = InvoiceStatus.VENCIDA.value
    else:
        invoice.status = InvoiceStatus.PENDIENTE.value
    return invoice.status


def build_invoice_read(invoice: Invoice, client: Client | None = None) -> InvoiceRead:
    c = client or invoice.client
    return InvoiceRead(
        id=invoice.id,
        client_id=invoice.client_id,
        client_rut=c.rut if c else None,
        client_razon_social=c.razon_social if c else None,
        client_is_sales_risk=bool(c.is_sales_risk) if c else False,
        external_id=invoice.external_id,
        tipo_dte=invoice.tipo_dte,
        tipo_dte_nombre=invoice.tipo_dte_nombre,
        folio=invoice.folio,
        fecha_emision=invoice.fecha_emision,
        fecha_vencimiento=invoice.fecha_vencimiento,
        fecha_pago=invoice.fecha_pago,
        monto_neto=invoice.monto_neto,
        monto_iva=invoice.monto_iva,
        monto_total=invoice.monto_total,
        monto_pagado=invoice.monto_pagado,
        saldo_pendiente=invoice.saldo_pendiente,
        status=invoice.status,
        dias_mora=compute_invoice_days_overdue(invoice),
        source_url=invoice.source_url,
        last_synced_at=invoice.last_synced_at,
    )


def build_client_summary(client: Client, invoices: list[Invoice] | None = None) -> ClientSummary:
    inv_list = invoices if invoices is not None else list(client.invoices)
    today = date.today()

    total_por_cobrar = Decimal("0.00")
    total_vencido = Decimal("0.00")
    total_pagado = Decimal("0.00")
    pendientes_count = 0
    vencidas_count = 0
    pagadas_count = 0
    max_dias_mora = 0

    for inv in inv_list:
        if inv.status == InvoiceStatus.ANULADA.value:
            continue
        if inv.status == InvoiceStatus.PAGADA.value:
            pagadas_count += 1
            total_pagado += inv.monto_total
        else:
            total_por_cobrar += inv.saldo_pendiente
            dias = compute_invoice_days_overdue(inv, today)
            if inv.status == InvoiceStatus.VENCIDA.value or dias > 0:
                vencidas_count += 1
                total_vencido += inv.saldo_pendiente
                if dias > max_dias_mora:
                    max_dias_mora = dias
            else:
                pendientes_count += 1

    return ClientSummary(
        id=client.id,
        rut=client.rut,
        razon_social=client.razon_social,
        nombre_fantasia=client.nombre_fantasia,
        encargado_compras_nombre=client.encargado_compras_nombre,
        encargado_compras_email=client.encargado_compras_email,
        encargado_compras_telefono=client.encargado_compras_telefono,
        credito_limite=client.credito_limite,
        dias_credito=client.dias_credito,
        reminder_count=client.reminder_count,
        last_reminder_at=client.last_reminder_at,
        is_sales_risk=client.is_sales_risk,
        sales_risk_marked_at=client.sales_risk_marked_at,
        sales_risk_reason=client.sales_risk_reason,
        sale_restriction_status=client.sale_restriction_status,
        sale_restriction_note=client.sale_restriction_note,
        sale_restriction_updated_at=client.sale_restriction_updated_at,
        last_synced_at=client.last_synced_at,
        total_por_cobrar=total_por_cobrar,
        total_vencido=total_vencido,
        total_pagado=total_pagado,
        facturas_pendientes_count=pendientes_count,
        facturas_vencidas_count=vencidas_count,
        facturas_pagadas_count=pagadas_count,
        max_dias_mora=max_dias_mora,
    )
