from telegram.ext import CommandHandler, MessageHandler, filters
from app.telegram.bot import app_tg
from app.telegram.commands import (
    cmd_start,
    cmd_help,
    cmd_connect_google,
    cmd_load_drive,
    cmd_list_files,
    cmd_show_email,
)
from app.core.logging_config import get_logger
import traceback
from telegram import Update
from telegram.ext import ContextTypes
from app.telegram.ai_reply import generate_reply
import asyncio

logger = get_logger(__name__)

# Универсальный лог ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error_text = f"❌ Произошла ошибка"
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(error_text)

    logger.warning("Ошибка: %s", error_text)
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)



async def msg_ai(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await update.message.chat.send_action("typing")

    loop = asyncio.get_running_loop()
    answer = await loop.run_in_executor(None, generate_reply, user_text)

    await update.message.reply_text(answer)


def register_handlers():
    app_tg.add_handler(CommandHandler("start", cmd_start))
    app_tg.add_handler(CommandHandler("help", cmd_help))
    app_tg.add_handler(CommandHandler("connect_google", cmd_connect_google))
    app_tg.add_handler(CommandHandler("load_drive", cmd_load_drive))
    app_tg.add_handler(CommandHandler("list_files", cmd_list_files))
    app_tg.add_handler(CommandHandler("my_email", cmd_show_email))

    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_ai))

    # глобальный catcher
    app_tg.add_error_handler(error_handler)