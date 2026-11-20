import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="shell">
      <aside class="sidebar" [class.open]="mobileMenuOpen()">
        <div class="brand-box">
          <div class="brand-mark">D</div>
          <div>
            <div class="brand-name">DABERUSA</div>
            <div class="brand-sub">Cobranza &amp; Riesgo</div>
          </div>
        </div>

        <nav class="nav-list" aria-label="Navegación principal">
          <a routerLink="/dashboard" routerLinkActive="active" (click)="closeMenu()" class="nav-item">
            <span class="nav-dot"></span> Resumen Cobranza
          </a>
          <a routerLink="/clientes" routerLinkActive="active" (click)="closeMenu()" class="nav-item">
            <span class="nav-dot"></span> Cuentas y Clientes
          </a>
          <a routerLink="/facturas" routerLinkActive="active" (click)="closeMenu()" class="nav-item">
            <span class="nav-dot"></span> Facturas (facturacion.cl)
          </a>
          <a routerLink="/recordatorios" routerLinkActive="active" (click)="closeMenu()" class="nav-item">
            <span class="nav-dot"></span> Historial Recordatorios
          </a>
          <a routerLink="/sincronizacion" routerLinkActive="active" (click)="closeMenu()" class="nav-item">
            <span class="nav-dot"></span> Automatización Scraper
          </a>
          @if (auth.isAdmin()) {
            <a routerLink="/configuracion" routerLinkActive="active" (click)="closeMenu()" class="nav-item">
              <span class="nav-dot"></span> Usuarios y SMTP
            </a>
          }
        </nav>

        <div class="sidebar-footer">
          <div class="user-chip">
            <div class="user-name">{{ auth.user()?.full_name }}</div>
            <div class="user-meta">
              <span class="role-pill">{{ auth.user()?.role }}</span>
              <span class="user-email">{{ auth.user()?.email }}</span>
            </div>
          </div>
          <button type="button" class="logout-btn" (click)="auth.logout()">
            Cerrar sesión
          </button>
        </div>
      </aside>

      <div class="main-wrap">
        <header class="mobile-bar">
          <button type="button" class="menu-toggle" (click)="toggleMenu()" aria-label="Abrir menú">
            ☰ Menú
          </button>
          <span class="mobile-title">DABERUSA · Cobranza</span>
        </header>

        <main class="content">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styles: [`
    .shell {
      display: flex;
      min-height: 100vh;
    }

    .sidebar {
      width: 256px;
      flex-shrink: 0;
      background: var(--bg-sidebar);
      color: var(--ink-inverse);
      display: flex;
      flex-direction: column;
      padding: 20px 14px;
      border-right: 1px solid #26242a;
    }

    .brand-box {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 6px 10px 20px;
      border-bottom: 1px solid #2b2930;
      margin-bottom: 18px;
    }

    .brand-mark {
      width: 36px;
      height: 36px;
      border-radius: 9px;
      background: var(--brand);
      color: #ffffff;
      font-weight: 700;
      font-size: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      letter-spacing: -0.02em;
    }

    .brand-name {
      font-size: 15px;
      font-weight: 700;
      letter-spacing: 0.06em;
    }

    .brand-sub {
      font-size: 11.5px;
      color: var(--ink-sidebar-muted);
    }

    .nav-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      color: var(--ink-sidebar-muted);
      font-size: 13.5px;
      font-weight: 500;
      text-decoration: none;
      transition: background-color 0.15s ease, color 0.15s ease;
    }

    .nav-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #4b4752;
      transition: background-color 0.15s ease;
    }

    .nav-item:hover {
      background: var(--bg-sidebar-hover);
      color: #ffffff;
      text-decoration: none;
    }

    .nav-item.active {
      background: var(--bg-sidebar-active);
      color: #ffffff;
      font-weight: 600;
    }

    .nav-item.active .nav-dot {
      background: #e16b80;
    }

    .sidebar-footer {
      border-top: 1px solid #2b2930;
      padding-top: 14px;
      margin-top: 16px;
    }

    .user-chip {
      padding: 0 6px 12px;
    }

    .user-name {
      font-size: 13px;
      font-weight: 600;
      color: #ffffff;
    }

    .user-meta {
      margin-top: 4px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .role-pill {
      display: inline-block;
      width: fit-content;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 10.5px;
      font-weight: 700;
      letter-spacing: 0.05em;
      background: rgba(124, 29, 47, 0.35);
      color: #f6b8c4;
    }

    .user-email {
      font-size: 11.5px;
      color: var(--ink-sidebar-muted);
      word-break: break-all;
    }

    .logout-btn {
      width: 100%;
      padding: 8px 12px;
      background: transparent;
      border: 1px solid #38353f;
      border-radius: 7px;
      color: #d6d3dc;
      font-family: var(--font-sans);
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 0.15s ease, color 0.15s ease;
    }

    .logout-btn:hover {
      background: #2b2831;
      color: #ffffff;
    }

    .main-wrap {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
    }

    .mobile-bar {
      display: none;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      background: var(--bg-sidebar);
      color: #ffffff;
    }

    .menu-toggle {
      background: #2b2831;
      border: 1px solid #3f3b47;
      color: #ffffff;
      padding: 6px 11px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
    }

    .mobile-title {
      font-weight: 700;
      letter-spacing: 0.04em;
      font-size: 13.5px;
    }

    .content {
      flex: 1;
      padding: 28px 32px;
      max-width: 1380px;
      width: 100%;
      margin: 0 auto;
    }

    @media (max-width: 900px) {
      .mobile-bar {
        display: flex;
      }
      .sidebar {
        position: fixed;
        inset: 0 auto 0 0;
        z-index: 900;
        transform: translateX(-100%);
        transition: transform 0.2s ease;
      }
      .sidebar.open {
        transform: translateX(0);
      }
      .content {
        padding: 20px 16px;
      }
    }
  `],
})
export class ShellComponent {
  readonly mobileMenuOpen = signal(false);

  constructor(public auth: AuthService) {}

  toggleMenu(): void {
    this.mobileMenuOpen.update((v) => !v);
  }

  closeMenu(): void {
    this.mobileMenuOpen.set(false);
  }
}
