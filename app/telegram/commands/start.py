from telegram import Update
from telegram.ext import ContextTypes
from pathlib import Path
from app.core.logging_config import get_logger

logger = get_logger(__name__)

WELCOME_TEXT = (
    "👋 <b>Добро пожаловать!</b>\n\n"
    "Этот бот поможет вам работать с файлами из Google Диска, "
    "отвечать на вопросы и давать рекомендации на основе загруженных материалов.\n\n"
    "🟢 Используйте команду /help для просмотра доступных команд."
)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Путь к изображению
    image_path = Path("app/assets/welcome.png")

    # Отправка изображения
    logger.info(f"Отправка изображения приветствия: {image_path}")
    if image_path.exists():
        logger.info(f"Изображение найдено: {image_path}")
        with open(image_path, "rb") as image:
            await update.message.reply_photo(photo=image)
    else:
        logger.error(f"Изображение не найдено: {image_path}")

    # Отправка текста
    await update.message.reply_text(WELCOME_TEXT, parse_mode="HTML")