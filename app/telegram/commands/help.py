from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "📖 <b>Доступные команды</b>:\n\n"
    "🟢 <b>/start</b> — Начало работы с ботом\n"
    "🛟 <b>/help</b> — Справка по командам\n"
    "🔗 <b>/connect_google</b> — Подключить аккаунт Google Диска\n"
    "📂 <b>/load_drive</b> — Загрузить и прочитать файлы с Google Диска\n"
)

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")