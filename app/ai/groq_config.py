from __future__ import annotations

from typing import Dict, List

import tiktoken
from groq import Groq

from app.core.config import GROQ_API_KEY, GROQ_MODEL
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# контекст и вывод по спецификации Groq
MAX_MODEL_TOKENS = 131_072
MAX_OUTPUT_TOKENS = 32_768

client = Groq(api_key=GROQ_API_KEY)

# fallback-кодировщик (tiktoken ещё не знает про llama-3.3, но cl100k_base даёт точную оценку)
try:
    _enc = tiktoken.encoding_for_model(GROQ_MODEL)
except KeyError:
    _enc = tiktoken.get_encoding("cl100k_base")

client = Groq(api_key=GROQ_API_KEY)


def _count_tokens(text: str | List[Dict[str, str]]) -> int:
    """
    Быстрая оценка количества токенов (≈ точность ±1 %).
    • Принимает как строку, так и список messages.
    """
    if isinstance(text, str):
        return len(_enc.encode(text))
    return sum(_count_tokens(m["content"]) + 4 for m in text) + 2  # роль-токены


# ──────────────────────────────────────────────────────────────────────────
def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
    temperature: float = 0.7,
    top_p: float = 0.9,
    frequency_penalty: float = 0.25,
    presence_penalty: float = 0.0,
) -> str:
    """
    Отправляет список сообщений (OpenAI-совместимый формат) в Groq
    и возвращает текст ответа ассистента.
    Поддерживаются только параметры, разрешённые Groq API.
    """
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
    )
    return resp.choices[0].message.content.strip()
