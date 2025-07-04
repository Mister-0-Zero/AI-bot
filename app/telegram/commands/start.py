from pathlib import Path

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.core.logging_config import get_logger

logger = get_logger(__name__)

WELCOME_TEXT = (
    "👋 <b>Добро пожаловать!</b>\n\n"
    "Если вы искали бота, который автоматизирует работу с Google Диском, "
    "отвечает на вопросы и дает рекомендации на основе ваших файлов, "
    "то вы попали по адресу!\n\n"
    "Этот бот может проанализировать ваши документы и ответить на вопросы, "
    "используя информацию из них. Открывайте инструкцию \\instruction и начните "
    "работу уже через пару минут!\n\n"
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

    # Клавиатура с кнопками
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            ["/instruction"],
            ["/help"],
        ],
        resize_keyboard=True,
    )

    # Отправка текста с клавиатурой
    await update.message.reply_text(
        WELCOME_TEXT, parse_mode="HTML", reply_markup=keyboard
    )
