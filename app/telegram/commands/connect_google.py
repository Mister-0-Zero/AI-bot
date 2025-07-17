from urllib.parse import urlencode

from telegram import Update
from telegram.ext import ContextTypes

from app.core.config import CLIENT_ID, CLIENT_SECRET
from app.core.config import GOOGLE_OAUTH_SCOPES as SCOPES
from app.core.config import REDIRECT_DOMAIN
from app.core.logging_config import get_logger
from app.core.state import put_state
from app.telegram.bot import app_tg

logger = get_logger(__name__)


async def cmd_connect_google(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not (CLIENT_ID and CLIENT_SECRET):
        await update.message.reply_text("⚠️ Google OAuth не настроен на сервере.")
        return

    telegram_id = update.effective_user.id
    logger.info("🔗 Авторизация запрошена пользователем %s", telegram_id)
    logger.info("redirect_uri: %s", f"https://{REDIRECT_DOMAIN}/oauth2callback")

    state = await put_state(telegram_id)
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": CLIENT_ID,
            "redirect_uri": f"https://{REDIRECT_DOMAIN}/oauth2callback",
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "false",
        }
    )

    await app_tg.bot.send_message(
        chat_id=telegram_id,
        text=f"Перейди по ссылке для подключения Google:\n{auth_url}",
    )
