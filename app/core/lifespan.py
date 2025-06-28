import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import USE_POLLING, RAILWAY_DOMAIN
from app.core.db import init_db
from app.telegram.bot import app_tg
from app.telegram.handlers import register_handlers
from app.core.logging_config import get_logger
import httpx

logger = get_logger(__name__)
WEBHOOK_PATH = "/telegram-webhook"
WEBHOOK_URL = f"https://{RAILWAY_DOMAIN}{WEBHOOK_PATH}" if RAILWAY_DOMAIN else None


async def wait_for_webhook_ready(url: str, timeout: int = 10):
    for i in range(timeout):
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url)
                if r.status_code == 405 or r.status_code == 200:
                    return
        except Exception:
            pass
        await asyncio.sleep(1)
    raise RuntimeError("Webhook URL не стал доступен за разумное время.")


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
        await wait_for_webhook_ready(WEBHOOK_URL)  # ← ждём, пока Railway поднимет URL
        logger.info(f"Установка webhook: {WEBHOOK_URL}")
        await app_tg.bot.set_webhook(url=WEBHOOK_URL)

    yield

    if not USE_POLLING:
        await app_tg.shutdown()