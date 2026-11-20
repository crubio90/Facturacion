import logging
import smtplib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from email.message import EmailMessage

from app.core.config import get_settings
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.reminder import ReminderStatus
from app.services.client_metrics import compute_invoice_days_overdue

logger = logging.getLogger(__name__)


@dataclass
class EmailDeliveryResult:
    status: str
    subject: str
    text_body: str
    html_body: str
    error_message: str | None = None


def format_clp(amount: Decimal) -> str:
    value = int(round(amount))
    return f"${value:,}".replace(",", ".")


def build_overdue_reminder_email(
    client: Client,
    overdue_invoices: list[Invoice],
    reminder_sequence: int,
    threshold: int,
    custom_note: str | None = None,
) -> tuple[str, str, str]:
    settings = get_settings()
    company = settings.COMPANY_NAME
    today = date.today()
    total_vencido = sum((inv.saldo_pendiente for inv in overdue_invoices), Decimal("0.00"))
    folios_str = ", ".join(f"#{inv.folio}" for inv in overdue_invoices)

    is_risk_trigger = reminder_sequence >= threshold
    subject_prefix = (
        f"[AVISO {reminder_sequence}° - RIESGO COMERCIAL]"
        if is_risk_trigger
        else f"[Recordatorio de Pago N° {reminder_sequence}]"
    )
    subject = f"{subject_prefix} {company} — Facturas vencidas ({folios_str}) | {client.razon_social}"

    recipient_greeting = client.encargado_compras_nombre or "Encargado(a) de Compras"

    lines_text = [
        f"Estimado(a) {recipient_greeting},",
        "",
        f"Le escribimos desde el área de Cobranzas de {company} para informarle que su cuenta "
        f"({client.razon_social}, RUT {client.rut}) registra documentos vencidos pendientes de regularización:",
        "",
    ]
    rows_html = []
    for inv in overdue_invoices:
        dias = compute_invoice_days_overdue(inv, today)
        lines_text.append(
            f"  - {inv.tipo_dte_nombre} Folio {inv.folio} | Emisión: {inv.fecha_emision.strftime('%d-%m-%Y')} "
            f"| Vencimiento: {inv.fecha_vencimiento.strftime('%d-%m-%Y')} ({dias} días de mora) "
            f"| Saldo pendiente: {format_clp(inv.saldo_pendiente)}"
        )
        rows_html.append(
            f"""
            <tr>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-family:monospace;">#{inv.folio}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{inv.tipo_dte_nombre}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;">{inv.fecha_emision.strftime('%d-%m-%Y')}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;color:#b91c1c;font-weight:600;">{inv.fecha_vencimiento.strftime('%d-%m-%Y')}</td>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">{dias} d</td>
              <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600;font-family:monospace;">{format_clp(inv.saldo_pendiente)}</td>
            </tr>
            """
        )

    lines_text.append("")
    lines_text.append(f"Total vencido a regularizar: {format_clp(total_vencido)}")
    lines_text.append(f"Número de recordatorio enviado: {reminder_sequence} de {threshold}")

    if custom_note:
        lines_text.extend(["", f"Nota adicional de Cobranza: {custom_note}"])

    risk_warning_html = ""
    if is_risk_trigger:
        lines_text.extend(
            [
                "",
                f"IMPORTANTE: Este corresponde al recordatorio N° {reminder_sequence}. "
                f"De acuerdo con la política comercial de {company}, su cuenta ha sido marcada en estado "
                "Riesgo de Venta, por lo que nuevos pedidos podrán quedar sujetos a restricción o validación comercial "
                "hasta regularizar el saldo vencido.",
            ]
        )
        risk_warning_html = f"""
        <div style="margin-top:20px;padding:14px 16px;background:#fef2f2;border-left:4px solid #b91c1c;border-radius:4px;color:#7f1d1d;font-size:14px;">
          <strong>Aviso importante (Recordatorio N° {reminder_sequence}):</strong>
          De acuerdo con la política comercial de {company}, su cuenta ha sido clasificada como
          <strong>Cliente de Riesgo de Venta</strong>. Nuevos pedidos podrán quedar sujetos a restricción o pago contado hasta regularizar el saldo pendiente.
        </div>
        """

    lines_text.extend(
        [
            "",
            "Si ya realizó el pago, por favor envíenos el comprobante respondiendo a este correo para actualizar su cuenta corriente.",
            "",
            f"Atentamente,",
            f"Equipo de Cobranza — {company}",
        ]
    )

    note_html = (
        f'<p style="margin-top:16px;padding:12px;background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;font-size:14px;">'
        f"<strong>Nota de Cobranza:</strong> {custom_note}</p>"
        if custom_note
        else ""
    )

    html_body = f"""<!DOCTYPE html>
<html lang="es">
<body style="margin:0;padding:24px;background:#f7f6f3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#171a1f;">
  <div style="max-width:660px;margin:0 auto;background:#ffffff;border:1px solid #e5e2dc;border-radius:10px;overflow:hidden;">
    <div style="background:#7c1d2f;color:#ffffff;padding:20px 28px;">
      <div style="font-size:12px;letter-spacing:1.4px;text-transform:uppercase;opacity:0.85;">{company} · Gestión de Cobranza</div>
      <h1 style="margin:6px 0 0;font-size:20px;font-weight:600;">Recordatorio de Pago N° {reminder_sequence}</h1>
    </div>
    <div style="padding:24px 28px;line-height:1.6;font-size:15px;">
      <p style="margin-top:0;">Estimado(a) <strong>{recipient_greeting}</strong>,</p>
      <p>Le informamos que la cuenta de <strong>{client.razon_social}</strong> (RUT <code>{client.rut}</code>) registra los siguientes documentos vencidos en {company}:</p>
      <table style="width:100%;border-collapse:collapse;margin:18px 0;font-size:13px;">
        <thead>
          <tr style="background:#f7f6f3;text-align:left;">
            <th style="padding:10px 12px;border-bottom:2px solid #e5e2dc;">Folio</th>
            <th style="padding:10px 12px;border-bottom:2px solid #e5e2dc;">Documento</th>
            <th style="padding:10px 12px;border-bottom:2px solid #e5e2dc;">Emisión</th>
            <th style="padding:10px 12px;border-bottom:2px solid #e5e2dc;">Vencimiento</th>
            <th style="padding:10px 12px;border-bottom:2px solid #e5e2dc;text-align:right;">Mora</th>
            <th style="padding:10px 12px;border-bottom:2px solid #e5e2dc;text-align:right;">Saldo</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
        <tfoot>
          <tr style="background:#faf9f7;">
            <td colspan="5" style="padding:12px;font-weight:700;text-align:right;">Total vencido a regularizar:</td>
            <td style="padding:12px;font-weight:700;text-align:right;font-family:monospace;color:#7c1d2f;">{format_clp(total_vencido)}</td>
          </tr>
        </tfoot>
      </table>
      {note_html}
      {risk_warning_html}
      <p style="margin-top:20px;font-size:14px;color:#4b5563;">
        Si ya efectuó el pago correspondiente, por favor responda este correo adjuntando el comprobante de transferencia para actualizar su cuenta corriente.
      </p>
      <p style="margin-bottom:0;font-size:14px;">Atentamente,<br/><strong>Área de Cobranzas — {company}</strong></p>
    </div>
  </div>
</body>
</html>"""

    return subject, "\n".join(lines_text), html_body


