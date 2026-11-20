#!/bin/sh
set -e

echo "[backend] Ejecutando migraciones de base de datos (Alembic)..."
alembic upgrade head

echo "[backend] Iniciando servidor FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
