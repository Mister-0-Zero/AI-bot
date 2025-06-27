import os, asyncio, threading
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# -- переменные окружения -----------------
load_dotenv()                               # локально берём .env; в Railway просто пропустит
BOT_TOKEN      = os.environ.get("BOT_TOKEN")
CLIENT_ID      = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET  = os.environ.get("GOOGLE_CLIENT_SECRET")
RAILWAY_DOMAIN = os.environ.get("RAILWAY_DOMAIN")   # без https://

print("RAILWAY DOMAIN =", RAILWAY_DOMAIN)
print("BOT TOKEN     =", BOT_TOKEN[:8], "...")  # только первые 8 символов

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing – добавь переменную в Railway!")

# -- Telegram-бот -------------------------
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Используй /connect_google для подключения Google-Диска.")

async def cmd_connect(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not CLIENT_ID:
        await update.message.reply_text("Google Client ID не настроен.")
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

def run_bot():
    bot_app.run_polling(handle_signals=False)

threading.Thread(target=run_bot, daemon=True).start()

# -- FastAPI ------------------------------
api = FastAPI()

@api.get("/")
async def root():
    return {"message": "Бот работает ✅"}

@api.get("/oauth2callback")
async def oauth2callback(request: Request):
    code = request.query_params.get("code")
    return {"message": f"Авторизация прошла успешно! Код: {code}"}

# для Uvicorn: app_web = api
app_web = api