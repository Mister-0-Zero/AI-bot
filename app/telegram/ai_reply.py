from app.ai.groq_config import chat_completion
from app.core.logging_config import get_logger
from app.core.vector_store import load_vector_db

logger = get_logger(__name__)
MAX_NEW_TOKENS = 350


def search_knowledge(
    query: str,
    user_id: int,
    k: int = 8,
) -> list[str]:
    """
    Возвращает релевантные чанки из базы пользователя.
    Для коротких ( < 3 слов) запросов ничего не ищет.
    """
    q = query.strip()
    words = q.split()

    # ⚑ 1. Мелкие сервис-фразы вообще не требуют файлового контекста
    if len(words) < 3:
        return []

    db = load_vector_db()

    # ⚑ 2. Сразу берём (Document, score)
    docs_scores = db.similarity_search_with_relevance_scores(
        q,
        k=k,
        filter={"user_id": user_id},  # ищем только среди файлов этого пользователя
    )

    # ⚑ 3. Динамический порог: чем короче запрос, тем выше порог
    min_score = 0.65 if len(words) == 3 else 0.55 if len(words) == 4 else 0.45

    return [doc.page_content for doc, score in docs_scores if score >= min_score]


MAX_MSGS = 6


def generate_reply(history: list[dict], user_id: int) -> str:
    latest_user_input = (
        next((m["text"] for m in reversed(history) if m["role"] == "user"), "...")
        .strip()
        .lower()
    )

    # ── RAG-контекст ───────────────────────────────────────────────
    context_chunks = search_knowledge(latest_user_input, user_id)
    if context_chunks:
        context_block = "Контекст:\n" + "\n\n".join(context_chunks)
        system_prompt = (
            "Ты полезный AI-ассистент. Используй контекст из файлов Google Диска "
            "для точных, кратких и понятных ответов.\n\n" + context_block
        )
    else:
        system_prompt = "Ты полезный AI-ассистент. Отвечай кратко и понятно на основе истории диалога."
    # ── messages ──────────────────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-MAX_MSGS:]:
        messages.append({"role": msg["role"], "content": msg["text"].strip()})

    logger.info("System prompt подготовлен")

    # ── вызов Groq ────────────────────────────────────────────────
    try:
        answer = chat_completion(messages, max_tokens=350, temperature=0.7)
    except Exception as e:
        logger.exception("Groq error: %s", e)
        return "⚠️ Не удалось получить ответ модели. Попробуйте ещё раз."

    return answer or "🤖 Пока не знаю, как ответить."
