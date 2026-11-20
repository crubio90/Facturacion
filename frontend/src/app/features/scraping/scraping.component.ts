import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { ScrapeJob, ScraperStatus } from '../../core/models/api.models';

@Component({
  selector: 'app-scraping',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-header">
      <div>
        <h1 class="page-title">Automatización Webscraping (facturacion.cl)</h1>
        <p class="page-subtitle">
          Control del contenedor Docker dedicado al scraping programado (scheduler) y bajo demanda desde el portal.
        </p>
      </div>

      @if (auth.canManageCollections()) {
        <div class="actions-row">
          <select class="select" style="width: auto;" [(ngModel)]="selectedMode" aria-label="Modo de extracción">
            <option value="mock">Modo Simulación (Datos DTE prueba)</option>
            <option value="playwright">Modo Playwright (facturacion.cl real)</option>
          </select>
          <button
            type="button"
            id="trigger-scrape-btn"
            class="btn btn-primary"
            [disabled]="running()"
            (click)="trigger()"
          >
            {{ running() ? 'Ejecutando extracción...' : 'Ejecutar Webscraping Ahora' }}
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

    <!-- Estado del contenedor scraper -->
    @if (status(); as st) {
      <section class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Contenedor Scraper</div>
          <div class="kpi-value" [class.ok]="st.reachable" [class.danger]="!st.reachable">
            {{ st.reachable ? 'Operativo' : 'Sin conexión' }}
          </div>
          <div class="kpi-meta">{{ st.detail || 'Servicio Docker independiente' }}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Modo por Defecto</div>
          <div class="kpi-value mono">{{ st.mode || '—' }}</div>
          <div class="kpi-meta">Configurable vía <code>SCRAPER_MODE</code></div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Scheduler (Cron)</div>
          <div class="kpi-value mono" style="font-size: 20px;">{{ st.schedule_cron || '—' }}</div>
          <div class="kpi-meta">Zona horaria: {{ st.timezone || 'America/Santiago' }}</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Próxima Ejecución</div>
          <div class="kpi-value mono" style="font-size: 16px;">
            {{ st.next_run_time ? (st.next_run_time | date:'dd-MM-yyyy HH:mm') : 'No programada' }}
          </div>
          <div class="kpi-meta">Estado actual: {{ st.is_running ? 'Ejecutando...' : 'En espera' }}</div>
        </div>
      </section>
    }

    <div class="card">
      <div class="card-header">
        <h2>Historial de Sincronizaciones</h2>
        <button type="button" class="btn btn-secondary btn-sm" (click)="loadAll()">Actualizar</button>
      </div>

      @if (loading()) {
        <div class="loading-box">Cargando ejecuciones...</div>
      } @else if (jobs().length === 0) {
        <div class="empty-state">
          <h3>Sin ejecuciones registradas aún</h3>
          <p>Presiona "Ejecutar Webscraping Ahora" para iniciar tu primera sincronización.</p>
        </div>
      } @else {
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Inicio</th>
                <th>Origen</th>
                <th>Modo</th>
                <th>Estado</th>
                <th class="text-right">Clientes</th>
                <th class="text-right">Nuevas / Act.</th>
                <th class="text-right">Vencidas</th>
                <th>Resumen</th>
              </tr>
            </thead>
            <tbody>
              @for (job of jobs(); track job.id) {
                <tr>
                  <td class="mono">#{{ job.id }}</td>
                  <td class="mono">{{ job.started_at | date:'dd-MM-yyyy HH:mm:ss' }}</td>
                  <td>
                    <span class="badge badge-neutral">{{ job.trigger_type }}</span>
                    <div class="text-muted" style="font-size: 11.5px;">{{ job.triggered_by_name }}</div>
                  </td>
                  <td class="mono">{{ job.mode }}</td>
                  <td>
                    <span
                      class="badge"
                      [class.badge-ok]="job.status === 'SUCCESS'"
                      [class.badge-danger]="job.status === 'FAILED'"
                      [class.badge-info]="job.status === 'RUNNING' || job.status === 'PENDING'"
                    >
                      {{ job.status }}
                    </span>
                  </td>
                  <td class="text-right mono">{{ job.clients_processed }}</td>
                  <td class="text-right mono">{{ job.invoices_created }} / {{ job.invoices_updated }}</td>
                  <td class="text-right mono fw-600" [class.text-danger]="job.overdue_detected > 0">
                    {{ job.overdue_detected }}
                  </td>
                  <td style="max-width: 320px;">
                    @if (job.error_message) {
                      <span class="text-danger">{{ job.error_message }}</span>
                    } @else {
                      <span>{{ job.log_summary || '—' }}</span>
                    }
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
export class ScrapingComponent implements OnInit {
  readonly status = signal<ScraperStatus | null>(null);
  readonly jobs = signal<ScrapeJob[]>([]);
  readonly loading = signal(true);
  readonly running = signal(false);
  readonly feedback = signal<string | null>(null);
  readonly feedbackType = signal<'ok' | 'error'>('ok');

  selectedMode: 'mock' | 'playwright' = 'mock';

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    this.loading.set(true);
    this.api.getScraperStatus().subscribe({
      next: (st) => {
        this.status.set(st);
        if (st.mode === 'playwright' || st.mode === 'mock') {
          this.selectedMode = st.mode;
        }
      },
    });
    this.api.getScrapeJobs().subscribe({
      next: (jobs) => {
        this.jobs.set(jobs);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  trigger(): void {
    this.running.set(true);
    this.feedback.set(null);
    this.api.triggerScrape(this.selectedMode).subscribe({
      next: (job) => {
        this.running.set(false);
        if (job.status === 'SUCCESS') {
          this.feedbackType.set('ok');
          this.feedback.set(job.log_summary || 'Sincronización finalizada correctamente.');
        } else {
          this.feedbackType.set('error');
          this.feedback.set(job.error_message || 'La sincronización terminó con errores.');
        }
        this.loadAll();
      },
      error: (err) => {
        this.running.set(false);
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'Error al invocar el contenedor scraper.');
        this.loadAll();
      },
    });
  }
}
