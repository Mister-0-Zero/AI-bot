import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import USE_POLLING, RAILWAY_DOMAIN
from app.core.db import init_db
from app.telegram.bot import app_tg
from app.telegram.handlers import register_handlers

WEBHOOK_PATH = "/telegram-webhook"
WEBHOOK_URL = f"https://{RAILWAY_DOMAIN}{WEBHOOK_PATH}" if RAILWAY_DOMAIN else None

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    register_handlers()

    if USE_POLLING:
        def _run():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(app_tg.run_polling())

        threading.Thread(target=_run, daemon=True).start()
    else:
        await app_tg.initialize()
        logger.info(f"Установка webhook: {WEBHOOK_URL}")
        await app_tg.bot.set_webhook(url=WEBHOOK_URL)

    yield

    if not USE_POLLING:
        await app_tg.bot.delete_webhook(drop_pending_updates=True)
        await app_tg.shutdown()