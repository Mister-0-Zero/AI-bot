from telegram import Update
from telegram.ext import ContextTypes
from app.core.vector_store import load_vector_db
from app.core.logging_config import get_logger

logger = get_logger(__name__)

VECTOR_DB_PATH = "app/data/chroma"  # путь должен совпадать с persist_directory в vector_store.py

async def cmd_clear_knowledge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info("📛 Пользователь %s вызвал очистку своих данных в векторной БД", telegram_id)

    try:
        db = load_vector_db()
        logger.info("🔍 Загружено документов: %d", len(db._collection.get()['ids']))

        # Удаляем документы по telegram_id
        db._collection.delete(where={"user_id": telegram_id})
        logger.info("🧹 Удалены документы с telegram_id=%s", telegram_id)

        await update.message.reply_text("🧹 Твои данные успешно удалены из базы знаний.")
    except Exception as e:
        logger.error("❌ Ошибка при удалении данных пользователя: %s", str(e))
        await update.message.reply_text("❌ Ошибка при удалении твоих данных.")

