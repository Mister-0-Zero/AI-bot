from telegram import Update
from telegram.ext import ContextTypes

HELP_TEXT = (
    "📖 <b>Доступные команды</b>:\n\n"
    "🟢 <b>/start</b> — Начало работы с ботом\n"
    "🛟 <b>/help</b> — Справка по командам\n"
    "🔗 <b>/connect_google</b> — Подключить аккаунт Google Диска\n"
    "📂 <b>/load_drive</b> — загрузите файлы (txt, pdf, docx, csv, excel ≤100 KБ)\n"
    "    <b>/load_drive all</b> — считать все файлы\n"
    "    <b>/load_drive file1.pdf, file2.docx</b> — конкретные файлы\n"
    "    <b>/load_drive Папка1/, Папка2/</b> — все файлы из папок\n"
    "Можно комбинировать: Папка/, отчет.docx\n"
    "🗂 <b>/list_files</b> — Посмотреть список загруженных файлов\n"
    "📧 <b>/my_email</b> — Показать привязанный Google аккаунт и Telegram ID\n"
    "🧹 <b>/clear_knowledge</b> или <b>/clear_knowledge all</b> удалить все данные в том числе о профиле\n"
    "   <b>/clear_knowledge data</b> только историю сообщений и загруженные файлы\n\n"
    "📘 <b>/instruction</b> — Инструкция по использованию бота\n\n"
)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="HTML")
