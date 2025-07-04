from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "📖 <b>Доступные команды</b>:\n\n"
    "🟢 <b>/start</b> — Начало работы с ботом\n"
    "🛟 <b>/help</b> — Справка по командам\n"
    "🔗 <b>/connect_google</b> — Подключить аккаунт Google Диска\n"
    "📂 <b>/load_drive</b> — Загрузить и прочитать файлы с Google Диска\n"
    "🗂 <b>/list_files</b> — Посмотреть список загруженных файлов\n"
    "📧 <b>/my_email</b> — Показать привязанный Google аккаунт и Telegram ID\n"
    "🧹 <b>/clear_knowledge</b> — Удалить свои данные из базы знаний\n"
    "📘 <b>/instruction</b> — Инструкция по использованию бота\n\n"
)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")
