from fastapi import FastAPI

from app.routes.oauth import router as oauth_router
from app.routes.telegram_webhook import router as telegram_router


def setup_routes(app: FastAPI):
    app.include_router(telegram_router)
    app.include_router(oauth_router)
