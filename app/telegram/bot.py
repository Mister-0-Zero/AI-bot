from telegram.ext import ApplicationBuilder
from telegram.request import HTTPXRequest

from app.core.config import BOT_TOKEN
from app.core.logging_config import get_logger

logger = get_logger(__name__)

request = HTTPXRequest(
    connect_timeout=90.0,
    read_timeout=90.0,
    write_timeout=90.0,
    pool_timeout=90.0,
)

app_tg = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

logger.info("Telegram Application initialized")
