from urllib.parse import urlencode
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from app.core.config import CLIENT_ID, CLIENT_SECRET, RAILWAY_DOMAIN
from app.core.state import put_state
from app.telegram.bot import app_tg

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я AI-бот.\nКоманда /connect_google подключит твой Google-Диск."
    )

async def cmd_connect_google(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not (CLIENT_ID and CLIENT_SECRET):
        await update.message.reply_text("⚠️ Google OAuth не настроен на сервере.")
        return

    state = put_state(update.effective_user.id)
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": f"https://{RAILWAY_DOMAIN}/oauth2callback",
        "scope": "https://www.googleapis.com/auth/drive.readonly",
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    await update.message.reply_text("Перейди по ссылке для авторизации:\n" + auth_url)


def register_handlers():
    app_tg.add_handler(CommandHandler("start", cmd_start))
    app_tg.add_handler(CommandHandler("connect_google", cmd_connect_google))