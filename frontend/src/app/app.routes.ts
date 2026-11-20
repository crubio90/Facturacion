import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { ShellComponent } from './shared/layout/shell.component';
import { LoginComponent } from './features/login/login.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { ClientsListComponent } from './features/clients/clients-list.component';
import { ClientDetailComponent } from './features/clients/client-detail.component';
import { InvoicesListComponent } from './features/invoices/invoices-list.component';
import { RemindersListComponent } from './features/reminders/reminders-list.component';
import { ScrapingComponent } from './features/scraping/scraping.component';
import { SettingsComponent } from './features/settings/settings.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', component: DashboardComponent },
      { path: 'clientes', component: ClientsListComponent },
      { path: 'clientes/:id', component: ClientDetailComponent },
      { path: 'facturas', component: InvoicesListComponent },
      { path: 'recordatorios', component: RemindersListComponent },
      { path: 'sincronizacion', component: ScrapingComponent },
      { path: 'configuracion', component: SettingsComponent },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
