import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { SystemConfigSummary, User, UserRole } from '../../core/models/api.models';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page-header">
      <div>
        <h1 class="page-title">Usuarios y Configuración del Sistema</h1>
        <p class="page-subtitle">
          Administración de cuentas por rol (Admin, Cobranza, Vendedor) y verificación de SMTP y reglas de Riesgo de Venta.
        </p>
      </div>
    </div>

    @if (feedback()) {
      <div class="alert" [class.alert-ok]="feedbackType() === 'ok'" [class.alert-danger]="feedbackType() === 'error'">
        <span>{{ feedback() }}</span>
        <button type="button" class="btn btn-ghost btn-sm" (click)="feedback.set(null)">Cerrar</button>
      </div>
    }

    @if (config(); as cfg) {
      <div class="card" style="margin-bottom: 22px;">
        <div class="card-header">
          <h2>Parámetros SMTP y Regla de Negocio</h2>
          <span class="badge" [class.badge-ok]="cfg.smtp_configured" [class.badge-warn]="!cfg.smtp_configured">
            {{ cfg.smtp_configured ? 'SMTP Real Activo' : 'Modo Simulación (DRY_RUN)' }}
          </span>
        </div>
        <div class="card-body">
          <div class="config-grid">
            <div>
              <div class="text-muted" style="font-size: 12px;">Empresa</div>
              <div class="fw-600">{{ cfg.company_name }}</div>
            </div>
            <div>
              <div class="text-muted" style="font-size: 12px;">Umbral Riesgo de Venta</div>
              <div class="fw-600 mono">{{ cfg.risk_reminder_threshold }} recordatorios enviados</div>
            </div>
            <div>
              <div class="text-muted" style="font-size: 12px;">Servidor SMTP</div>
              <div class="mono">{{ cfg.smtp_host || '(sin configurar)' }}:{{ cfg.smtp_port }} (TLS: {{ cfg.smtp_use_tls ? 'Sí' : 'No' }})</div>
            </div>
            <div>
              <div class="text-muted" style="font-size: 12px;">Remitente</div>
              <div class="mono">{{ cfg.smtp_from_name }} &lt;{{ cfg.smtp_from_email }}&gt;</div>
            </div>
          </div>
          <p class="text-muted" style="margin: 14px 0 0; font-size: 12.5px;">
            Para activar el envío real de correos vía Gmail, Microsoft 365 o SMTP corporativo, configura
            <code>SMTP_DRY_RUN=false</code>, <code>SMTP_HOST</code>, <code>SMTP_USER</code> y <code>SMTP_PASSWORD</code> en tu archivo <code>.env</code> y reinicia el contenedor <code>backend</code>.
          </p>
        </div>
      </div>
    }

    @if (auth.isAdmin()) {
      <div class="two-col">
        <div class="card">
          <div class="card-header">
            <h2>Crear Nuevo Usuario</h2>
          </div>
          <div class="card-body">
            <form (ngSubmit)="createUser()" class="user-form">
              <div class="form-field">
                <label>Nombre completo</label>
                <input class="input" [(ngModel)]="newUser.full_name" name="full_name" required placeholder="Ej. Juan Pérez" />
              </div>
              <div class="form-field">
                <label>Correo electrónico</label>
                <input class="input" type="email" [(ngModel)]="newUser.email" name="email" required placeholder="j.perez@daberusa.cl" />
              </div>
              <div class="form-field">
                <label>Contraseña temporal</label>
                <input class="input" type="password" [(ngModel)]="newUser.password" name="password" required minlength="6" placeholder="Mínimo 6 caracteres" />
              </div>
              <div class="form-field">
                <label>Rol</label>
                <select class="select" [(ngModel)]="newUser.role" name="role">
                  <option value="COBRANZA">COBRANZA (Gestiona recordatorios y scraping)</option>
                  <option value="VENDEDOR">VENDEDOR (Consulta riesgo y restringe ventas)</option>
                  <option value="ADMIN">ADMIN (Control total del portal)</option>
                </select>
              </div>
              <button type="submit" class="btn btn-primary" [disabled]="creating()">
                {{ creating() ? 'Creando...' : 'Crear usuario' }}
              </button>
            </form>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h2>Usuarios Registrados ({{ users().length }})</h2>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Correo</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th class="text-right">Acción</th>
                </tr>
              </thead>
              <tbody>
                @for (u of users(); track u.id) {
                  <tr>
                    <td class="fw-600">{{ u.full_name }}</td>
                    <td class="mono" style="font-size: 12.5px;">{{ u.email }}</td>
                    <td><span class="badge badge-brand">{{ u.role }}</span></td>
                    <td>
                      <span class="badge" [class.badge-ok]="u.is_active" [class.badge-neutral]="!u.is_active">
                        {{ u.is_active ? 'Activo' : 'Inactivo' }}
                      </span>
                    </td>
                    <td class="text-right">
                      <button
                        type="button"
                        class="btn btn-secondary btn-sm"
                        [disabled]="u.id === auth.user()?.id"
                        (click)="toggleActive(u)"
                      >
                        {{ u.is_active ? 'Desactivar' : 'Reactivar' }}
                      </button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .config-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
    }

    .two-col {
      display: grid;
      grid-template-columns: 0.8fr 1.2fr;
      gap: 18px;
      align-items: start;
    }

    .user-form {
      display: flex;
      flex-direction: column;
      gap: 13px;
    }

    @media (max-width: 960px) {
      .two-col {
        grid-template-columns: 1fr;
      }
    }
  `],
})
export class SettingsComponent implements OnInit {
  readonly users = signal<User[]>([]);
  readonly config = signal<SystemConfigSummary | null>(null);
  readonly creating = signal(false);
  readonly feedback = signal<string | null>(null);
  readonly feedbackType = signal<'ok' | 'error'>('ok');

  newUser: { full_name: string; email: string; password: string; role: UserRole } = {
    full_name: '',
    email: '',
    password: '',
    role: 'COBRANZA',
  };

  constructor(private api: ApiService, public auth: AuthService) {}

  ngOnInit(): void {
    this.api.getSystemConfig().subscribe({ next: (c) => this.config.set(c) });
    if (this.auth.isAdmin()) {
      this.loadUsers();
    }
  }

  loadUsers(): void {
    this.api.getUsers().subscribe({ next: (list) => this.users.set(list) });
  }

  createUser(): void {
    this.creating.set(true);
    this.feedback.set(null);
    this.api.createUser(this.newUser).subscribe({
      next: () => {
        this.creating.set(false);
        this.newUser = { full_name: '', email: '', password: '', role: 'COBRANZA' };
        this.feedbackType.set('ok');
        this.feedback.set('Usuario creado correctamente.');
        this.loadUsers();
      },
      error: (err) => {
        this.creating.set(false);
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'No se pudo crear el usuario.');
      },
    });
  }

  toggleActive(u: User): void {
    this.api.updateUser(u.id, { is_active: !u.is_active }).subscribe({
      next: () => {
        this.feedbackType.set('ok');
        this.feedback.set(`Usuario ${u.email} ${u.is_active ? 'desactivado' : 'reactivado'}.`);
        this.loadUsers();
      },
      error: (err) => {
        this.feedbackType.set('error');
        this.feedback.set(err?.error?.detail || 'No se pudo actualizar el usuario.');
      },
    });
  }
}
