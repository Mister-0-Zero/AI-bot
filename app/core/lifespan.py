import asyncio
import threading
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.core.config import USE_POLLING
from app.core.db import init_db
from app.core.logging_config import get_logger
from app.telegram.bot import app_tg
from app.telegram.handlers import register_handlers

logger = get_logger(__name__)

WEBHOOK_PATH = "/telegram-webhook"
WEBHOOK_URL = ""  # ← прописать, если будете работать с веб-хуком


async def wait_for_webhook_ready(url: str, timeout: int = 30) -> bool:
    for i in range(timeout):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url)
                if r.status_code in {200, 405}:
                    logger.info("Webhook URL стал доступен на %d-й секунде", i + 1)
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    logger.warning("Webhook URL не стал доступен за %s c: %s", timeout, url)
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── инициализация БД и Telegram-бота ───────────────────────────────────
    await init_db()
    register_handlers()

    if USE_POLLING:  # локальная разработка

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(app_tg.run_polling(stop_signals=None))

        threading.Thread(target=_run, daemon=True).start()

    else:  # prod-режим с веб-хуком
        await app_tg.initialize()
        await wait_for_webhook_ready(WEBHOOK_URL)
        logger.info("Установка webhook: %s", WEBHOOK_URL)
        await app_tg.bot.set_webhook(url=WEBHOOK_URL)

    yield  # ← здесь запускается FastAPI

    if not USE_POLLING:
        await app_tg.shutdown()
