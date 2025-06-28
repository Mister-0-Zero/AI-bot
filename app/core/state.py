import os, secrets, logging
from datetime import datetime, timezone, timedelta

TTL_SEC = 600                       # 10 минут
logger  = logging.getLogger("state")

REDIS_URL = os.getenv("REDIS_URL")  # в продакшене Railway задаёт её автоматически

# ────────────────────────────────────────────────────────────────────────────────
# 1. Режим с Redis (если переменная есть)
# ────────────────────────────────────────────────────────────────────────────────
if REDIS_URL:
    import redis.asyncio as redis   # библиотека ставится однажды: pip install redis>=4.5

    _r = redis.from_url(REDIS_URL, decode_responses=True)

    async def put_state(tid: int) -> str:
        state = secrets.token_urlsafe(16)
        await _r.setex(f"oauth_state:{state}", TTL_SEC, str(tid))
        logger.debug("State %s saved to Redis for %s", state, tid)
        return state

    async def pop_state(state: str) -> int | None:
        tid = await _r.getdel(f"oauth_state:{state}")     # атомарно получить и удалить
        return int(tid) if tid else None

# ────────────────────────────────────────────────────────────────────────────────
# 2. Fallback — обычный словарь (локальный однопроцессный запуск)
# ────────────────────────────────────────────────────────────────────────────────
else:
    logger.warning("REDIS_URL not set – falling back to in-memory state cache.")
    _cache: dict[str, tuple[int, datetime]] = {}

    async def put_state(tid: int) -> str:
        state = secrets.token_urlsafe(16)
        _cache[state] = (tid, datetime.now(timezone.utc))
        logger.debug("State %s saved to local cache for %s", state, tid)
        return state

    async def pop_state(state: str) -> int | None:
        tpl = _cache.pop(state, None)
        if tpl is None:
            return None
        tid, created = tpl
        if datetime.now(timezone.utc) - created > timedelta(seconds=TTL_SEC):
            return None
        return tid