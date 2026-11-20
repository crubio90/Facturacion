from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus
from app.models.scrape_job import ScrapeJob, ScrapeStatus
from app.schemas.scrape import SyncIngestPayload
from app.services.client_metrics import refresh_invoice_status


def normalize_rut(rut: str) -> str:
    cleaned = rut.strip().upper().replace(" ", "")
    return cleaned


def ingest_scrape_payload(db: Session, payload: SyncIngestPayload) -> ScrapeJob:
    now = datetime.now(timezone.utc)
    today = date.today()

    job: ScrapeJob | None = None
    if payload.job_id is not None:
        job = db.get(ScrapeJob, payload.job_id)

    if job is None:
        job = ScrapeJob(
            trigger_type=payload.trigger_type,
            mode=payload.mode,
            status=ScrapeStatus.RUNNING.value,
            started_at=now,
        )
        db.add(job)
        db.flush()

    if payload.status == ScrapeStatus.FAILED.value:
        job.status = ScrapeStatus.FAILED.value
        job.finished_at = now
        job.error_message = payload.error_message or "Error desconocido en proceso de webscraping."
        job.log_summary = payload.log_summary
        db.commit()
        db.refresh(job)
        return job

    clients_processed = 0
    invoices_created = 0
    invoices_updated = 0
    overdue_detected = 0

    for c_in in payload.clients:
        rut = normalize_rut(c_in.rut)
        client = db.scalar(select(Client).where(Client.rut == rut))
        if client is None:
            client = Client(
                rut=rut,
                razon_social=c_in.razon_social.strip(),
                nombre_fantasia=c_in.nombre_fantasia,
                encargado_compras_nombre=c_in.encargado_compras_nombre,
                encargado_compras_email=c_in.encargado_compras_email,
                encargado_compras_telefono=c_in.encargado_compras_telefono,
                credito_limite=c_in.credito_limite if c_in.credito_limite is not None else Decimal("0.00"),
                dias_credito=c_in.dias_credito if c_in.dias_credito is not None else 30,
                last_synced_at=now,
            )
            db.add(client)
            db.flush()
        else:
            client.razon_social = c_in.razon_social.strip()
            if c_in.nombre_fantasia:
                client.nombre_fantasia = c_in.nombre_fantasia
            # Preservar contacto editado manualmente si facturacion.cl no trae uno
            if c_in.encargado_compras_nombre and not client.encargado_compras_nombre:
                client.encargado_compras_nombre = c_in.encargado_compras_nombre
            if c_in.encargado_compras_email and not client.encargado_compras_email:
                client.encargado_compras_email = c_in.encargado_compras_email
            if c_in.encargado_compras_telefono and not client.encargado_compras_telefono:
                client.encargado_compras_telefono = c_in.encargado_compras_telefono
            if c_in.credito_limite is not None and client.credito_limite == Decimal("0.00"):
                client.credito_limite = c_in.credito_limite
            if c_in.dias_credito is not None:
                client.dias_credito = c_in.dias_credito
            client.last_synced_at = now

        clients_processed += 1

        for inv_in in c_in.invoices:
            saldo = (
                inv_in.saldo_pendiente
                if inv_in.saldo_pendiente is not None
                else max(Decimal("0.00"), inv_in.monto_total - inv_in.monto_pagado)
            )
            existing = db.scalar(select(Invoice).where(Invoice.external_id == inv_in.external_id))
            if existing is None:
                inv = Invoice(
                    client_id=client.id,
                    external_id=inv_in.external_id,
                    tipo_dte=inv_in.tipo_dte,
                    tipo_dte_nombre=inv_in.tipo_dte_nombre,
                    folio=inv_in.folio,
                    fecha_emision=inv_in.fecha_emision,
                    fecha_vencimiento=inv_in.fecha_vencimiento,
                    fecha_pago=inv_in.fecha_pago,
                    monto_neto=inv_in.monto_neto,
                    monto_iva=inv_in.monto_iva,
                    monto_total=inv_in.monto_total,
                    monto_pagado=inv_in.monto_pagado,
                    saldo_pendiente=saldo,
                    status=inv_in.status or InvoiceStatus.PENDIENTE.value,
                    source_url=inv_in.source_url,
                    raw_metadata=inv_in.raw_metadata,
                    last_synced_at=now,
                )
                refresh_invoice_status(inv, today)
                db.add(inv)
                invoices_created += 1
                if inv.status == InvoiceStatus.VENCIDA.value:
                    overdue_detected += 1
            else:
                existing.client_id = client.id
                existing.tipo_dte = inv_in.tipo_dte
                existing.tipo_dte_nombre = inv_in.tipo_dte_nombre
                existing.folio = inv_in.folio
                existing.fecha_emision = inv_in.fecha_emision
                existing.fecha_vencimiento = inv_in.fecha_vencimiento
                existing.fecha_pago = inv_in.fecha_pago
                existing.monto_neto = inv_in.monto_neto
                existing.monto_iva = inv_in.monto_iva
                existing.monto_total = inv_in.monto_total
                existing.monto_pagado = inv_in.monto_pagado
                existing.saldo_pendiente = saldo
                if inv_in.status == InvoiceStatus.ANULADA.value:
                    existing.status = InvoiceStatus.ANULADA.value
                else:
                    existing.status = inv_in.status or existing.status
                existing.source_url = inv_in.source_url
                existing.raw_metadata = inv_in.raw_metadata
                existing.last_synced_at = now
                refresh_invoice_status(existing, today)
                invoices_updated += 1
                if existing.status == InvoiceStatus.VENCIDA.value:
                    overdue_detected += 1

    job.status = ScrapeStatus.SUCCESS.value
    job.mode = payload.mode
    job.finished_at = now
    job.clients_processed = clients_processed
    job.invoices_created = invoices_created
    job.invoices_updated = invoices_updated
    job.overdue_detected = overdue_detected
    job.log_summary = payload.log_summary or (
        f"Sincronización completada ({payload.mode}): {clients_processed} clientes, "
        f"{invoices_created} facturas nuevas, {invoices_updated} actualizadas, {overdue_detected} vencidas."
    )
    job.error_message = None

    db.commit()
    db.refresh(job)
    return job
