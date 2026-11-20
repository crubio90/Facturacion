export type UserRole = 'ADMIN' | 'COBRANZA' | 'VENDEDOR';
export type SaleRestrictionStatus = 'NONE' | 'LIMITED' | 'RESTRICTED';
export type RiskDecisionType = 'RESTRICT_SALE' | 'LIMIT_SALE' | 'ALLOW_EXCEPTION' | 'CLEAR_RISK';
export type InvoiceStatus = 'PENDIENTE' | 'VENCIDA' | 'PAGADA' | 'ANULADA';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ClientSummary {
  id: number;
  rut: string;
  razon_social: string;
  nombre_fantasia: string | null;
  encargado_compras_nombre: string | null;
  encargado_compras_email: string | null;
  encargado_compras_telefono: string | null;
  credito_limite: string | number;
  dias_credito: number;

  reminder_count: number;
  last_reminder_at: string | null;
  is_sales_risk: boolean;
  sales_risk_marked_at: string | null;
  sales_risk_reason: string | null;

  sale_restriction_status: SaleRestrictionStatus;
  sale_restriction_note: string | null;
  sale_restriction_updated_at: string | null;
  last_synced_at: string | null;

  total_por_cobrar: string | number;
  total_vencido: string | number;
  total_pagado: string | number;
  facturas_pendientes_count: number;
  facturas_vencidas_count: number;
  facturas_pagadas_count: number;
  max_dias_mora: number;
}

export interface Invoice {
  id: number;
  client_id: number;
  client_rut: string | null;
  client_razon_social: string | null;
  client_is_sales_risk: boolean;
  external_id: string;
  tipo_dte: string;
  tipo_dte_nombre: string;
  folio: number;
  fecha_emision: string;
  fecha_vencimiento: string;
  fecha_pago: string | null;
  monto_neto: string | number;
  monto_iva: string | number;
  monto_total: string | number;
  monto_pagado: string | number;
  saldo_pendiente: string | number;
  status: InvoiceStatus;
  dias_mora: number;
  source_url: string | null;
  last_synced_at: string | null;
}

export interface PaymentReminder {
  id: number;
  client_id: number;
  client_rut: string | null;
  client_razon_social: string | null;
  invoice_id: number | null;
  invoice_ids: number[];
  invoice_folios: number[];
  recipient_email: string;
  recipient_name: string | null;
  subject: string;
  body_preview: string;
  reminder_sequence: number;
  status: 'SENT' | 'DRY_RUN' | 'FAILED';
  error_message: string | null;
  trigger_type: string;
  triggered_by_name: string | null;
  sent_at: string;
  marked_as_sales_risk: boolean;
}

export interface BulkReminderResult {
  total_targeted: number;
  sent_count: number;
  dry_run_count: number;
  failed_count: number;
  skipped_count: number;
  newly_marked_risk_clients: string[];
  reminders: PaymentReminder[];
}

export interface SaleRiskDecision {
  id: number;
  client_id: number;
  user_id: number | null;
  user_name: string | null;
  decision: RiskDecisionType;
  order_reference: string | null;
  order_amount: string | number | null;
  reason: string;
  created_at: string;
}

export interface ClientDetailResponse {
  client: ClientSummary;
  invoices: Invoice[];
  reminders: PaymentReminder[];
  risk_decisions: SaleRiskDecision[];
}

export interface ScrapeJob {
  id: number;
  trigger_type: string;
  mode: string;
  status: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED';
  triggered_by_name: string | null;
  started_at: string;
  finished_at: string | null;
  clients_processed: number;
  invoices_created: number;
  invoices_updated: number;
  overdue_detected: number;
  log_summary: string | null;
  error_message: string | null;
}

export interface ScraperStatus {
  reachable: boolean;
  mode: string | null;
  schedule_cron: string | null;
  timezone: string | null;
  next_run_time: string | null;
  is_running: boolean;
  detail: string | null;
}

export interface DashboardMetrics {
  total_clients: number;
  clients_with_overdue: number;
  clients_sales_risk: number;
  clients_sale_restricted: number;
  total_por_cobrar: string | number;
  total_vencido: string | number;
  total_pagado: string | number;
  facturas_pendientes: number;
  facturas_vencidas: number;
  facturas_pagadas: number;
  reminders_sent_30d: number;
  risk_reminder_threshold: number;
  smtp_configured: boolean;
  smtp_dry_run: boolean;
  last_scrape_job: ScrapeJob | null;
  priority_clients: ClientSummary[];
}

export interface SystemConfigSummary {
  company_name: string;
  risk_reminder_threshold: number;
  smtp_dry_run: boolean;
  smtp_host: string;
  smtp_port: number;
  smtp_from_email: string;
  smtp_from_name: string;
  smtp_use_tls: boolean;
  smtp_configured: boolean;
  scraper_service_url: string;
  server_time: string;
}
