import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

TTL_SEC = 600
HISTORY_LIMIT = 6
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL")


if REDIS_URL:

    async def get_redis():
        import redis.asyncio as redis  # type: ignore

        return await redis.from_url(REDIS_URL, decode_responses=True)

    # --------- ХРАНЕНИЕ ВРЕМЕННОГО STATE (OAuth) ---------
    async def put_state(tid: int) -> str:
        r = await get_redis()
        state = secrets.token_urlsafe(16)
        await r.setex(f"oauth_state:{state}", TTL_SEC, str(tid))
        logger.debug("State %s saved to Redis for %s", state, tid)
        return state

    async def pop_state(state: str) -> int | None:
        r = await get_redis()
        key = f"oauth_state:{state}"
        tid = await r.get(key)
        await r.delete(key)
        return int(tid) if tid else None

    # --------- ХРАНЕНИЕ ИСТОРИИ ЧАТА ---------
    async def push_history(user_id: int, role: str, text: str) -> None:
        r = await get_redis()
        key = f"chat_history:{user_id}"
        await r.rpush(key, json.dumps({"role": role, "text": text}))
        await r.ltrim(key, -HISTORY_LIMIT, -1)

    async def get_history(user_id: int) -> list[dict]:
        r = await get_redis()
        key = f"chat_history:{user_id}"
        messages = await r.lrange(key, 0, -1)
        return [json.loads(m) for m in messages]

    async def clear_history(user_id: int) -> None:
        r = await get_redis()
        key = f"chat_history:{user_id}"
        await r.delete(key)


# --------- FALLBACK: без Redis (локальный режим) ---------
else:
    _cache_state: dict[str, tuple[int, datetime]] = {}
    _cache_history: dict[int, list[dict]] = {}

    async def put_state(tid: int) -> str:
        state = secrets.token_urlsafe(16)
        _cache_state[state] = (tid, datetime.now(timezone.utc))
        logger.info("State записан локально: %s → %s", state, tid)
        return state

    async def pop_state(state: str) -> int | None:
        tpl = _cache_state.pop(state, None)
        if tpl is None:
            return None
        tid, created = tpl
        if datetime.now(timezone.utc) - created > timedelta(seconds=TTL_SEC):
            return None
        return tid

    async def push_history(user_id: int, role: str, text: str) -> None:
        history = _cache_history.setdefault(user_id, [])
        history.append({"role": role, "text": text})
        if len(history) > HISTORY_LIMIT:
            _cache_history[user_id] = history[-HISTORY_LIMIT:]

    async def get_history(user_id: int) -> list[dict]:
        return _cache_history.get(user_id, [])

    async def clear_history(user_id: int) -> None:
        _cache_history.pop(user_id, None)
