import re
from typing import List

import tiktoken

from app.ai.groq_config import chat_completion
from app.core.logging_config import get_logger
from app.core.vector_store import load_vector_db

LLAMA_MODEL = "llama-3.3-70b-versatile"
MAX_CTX_TOKENS = 131_072  # полное окно модели
MAX_OUTPUT_TOKENS = 32_768  # лимит Groq на «completion»

try:
    _enc = tiktoken.encoding_for_model(LLAMA_MODEL)
except KeyError:  # fallback для новых моделей
    _enc = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def convert_md_to_html(text: str) -> str:
    """
    Преобразует **жирный** и *курсив* из Markdown в HTML,
    чтобы Telegram правильно отобразил.
    """
    # сначала жирный, потом курсив, чтобы не пересекались
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text


logger = get_logger(__name__)


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
            "для точных, кратких и понятных ответов. Если необходимо задавай уточняющие вопросы"
            "для выдачи более точных ответов. Пиши пошаговые стратегии, идеи и решения для поставленных вопросов.\n\n"
            + context_block
        )
    else:
        system_prompt = "Ты полезный AI-ассистент. Отвечай кратко и понятно на основе истории диалога."

    # ── messages ──────────────────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-MAX_MSGS:]:
        messages.append({"role": msg["role"], "content": msg["text"].strip()})

    logger.info("Сообщения для Groq: %s", messages)

    # ── вызов Groq ────────────────────────────────────────────────
    RESERVED_OUT = 1024  # хотим ≤1024 токенов на ответ
    MAX_PROMPT = MAX_CTX_TOKENS - RESERVED_OUT

    def _messages_tokens(msgs: list[dict]) -> int:
        return sum(_count_tokens(m["content"]) + 4 for m in msgs) + 2

    # — динамическая усадка промпта —
    while True:
        prompt_tokens = _messages_tokens(messages)
        if prompt_tokens <= MAX_PROMPT:
            break

        # 1) убираем самое старое сообщение истории
        if len(messages) > 2:
            messages.pop(1)  # messages[0] — system
            continue

        # 2) режем последний чанк контекста
        if "Контекст:" in messages[0]["content"]:
            parts = messages[0]["content"].split("\n\n")
            if len(parts) > 2:  # «Контекст:\n» + ≥1 чанка
                parts.pop()
                messages[0]["content"] = "\n\n".join(parts)
                continue

        # 3) край: грубо обрезаем строку
        messages[0]["content"] = messages[0]["content"][:8000] + "…"
        break

    # свободные токены и лимит вывода
    free_tokens = MAX_CTX_TOKENS - _messages_tokens(messages)
    max_tokens = min(RESERVED_OUT, free_tokens - 1, MAX_OUTPUT_TOKENS)

    logger.info(
        "prompt %d токенов, свободно %d, запрашиваю %d",
        MAX_CTX_TOKENS - free_tokens,
        free_tokens,
        max_tokens,
    )

    try:
        answer = chat_completion(
            messages,
            max_tokens=max_tokens,
            temperature=0.7,
            top_p=0.9,
            frequency_penalty=0.25,  # мягко подавляем повторы
        )
    except Exception as e:
        logger.exception("Groq error: %s", e)
        return "⚠️ Не удалось получить ответ модели. Попробуйте ещё раз."

    answer = convert_md_to_html(answer.strip())
    logger.info("Ответ от Groq: %s", answer)
    return answer or "🤖 Пока не знаю, как ответить."
