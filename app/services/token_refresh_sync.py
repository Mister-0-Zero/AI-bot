import asyncio

from app.core.db import get_session
from app.services.token_refresh import get_valid_access_token


def get_valid_access_token_sync(telegram_id: int) -> str:
    async def _run():
        async with get_session() as session:
            return await get_valid_access_token(telegram_id, session)

    return asyncio.run(_run())
