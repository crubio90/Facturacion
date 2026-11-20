import logging
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

DEFAULT_USERS = [
    ("admin@daberusa.cl", "Administrador DABERUSA", "Admin123!", UserRole.ADMIN.value),
    ("cobranza@daberusa.cl", "Analista Cobranza DABERUSA", "Cobranza123!", UserRole.COBRANZA.value),
    ("vendedor@daberusa.cl", "Ejecutivo Ventas DABERUSA", "Vendedor123!", UserRole.VENDEDOR.value),
]


def seed_initial_users(db: Session) -> None:
    settings = get_settings()
    if not settings.AUTO_SEED_DEMO_USERS:
        return

    existing_count = db.scalar(select(User.id).limit(1))
    if existing_count is not None:
        return

    for email, full_name, raw_password, role in DEFAULT_USERS:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(raw_password),
            role=role,
            is_active=True,
        )
        db.add(user)

    db.commit()
    logger.info("Usuarios iniciales de DABERUSA creados (%d cuentas).", len(DEFAULT_USERS))
