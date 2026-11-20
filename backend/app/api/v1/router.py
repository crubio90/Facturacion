from fastapi import APIRouter

from app.api.v1 import auth, clients, dashboard, invoices, reminders, scrape, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(clients.router)
api_router.include_router(invoices.router)
api_router.include_router(reminders.router)
api_router.include_router(scrape.router)
api_router.include_router(users.router)
