import httpx
from datetime import datetime, timezone, timedelta
from fastapi import Request, Depends, APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.core.config import CLIENT_ID, CLIENT_SECRET, RAILWAY_DOMAIN
from app.core.db import get_session
from app.core.state import pop_state
from app.models.user import User
from app.telegram.bot import app_tg
from app.core.logging_config import get_logger
from app.core.state import pop_state 
from fastapi.responses import RedirectResponse

logger = get_logger(__name__)

router = APIRouter()
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

async def exchange_code(code: str) -> dict:
    logger.info("Обмен authorization code на токены")
    async with httpx.AsyncClient(http2=True, timeout=10) as client:
        # 1. Получаем токены
        resp = await client.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": f"https://{RAILWAY_DOMAIN}/oauth2callback",
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        logger.info("Ответ от Google получен")

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")  # ← добавить это

        # 2. Получаем информацию о пользователе
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()
        logger.info("Информация о пользователе получена: %s", userinfo.get("email"))
        logger.info("Tokens: %s", tokens)
        logger.info("Сохраняем пользователя: access_token=%s, refresh_token=%s, email=%s", access_token, refresh_token, userinfo.get("email"))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": tokens.get("expires_in"),
            "email": userinfo.get("email"),
        }
    
@router.get("/oauth2callback")
async def oauth2callback(request: Request, session: AsyncSession = Depends(get_session)):
    try:
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code or not state:
            logger.warning("Недостающие параметры: code или state")
            raise HTTPException(status_code=400, detail="Missing code or state")

        telegram_id = await pop_state(state)
        if telegram_id is None:
            logger.warning("Просроченный или неверный state")
            raise HTTPException(status_code=400, detail="Invalid or expired state")

        tokens = await exchange_code(code)

        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 0)
        email = tokens.get("email")
        expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).replace(tzinfo=None)

        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(
                telegram_id=telegram_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=expiry,
                email=email,
            )
            session.add(user)
            logger.info("Создан новый пользователь: %s", telegram_id)
        else:
            user.email = email or user.email
            user.access_token = access_token
            user.refresh_token = refresh_token or user.refresh_token
            user.token_expiry = expiry
            logger.info("Обновлён пользователь: %s", telegram_id)

        logger.info("Пользователь перед сохранением: %s", user.dict())
        try:
            await session.commit()
        except Exception:
            logger.exception("Ошибка при сохранении пользователя в БД")
            raise HTTPException(status_code=500, detail="Ошибка при сохранении в БД")

        await app_tg.bot.send_message(chat_id=telegram_id, text="✅ Google аккаунт успешно подключён!")
        logger.info("Уведомление отправлено пользователю: %s", telegram_id)

        return RedirectResponse(url=f"https://t.me/AI_Google_Disk_helper_bot")

    except Exception:
        logger.exception("Ошибка в oauth2callback")
        raise HTTPException(status_code=500, detail="Internal Server Error")