import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import {
  ClientDetailResponse,
  PaymentReminder,
  RiskDecisionType,
} from '../../core/models/api.models';
import { ClpPipe } from '../../shared/pipes/clp.pipe';

@Component({
  selector: 'app-client-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, ClpPipe],
  template: `
    <div style="margin-bottom: 14px;">
      <a routerLink="/clientes" class="text-secondary" style="font-size: 13px;">← Volver a Cuentas de Clientes</a>
    </div>

    @if (feedback()) {
      <div class="alert" [class.alert-ok]="feedbackType() === 'ok'" [class.alert-danger]="feedbackType() === 'error'">
        <span>{{ feedback() }}</span>
        <button type="button" class="btn btn-ghost btn-sm" (click)="feedback.set(null)">Cerrar</button>
      </div>
    }

    @if (loading()) {
      <div class="card loading-box">Cargando cuenta del cliente...</div>
    } @else {
      @if (detail(); as d) {
      <div class="page-header">
        <div>
          <h1 class="page-title">{{ d.client.razon_social }}</h1>
          <p class="page-subtitle">
            <span class="mono">{{ d.client.rut }}</span>
            @if (d.client.nombre_fantasia) { · {{ d.client.nombre_fantasia }} }
            · Crédito {{ d.client.dias_credito }} días (Límite {{ d.client.credito_limite | clp }})
          </p>
        </div>

        @if (auth.canManageCollections() && d.client.facturas_vencidas_count > 0) {
          <div class="actions-row">
            <button
              type="button"
              id="send-consolidated-reminder-btn"
              class="btn btn-primary"
              [disabled]="sendingReminder()"
              (click)="sendReminder(null)"
            >
              {{
                sendingReminder()
                  ? 'Enviando recordatorio...'
                  : 'Enviar recordatorio #' + (d.client.reminder_count + 1) + ' al encargado de compras'
              }}
            </button>
          </div>
        }
      </div>

      <!-- Banner prominente de Riesgo de Venta -->
      @if (d.client.is_sales_risk) {
        <div class="risk-banner">
          <div class="risk-banner-main">
            <div class="risk-title">CLIENTE MARCADO COMO RIESGO DE VENTA</div>
            <p class="risk-desc">
              {{ d.client.sales_risk_reason || 'Superó el límite de recordatorios de pago por facturas vencidas.' }}
              @if (d.client.sales_risk_marked_at) {
                <span class="mono"> ({{ d.client.sales_risk_marked_at | date:'dd-MM-yyyy HH:mm' }})</span>
              }
            </p>
            <div class="risk-status-line">
              Estado actual de venta en DABERUSA:
              @if (d.client.sale_restriction_status === 'RESTRICTED') {
                <span class="badge badge-danger">VENTA RESTRINGIDA / BLOQUEADA</span>
              } @else if (d.client.sale_restriction_status === 'LIMITED') {
                <span class="badge badge-warn">VENTA LIMITADA (SOLO CONTADO / CUPO)</span>
              } @else {
                <span class="badge badge-neutral">SIN RESTRICCIÓN ACTIVA — PENDIENTE DECISIÓN DEL VENDEDOR</span>
              }
              @if (d.client.sale_restriction_note) {
                <span class="risk-note">— {{ d.client.sale_restriction_note }}</span>
              }
            </div>
          </div>
        </div>
      }

      <!-- KPIs de la cuenta -->
      <section class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Saldo por Cobrar</div>
          <div class="kpi-value mono">{{ d.client.total_por_cobrar | clp }}</div>
          <div class="kpi-meta">{{ d.client.facturas_pendientes_count + d.client.facturas_vencidas_count }} facturas abiertas</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Saldo Vencido</div>
          <div class="kpi-value danger mono">{{ d.client.total_vencido | clp }}</div>
          <div class="kpi-meta">{{ d.client.facturas_vencidas_count }} vencida(s) · Mora máx. {{ d.client.max_dias_mora }} días</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Recordatorios Enviados</div>
          <div class="kpi-value brand mono">{{ d.client.reminder_count }} / 3</div>
          <div class="kpi-meta">
            @if (d.client.last_reminder_at) {
              Último: {{ d.client.last_reminder_at | date:'dd-MM-yyyy HH:mm' }}
            } @else {
              Sin recordatorios registrados
            }
          </div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Total Facturas Pagadas</div>
          <div class="kpi-value ok mono">{{ d.client.total_pagado | clp }}</div>
          <div class="kpi-meta">{{ d.client.facturas_pagadas_count }} documento(s) saldados</div>
        </div>
      </section>

      <!-- Dos columnas superiores: Encargado de compras + Control Comercial del Vendedor -->
      <div class="two-col">
        <div class="card">
          <div class="card-header">
            <h2>Encargado de Compras (Destinatario de Cobranza)</h2>
            @if (auth.canManageCollections() && !editingContact()) {
              <button type="button" class="btn btn-secondary btn-sm" (click)="startEditContact()">Editar contacto</button>
            }
          </div>
          <div class="card-body">
            @if (editingContact()) {
              <form (ngSubmit)="saveContact()" class="contact-form">
                <div class="form-field">
                  <label>Nombre Encargado de Compras</label>
                  <input class="input" [(ngModel)]="contactForm.encargado_compras_nombre" name="cname" />
                </div>
                <div class="form-field">
                  <label>Correo Electrónico</label>
                  <input class="input" type="email" [(ngModel)]="contactForm.encargado_compras_email" name="cemail" />
                </div>
                <div class="form-field">
                  <label>Teléfono</label>
                  <input class="input" [(ngModel)]="contactForm.encargado_compras_telefono" name="cphone" />
                </div>
                <div class="actions-row">
                  <button type="submit" class="btn btn-primary btn-sm" [disabled]="savingContact()">Guardar</button>
                  <button type="button" class="btn btn-secondary btn-sm" (click)="editingContact.set(false)">Cancelar</button>
                </div>
              </form>
            } @else {
              <dl class="info-list">
                <div>
                  <dt>Encargado</dt>
                  <dd>{{ d.client.encargado_compras_nombre || 'No registrado' }}</dd>
                </div>
                <div>
                  <dt>Correo electrónico</dt>
                  <dd class="mono">{{ d.client.encargado_compras_email || 'Sin correo (requerido para enviar avisos)' }}</dd>
                </div>
                <div>
                  <dt>Teléfono</dt>
                  <dd class="mono">{{ d.client.encargado_compras_telefono || 'No registrado' }}</dd>
                </div>
              </dl>
            }
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h2>Control de Venta DABERUSA (A demanda del vendedor)</h2>
          </div>
          <div class="card-body">
            <p class="text-secondary" style="margin-top: 0; font-size: 13px;">
              Cuando este cliente solicite un nuevo pedido de licores o bebidas analcohólicas, el vendedor puede
              restringir, limitar o autorizar la venta dejando registro auditable.
            </p>

            @if (auth.canManageSalesRisk()) {
              <form (ngSubmit)="submitRiskDecision()" class="risk-form">
                <div class="form-grid">
                  <div class="form-field">
                    <label for="decision-select">Acción comercial</label>
                    <select id="decision-select" class="select" [(ngModel)]="decisionForm.decision" name="decision">
                      <option value="RESTRICT_SALE">Restringir / Bloquear venta</option>
                      <option value="LIMIT_SALE">Limitar venta (Solo contado / cupo reducido)</option>
                      <option value="ALLOW_EXCEPTION">Autorizar pedido por excepción</option>
                      <option value="CLEAR_RISK">Levantar Riesgo de Venta (Deuda regularizada)</option>
                    </select>
                  </div>
                  <div class="form-field">
                    <label for="order-ref">N° Pedido (Opcional)</label>
                    <input
                      id="order-ref"
                      class="input"
                      [(ngModel)]="decisionForm.order_reference"
                      name="order_ref"
                      placeholder="Ej. PED-2026-4120"
                    />
                  </div>
                  <div class="form-field">
                    <label for="order-amount">Monto Pedido CLP (Opcional)</label>
                    <input
                      id="order-amount"
                      type="number"
                      class="input"
                      [(ngModel)]="decisionForm.order_amount"
                      name="order_amount"
                      placeholder="Ej. 950000"
                    />
                  </div>
                </div>

                <div class="form-field" style="margin-top: 10px;">
                  <label for="decision-reason">Motivo / Resolución del vendedor</label>
                  <textarea
                    id="decision-reason"
                    class="textarea"
                    rows="2"
                    [(ngModel)]="decisionForm.reason"
                    name="reason"
                    placeholder="Indica el criterio comercial aplicado para este cliente..."
                    required
                  ></textarea>
                </div>

                <div class="actions-row" style="margin-top: 12px;">
                  <button
                    type="submit"
                    id="apply-risk-decision-btn"
                    class="btn"
                    [class.btn-danger]="decisionForm.decision === 'RESTRICT_SALE'"
                    [class.btn-warn]="decisionForm.decision === 'LIMIT_SALE'"
                    [class.btn-ok]="decisionForm.decision === 'ALLOW_EXCEPTION' || decisionForm.decision === 'CLEAR_RISK'"
                    [disabled]="savingDecision()"
                  >
                    {{ savingDecision() ? 'Registrando...' : 'Aplicar decisión comercial' }}
                  </button>
                </div>
              </form>
            }
          </div>
        </div>
      </div>

      <!-- Pestañas inferiores: Facturas, Recordatorios, Auditoría de Decisiones -->
      <div class="tabs" style="margin-top: 24px;">
        <button type="button" class="tab-btn" [class.active]="activeTab() === 'INVOICES'" (click)="activeTab.set('INVOICES')">
          Facturas ({{ d.invoices.length }})
        </button>
        <button type="button" class="tab-btn" [class.active]="activeTab() === 'REMINDERS'" (click)="activeTab.set('REMINDERS')">
          Historial de Recordatorios ({{ d.reminders.length }})
        </button>
        <button type="button" class="tab-btn" [class.active]="activeTab() === 'DECISIONS'" (click)="activeTab.set('DECISIONS')">
          Bitácora Riesgo / Ventas ({{ d.risk_decisions.length }})
        </button>
      </div>

      @if (activeTab() === 'INVOICES') {
        <div class="card">
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Folio</th>
                  <th>Documento</th>
                  <th>Emisión</th>
                  <th>Vencimiento</th>
                  <th>Mora</th>
                  <th class="text-right">Total</th>
                  <th class="text-right">Saldo Pendiente</th>
                  <th>Estado</th>
                  @if (auth.canManageCollections()) {
                    <th class="text-right">Recordatorio</th>
                  }
                </tr>
              </thead>
              <tbody>
                @for (inv of d.invoices; track inv.id) {
                  <tr>
                    <td class="mono fw-600">#{{ inv.folio }}</td>
                    <td>{{ inv.tipo_dte_nombre }}</td>
                    <td class="mono">{{ inv.fecha_emision }}</td>
                    <td class="mono" [class.text-danger]="inv.status === 'VENCIDA'">{{ inv.fecha_vencimiento }}</td>
                    <td class="mono">{{ inv.dias_mora > 0 ? inv.dias_mora + ' días' : '—' }}</td>
                    <td class="text-right mono">{{ inv.monto_total | clp }}</td>
                    <td class="text-right mono fw-600" [class.text-danger]="inv.status === 'VENCIDA'">
                      {{ inv.saldo_pendiente | clp }}
                    </td>
                    <td>
                      <span
                        class="badge"
                        [class.badge-danger]="inv.status === 'VENCIDA'"
                        [class.badge-warn]="inv.status === 'PENDIENTE'"
                        [class.badge-ok]="inv.status === 'PAGADA'"
                        [class.badge-neutral]="inv.status === 'ANULADA'"
                      >
                        {{ inv.status }}
                      </span>
                    </td>
                    @if (auth.canManageCollections()) {
                      <td class="text-right">
                        @if (inv.status === 'VENCIDA') {
                          <button
                            type="button"
                            class="btn btn-secondary btn-sm"
                            [disabled]="sendingReminder()"
                            (click)="sendReminder(inv.id)"
                          >
                            Enviar aviso
                          </button>
                        } @else {
                          <span class="text-muted">—</span>
                        }
                      </td>
                    }
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }

      @if (activeTab() === 'REMINDERS') {
        <div class="card">
          @if (d.reminders.length === 0) {
            <div class="empty-state">
              <h3>Aún no se han enviado recordatorios de pago a este cliente</h3>
              <p>Cada envío quedará registrado con fecha, hora, folios incluidos y destinatario.</p>
            </div>
          } @else {
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>N° Aviso</th>
                    <th>Fecha y Hora</th>
                    <th>Destinatario</th>
                    <th>Folios Incluidos</th>
                    <th>Estado Envío</th>
                    <th>Enviado por</th>
                    <th class="text-right">Contenido</th>
                  </tr>
                </thead>
                <tbody>
                  @for (rem of d.reminders; track rem.id) {
                    <tr>
                      <td>
                        <span class="badge" [class.badge-danger]="rem.reminder_sequence >= 3" [class.badge-warn]="rem.reminder_sequence < 3">
                          Aviso #{{ rem.reminder_sequence }}
                        </span>
                      </td>
                      <td class="mono">{{ rem.sent_at | date:'dd-MM-yyyy HH:mm' }}</td>
                      <td class="mono" style="font-size: 12.5px;">{{ rem.recipient_email }}</td>
                      <td class="mono">{{ formatFolios(rem.invoice_folios) }}</td>
                      <td>
                        <span
                          class="badge"
                          [class.badge-ok]="rem.status === 'SENT'"
                          [class.badge-info]="rem.status === 'DRY_RUN'"
                          [class.badge-danger]="rem.status === 'FAILED'"
                        >
                          {{ rem.status === 'DRY_RUN' ? 'SIMULADO' : rem.status }}
                        </span>
                      </td>
                      <td>{{ rem.triggered_by_name || 'Automático' }}</td>
                      <td class="text-right">
                        <button type="button" class="btn btn-ghost btn-sm" (click)="previewReminder.set(rem)">
                          Ver correo
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>
      }

      @if (activeTab() === 'DECISIONS') {
        <div class="card">
          @if (d.risk_decisions.length === 0) {
            <div class="empty-state">
              <h3>Sin decisiones comerciales registradas</h3>
              <p>Cuando un vendedor restrinja, limite o autorice un pedido, aparecerá en esta bitácora.</p>
            </div>
          } @else {
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Fecha y Hora</th>
                    <th>Decisión</th>
                    <th>Pedido</th>
                    <th class="text-right">Monto</th>
                    <th>Motivo</th>
                    <th>Responsable</th>
                  </tr>
                </thead>
                <tbody>
                  @for (dec of d.risk_decisions; track dec.id) {
                    <tr>
                      <td class="mono">{{ dec.created_at | date:'dd-MM-yyyy HH:mm' }}</td>
                      <td>
                        <span
                          class="badge"
                          [class.badge-danger]="dec.decision === 'RESTRICT_SALE'"
                          [class.badge-warn]="dec.decision === 'LIMIT_SALE'"
                          [class.badge-ok]="dec.decision === 'ALLOW_EXCEPTION' || dec.decision === 'CLEAR_RISK'"
                        >
                          {{ decisionLabel(dec.decision) }}
                        </span>
                      </td>
                      <td class="mono">{{ dec.order_reference || '—' }}</td>
                      <td class="text-right mono">{{ dec.order_amount ? (dec.order_amount | clp) : '—' }}</td>
                      <td>{{ dec.reason }}</td>
                      <td>{{ dec.user_name || 'Sistema' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>
      }
      }
    }

    <!-- Modal vista previa de correo enviado -->
    @if (previewReminder(); as rem) {
      <div class="modal-backdrop" (click)="previewReminder.set(null)">
        <div class="modal-panel" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <h3>Recordatorio N° {{ rem.reminder_sequence }}</h3>
            <button type="button" class="btn btn-ghost btn-sm" (click)="previewReminder.set(null)">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom: 12px; font-size: 13px;">
              <div><strong>Para:</strong> <span class="mono">{{ rem.recipient_email }}</span></div>
              <div><strong>Asunto:</strong> {{ rem.subject }}</div>
              <div><strong>Fecha:</strong> <span class="mono">{{ rem.sent_at | date:'dd-MM-yyyy HH:mm:ss' }}</span></div>
              @if (rem.error_message) {
                <div class="text-danger" style="margin-top: 6px;"><strong>Error SMTP:</strong> {{ rem.error_message }}</div>
              }
            </div>
            <pre class="email-preview">{{ rem.body_preview }}</pre>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" (click)="previewReminder.set(null)">Cerrar</button>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .risk-banner {
      background: #fef2f2;
      border: 1px solid #f5bcbc;
      border-left: 5px solid #b91c1c;
      border-radius: var(--radius-md);
      padding: 16px 20px;
      margin-bottom: 22px;
    }

    .risk-title {
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.06em;
      color: #991b1b;
    }

    .risk-desc {
      margin: 6px 0 10px;
      font-size: 13.5px;
      color: #7f1d1d;
    }

    .risk-status-line {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #5c1919;
    }

    .risk-note {
      font-style: italic;
    }

    .two-col {
      display: grid;
      grid-template-columns: 0.9fr 1.1fr;
      gap: 18px;
    }

    .info-list {
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .info-list dt {
      font-size: 11.5px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--ink-muted);
      font-weight: 600;
    }

    .info-list dd {
      margin: 2px 0 0;
      font-size: 14px;
      color: var(--ink-primary);
    }

    .contact-form {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    @media (max-width: 960px) {
      .two-col {
        grid-template-columns: 1fr;
      }
    }
  `],
})
export class ClientDetailComponent implements OnInit {
  readonly detail = signal<ClientDetailResponse | null>(null);
  readonly loading = signal(true);
  readonly activeTab = signal<'INVOICES' | 'REMINDERS' | 'DECISIONS'>('INVOICES');
  readonly sendingReminder = signal(false);
  readonly editingContact = signal(false);
  readonly savingContact = signal(false);
  readonly savingDecision = signal(false);
  readonly feedback = signal<string | null>(null);
  readonly feedbackType = signal<'ok' | 'error'>('ok');
  readonly previewReminder = signal<PaymentReminder | null>(null);