def send_reminder_email(
    recipient_email: str,
    client: Client,
    overdue_invoices: list[Invoice],
    reminder_sequence: int,
    threshold: int,
    custom_note: str | None = None,
) -> EmailDeliveryResult:
    settings = get_settings()
    subject, text_body, html_body = build_overdue_reminder_email(
        client=client,
        overdue_invoices=overdue_invoices,
        reminder_sequence=reminder_sequence,
        threshold=threshold,
        custom_note=custom_note,
    )

    if settings.SMTP_DRY_RUN or not settings.SMTP_HOST:
        logger.info(
            "[SMTP DRY_RUN] Recordatorio #%s simulado para %s (%s) — Asunto: %s",
            reminder_sequence,
            client.razon_social,
            recipient_email,
            subject,
        )
        return EmailDeliveryResult(
            status=ReminderStatus.DRY_RUN.value,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = recipient_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                server.ehlo()
                if settings.SMTP_USE_TLS:
                    server.starttls()
                    server.ehlo()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

        logger.info(
            "[SMTP SENT] Recordatorio #%s enviado a %s (%s)",
            reminder_sequence,
            recipient_email,
            client.razon_social,
        )
        return EmailDeliveryResult(
            status=ReminderStatus.SENT.value,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception as exc:
        logger.exception("Error enviando correo SMTP a %s: %s", recipient_email, exc)
        return EmailDeliveryResult(
            status=ReminderStatus.FAILED.value,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            error_message=str(exc),
        )
