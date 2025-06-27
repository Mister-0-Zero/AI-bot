import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

STATE_TTL = timedelta(minutes=10)
_state_cache = {}

def put_state(telegram_id: int) -> str:
    state = secrets.token_urlsafe(16)
    _state_cache[state] = (telegram_id, datetime.now(timezone.utc))
    return state

def pop_state(state: str) -> Optional[int]:
    tpl = _state_cache.pop(state, None)
    if tpl is None:
        return None
    telegram_id, created = tpl
    if datetime.now(timezone.utc) - created > STATE_TTL:
        return None
    return telegram_id