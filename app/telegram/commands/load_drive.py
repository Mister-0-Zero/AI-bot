import multiprocessing

from telegram import Update
from telegram.ext import ContextTypes

from app.core.logging_config import get_logger
from app.core.vector_store import store_documents_async
from app.services.google_drive import read_files_from_drive

logger = get_logger(__name__)


def _fetch_token_process(telegram_id: int, conn):
    from app.services.token_refresh_sync import get_valid_access_token_sync

    try:
        token = get_valid_access_token_sync(telegram_id)
        conn.send(token)
    except Exception as e:
        conn.send(e)
    finally:
        conn.close()


async def cmd_load_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info("🚀 /load_drive запущен, telegram_id=%s", telegram_id)

    # 1️⃣  Разбор аргументов: all | список имён
    raw_parts = (update.message.text or "").split(maxsplit=1)
    argument = raw_parts[1].strip() if len(raw_parts) > 1 else "all"
    selected_names = (
        None
        if argument.lower() == "all"
        else [n.strip() for n in argument.split(",") if n.strip()]
    )

    # 2️⃣  Получаем access_token в изолированном процессе
    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=_fetch_token_process, args=(telegram_id, child_conn)
    )
    proc.start()
    result = parent_conn.recv()
    proc.join()

    if isinstance(result, Exception):
        logger.warning("❌ Токен не получен: %s", result)
        await update.message.reply_text(
            "❌ Не удалось получить токен Google. Используй /connect_google"
        )
        return

    access_token: str = result
    logger.info("✅ Токен получен, telegram_id=%s", telegram_id)

    async def progress(text: str):
        logger.info(text)
        await update.message.reply_text(text)

    await update.message.reply_text("🔄 Начинаю чтение файлов…")

    # 3️⃣  Читаем файлы (all или выборочные)
    try:
        files = await read_files_from_drive(
            access_token=access_token,
            user_id=telegram_id,
            on_progress=progress,
            selected_names=selected_names,
        )
    except Exception as e:
        logger.error("❌ Ошибка чтения: %s", e)
        await update.message.reply_text("❌ Произошла ошибка при чтении файлов.")
        return

    if not files:
        await update.message.reply_text("⚠️ Файлы не найдены.")
        return

    await update.message.reply_text(f"📚 Считано файлов: {len(files)}")
    await update.message.reply_text("💾 Сохраняю данные в базу знаний…")

    # 4️⃣  Сохраняем в векторное хранилище
    try:
        await store_documents_async(files)
        await update.message.reply_text("✅ Файлы успешно сохранены в базу знаний!")
    except Exception as e:
        logger.error("❌ Ошибка при сохранении: %s", e)
        await update.message.reply_text("❌ Ошибка при сохранении в базу знаний.")
