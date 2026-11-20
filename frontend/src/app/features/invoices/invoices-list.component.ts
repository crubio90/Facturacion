import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { Invoice } from '../../core/models/api.models';
import { ClpPipe } from '../../shared/pipes/clp.pipe';

@Component({
  selector: 'app-invoices-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, ClpPipe],
  template: `
    <div class="page-header">
      <div>
        <h1 class="page-title">Facturas (facturacion.cl)</h1>
        <p class="page-subtitle">
          Documentos tributarios electrónicos por cobrar, vencidos y pagados sincronizados desde facturacion.cl.
        </p>
      </div>
    </div>

    @if (feedback()) {
      <div class="alert" [class.alert-ok]="feedbackType() === 'ok'" [class.alert-danger]="feedbackType() === 'error'">
        <span>{{ feedback() }}</span>
        <button type="button" class="btn btn-ghost btn-sm" (click)="feedback.set(null)">Cerrar</button>
      </div>
    }

    <div class="tabs">
      <button type="button" class="tab-btn" [class.active]="statusFilter() === ''" (click)="setStatus('')">Todas</button>
      <button type="button" class="tab-btn" [class.active]="statusFilter() === 'VENCIDA'" (click)="setStatus('VENCIDA')">Vencidas</button>
      <button type="button" class="tab-btn" [class.active]="statusFilter() === 'PENDIENTE'" (click)="setStatus('PENDIENTE')">Pendientes por vencer</button>
      <button type="button" class="tab-btn" [class.active]="statusFilter() === 'PAGADA'" (click)="setStatus('PAGADA')">Pagadas</button>
    </div>

    <div class="filter-bar">
      <input
        type="search"
        class="input search-input"
        placeholder="Buscar por folio, RUT o cliente..."
        [(ngModel)]="search"
        (ngModelChange)="load()"
      />
      <span class="text-muted" style="font-size: 12.5px;">{{ invoices().length }} documento(s)</span>
    </div>

    <div class="card">
      @if (loading()) {
        <div class="loading-box">Cargando facturas...</div>
      } @else if (invoices().length === 0) {
        <div class="empty-state">
          <h3>No hay facturas para mostrar</h3>
          <p>Sincroniza con facturacion.cl o cambia los filtros activos.</p>
        </div>
      } @else {
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Folio</th>
                <th>Cliente</th>
                <th>Emisión</th>
                <th>Vencimiento</th>
                <th>Mora</th>
                <th class="text-right">Monto Total</th>
                <th class="text-right">Saldo Pendiente</th>
                <th>Estado</th>
                @if (auth.canManageCollections()) {
                  <th class="text-right">Acción</th>
                }
              </tr>
            </thead>
            <tbody>
              @for (inv of invoices(); track inv.id) {
                <tr>
                  <td>
                    <div class="mono fw-600">#{{ inv.folio }}</div>
                    <div class="text-muted" style="font-size: 11.5px;">{{ inv.tipo_dte_nombre }}</div>
                  </td>
                  <td>
                    <a [routerLink]="['/clientes', inv.client_id]" class="fw-600">
                      {{ inv.client_razon_social }}
                    </a>
                    <div class="mono text-muted" style="font-size: 12px;">
                      {{ inv.client_rut }}
                      @if (inv.client_is_sales_risk) {
                        <span class="badge badge-danger" style="margin-left: 6px;">Riesgo</span>
                      }
                    </div>
                  </td>
                  <td class="mono">{{ inv.fecha_emision }}</td>
                  <td class="mono" [class.text-danger]="inv.status === 'VENCIDA'">{{ inv.fecha_vencimiento }}</td>
                  <td class="mono">{{ inv.dias_mora > 0 ? inv.dias_mora + ' d' : '—' }}</td>
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
                          [disabled]="sendingId() === inv.id"
                          (click)="sendForInvoice(inv)"
                        >
                          {{ sendingId() === inv.id ? 'Enviando...' : 'Recordatorio' }}
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
      }
    </div>
  `,
})
export class InvoicesListComponent implements OnInit {
  readonly invoices = signal<Invoice[]>([]);
  readonly loading = signal(true);
  readonly statusFilter = signal<string>('');
  readonly sendingId = signal<number | null>(null);
  readonly feedback = signal<string | null>(null);
  readonly feedbackType = signal<'ok' | 'error'>('ok');
  search = '';

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.load();
  }

  setStatus(status: string): void {
    this.statusFilter.set(status);
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api
      .getInvoices({
        status: this.statusFilter() || undefined,
        search: this.search || undefined,
      })
      .subscribe({
        next: (data) => {
          this.invoices.set(data);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  sendForInvoice(inv: Invoice): void {
    this.sendingId.set(inv.id);
    this.feedback.set(null);
    this.api.sendReminder({ client_id: inv.client_id, invoice_id: inv.id }).subscribe({
      next: (rem) => {
        this.sendingId.set(null);
        this.feedbackType.set('ok');
        const risk = rem.marked_as_sales_risk ? ' Cliente marcado como RIESGO DE VENTA (3° aviso).' : '';
        this.feedback.set(
          `Recordatorio #${rem.reminder_sequence} enviado (${rem.status}) para Folio #${inv.folio}.${risk}`
        );
        this.load();
      },
      error: (err) => {
        this.sendingId.set(null);
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'No se pudo enviar el recordatorio.');
      },
    });
  }
}
