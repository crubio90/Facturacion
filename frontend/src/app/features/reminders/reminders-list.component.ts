import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { PaymentReminder } from '../../core/models/api.models';

@Component({
  selector: 'app-reminders-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page-header">
      <div>
        <h1 class="page-title">Historial de Recordatorios de Pago</h1>
        <p class="page-subtitle">
          Trazabilidad completa de correos de cobranza enviados a encargados de compras. Al 3° aviso se marca Riesgo de Venta.
        </p>
      </div>
    </div>

    <div class="card">
      @if (loading()) {
        <div class="loading-box">Cargando historial de recordatorios...</div>
      } @else if (reminders().length === 0) {
        <div class="empty-state">
          <h3>Sin recordatorios enviados todavía</h3>
          <p>Envía un recordatorio desde el Resumen o desde la ficha de un cliente con facturas vencidas.</p>
        </div>
      } @else {
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Fecha y Hora</th>
                <th>Cliente</th>
                <th>N° Aviso</th>
                <th>Destinatario</th>
                <th>Folios</th>
                <th>Estado</th>
                <th>Ejecutado por</th>
                <th class="text-right">Detalle</th>
              </tr>
            </thead>
            <tbody>
              @for (rem of reminders(); track rem.id) {
                <tr>
                  <td class="mono">{{ rem.sent_at | date:'dd-MM-yyyy HH:mm' }}</td>
                  <td>
                    <a [routerLink]="['/clientes', rem.client_id]" class="fw-600">
                      {{ rem.client_razon_social }}
                    </a>
                    <div class="mono text-muted" style="font-size: 12px;">{{ rem.client_rut }}</div>
                  </td>
                  <td>
                    <span class="badge" [class.badge-danger]="rem.reminder_sequence >= 3" [class.badge-warn]="rem.reminder_sequence < 3">
                      #{{ rem.reminder_sequence }}
                    </span>
                  </td>
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
                    <button type="button" class="btn btn-ghost btn-sm" (click)="selected.set(rem)">
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

    @if (selected(); as rem) {
      <div class="modal-backdrop" (click)="selected.set(null)">
        <div class="modal-panel" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <h3>Recordatorio #{{ rem.reminder_sequence }} — {{ rem.client_razon_social }}</h3>
            <button type="button" class="btn btn-ghost btn-sm" (click)="selected.set(null)">✕</button>
          </div>
          <div class="modal-body">
            <div style="margin-bottom: 12px; font-size: 13px;">
              <div><strong>Destinatario:</strong> <span class="mono">{{ rem.recipient_email }}</span></div>
              <div><strong>Asunto:</strong> {{ rem.subject }}</div>
              <div><strong>Fecha:</strong> <span class="mono">{{ rem.sent_at | date:'dd-MM-yyyy HH:mm:ss' }}</span></div>
            </div>
            <pre class="email-preview">{{ rem.body_preview }}</pre>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" (click)="selected.set(null)">Cerrar</button>
          </div>
        </div>
      </div>
    }
  `,
})
export class RemindersListComponent implements OnInit {
  readonly reminders = signal<PaymentReminder[]>([]);
  readonly loading = signal(true);
  readonly selected = signal<PaymentReminder | null>(null);

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.getReminders().subscribe({
      next: (data) => {
        this.reminders.set(data);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  formatFolios(folios: number[]): string {
    return folios.map((f) => `#${f}`).join(', ');
  }
}
