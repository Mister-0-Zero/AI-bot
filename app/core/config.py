import os

from dotenv import load_dotenv

load_dotenv()

# Основные настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Использовать polling (для локальной разработки)
USE_POLLING = os.getenv("USE_POLLING", "1").lower() in ("1", "true")

# Домен для редиректа (локальный по умолчанию)
REDIRECT_DOMAIN = os.getenv("REDIRECT_DOMAIN", "localhost:8000")

# Подключение к БД — Railway больше не используется
DATABASE_URL = os.getenv("DATABASE_URL_LOCAL")

MODEL_TOKEN = os.getenv("MODEL_TOKEN", "")

MODEL_ID = os.getenv("MODEL_ID", "google/gemma-2b-it")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is required")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL is not set")
if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("❌ Google OAuth is not configured")

# Скоупы Google OAuth
GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "openid",
]
