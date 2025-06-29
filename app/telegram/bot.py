from telegram.ext import ApplicationBuilder
from app.core.config import BOT_TOKEN
from app.core.logging_config import get_logger
from app.telegram.handlers import error_handler

logger = get_logger(__name__)

app_tg = ApplicationBuilder().token(BOT_TOKEN).build()
app_tg.add_error_handler(error_handler)
logger.info("Telegram Application initialized")