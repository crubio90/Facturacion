# DABERUSA — Sistema Web de Cobranza y Control de Riesgo de Venta

Sistema web de gestión y trazabilidad de cobranzas desarrollado para **DABERUSA** (distribuidora de licores y bebidas analcohólicas), integrado con sincronización automática y bajo demanda desde **facturacion.cl**.

## Arquitectura (4 Contenedores Docker Independientes)

| Contenedor | Tecnología | Puerto (defecto) | Responsabilidad |
|---|---|---|---|
| `db` | PostgreSQL 16 (`postgres:16-alpine`) | `5432` | Almacenamiento relacional persistente de clientes, DTE/facturas, recordatorios, ejecuciones de scraping y bitácora de decisiones comerciales. |
| `backend` | FastAPI + SQLAlchemy 2.0 + Alembic + PyJWT | `8000` | API REST (`/api/v1`), autenticación JWT con roles, reglas de morosidad y Riesgo de Venta, envío SMTP y orquestación del scraper. |
| `scraper` | Python + Playwright Chromium + APScheduler + FastAPI | `8001` | Automatización de webscraping hacia `facturacion.cl` mediante **scheduler cron** y también **on-demand** invocado desde el portal web. Incluye modo simulación (`mock`) y modo real (`playwright`). |
| `frontend` | Angular 19 (Standalone Components) + Nginx | `8080` | Portal web responsive de Cobranzas y Riesgo Comercial con proxy inverso `/api/` hacia el backend. |

---

## Funcionalidades Principales

1. **Sincronización con `facturacion.cl` (Scheduler + On-Demand)**:
   - El contenedor `scraper` ejecuta un scheduler configurable vía cron (`SCRAPE_SCHEDULE_CRON`, zona horaria `America/Santiago`) y expone un endpoint interno (`POST /scrape/run`) para que usuarios de `COBRANZA` o `ADMIN` disparen una actualización inmediata desde el portal.
   - Modo `mock` incluido con cuentas y facturas chilenas realistas (RUTs, DTE tipo 33 vencidos, pendientes y pagados) para validar todo el flujo end-to-end antes de ingresar credenciales productivas.
   - Modo `playwright` modular con selectores CSS configurables (`scraper/selectors.example.json` → `scraper/selectors.json`) para adaptarse al sistema específico contratado en `facturacion.cl`.

2. **Recordatorios de Pago al Encargado de Compras**:
   - Envío individual (por factura vencida o consolidado por cliente) y masivo a todos los clientes con facturas vencidas.
   - Registro completo en base de datos (`payment_reminders`): fecha y hora exacta, N° de aviso (`1°`, `2°`, `3°`...), folios incluidos, correo destinatario, estado (`SENT`, `DRY_RUN`, `FAILED`) y vista previa del correo enviado.
   - Servicio SMTP estándar configurable para **Gmail**, **Microsoft 365** o servidor corporativo propio.

3. **Regla Automática de Cliente de Riesgo de Venta (3° Recordatorio)**:
   - Al alcanzar el **tercer envío de recordatorio de pago** (`RISK_REMINDER_THRESHOLD=3`), el sistema marca automáticamente al cliente como **Cliente de Riesgo de Venta** (`is_sales_risk = true`) registrando fecha y motivo.

4. **Restricción o Limitación de Venta a Demanda del Vendedor**:
   - Cuando un cliente solicita un nuevo pedido a DABERUSA, el vendedor visualiza de inmediato el banner de **Riesgo de Venta** en la ficha del cliente y puede aplicar a demanda:
     - **Restringir / Bloquear venta** (`RESTRICT_SALE`)
     - **Limitar venta** — ej. solo pago contado o cupo reducido (`LIMIT_SALE`)
     - **Autorizar pedido por excepción** (`ALLOW_EXCEPTION`)
     - **Levantar Riesgo de Venta** una vez regularizada la deuda (`CLEAR_RISK`)
   - Cada resolución queda auditada en `sale_risk_decisions` con usuario, fecha, número de pedido, monto y motivo.

