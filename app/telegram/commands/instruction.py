from telegram import Update
from telegram.ext import ContextTypes

INSTRUCTION_TEXT = (
    "📘 <b>Как пользоваться ботом:</b>\n\n"
    "1️⃣ /connect_google – подключите Google Диск\n"
    "2️⃣ /load_drive – загрузите файлы (txt, pdf, docx, csv, excel ≤100 KБ)\n"
    "3️⃣ Напишите любой вопрос – бот ответит на основе загруженных материалов\n\n"
    "🔧 Дополнительно:\n"
    "• /list_files – показать загруженные файлы\n"
    "• /my_email – ваш подключённый Google-аккаунт\n"
    "• /clear_knowledge – сбросить все загруженные данные\n\n"
    "⚠️ Это бета-версия. Возможны ошибки.\n"
    "✅ После подключения и загрузки файлов, ИИ будет точно отвечать на ваши вопросы. Пишите любые!"
)


async def cmd_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(INSTRUCTION_TEXT, parse_mode="HTML")
