import os
import threading
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# === Загрузка переменных окружения ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
RAILWAY_DOMAIN = os.getenv("RAILWAY_DOMAIN")  # Без https://

# === Проверка переменных окружения ===
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден. Проверь .env или переменные Railway.")
if not RAILWAY_DOMAIN:
    raise ValueError("❌ RAILWAY_DOMAIN не найден.")

# === Telegram Bot ===
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй /connect_google для подключения Google Диска.")

async def connect_google(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not CLIENT_ID:
        await update.message.reply_text("⚠️ Google Client ID не настроен.")
        return

    oauth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri=https://{RAILWAY_DOMAIN}/oauth2callback&"
        f"scope=https://www.googleapis.com/auth/drive.readonly&"
        f"response_type=code&access_type=offline&prompt=consent"
    )
    await update.message.reply_text(f"Перейди по ссылке для авторизации:\n{oauth_url}")

app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("connect_google", connect_google))

# === Запуск Telegram-бота в фоне ===
def start_bot():
    asyncio.run(app_bot.run_polling())

threading.Thread(target=start_bot, daemon=True).start()

# === FastAPI сервер ===
app_web = FastAPI()

@app_web.get("/")
async def root():
    return {"message": "Бот работает ✅"}

@app_web.get("/oauth2callback")
async def oauth2callback(request: Request):
    code = request.query_params.get("code")
    return {"message": f"Авторизация прошла успешно! Код: {code}"}
