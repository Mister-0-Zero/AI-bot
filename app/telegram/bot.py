from telegram.ext import ApplicationBuilder
from app.core.config import BOT_TOKEN
from app.core.logging_config import get_logger

logger = get_logger(__name__)

app_tg = ApplicationBuilder().token(BOT_TOKEN).build()
logger.info("Telegram Application initialized")