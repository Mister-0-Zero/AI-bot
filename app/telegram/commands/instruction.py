from telegram import Update
from telegram.ext import ContextTypes

INSTRUCTION_TEXT = (
    "📘 <b>Как пользоваться ботом:</b>\n\n"
    "1️⃣ /connect_google – подключите Google Диск\n"
    "2️⃣ <b>/load_drive</b> — загрузите файлы (txt, pdf, docx, csv, excel ≤100 KБ)\n"
    "  <b>/load_drive all</b> — считать все файлы\n"
    "  <b>/load_drive file1.pdf, file2.docx</b> — конкретные файлы\n"
    "  <b>/load_drive Папка1/, Папка2/</b> — все файлы из папок\n"
    "Можно комбинировать: Папка/, отчет.docx\n"
    "3️⃣ Напишите любой вопрос – бот ответит на основе загруженных материалов\n\n"
    "🔧 Дополнительно:\n"
    "• /list_files – показать загруженные файлы\n"
    "• /my_email – ваш подключённый Google-аккаунт\n"
    "• <b>/clear_knowledge</b> или <b>/clear_knowledge all</b> удалить все данные в том числе о профиле\n"
    "• <b>/clear_knowledge data</b> только историю сообщений и загруженные файлы\n\n"
    "⚠️ Это бета-версия. Возможны ошибки.\n"
    "✅ После подключения и загрузки файлов, ИИ будет точно отвечать на ваши вопросы. Пишите любые!"
)


async def cmd_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(INSTRUCTION_TEXT, parse_mode="HTML")
