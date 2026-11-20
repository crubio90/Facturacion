from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.services.seed_service import seed_initial_users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Ensure schema exists when running outside Alembic (e.g. SQLite tests/dev)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_initial_users(db)
    finally:
        db.close()
    yield


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API REST del Sistema Web de Cobranzas y Control de Riesgo de Venta para DABERUSA. "
        "Integrado con contenedor de automatización webscraping de facturacion.cl."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Sistema"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "daberusa-cobranza-backend"}