  contactForm = {
    encargado_compras_nombre: '',
    encargado_compras_email: '',
    encargado_compras_telefono: '',
  };

  decisionForm: {
    decision: RiskDecisionType;
    order_reference: string;
    order_amount: number | null;
    reason: string;
  } = {
    decision: 'RESTRICT_SALE',
    order_reference: '',
    order_amount: null,
    reason: '',
  };

  private clientId = 0;

  constructor(
    private route: ActivatedRoute,
    private api: ApiService,
    public auth: AuthService
  ) {}

  ngOnInit(): void {
    this.clientId = Number(this.route.snapshot.paramMap.get('id'));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.getClientDetail(this.clientId).subscribe({
      next: (res) => {
        this.detail.set(res);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'No se pudo cargar el cliente.');
      },
    });
  }

  startEditContact(): void {
    const c = this.detail()?.client;
    if (!c) return;
    this.contactForm = {
      encargado_compras_nombre: c.encargado_compras_nombre || '',
      encargado_compras_email: c.encargado_compras_email || '',
      encargado_compras_telefono: c.encargado_compras_telefono || '',
    };
    this.editingContact.set(true);
  }

  saveContact(): void {
    this.savingContact.set(true);
    this.api
      .updateClient(this.clientId, {
        encargado_compras_nombre: this.contactForm.encargado_compras_nombre || null,
        encargado_compras_email: this.contactForm.encargado_compras_email || null,
        encargado_compras_telefono: this.contactForm.encargado_compras_telefono || null,
      })
      .subscribe({
        next: () => {
          this.savingContact.set(false);
          this.editingContact.set(false);
          this.feedbackType.set('ok');
          this.feedback.set('Datos del encargado de compras actualizados.');
          this.load();
        },
        error: (err) => {
          this.savingContact.set(false);
          this.feedbackType.set('error');
          this.feedback.set(err?.error?.detail || 'Error al guardar datos de contacto.');
        },
      });
  }

  sendReminder(invoiceId: number | null): void {
    this.sendingReminder.set(true);
    this.feedback.set(null);
    this.api.sendReminder({ client_id: this.clientId, invoice_id: invoiceId }).subscribe({
      next: (rem) => {
        this.sendingReminder.set(false);
        this.feedbackType.set('ok');
        const riskNotice = rem.marked_as_sales_risk
          ? ' ALERTA: Al alcanzar el 3° envío, el cliente fue marcado automáticamente como CLIENTE DE RIESGO DE VENTA.'
          : '';
        this.feedback.set(
          `Recordatorio #${rem.reminder_sequence} registrado (${rem.status}) hacia ${rem.recipient_email}.${riskNotice}`
        );
        this.load();
      },
      error: (err) => {
        this.sendingReminder.set(false);
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'No se pudo enviar el recordatorio.');
      },
    });
  }

  submitRiskDecision(): void {
    if (!this.decisionForm.reason.trim()) return;
    this.savingDecision.set(true);
    this.feedback.set(null);

    this.api
      .applyRiskDecision(this.clientId, {
        decision: this.decisionForm.decision,
        order_reference: this.decisionForm.order_reference || null,
        order_amount: this.decisionForm.order_amount,
        reason: this.decisionForm.reason.trim(),
      })
      .subscribe({
        next: () => {
          this.savingDecision.set(false);
          this.decisionForm.order_reference = '';
          this.decisionForm.order_amount = null;
          this.decisionForm.reason = '';
          this.feedbackType.set('ok');
          this.feedback.set('Decisión comercial registrada correctamente en la bitácora.');
          this.load();
        },
        error: (err) => {
          this.savingDecision.set(false);
          this.feedbackType.set('error');
          this.feedback.set(err?.error?.detail || 'No se pudo registrar la decisión.');
        },
      });
  }

  formatFolios(folios: number[]): string {
    return folios.map((f) => `#${f}`).join(', ');
  }

  decisionLabel(code: string): string {
    const map: Record<string, string> = {
      RESTRICT_SALE: 'Venta Restringida',
      LIMIT_SALE: 'Venta Limitada',
      ALLOW_EXCEPTION: 'Excepción Autorizada',
      CLEAR_RISK: 'Riesgo Levantado',
    };
    return map[code] || code;
  }
}
