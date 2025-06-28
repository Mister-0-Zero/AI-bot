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

logger = get_logger(__name__)

router = APIRouter()
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

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

        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 0)
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(
                telegram_id=telegram_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=expiry,
            )
            session.add(user)
            logger.info("Создан новый пользователь: %s", telegram_id)
        else:
            user.access_token = access_token
            user.refresh_token = refresh_token or user.refresh_token
            user.token_expiry = expiry
            logger.info("Обновлён пользователь: %s", telegram_id)

        await session.commit()

        await app_tg.bot.send_message(chat_id=telegram_id, text="✅ Google аккаунт успешно подключён!")
        logger.info("Уведомление отправлено пользователю: %s", telegram_id)

        return {"message": "Авторизация завершена. Можешь закрыть окно."}

    except Exception:
        logger.exception("Ошибка в oauth2callback")
        raise HTTPException(status_code=500, detail="Internal Server Error")
