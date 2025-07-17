import os
from pathlib import Path

from dotenv import load_dotenv

# ─── Загрузка .env ────────────────────────────────────────────────────────────
load_dotenv()

# ─── Базовые директории ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Telegram Bot / Google OAuth ──────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Использовать polling (удобно для локальной разработки)
USE_POLLING = os.getenv("USE_POLLING", "1").lower() in ("1", "true")

# Домен редиректа для OAuth
REDIRECT_DOMAIN = os.getenv("REDIRECT_DOMAIN", "localhost:8000")

# ─── База данных ──────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL_LOCAL")

# ─── Groq Cloud ───────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # берём ключ из .env
GROQ_MODEL = "llama-3.3-70b-versatile"  # фиксируем модель

# ─── Redis и локальные каталоги ───────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CHROMA_DIR = BASE_DIR / "data" / "chroma"
EMBEDDING_DIR = BASE_DIR / "models" / "embeding_model"

# ─── Валидация критичных переменных ───────────────────────────────────────────
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is required")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL is not set")
if not CLIENT_ID or not CLIENT_SECRET:
    raise RuntimeError("❌ Google OAuth is not configured")
if not GROQ_API_KEY:
    raise RuntimeError("❌ GROQ_API_KEY is required")

# Скоупы Google OAuth
GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "openid",
]
