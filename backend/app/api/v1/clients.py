from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.client import Client, SaleRestrictionStatus
from app.models.reminder import PaymentReminder
from app.models.risk_decision import RiskDecisionType, SaleRiskDecision
from app.models.user import User, UserRole
from app.schemas.client import (
    ClientSummary,
    ClientUpdate,
    SaleRiskDecisionCreate,
    SaleRiskDecisionRead,
)
from app.schemas.dashboard import ClientDetailResponse
from app.services.client_metrics import (
    build_client_summary,
    build_invoice_read,
    refresh_invoice_status,
)
from app.services.reminder_service import serialize_reminder

router = APIRouter(prefix="/clients", tags=["Clientes y Riesgo de Venta"])


@router.get("", response_model=list[ClientSummary])
def list_clients(
    search: str | None = Query(default=None, description="Buscar por RUT, razón social o fantasía"),
    only_overdue: bool = Query(default=False),
    only_sales_risk: bool = Query(default=False),
    restriction_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ClientSummary]:
    clients = list(
        db.scalars(
            select(Client)
            .options(selectinload(Client.invoices))
            .order_by(Client.razon_social.asc())
        ).all()
    )

    dirty = False
    for c in clients:
        for inv in c.invoices:
            old = inv.status
            if refresh_invoice_status(inv) != old:
                dirty = True
    if dirty:
        db.commit()

    results: list[ClientSummary] = []
    q = search.strip().lower() if search else None

    for c in clients:
        if q:
            haystack = f"{c.rut} {c.razon_social} {c.nombre_fantasia or ''} {c.encargado_compras_email or ''}".lower()
            if q not in haystack:
                continue
        summary = build_client_summary(c, list(c.invoices))
        if only_overdue and summary.facturas_vencidas_count == 0:
            continue
        if only_sales_risk and not summary.is_sales_risk:
            continue
        if restriction_status and summary.sale_restriction_status != restriction_status:
            continue
        results.append(summary)

    results.sort(key=lambda x: (not x.is_sales_risk, -x.total_vencido, x.razon_social))
    return results


@router.get("/{client_id}", response_model=ClientDetailResponse)
def get_client_detail(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ClientDetailResponse:
    client = db.scalar(
        select(Client)
        .where(Client.id == client_id)
        .options(
            selectinload(Client.invoices),
            selectinload(Client.reminders).selectinload(PaymentReminder.triggered_by),
            selectinload(Client.risk_decisions).selectinload(SaleRiskDecision.user),
        )
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    dirty = False
    for inv in client.invoices:
        old = inv.status
        if refresh_invoice_status(inv) != old:
            dirty = True
    if dirty:
        db.commit()

    invoices_sorted = sorted(
        client.invoices,
        key=lambda i: (i.status != "VENCIDA", i.fecha_vencimiento),
    )
    reminders_sorted = sorted(client.reminders, key=lambda r: r.sent_at, reverse=True)
    decisions_sorted = sorted(client.risk_decisions, key=lambda d: d.created_at, reverse=True)

    return ClientDetailResponse(
        client=build_client_summary(client, invoices_sorted),
        invoices=[build_invoice_read(inv, client) for inv in invoices_sorted],
        reminders=[serialize_reminder(rem, client) for rem in reminders_sorted],
        risk_decisions=[
            SaleRiskDecisionRead(
                id=d.id,
                client_id=d.client_id,
                user_id=d.user_id,
                user_name=d.user.full_name if d.user else None,
                decision=d.decision,
                order_reference=d.order_reference,
                order_amount=d.order_amount,
                reason=d.reason,
                created_at=d.created_at,
            )
            for d in decisions_sorted
        ],
    )


@router.patch("/{client_id}", response_model=ClientSummary)
def update_client_contact(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.COBRANZA)),
) -> ClientSummary:
    client = db.scalar(
        select(Client).where(Client.id == client_id).options(selectinload(Client.invoices))
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    db.commit()
    db.refresh(client)
    return build_client_summary(client, list(client.invoices))


@router.post("/{client_id}/risk-decision", response_model=ClientSummary)
def apply_sale_risk_decision(
    client_id: int,
    payload: SaleRiskDecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.VENDEDOR, UserRole.COBRANZA)),
) -> ClientSummary:
    """Permite al vendedor (o admin/cobranza) restringir, limitar o autorizar por excepción
    la venta a un cliente marcado como Riesgo de Venta cuando solicita un nuevo pedido a DABERUSA."""
    client = db.scalar(
        select(Client).where(Client.id == client_id).options(selectinload(Client.invoices))
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    now = datetime.now(timezone.utc)

    decision_record = SaleRiskDecision(
        client_id=client.id,
        user_id=current_user.id,
        decision=payload.decision.value,
        order_reference=payload.order_reference,
        order_amount=payload.order_amount,
        reason=payload.reason.strip(),
        created_at=now,
    )
    db.add(decision_record)

    if payload.decision == RiskDecisionType.RESTRICT_SALE:
        client.sale_restriction_status = SaleRestrictionStatus.RESTRICTED.value
        client.sale_restriction_note = payload.reason.strip()
        client.sale_restriction_updated_at = now
        client.sale_restriction_updated_by_id = current_user.id
    elif payload.decision == RiskDecisionType.LIMIT_SALE:
        client.sale_restriction_status = SaleRestrictionStatus.LIMITED.value
        client.sale_restriction_note = payload.reason.strip()
        client.sale_restriction_updated_at = now
        client.sale_restriction_updated_by_id = current_user.id
    elif payload.decision == RiskDecisionType.ALLOW_EXCEPTION:
        client.sale_restriction_status = SaleRestrictionStatus.NONE.value
        client.sale_restriction_note = f"Excepción autorizada: {payload.reason.strip()}"
        client.sale_restriction_updated_at = now
        client.sale_restriction_updated_by_id = current_user.id
    elif payload.decision == RiskDecisionType.CLEAR_RISK:
        client.is_sales_risk = False
        client.sales_risk_reason = None
        client.sales_risk_marked_at = None
        client.reminder_count = 0
        client.sale_restriction_status = SaleRestrictionStatus.NONE.value
        client.sale_restriction_note = f"Riesgo levantado: {payload.reason.strip()}"
        client.sale_restriction_updated_at = now
        client.sale_restriction_updated_by_id = current_user.id

    db.commit()
    db.refresh(client)
    return build_client_summary(client, list(client.invoices))
