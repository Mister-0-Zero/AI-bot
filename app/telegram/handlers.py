from urllib.parse import urlencode
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from app.core.config import CLIENT_ID, CLIENT_SECRET, RAILWAY_DOMAIN, GOOGLE_OAUTH_SCOPES as SCOPES
from app.core.state import put_state          
from app.telegram.bot import app_tg
from app.services.token_refresh import get_valid_access_token
from app.core.db import get_session
from app.services.google_drive import read_files_from_drive
import traceback
from app.core.logging_config import get_logger
from sqlmodel import select
from app.models.user import User

logger = get_logger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    error_text = f"❌ Произошла ошибка: {context.error}"
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(error_text)

    # Также логируем стек
    logger.warning("Ошибка: %s", error_text)
    traceback.print_exception(type(context.error), context.error, context.error.__traceback__)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 <b>Доступные команды</b>:\n\n"
        "🟢 <b>/start</b> — Начало работы с ботом\n"
        "🛟 <b>/help</b> — Справка по командам\n"
        "🔗 <b>/connect_google</b> — Подключить аккаунт Google Диска\n"
        "📂 <b>/load_drive</b> — Загрузить и прочитать файлы с Google Диска\n"
    )

    await update.message.reply_text(help_text, parse_mode="HTML")


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я AI-бот.\nКоманда /connect_google подключит твой Google-Диск."
    )


async def cmd_connect_google(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not (CLIENT_ID and CLIENT_SECRET):
        await update.message.reply_text("⚠️ Google OAuth не настроен на сервере.")
        return

    telegram_id = update.effective_user.id
    logger.info("🔗 Авторизация запрошена пользователем %s", telegram_id)

    state = await put_state(telegram_id)

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?" +
        urlencode({
            "client_id": CLIENT_ID,
            "redirect_uri": f"https://{RAILWAY_DOMAIN}/oauth2callback",
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        })
    )

    await app_tg.bot.send_message(
        chat_id=telegram_id,
        text=f"Перейди по ссылке для подключения Google:\n{auth_url}"
    )


async def cmd_load_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id

    async with get_session() as session:
        try:
            logger.info("📨 Проверка доступа к токену для telegram_id=%s", telegram_id)
            access_token = await get_valid_access_token(telegram_id, session)
        except Exception:
            await update.message.reply_text(
                "❌ У тебя не привязан Google Диск.\n\nИспользуй команду /connect_google"
            )
            return

        logger.info("завожу функцию progress_calback")

        async def progress_callback(text: str):
            await update.message.reply_text(text)

        logger.info("Начинаю чтение файлов...")
        await update.message.reply_text("🔄 Начинаю чтение файлов...")
        files = await read_files_from_drive(access_token, progress_callback)

        await update.message.reply_text(f"📚 Всего считано файлов: {len(files)}")


def register_handlers():
    app_tg.add_handler(CommandHandler("start", cmd_start))
    app_tg.add_handler(CommandHandler("connect_google", cmd_connect_google))
    app_tg.add_handler(CommandHandler("load_drive", cmd_load_drive))
    app_tg.add_handler(CommandHandler("help", cmd_help))