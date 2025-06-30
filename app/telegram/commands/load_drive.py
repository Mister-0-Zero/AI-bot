from telegram import Update
from telegram.ext import ContextTypes
from app.core.db import get_session
from app.services.token_refresh import get_valid_access_token
from app.services.google_drive import read_files_from_drive
from app.core.logging_config import get_logger

logger = get_logger(__name__)

async def cmd_load_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id

    async with get_session() as session:
        try:
            logger.info("📨 Проверка доступа к токену для telegram_id=%s", telegram_id)
            access_token = await get_valid_access_token(telegram_id, session)
        except Exception:
            await update.message.reply_text(
                "❌ У тебя не привязан Google Диск.\n\nИспользуй команду /connect_google"
            )
            return

        async def progress_callback(text: str):
            await update.message.reply_text(text)

        await update.message.reply_text("🔄 Начинаю чтение файлов...")
        files = await read_files_from_drive(access_token, progress_callback)
        await update.message.reply_text(f"📚 Всего считано файлов: {len(files)}")