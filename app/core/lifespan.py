import asyncio
import os
import threading
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

import httpx
from fastapi import FastAPI
from huggingface_hub import login, snapshot_download

from app.core.config import MODEL_ID, MODEL_TOKEN, USE_POLLING
from app.core.db import init_db
from app.core.logging_config import get_logger
from app.telegram.bot import app_tg
from app.telegram.handlers import register_handlers

logger = get_logger(__name__)
WEBHOOK_PATH = "/telegram-webhook"
WEBHOOK_URL = (
    ""  # f"https://{RAILWAY_DOMAIN}{WEBHOOK_PATH}" if RAILWAY_DOMAIN else None
)
HF_CACHE_DIR = os.getenv("HF_HOME", "/mnt/models")

login(token=MODEL_TOKEN)  # Авторизация Hugging Face


async def _ensure_model():
    """
    ▸ Если MODEL_ID указывает на существующую локальную папку — ничего не скачиваем.
    ▸ Иначе считаем, что это repo_id на Hugging Face и загружаем веса в HF_CACHE_DIR.
    """
    model_path = Path(MODEL_ID).expanduser().resolve()

    # 1️⃣  Локальная модель уже есть
    if model_path.is_dir():
        logger.info("✅ Локальная модель найдена: %s", model_path)
        return

    # 2️⃣  Скачиваем репозиторий с Hugging Face
    logger.info("⬇️  Скачивание модели %s в %s", MODEL_ID, HF_CACHE_DIR)

    target_dir = os.path.join(HF_CACHE_DIR, f"models--{MODEL_ID.replace('/', '--')}")

    if os.path.isdir(target_dir):
        logger.info("✅ Модель уже в кеше: %s", target_dir)
        return

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(
            None,
            partial(
                snapshot_download,
                repo_id=MODEL_ID,
                cache_dir=HF_CACHE_DIR,
                allow_patterns=["*.safetensors", "*.bin", "*.json", "*.txt"],
                resume_download=True,
            ),
        )
        logger.info("✅ Модель успешно скачана")
    except Exception as e:
        logger.error("❌ Ошибка при скачивании модели %s: %s", MODEL_ID, e)
        raise RuntimeError(f"Не удалось скачать модель {MODEL_ID}: {e}") from e


async def wait_for_webhook_ready(url: str, timeout: int = 30):
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
    logger.warning("Webhook URL не стал доступен за %s с: %s", timeout, url)
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _ensure_model()
    register_handlers()

    if USE_POLLING:

        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # ОТКЛЮЧАЕМ регистрацию сигналов — нужно для Linux (uvicorn/uvloop)
            loop.run_until_complete(app_tg.run_polling(stop_signals=None))

        threading.Thread(target=_run, daemon=True).start()

    else:
        await app_tg.initialize()
        await wait_for_webhook_ready(WEBHOOK_URL)
        logger.info("Установка webhook: %s", WEBHOOK_URL)
        await app_tg.bot.set_webhook(url=WEBHOOK_URL)

    yield

    if not USE_POLLING:
        await app_tg.shutdown()
