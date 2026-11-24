#!/usr/bin/env bash
set -euo pipefail

echo "============================================================"
echo " DABERUSA - Instalador y Arranque Local (Docker Compose)"
echo "============================================================"

command -v git >/dev/null 2>&1 || { echo "[ERROR] Git no está instalado."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "[ERROR] Docker no está instalado."; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "[ERROR] Docker Compose v2 no está disponible."; exit 1; }

if [ ! -f ".env" ]; then
  echo "[1/4] Creando archivo .env desde .env.example..."
  cp .env.example .env
else
  echo "[1/4] Archivo .env ya existe (se conserva configuración actual)."
fi

echo "[2/4] Construyendo e iniciando los 4 contenedores (db, backend, scraper, frontend)..."
docker compose up --build -d

echo "[3/4] Esperando disponibilidad de servicios..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:${BACKEND_PORT:-8000}/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "[4/4] Estado actual de los contenedores:"
docker compose ps

echo ""
echo "Listo! Servicios disponibles:"
echo "  - Portal Web Angular : http://localhost:${FRONTEND_PORT:-8080}"
echo "  - API Swagger        : http://localhost:${BACKEND_PORT:-8000}/docs"
echo "  - Scraper Health     : http://localhost:${SCRAPER_PORT:-8001}/health"
echo ""
echo "Accesos demo: admin@daberusa.cl / Admin123! | cobranza@daberusa.cl / Cobranza123! | vendedor@daberusa.cl / Vendedor123!"
