import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import CLIENT_ID, CLIENT_SECRET
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_valid_access_token(telegram_id: int, session: AsyncSession) -> str:
    logger.info(
        "🔍 get_valid_access_token: старт проверки для telegram_id=%s", telegram_id
    )

    # 1. Достаем пользователя
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        logger.warning("❌ Пользователь не найден в БД: telegram_id=%s", telegram_id)
        raise RuntimeError("Пользователь не найден")

    # 2. Проверяем срок токена
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.token_expiry and user.token_expiry > now + timedelta(minutes=1):
        logger.info(
            "🔒 Токен действителен, expires at %s (now %s)", user.token_expiry, now
        )
        return user.access_token

    # 3. Токен истек — обновляем
    logger.info(
        "🔄 Токен устарел (expiry=%s, now=%s). Обновление по refresh_token...",
        user.token_expiry,
        now,
    )
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
        logger.exception("❌ Ошибка при обращении к Google для обновления токена")
        raise RuntimeError("Ошибка обновления токена")

    # 4. Сохраняем новый токен и expiry
    user.access_token = tokens["access_token"]
    user.token_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))
    ).replace(tzinfo=None)

    await session.commit()
    logger.info("✅ Токен обновлён и сохранён: new expiry=%s", user.token_expiry)
    return user.access_token
