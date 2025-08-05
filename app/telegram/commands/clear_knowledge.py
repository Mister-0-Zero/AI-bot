from telegram import Update
from telegram.ext import ContextTypes

from app.core.logging_config import get_logger
from app.core.state import clear_history
from app.core.vector_store import load_vector_db

logger = get_logger(__name__)

VECTOR_DB_PATH = (
    "app/data/chroma"  # путь должен совпадать с persist_directory в vector_store.py
)


async def cmd_clear_knowledge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info("📛 Пользователь %s вызвал очистку своих данных", telegram_id)

    # 1️⃣ Разбор аргументов
    raw_parts = (update.message.text or "").split(maxsplit=1)
    if len(raw_parts) == 1 or raw_parts[1].strip().lower() == "all":
        # требуется подтверждение
        await update.message.reply_text(
            "⚠️ Ты точно хочешь удалить ВСЁ — токены, историю и документы?\n"
            "Ответь сообщением <b>ДА</b>, чтобы подтвердить. Иначе удаление отменится.",
            parse_mode="HTML",
        )
        # сохраняем состояние ожидания подтверждения
        ctx.user_data["confirm_clear_all"] = True
        return

    elif raw_parts[1].strip().lower() == "data":
        try:
            db = load_vector_db()
            db._collection.delete(where={"user_id": telegram_id})
            logger.info("🧹 Удалены документы с telegram_id=%s", telegram_id)

            await clear_history(telegram_id)
            logger.info("🧹 Очищена история диалога пользователя %s", telegram_id)

            await update.message.reply_text(
                "🧹 Данные и история удалены (токены сохранены)."
            )
        except Exception as e:
            logger.error("❌ Ошибка при удалении данных: %s", str(e))
            await update.message.reply_text("❌ Произошла ошибка при удалении данных.")
        return

    else:
        await update.message.reply_text(
            "⚠️ Неизвестный аргумент. Используй:\n"
            "• `/clear_knowledge` или `/clear_knowledge all` — удалить всё (с подтверждением)\n"
            "• `/clear_knowledge data` — удалить только документы и историю"
        )
