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
    logger.info(
        "🚀 Запуск команды /load_drive от пользователя telegram_id=%s", telegram_id
    )

    # Получение access_token в изолированном процессе
    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=_fetch_token_process, args=(telegram_id, child_conn)
    )
    proc.start()
    result = parent_conn.recv()
    proc.join()

    if isinstance(result, Exception):
        logger.warning("❌ Не удалось получить токен: %s", result)
        await update.message.reply_text(
            "❌ Не удалось получить токен Google. Используй /connect_google"
        )
        return

    access_token = result
    logger.info("✅ Токен получен успешно для telegram_id=%s", telegram_id)

    async def progress_callback(text: str):
        logger.info("📥 %s", text)
        await update.message.reply_text(text)

    await update.message.reply_text("🔄 Начинаю чтение файлов...")
    logger.info("📁 Чтение файлов с Google Диска для telegram_id=%s", telegram_id)

    try:
        files = await read_files_from_drive(
            access_token, telegram_id, progress_callback
        )
        logger.info(
            "📚 Успешно считано файлов: %d для telegram_id=%s", len(files), telegram_id
        )
    except Exception as e:
        logger.error("❌ Ошибка при чтении файлов: %s", str(e))
        await update.message.reply_text("❌ Произошла ошибка при чтении файлов.")
        return

    await update.message.reply_text(f"📚 Всего считано файлов: {len(files)}")

    try:
        await update.message.reply_text(
            "💾 Сохраняю данные в базу данных, налейте кофейку, это может занять время"
        )
        logger.info(
            "💾 Сохранение в векторную БД начато для telegram_id=%s", telegram_id
        )

        await store_documents_async(files)

        logger.info(
            "✅ Сохранение в векторную БД завершено для telegram_id=%s", telegram_id
        )
        await update.message.reply_text("✅ Файлы успешно сохранены в базу знаний!")

    except Exception as e:
        logger.error("❌ Ошибка при сохранении в векторную БД: %s", str(e))
        await update.message.reply_text("❌ Ошибка при сохранении в базу знаний.")
