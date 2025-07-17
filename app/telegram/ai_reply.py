import re
from typing import List

from app.ai.groq_config import chat_completion
from app.core.logging_config import get_logger
from app.core.vector_store import load_vector_db

logger = get_logger(__name__)
MAX_NEW_TOKENS = 350


def _translate_ru_to_en(text: str) -> str:
    """
    Одноразовый перевод запроса на английский.
    Используем Groq — бесплатно и 1-2 токена.
    """
    try:
        resp = chat_completion(
            [
                {"role": "system", "content": "Translate the text to English."},
                {"role": "user", "content": text},
            ],
            max_tokens=60,
            temperature=0.0,
        )
        return resp.strip()
    except Exception as e:
        logger.warning("Translation failed: %s", e)
        return ""


def search_knowledge(query: str, user_id: int, k: int = 8) -> List[str]:
    """
    Возвращает релевантные текстовые чанки из базы пользователя.
    * Если пользователь явно упоминает «файл(ы) по …» — фильтруем по имени.
    * Если запрос целиком на кириллице, ищем ещё и английскую версию.
    """
    q = query.strip()
    words = q.split()
    if len(words) < 3:  # сервис-фразы не требуют RAG
        return []

    # ── детектируем подсказку имени файла ───────────────────────────────
    m = re.search(r"(?:файл(?:ы)? по|files? (?:about|on))\s+([\w\-\.\s]+)", q, re.I)
    filename_hint = m.group(1).strip().lower() if m else None

    # ── готовим список запросов (ru + en) ───────────────────────────────
    queries = [q]
    if not re.search(r"[A-Za-z]", q):  # только кириллица
        en = _translate_ru_to_en(q)
        if en:
            queries.append(en)

    db = load_vector_db()
    results = []

    # ── делаем семантический поиск по каждому запросу ───────────────────
    for q_ in queries:
        docs_scores = db.similarity_search_with_relevance_scores(
            q_,
            k=k,
            filter={"user_id": user_id},
        )
        results.extend(docs_scores)

    # ── объединяем, фильтруем по имени файла (если был хинт) ─────────────
    uniq: dict[str, float] = {}  # id -> best_score
    docs: dict[str, str] = {}  # id -> text

    for doc, score in results:
        fname = doc.metadata.get("file_name", "").lower()
        if filename_hint and filename_hint not in fname:
            continue  # не тот файл
        doc_id = doc.metadata["file_id"] + doc.page_content[:20]
        best = uniq.get(doc_id, 0)
        if score > best:
            uniq[doc_id] = score
            docs[doc_id] = doc.page_content

    # ── динамический порог ──────────────────────────────────────────────
    min_score = 0.65 if len(words) == 3 else 0.55 if len(words) == 4 else 0.35

    # оставляем только те, что выше порога
    return [docs[d] for d, s in uniq.items() if s >= min_score][:k]


MAX_MSGS = 6


def generate_reply(history: list[dict], user_id: int) -> str:
    latest_user_input = (
        next((m["text"] for m in reversed(history) if m["role"] == "user"), "...")
        .strip()
        .lower()
    )

    logger.info("Пользовательский ввод: %s", latest_user_input)

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

    logger.info("Сообщения для Groq: %s", messages)

    # ── вызов Groq ────────────────────────────────────────────────
    try:
        answer = chat_completion(messages, max_tokens=350, temperature=0.7)
    except Exception as e:
        logger.exception("Groq error: %s", e)
        return "⚠️ Не удалось получить ответ модели. Попробуйте ещё раз."

    logger.info("Ответ от Groq: %s", answer)

    return answer or "🤖 Пока не знаю, как ответить."
