from telegram import Update
from telegram.ext import ContextTypes

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я AI-бот.\nКоманда /connect_google подключит твой Google-Диск."
    )