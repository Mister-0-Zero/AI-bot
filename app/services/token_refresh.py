from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.models.user import User
from app.core.config import CLIENT_ID, CLIENT_SECRET
import httpx
import logging

logger = logging.getLogger(__name__)

async def get_valid_access_token(telegram_id: int, session: AsyncSession) -> str:
    logger.info("Ищу пользователя с telegram_id: %s", telegram_id)
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        logger.warning("Пользователь не найден в БД: %s", telegram_id)
    else:
        logger.info("Пользователь найден: %s", user.email)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.token_expiry and user.token_expiry > now + timedelta(minutes=1):
        return user.access_token


    logger.info("🔄 Токен устарел. Обновляем по refresh_token...")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "refresh_token": user.refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            tokens = resp.json()
    except Exception:
        logger.exception("❌ Ошибка при обновлении токена через refresh_token")
        raise RuntimeError("Ошибка обновления токена")

    user.access_token = tokens["access_token"]
    user.token_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))
    ).replace(tzinfo=None)

    await session.commit()
    logger.info("✅ Токен успешно обновлён для telegram_id=%s", telegram_id)
    return user.access_token
