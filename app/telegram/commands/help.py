from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.core.db import get_session
from app.models.user import User

HELP_TEXT = {
    "ru": (
        "📖 <b>Доступные команды</b>\n\n"
        "🟢 <b>/start</b> — старт и меню\n"
        "🛟 <b>/help</b> — эта справка\n"
        "🌐 <b>/language</b> — сменить язык интерфейса\n"
        "🔗 <b>/connect_google</b> — подключить Google Drive\n"
        "📂 <b>/load_drive</b> — загрузить файлы (txt, pdf, docx, csv, xlsx ≤ 100 KB)\n"
        "    /load_drive all — все файлы\n"
        "    /load_drive file1.pdf, file2.docx — конкретные файлы\n"
        "    /load_drive Папка1/, Папка2/ — все файлы из папок\n"
        "🗂 <b>/list_files</b> — список загруженных файлов\n"
        "📧 <b>/my_email</b> — привязанный Google и ваш Telegram ID\n"
        "🧹 <b>/clear_knowledge</b> — очистка данных\n"
        "    /clear_knowledge data — только история и файлы\n"
        "    /clear_knowledge all — всё (включая профиль)\n\n"
        "📘 <b>/instruction</b> — краткая инструкция\n"
    ),
    "en": (
        "📖 <b>Available commands</b>\n\n"
        "🟢 <b>/start</b> — start and menu\n"
        "🛟 <b>/help</b> — this help\n"
        "🌐 <b>/language</b> — change interface language\n"
        "🔗 <b>/connect_google</b> — connect Google Drive\n"
        "📂 <b>/load_drive</b> — load files (txt, pdf, docx, csv, xlsx ≤ 100 KB)\n"
        "    /load_drive all — all files\n"
        "    /load_drive file1.pdf, file2.docx — specific files\n"
        "    /load_drive Folder1/, Folder2/ — all files from folders\n"
        "🗂 <b>/list_files</b> — list of loaded files\n"
        "📧 <b>/my_email</b> — linked Google and your Telegram ID\n"
        "🧹 <b>/clear_knowledge</b> — clear data\n"
        "    /clear_knowledge data — only history and files\n"
        "    /clear_knowledge all — everything (including profile)\n\n"
        "📘 <b>/instruction</b> — quick guide\n"
    ),
}


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Определяем язык пользователя из БД; по умолчанию ru
    async with get_session() as session:
        user = await session.get(User, update.effective_user.id)
    lang = user.lang if user and user.lang in ("ru", "en") else "ru"

    text = HELP_TEXT[lang]
    await (update.message or update.effective_message).reply_text(
        text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )
