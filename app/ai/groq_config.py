from typing import Dict, List

from groq import Groq

from app.core.config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)


def chat_completion(
    messages: List[Dict[str, str]],
    max_tokens: int = 350,
    temperature: float = 0.7,
) -> str:
    """
    Отправляет список сообщений (OpenAI-совместимый формат) в Groq
    и возвращает текст ответа ассистента.
    """
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()
