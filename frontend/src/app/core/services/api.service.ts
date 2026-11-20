import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  BulkReminderResult,
  ClientDetailResponse,
  ClientSummary,
  DashboardMetrics,
  Invoice,
  PaymentReminder,
  RiskDecisionType,
  ScrapeJob,
  ScraperStatus,
  SystemConfigSummary,
  User,
  UserRole,
} from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly base = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  getDashboard(): Observable<DashboardMetrics> {
    return this.http.get<DashboardMetrics>(`${this.base}/dashboard`);
  }

  getClients(filters?: {
    search?: string;
    only_overdue?: boolean;
    only_sales_risk?: boolean;
    restriction_status?: string;
  }): Observable<ClientSummary[]> {
    let params = new HttpParams();
    if (filters?.search) params = params.set('search', filters.search);
    if (filters?.only_overdue) params = params.set('only_overdue', 'true');
    if (filters?.only_sales_risk) params = params.set('only_sales_risk', 'true');
    if (filters?.restriction_status) params = params.set('restriction_status', filters.restriction_status);
    return this.http.get<ClientSummary[]>(`${this.base}/clients`, { params });
  }

  getClientDetail(clientId: number): Observable<ClientDetailResponse> {
    return this.http.get<ClientDetailResponse>(`${this.base}/clients/${clientId}`);
  }

  updateClient(
    clientId: number,
    payload: {
      nombre_fantasia?: string | null;
      encargado_compras_nombre?: string | null;
      encargado_compras_email?: string | null;
      encargado_compras_telefono?: string | null;
      credito_limite?: number;
      dias_credito?: number;
    }
  ): Observable<ClientSummary> {
    return this.http.patch<ClientSummary>(`${this.base}/clients/${clientId}`, payload);
  }

  applyRiskDecision(
    clientId: number,
    payload: {
      decision: RiskDecisionType;
      order_reference?: string | null;
      order_amount?: number | null;
      reason: string;
    }
  ): Observable<ClientSummary> {
    return this.http.post<ClientSummary>(`${this.base}/clients/${clientId}/risk-decision`, payload);
  }

  getInvoices(filters?: {
    status?: string;
    client_id?: number;
    search?: string;
  }): Observable<Invoice[]> {
    let params = new HttpParams();
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.client_id) params = params.set('client_id', String(filters.client_id));
    if (filters?.search) params = params.set('search', filters.search);
    return this.http.get<Invoice[]>(`${this.base}/invoices`, { params });
  }

  getReminders(clientId?: number): Observable<PaymentReminder[]> {
    let params = new HttpParams();
    if (clientId) params = params.set('client_id', String(clientId));
    return this.http.get<PaymentReminder[]>(`${this.base}/reminders`, { params });
  }

  sendReminder(payload: {
    client_id: number;
    invoice_id?: number | null;
    override_email?: string | null;
    custom_note?: string | null;
  }): Observable<PaymentReminder> {
    return this.http.post<PaymentReminder>(`${this.base}/reminders/send`, payload);
  }

  sendBulkReminders(payload: {
    only_clients_with_email?: boolean;
    exclude_already_risk?: boolean;
    custom_note?: string | null;
  }): Observable<BulkReminderResult> {
    return this.http.post<BulkReminderResult>(`${this.base}/reminders/send-bulk`, payload);
  }

  getScraperStatus(): Observable<ScraperStatus> {
    return this.http.get<ScraperStatus>(`${this.base}/scrape/status`);
  }

  getScrapeJobs(): Observable<ScrapeJob[]> {
    return this.http.get<ScrapeJob[]>(`${this.base}/scrape/jobs`);
  }

  triggerScrape(mode?: 'mock' | 'playwright'): Observable<ScrapeJob> {
    return this.http.post<ScrapeJob>(`${this.base}/scrape/trigger`, mode ? { mode } : {});
  }

  getUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${this.base}/users`);
  }

  createUser(payload: {
    email: string;
    full_name: string;
    password: string;
    role: UserRole;
  }): Observable<User> {
    return this.http.post<User>(`${this.base}/users`, payload);
  }

  updateUser(
    userId: number,
    payload: {
      full_name?: string;
      role?: UserRole;
      is_active?: boolean;
      password?: string;
    }
  ): Observable<User> {
    return this.http.patch<User>(`${this.base}/users/${userId}`, payload);
  }

  getSystemConfig(): Observable<SystemConfigSummary> {
    return this.http.get<SystemConfigSummary>(`${this.base}/system/config`);
  }
}
