from datetime import date, timedelta
from decimal import Decimal
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configure isolated SQLite database for tests before importing app
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ["SMTP_DRY_RUN"] = "true"
os.environ["SCRAPER_INTERNAL_TOKEN"] = "test-internal-token"
os.environ["RISK_REMINDER_THRESHOLD"] = "3"

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.seed_service import seed_initial_users  # noqa: E402

engine = create_engine(
    f"sqlite:///{_tmp_db.name}",
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_initial_users(db)
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def login_token(client: TestClient, email: str, password: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def sample_ingest_payload() -> dict:
    today = date.today()
    return {
        "trigger_type": "SCHEDULED",
        "mode": "mock",
        "status": "SUCCESS",
        "clients": [
            {
                "rut": "76.543.210-K",
                "razon_social": "Botillería Los Andes SpA",
                "nombre_fantasia": "Licorería Los Andes",
                "encargado_compras_nombre": "Carolina Muñoz",
                "encargado_compras_email": "compras@losandes.cl",
                "encargado_compras_telefono": "+56 9 8123 4567",
                "credito_limite": "5000000",
                "dias_credito": 30,
                "invoices": [
                    {
                        "external_id": "DTE-33-10001",
                        "tipo_dte": "33",
                        "tipo_dte_nombre": "Factura Electrónica",
                        "folio": 10001,
                        "fecha_emision": (today - timedelta(days=50)).isoformat(),
                        "fecha_vencimiento": (today - timedelta(days=20)).isoformat(),
                        "monto_neto": "1000000",
                        "monto_iva": "190000",
                        "monto_total": "1190000",
                        "monto_pagado": "0",
                        "saldo_pendiente": "1190000",
                    },
                    {
                        "external_id": "DTE-33-10002",
                        "tipo_dte": "33",
                        "tipo_dte_nombre": "Factura Electrónica",
                        "folio": 10002,
                        "fecha_emision": (today - timedelta(days=60)).isoformat(),
                        "fecha_vencimiento": (today - timedelta(days=30)).isoformat(),
                        "fecha_pago": (today - timedelta(days=28)).isoformat(),
                        "monto_neto": "500000",
                        "monto_iva": "95000",
                        "monto_total": "595000",
                        "monto_pagado": "595000",
                        "saldo_pendiente": "0",
                    },
                ],
            }
        ],
    }


def test_health_and_rbac(client: TestClient):
    assert client.get("/health").status_code == 200

    admin_headers = login_token(client, "admin@daberusa.cl", "Admin123!")
    vendedor_headers = login_token(client, "vendedor@daberusa.cl", "Vendedor123!")

    # Admin can list users, Vendedor cannot
    assert client.get("/api/v1/users", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/users", headers=vendedor_headers).status_code == 403


def test_sync_three_reminders_sales_risk_and_seller_restriction(client: TestClient):
    # Internal ingestion rejects invalid token
    bad_ingest = client.post(
        "/api/v1/internal/sync/ingest",
        json=sample_ingest_payload(),
        headers={"X-Internal-Token": "wrong"},
    )
    assert bad_ingest.status_code == 401

    # Valid ingestion succeeds
    ingest = client.post(
        "/api/v1/internal/sync/ingest",
        json=sample_ingest_payload(),
        headers={"X-Internal-Token": "test-internal-token"},
    )
    assert ingest.status_code == 200, ingest.text
    job = ingest.json()
    assert job["clients_processed"] == 1
    assert job["invoices_created"] == 2
    assert job["overdue_detected"] == 1

    cobranza_headers = login_token(client, "cobranza@daberusa.cl", "Cobranza123!")
    vendedor_headers = login_token(client, "vendedor@daberusa.cl", "Vendedor123!")

    # Verify client list and computed overdue metrics
    clients_resp = client.get("/api/v1/clients", headers=cobranza_headers)
    assert clients_resp.status_code == 200
    clients = clients_resp.json()
    assert len(clients) == 1
    c = clients[0]
    assert c["facturas_vencidas_count"] == 1
    assert c["facturas_pagadas_count"] == 1
    assert Decimal(c["total_vencido"]) == Decimal("1190000")
    assert c["is_sales_risk"] is False

    # Vendedor cannot dispatch payment reminders
    forbidden_rem = client.post(
        "/api/v1/reminders/send",
        json={"client_id": c["id"]},
        headers=vendedor_headers,
    )
    assert forbidden_rem.status_code == 403

    # Send 1st and 2nd reminders: still NOT marked as Sales Risk
    r1 = client.post("/api/v1/reminders/send", json={"client_id": c["id"]}, headers=cobranza_headers)
    assert r1.status_code == 200, r1.text
    assert r1.json()["reminder_sequence"] == 1
    assert r1.json()["marked_as_sales_risk"] is False

    r2 = client.post("/api/v1/reminders/send", json={"client_id": c["id"]}, headers=cobranza_headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["reminder_sequence"] == 2
    assert r2.json()["marked_as_sales_risk"] is False

    # Send 3rd reminder -> MUST mark client as Cliente de Riesgo de Venta!
    r3 = client.post("/api/v1/reminders/send", json={"client_id": c["id"]}, headers=cobranza_headers)
    assert r3.status_code == 200, r3.text
    assert r3.json()["reminder_sequence"] == 3
    assert r3.json()["marked_as_sales_risk"] is True

    detail = client.get(f"/api/v1/clients/{c['id']}", headers=vendedor_headers).json()
    assert detail["client"]["is_sales_risk"] is True
    assert detail["client"]["reminder_count"] == 3
    assert len(detail["reminders"]) == 3

    # Seller restricts sale on demand when customer requests a new order
    decision_resp = client.post(
        f"/api/v1/clients/{c['id']}/risk-decision",
        json={
            "decision": "RESTRICT_SALE",
            "order_reference": "PED-2026-8841",
            "order_amount": "850000",
            "reason": "Cliente en Riesgo de Venta con 3 recordatorios sin pago. Se restringe despacho.",
        },
        headers=vendedor_headers,
    )
    assert decision_resp.status_code == 200, decision_resp.text
    assert decision_resp.json()["sale_restriction_status"] == "RESTRICTED"

    # Dashboard reflects risk & restricted counts
    dash = client.get("/api/v1/dashboard", headers=cobranza_headers).json()
    assert dash["clients_sales_risk"] == 1
    assert dash["clients_sale_restricted"] == 1
    assert dash["facturas_vencidas"] == 1
