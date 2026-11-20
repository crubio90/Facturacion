import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiService } from '../../core/services/api.service';
import { ClientSummary } from '../../core/models/api.models';
import { ClpPipe } from '../../shared/pipes/clp.pipe';

type ClientFilterTab = 'ALL' | 'OVERDUE' | 'RISK' | 'RESTRICTED';

@Component({
  selector: 'app-clients-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, ClpPipe],
  template: `
    <div class="page-header">
      <div>
        <h1 class="page-title">Cuentas de Clientes</h1>
        <p class="page-subtitle">
          Historial de cobranzas, vencimientos, contador de recordatorios y clasificación de Riesgo de Venta.
        </p>
      </div>
    </div>

    <div class="tabs">
      <button type="button" class="tab-btn" [class.active]="activeTab() === 'ALL'" (click)="setTab('ALL')">
        Todos los clientes
      </button>
      <button type="button" class="tab-btn" [class.active]="activeTab() === 'OVERDUE'" (click)="setTab('OVERDUE')">
        Con facturas vencidas
      </button>
      <button type="button" class="tab-btn" [class.active]="activeTab() === 'RISK'" (click)="setTab('RISK')">
        Riesgo de Venta (3+ avisos)
      </button>
      <button type="button" class="tab-btn" [class.active]="activeTab() === 'RESTRICTED'" (click)="setTab('RESTRICTED')">
        Venta Restringida
      </button>
    </div>

    <div class="filter-bar">
      <input
        type="search"
        class="input search-input"
        placeholder="Buscar por RUT, razón social o correo de compras..."
        [(ngModel)]="search"
        (ngModelChange)="load()"
      />
      <span class="text-muted" style="font-size: 12.5px;">{{ clients().length }} cuenta(s)</span>
    </div>

    <div class="card">
      @if (loading()) {
        <div class="loading-box">Cargando cartera de clientes...</div>
      } @else if (clients().length === 0) {
        <div class="empty-state">
          <h3>No se encontraron clientes con estos criterios</h3>
          <p>Ajusta los filtros o sincroniza los datos desde facturacion.cl.</p>
        </div>
      } @else {
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Cliente / RUT</th>
                <th>Encargado de Compras</th>
                <th class="text-right">Por Cobrar</th>
                <th class="text-right">Vencido</th>
                <th>Facturas (V / P / Pag)</th>
                <th>Avisos</th>
                <th>Riesgo &amp; Venta</th>
                <th class="text-right">Ficha</th>
              </tr>
            </thead>
            <tbody>
              @for (c of clients(); track c.id) {
                <tr>
                  <td>
                    <div class="fw-600">{{ c.razon_social }}</div>
                    <div class="mono text-muted" style="font-size: 12px;">
                      {{ c.rut }} @if (c.nombre_fantasia) { · {{ c.nombre_fantasia }} }
                    </div>
                  </td>
                  <td>
                    <div>{{ c.encargado_compras_nombre || 'Sin asignar' }}</div>
                    <div class="text-muted" style="font-size: 12px;">{{ c.encargado_compras_email || 'Sin correo' }}</div>
                  </td>
                  <td class="text-right mono">{{ c.total_por_cobrar | clp }}</td>
                  <td class="text-right mono fw-600" [class.text-danger]="+c.total_vencido > 0">
                    {{ c.total_vencido | clp }}
                  </td>
                  <td class="mono" style="font-size: 12.5px;">
                    <span [class.text-danger]="c.facturas_vencidas_count > 0">{{ c.facturas_vencidas_count }}V</span> /
                    {{ c.facturas_pendientes_count }}P /
                    <span class="text-muted">{{ c.facturas_pagadas_count }}Pag</span>
                  </td>
                  <td>
                    <div class="step-dots">
                      @for (step of [1, 2, 3]; track step) {
                        <span
                          class="step-dot"
                          [class.filled-warn]="c.reminder_count >= step && !c.is_sales_risk"
                          [class.filled-danger]="c.reminder_count >= step && c.is_sales_risk"
                        ></span>
                      }
                      <span class="mono" style="margin-left: 5px; font-size: 12px;">{{ c.reminder_count }}</span>
                    </div>
                  </td>
                  <td>
                    <div style="display: flex; flex-wrap: wrap; gap: 5px;">
                      @if (c.is_sales_risk) {
                        <span class="badge badge-danger">Riesgo de Venta</span>
                      } @else if (c.facturas_vencidas_count > 0) {
                        <span class="badge badge-warn">Mora {{ c.max_dias_mora }}d</span>
                      } @else {
                        <span class="badge badge-ok">Al día</span>
                      }

                      @if (c.sale_restriction_status === 'RESTRICTED') {
                        <span class="badge badge-brand">Restringida</span>
                      } @else if (c.sale_restriction_status === 'LIMITED') {
                        <span class="badge badge-warn">Limitada</span>
                      }
                    </div>
                  </td>
                  <td class="text-right">
                    <a [routerLink]="['/clientes', c.id]" class="btn btn-secondary btn-sm">Abrir cuenta</a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
})
export class ClientsListComponent implements OnInit {
  readonly clients = signal<ClientSummary[]>([]);
  readonly loading = signal(true);
  readonly activeTab = signal<ClientFilterTab>('ALL');
  search = '';

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.load();
  }

  setTab(tab: ClientFilterTab): void {
    this.activeTab.set(tab);
    this.load();
  }

  load(): void {
    this.loading.set(true);
    const tab = this.activeTab();
    this.api
      .getClients({
        search: this.search || undefined,
        only_overdue: tab === 'OVERDUE',
        only_sales_risk: tab === 'RISK',
        restriction_status: tab === 'RESTRICTED' ? 'RESTRICTED' : undefined,
      })
      .subscribe({
        next: (list) => {
          this.clients.set(list);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }
}
