from urllib.parse import urlencode
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from app.core.config import CLIENT_ID, CLIENT_SECRET, RAILWAY_DOMAIN
from app.core.state import put_state          
from app.telegram.bot import app_tg
from app.services.token_refresh import get_valid_access_token
from app.core.db import get_session
from app.services.google_drive import read_files_from_drive

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
                "scope":        "openid email profile https://www.googleapis.com/auth/drive.file",
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

async def cmd_load_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id

    async with get_session() as session:
        try:
            access_token = await get_valid_access_token(telegram_id, session)
        except Exception:
            await update.message.reply_text(
                "❌ У тебя не привязан Google Диск.\n\nИспользуй команду /connect_google"
            )
            return

        await update.message.reply_text("🔄 Начинаю чтение файлов...")

        async def progress_callback(text: str):
            await update.message.reply_text(text)

        files = await read_files_from_drive(access_token, progress_callback)

        await update.message.reply_text(f"📚 Всего считано файлов: {len(files)}")

def register_handlers():
    app_tg.add_handler(CommandHandler("start", cmd_start))
    app_tg.add_handler(CommandHandler("connect_google", cmd_connect_google))
    app_tg.add_handler(CommandHandler("load_drive", cmd_load_drive))
