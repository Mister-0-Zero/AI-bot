import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
RAILWAY_DOMAIN = os.getenv("RAILWAY_DOMAIN")
USE_POLLING = os.getenv("USE_POLLING", "").lower() in ("1", "true")
USE_RAILWAY = os.getenv("USE_RAILWAY", "false").lower() in ("1", "true")
DATABASE_URL = (
    os.getenv("DATABASE_URL_RAILWAY")
    if USE_RAILWAY
    else os.getenv("DATABASE_URL_LOCAL")
)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required")
if not USE_POLLING and not RAILWAY_DOMAIN:
    raise RuntimeError("RAILWAY_DOMAIN is required for webhook mode")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "openid"
]

