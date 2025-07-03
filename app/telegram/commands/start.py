from telegram import Update
from telegram.ext import ContextTypes
from pathlib import Path

WELCOME_TEXT = (
    "👋 <b>Добро пожаловать!</b>\n\n"
    "Этот бот поможет вам работать с файлами из Google Диска, "
    "отвечать на вопросы и давать рекомендации на основе загруженных материалов.\n\n"
    "🟢 Используйте команду /help для просмотра доступных команд."
)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Путь к изображению
    image_path = Path("assets/welcome.png")

    # Отправка текста
    await update.message.reply_text(WELCOME_TEXT, parse_mode="HTML")

    # Отправка изображения
    if image_path.exists():
        with open(image_path, "rb") as image:
            await update.message.reply_photo(photo=image)