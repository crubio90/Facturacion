import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { DashboardMetrics } from '../../core/models/api.models';
import { ClpPipe } from '../../shared/pipes/clp.pipe';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, ClpPipe],
  template: `
    <div class="page-header">
      <div>
        <h1 class="page-title">Resumen de Cobranza</h1>
        <p class="page-subtitle">
          Estado actualizado de cuentas por cobrar, morosidad y clientes en Riesgo de Venta de DABERUSA.
        </p>
      </div>

      @if (auth.canManageCollections()) {
        <div class="actions-row">
          <button
            type="button"
            id="dashboard-sync-btn"
            class="btn btn-secondary"
            [disabled]="syncing()"
            (click)="runSync()"
          >
            {{ syncing() ? 'Sincronizando facturacion.cl...' : 'Sincronizar facturacion.cl' }}
          </button>
          <button
            type="button"
            id="dashboard-bulk-reminder-btn"
            class="btn btn-primary"
            [disabled]="sendingBulk()"
            (click)="sendBulkReminders()"
          >
            {{ sendingBulk() ? 'Enviando recordatorios...' : 'Enviar recordatorios a vencidos' }}
          </button>
        </div>
      }
    </div>

    @if (feedback()) {
      <div class="alert" [class.alert-ok]="feedbackType() === 'ok'" [class.alert-danger]="feedbackType() === 'error'">
        <span>{{ feedback() }}</span>
        <button type="button" class="btn btn-ghost btn-sm" (click)="feedback.set(null)">Cerrar</button>
      </div>
    }

    @if (loading()) {
      <div class="card loading-box">Cargando métricas de cobranza...</div>
    } @else {
      @if (metrics(); as m) {
      @if (m.smtp_dry_run) {
        <div class="alert alert-warn">
          <div>
            <strong>Modo Simulación de Correo (SMTP_DRY_RUN activo):</strong>
            Los recordatorios se registran en el historial y activan la regla de Riesgo de Venta al {{ m.risk_reminder_threshold }}° envío sin despachar correos reales hasta configurar tu servidor SMTP en <code>.env</code>.
          </div>
        </div>
      }

      <section class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Total por Cobrar</div>
          <div class="kpi-value mono">{{ m.total_por_cobrar | clp }}</div>
          <div class="kpi-meta">{{ m.facturas_pendientes + m.facturas_vencidas }} facturas abiertas</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Monto Vencido</div>
          <div class="kpi-value danger mono">{{ m.total_vencido | clp }}</div>
          <div class="kpi-meta">{{ m.facturas_vencidas }} facturas vencidas en {{ m.clients_with_overdue }} clientes</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Clientes Riesgo de Venta</div>
          <div class="kpi-value brand mono">{{ m.clients_sales_risk }}</div>
          <div class="kpi-meta">
            {{ m.clients_sale_restricted }} con venta restringida o limitada
          </div>
        </div>

        <div class="kpi-card">
          <div class="kpi-label">Recaudado (Pagadas)</div>
          <div class="kpi-value ok mono">{{ m.total_pagado | clp }}</div>
          <div class="kpi-meta">{{ m.facturas_pagadas }} facturas pagadas · {{ m.reminders_sent_30d }} recordatorios (30d)</div>
        </div>
      </section>

      <div class="card" style="margin-bottom: 20px;">
        <div class="card-header">
          <h2>Clientes prioritarios (Mora y Riesgo de Venta)</h2>
          <a routerLink="/clientes" class="btn btn-ghost btn-sm">Ver todas las cuentas →</a>
        </div>

        @if (m.priority_clients.length === 0) {
          <div class="empty-state">
            <h3>Sin cuentas vencidas registradas</h3>
            <p>Ejecuta una sincronización con facturacion.cl para importar cuentas y facturas.</p>
          </div>
        } @else {
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Cliente</th>
                  <th>Encargado de Compras</th>
                  <th class="text-right">Monto Vencido</th>
                  <th>Mora Máx.</th>
                  <th>Recordatorios</th>
                  <th>Estado Comercial</th>
                  <th class="text-right">Acción</th>
                </tr>
              </thead>
              <tbody>
                @for (c of m.priority_clients; track c.id) {
                  <tr>
                    <td>
                      <div class="fw-600">{{ c.razon_social }}</div>
                      <div class="mono text-muted" style="font-size: 12px;">{{ c.rut }}</div>
                    </td>
                    <td>
                      <div>{{ c.encargado_compras_nombre || 'Sin definir' }}</div>
                      <div class="text-muted" style="font-size: 12px;">{{ c.encargado_compras_email || 'Sin correo' }}</div>
                    </td>
                    <td class="text-right mono fw-600 text-danger">{{ c.total_vencido | clp }}</td>
                    <td class="mono">{{ c.max_dias_mora }} días</td>
                    <td>
                      <div class="step-dots" [title]="c.reminder_count + ' de ' + m.risk_reminder_threshold + ' recordatorios'">
                        @for (step of [1, 2, 3]; track step) {
                          <span
                            class="step-dot"
                            [class.filled-warn]="c.reminder_count >= step && !c.is_sales_risk"
                            [class.filled-danger]="c.reminder_count >= step && c.is_sales_risk"
                          ></span>
                        }
                        <span class="mono" style="margin-left: 6px; font-size: 12px;">
                          {{ c.reminder_count }}/{{ m.risk_reminder_threshold }}
                        </span>
                      </div>
                    </td>
                    <td>
                      @if (c.sale_restriction_status === 'RESTRICTED') {
                        <span class="badge badge-danger">Venta Restringida</span>
                      } @else if (c.sale_restriction_status === 'LIMITED') {
                        <span class="badge badge-warn">Venta Limitada</span>
                      } @else if (c.is_sales_risk) {
                        <span class="badge badge-danger">Riesgo de Venta</span>
                      } @else {
                        <span class="badge badge-warn">En Cobranza</span>
                      }
                    </td>
                    <td class="text-right">
                      <a [routerLink]="['/clientes', c.id]" class="btn btn-secondary btn-sm">Gestionar</a>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>

      @if (m.last_scrape_job; as job) {
        <div class="card">
          <div class="card-header">
            <h3>Última sincronización facturacion.cl</h3>
            <a routerLink="/sincronizacion" class="btn btn-ghost btn-sm">Ver historial scraper →</a>
          </div>
          <div class="card-body sync-strip">
            <div>
              <span class="badge" [class.badge-ok]="job.status === 'SUCCESS'" [class.badge-danger]="job.status === 'FAILED'" [class.badge-info]="job.status === 'RUNNING'">
                {{ job.status }}
              </span>
              <span style="margin-left: 10px;" class="fw-600">{{ job.log_summary || 'Proceso ejecutado' }}</span>
            </div>
            <div class="text-muted" style="font-size: 12.5px;">
              Modo: <strong class="mono">{{ job.mode }}</strong> · Origen: {{ job.trigger_type }} ·
              {{ job.started_at | date:'dd-MM-yyyy HH:mm' }}
            </div>
          </div>
        </div>
      }
      }
    }
  `,
  styles: [`
    .sync-strip {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
  `],
})
export class DashboardComponent implements OnInit {
  readonly metrics = signal<DashboardMetrics | null>(null);
  readonly loading = signal(true);
  readonly syncing = signal(false);
  readonly sendingBulk = signal(false);
  readonly feedback = signal<string | null>(null);
  readonly feedbackType = signal<'ok' | 'error'>('ok');

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.getDashboard().subscribe({
      next: (data) => {
        this.metrics.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'Error al cargar el panel de cobranza.');
      },
    });
  }

  runSync(): void {
    this.syncing.set(true);
    this.feedback.set(null);
    this.api.triggerScrape().subscribe({
      next: (job) => {
        this.syncing.set(false);
        this.feedbackType.set('ok');
        this.feedback.set(job.log_summary || 'Sincronización completada correctamente.');
        this.load();
      },
      error: (err) => {
        this.syncing.set(false);
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'No se pudo ejecutar la sincronización con facturacion.cl.');
      },
    });
  }

  sendBulkReminders(): void {
    if (!confirm('¿Enviar recordatorio de pago a todos los clientes con facturas vencidas y correo registrado?')) {
      return;
    }
    this.sendingBulk.set(true);
    this.feedback.set(null);
    this.api.sendBulkReminders({ only_clients_with_email: true }).subscribe({
      next: (res) => {
        this.sendingBulk.set(false);
        this.feedbackType.set('ok');
        const riskInfo = res.newly_marked_risk_clients.length
          ? ` Nuevos en Riesgo de Venta: ${res.newly_marked_risk_clients.join(', ')}.`
          : '';
        this.feedback.set(
          `Proceso masivo completado: ${res.sent_count} enviados, ${res.dry_run_count} simulados, ${res.failed_count} con error, ${res.skipped_count} omitidos.${riskInfo}`
        );
        this.load();
      },
      error: (err) => {
        this.sendingBulk.set(false);
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'Error al despachar recordatorios masivos.');
      },
    });
  }
}
