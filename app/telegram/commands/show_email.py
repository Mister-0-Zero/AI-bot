from telegram import Update
from telegram.ext import ContextTypes
from app.core.db import get_session
from app.models.user import User
from sqlalchemy import select
from app.core.logging_config import get_logger

logger = get_logger(__name__)

async def cmd_show_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info("📧 Команда /my_email от пользователя %s", telegram_id)

    async with get_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))

        if not user or not user.email:
            await update.message.reply_text("❌ У тебя не привязан Google аккаунт.")
            return

        text = (
            f"🧾 Информация об аккаунте:\n\n"
            f"📧 Email: {user.email}\n"
            f"🆔 Telegram ID: {user.telegram_id}"
        )
        await update.message.reply_text(text)
