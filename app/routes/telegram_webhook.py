from fastapi import Request
from fastapi.routing import APIRouter
from telegram import Update
from app.telegram.bot import app_tg
from app.core.logging_config import get_logger
import os

logger = get_logger(__name__)

router = APIRouter()

DOMAIN = os.getenv("RAILWAY_DOMAIN", "localhost:8000")
WEBHOOK_URL = f"https://{DOMAIN}/telegram-webhook"

@router.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    logger.info("Получен webhook от Telegram")
    data = await request.json()
    update = Update.de_json(data, app_tg.bot)
    await app_tg.process_update(update)
    logger.info("Обновление обработано Telegram Bot API")
    return {"ok": True}