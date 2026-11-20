from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.invoice import InvoiceRead
from app.services.client_metrics import build_invoice_read, refresh_invoice_status

router = APIRouter(prefix="/invoices", tags=["Facturas"])


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    status_filter: str | None = Query(default=None, alias="status"),
    client_id: int | None = Query(default=None),
    search: str | None = Query(default=None, description="Buscar por folio, RUT o razón social"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[InvoiceRead]:
    stmt = select(Invoice).options(selectinload(Invoice.client))
    if client_id is not None:
        stmt = stmt.where(Invoice.client_id == client_id)

    invoices = list(db.scalars(stmt.order_by(Invoice.fecha_vencimiento.asc())).all())

    dirty = False
    for inv in invoices:
        old = inv.status
        if refresh_invoice_status(inv) != old:
            dirty = True
    if dirty:
        db.commit()

    q = search.strip().lower() if search else None
    results: list[InvoiceRead] = []
    for inv in invoices:
        if status_filter and inv.status != status_filter:
            continue
        if q:
            haystack = (
                f"{inv.folio} {inv.external_id} {inv.tipo_dte_nombre} "
                f"{inv.client.rut if inv.client else ''} {inv.client.razon_social if inv.client else ''}"
            ).lower()
            if q not in haystack:
                continue
        results.append(build_invoice_read(inv, inv.client))

    results.sort(key=lambda x: (x.status != "VENCIDA", -x.dias_mora, x.fecha_vencimiento))
    return results
