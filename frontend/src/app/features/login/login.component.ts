import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-page">
      <div class="login-shell">
        <section class="login-brand">
          <div class="brand-badge">DABERUSA</div>
          <h1>Portal de Cobranza y Control de Riesgo Comercial</h1>
          <p>
            Centraliza cuentas corrientes sincronizadas desde <strong>facturacion.cl</strong>,
            gestiona recordatorios de pago al encargado de compras y alerta al equipo de ventas
            al tercer aviso para restringir o limitar nuevos pedidos.
          </p>
          <ul class="feature-list">
            <li>Sincronización automática (scheduler) y on-demand con facturacion.cl</li>
            <li>Registro completo de historial de recordatorios de pago</li>
            <li>Marcación automática de Riesgo de Venta al 3° envío</li>
            <li>Control de restricción comercial a demanda del vendedor</li>
          </ul>
        </section>

        <section class="login-card">
          <h2>Iniciar sesión</h2>
          <p class="subtitle">Ingresa con tu cuenta corporativa de DABERUSA.</p>

          @if (error()) {
            <div class="alert alert-danger">{{ error() }}</div>
          }

          <form (ngSubmit)="submit()" class="login-form">
            <div class="form-field">
              <label for="email">Correo electrónico</label>
              <input
                id="email"
                name="email"
                type="email"
                class="input"
                [(ngModel)]="email"
                placeholder="usuario@daberusa.cl"
                required
              />
            </div>

            <div class="form-field">
              <label for="password">Contraseña</label>
              <input
                id="password"
                name="password"
                type="password"
                class="input"
                [(ngModel)]="password"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              id="login-submit-btn"
              class="btn btn-primary full-width"
              [disabled]="loading()"
            >
              {{ loading() ? 'Ingresando...' : 'Entrar al portal' }}
            </button>
          </form>

          <div class="demo-box">
            <div class="demo-title">Accesos iniciales de prueba</div>
            <div class="demo-grid">
              <button type="button" class="demo-btn" (click)="fillDemo('admin@daberusa.cl', 'Admin123!')">
                <strong>Admin</strong><span>admin&#64;daberusa.cl</span>
              </button>
              <button type="button" class="demo-btn" (click)="fillDemo('cobranza@daberusa.cl', 'Cobranza123!')">
                <strong>Cobranza</strong><span>cobranza&#64;daberusa.cl</span>
              </button>
              <button type="button" class="demo-btn" (click)="fillDemo('vendedor@daberusa.cl', 'Vendedor123!')">
                <strong>Vendedor</strong><span>vendedor&#64;daberusa.cl</span>
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  `,
  styles: [`
    .login-page {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      background: var(--bg-canvas);
    }

    .login-shell {
      width: 100%;
      max-width: 960px;
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: var(--shadow-md);
    }

    .login-brand {
      background: #18171a;
      color: #f7f5f2;
      padding: 44px 40px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

    .brand-badge {
      width: fit-content;
      padding: 5px 11px;
      border-radius: 6px;
      background: var(--brand);
      color: #ffffff;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.1em;
      margin-bottom: 20px;
    }

    .login-brand h1 {
      margin: 0 0 14px;
      font-size: 26px;
      line-height: 1.25;
      letter-spacing: -0.02em;
    }

    .login-brand p {
      margin: 0 0 24px;
      color: #b7b3bf;
      font-size: 14px;
      line-height: 1.65;
    }

    .feature-list {
      margin: 0;
      padding-left: 18px;
      color: #dad6e0;
      font-size: 13.5px;
      display: flex;
      flex-direction: column;
      gap: 9px;
    }

    .login-card {
      padding: 44px 38px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

    .login-card h2 {
      margin: 0;
      font-size: 21px;
      font-weight: 700;
    }

    .subtitle {
      margin: 6px 0 22px;
      color: var(--ink-secondary);
      font-size: 13.5px;
    }

    .login-form {
      display: flex;
      flex-direction: column;
      gap: 15px;
    }

    .full-width {
      width: 100%;
      padding: 10px 16px;
      margin-top: 4px;
    }

    .demo-box {
      margin-top: 26px;
      padding-top: 18px;
      border-top: 1px solid var(--border);
    }

    .demo-title {
      font-size: 11.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--ink-muted);
      margin-bottom: 10px;
    }

    .demo-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 8px;
    }

    .demo-btn {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
      padding: 8px 9px;
      background: #faf9f6;
      border: 1px solid var(--border);
      border-radius: 7px;
      cursor: pointer;
      text-align: left;
      font-family: var(--font-sans);
      transition: border-color 0.15s ease, background-color 0.15s ease;
    }

    .demo-btn:hover {
      border-color: var(--brand);
      background: var(--brand-soft);
    }

    .demo-btn strong {
      font-size: 12px;
      color: var(--ink-primary);
    }

    .demo-btn span {
      font-size: 10.5px;
      color: var(--ink-muted);
      word-break: break-all;
    }

    @media (max-width: 820px) {
      .login-shell {
        grid-template-columns: 1fr;
      }
      .login-brand, .login-card {
        padding: 30px 24px;
      }
      .demo-grid {
        grid-template-columns: 1fr;
      }
    }
  `],
})
export class LoginComponent {
  email = '';
  password = '';
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  constructor(private auth: AuthService, private router: Router) {
    if (this.auth.isAuthenticated()) {
      this.router.navigate(['/dashboard']);
    }
  }

  fillDemo(email: string, password: string): void {
    this.email = email;
    this.password = password;
    this.error.set(null);
  }

  submit(): void {
    if (!this.email || !this.password) return;
    this.loading.set(true);
    this.error.set(null);

    this.auth.login(this.email, this.password).subscribe({
      next: () => {
        this.loading.set(false);
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.error?.detail || 'No fue posible iniciar sesión.');
      },
    });
  }
}
