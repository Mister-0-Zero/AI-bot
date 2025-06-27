import os, logging, asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------- конфиг ----------
load_dotenv()
BOT_TOKEN      = os.getenv("BOT_TOKEN")
CLIENT_ID      = os.getenv("GOOGLE_CLIENT_ID")
RAILWAY_DOMAIN = os.getenv("RAILWAY_DOMAIN")
CLIENT_SECRET  = os.getenv("GOOGLE_CLIENT_SECRET")
USE_POLLING    = bool(os.getenv("USE_POLLING"))           # без https://

logging.info(f"🔗 USE_POLLING = {USE_POLLING}")

if not BOT_TOKEN or not RAILWAY_DOMAIN:
    raise RuntimeError("BOT_TOKEN и RAILWAY_DOMAIN обязательны!")

# ---------- Telegram ----------
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Используй /connect_google для подключения Google-Диска."
    )

async def cmd_connect(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not CLIENT_ID:
        await update.message.reply_text("⚠️  Google Client ID не настроен.")
        return
    url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri=https://{RAILWAY_DOMAIN}/oauth2callback&"
        f"scope=https://www.googleapis.com/auth/drive.readonly&"
        f"response_type=code&access_type=offline&prompt=consent"
    )
    await update.message.reply_text(f"Перейди по ссылке для авторизации:\n{url}")

bot_app.add_handler(CommandHandler("start", cmd_start))
bot_app.add_handler(CommandHandler("connect_google", cmd_connect))

# ---------- FastAPI + lifespan ----------
WEBHOOK_PATH = "/telegram-webhook"
WEBHOOK_URL  = f"https://{RAILWAY_DOMAIN}{WEBHOOK_PATH}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not USE_POLLING and WEBHOOK_URL:
        logging.info("🔗 Регистрирую webhook %s", WEBHOOK_URL)
        await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    yield
    if not USE_POLLING and WEBHOOK_URL:
        await bot_app.bot.delete_webhook()

api = FastAPI(lifespan=lifespan)

@api.get("/")
async def root():
    return {"message": "Бот работает ✅"}

@api.get("/oauth2callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    return {"message": f"Код авторизации получен: {code}"}

@api.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Telegram шлёт сюда все обновления."""
    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}

# Uvicorn ищет переменную app_web (см. Procfile)
app_web = api

if USE_POLLING:                    
    import threading
    def run_polling():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_app.run_polling(stop_signals=[]))
    threading.Thread(target=run_polling, daemon=True).start()