5. **Autenticación JWT y Roles**:
   - `ADMIN`: Gestión total, usuarios, configuración SMTP, scraping, cobranza y decisiones de riesgo.
   - `COBRANZA`: Gestión de cuentas, edición de contacto de compras, disparo de scraping y envío de recordatorios.
   - `VENDEDOR`: Consulta de estado de cuentas/morosidad, alerta de Riesgo de Venta y aplicación de restricciones de venta a demanda.

---

## Puesta en Marcha Rápida con Docker Compose

```bash
# 1. Crear archivo de variables de entorno
cp .env.example .env

# 2. Construir y levantar los 4 contenedores
docker compose up --build -d

# 3. Verificar estado de los servicios
docker compose ps
```

Accesos locales una vez levantado:
- **Portal Web Angular**: `http://localhost:8080`
- **API FastAPI (Swagger / OpenAPI)**: `http://localhost:8000/docs`
- **Healthcheck Scraper**: `http://localhost:8001/health`

### Usuarios Iniciales de Prueba (`AUTO_SEED_DEMO_USERS=true`)

| Rol | Correo | Contraseña |
|---|---|---|
| `ADMIN` | `admin@daberusa.cl` | `Admin123!` |
| `COBRANZA` | `cobranza@daberusa.cl` | `Cobranza123!` |
| `VENDEDOR` | `vendedor@daberusa.cl` | `Vendedor123!` |

> **Importante para producción:** Cambia estas contraseñas, reemplaza `JWT_SECRET_KEY`, `SCRAPER_INTERNAL_TOKEN` y `POSTGRES_PASSWORD` en `.env`, y define `AUTO_SEED_DEMO_USERS=false`.

---

## Configuración de Correo SMTP Real

Por defecto `.env.example` inicia con `SMTP_DRY_RUN=true` para que puedas probar los 3 envíos de recordatorios y la marcación de **Riesgo de Venta** sin enviar correos reales.

Para activar envíos reales (Microsoft 365, Gmail o SMTP propio), edita `.env`:

```env
SMTP_DRY_RUN=false
SMTP_HOST=smtp.office365.com        # o smtp.gmail.com
SMTP_PORT=587
SMTP_USER=cobranza@daberusa.cl
SMTP_PASSWORD=tu_clave_de_aplicacion
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_FROM_EMAIL=cobranza@daberusa.cl
SMTP_FROM_NAME=Cobranza DABERUSA
```

Luego reinicia el backend: `docker compose up -d backend`.

---

## Configuración de Scraping Real en `facturacion.cl`

1. Copia la plantilla de selectores:
   ```bash
   cp scraper/selectors.example.json scraper/selectors.json
   ```
2. Ajusta los selectores CSS/columnas en `scraper/selectors.json` según el HTML de la vista de Cuentas Corrientes / Documentos Emitidos de tu portal en `facturacion.cl`.
3. Monta `./scraper/selectors.json:/app/selectors.json:ro` en el servicio `scraper` de `docker-compose.yml` y configura en `.env`:
   ```env
   SCRAPER_MODE=playwright
   FACTURACION_BASE_URL=https://www.facturacion.cl
   FACTURACION_SYSTEM_SLUG=tu_sistema
   FACTURACION_USERNAME=tu_usuario
   FACTURACION_PASSWORD=tu_clave
   ```
4. Si ocurre un error de login o timeout, el scraper guarda capturas de diagnóstico en `scraper/debug_screenshots/`.

---

## Pruebas Automatizadas

```bash
# Backend (FastAPI + reglas de negocio + RBAC + 3° recordatorio -> Riesgo de Venta)
cd backend && pytest tests -v

# Scraper (parsers CLP/fechas chilenas + modo simulación)
cd scraper && pytest tests -v

# Frontend (compilación producción Angular 19)
cd frontend && npm install && npm run build
```
