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

    telegram_id = update.effective_user.id      

    # 1. генерируем state и заносим в Redis
    state = await put_state(telegram_id)

    # 2. формируем ссылку
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urlencode(
            {
                "client_id":    CLIENT_ID,
                "redirect_uri": f"https://{RAILWAY_DOMAIN}/oauth2callback",
                "response_type":"code",
                "scope":        "https://www.googleapis.com/auth/drive.file",
                "state":        state,
                "access_type":  "offline",
                "prompt":       "consent",
            }
        )
    )


    await app_tg.bot.send_message(
        chat_id=telegram_id,
        text=f"Перейди по ссылке для подключения Google:\n{auth_url}"
    )
  

def register_handlers():
    app_tg.add_handler(CommandHandler("start",          cmd_start))
    app_tg.add_handler(CommandHandler("connect_google", cmd_connect_google))
