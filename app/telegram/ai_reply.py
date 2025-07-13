import torch

from app.core.logging_config import get_logger
from app.core.vector_store import load_vector_db
from app.llm import get_model

logger = get_logger(__name__)
MAX_NEW_TOKENS = 120


def search_knowledge(query: str, k: int = 5) -> list[str]:
    db = load_vector_db()
    results = db.similarity_search(query, k=k)
    return [r.page_content for r in results]


def generate_reply(history: list[dict]) -> str:
    latest_user_input = next(
        (msg["text"] for msg in reversed(history) if msg["role"] == "user"), "..."
    )

    logger.info("Генерация ответа, последнее сообщение: %s", latest_user_input)

    context_chunks = search_knowledge(latest_user_input)
    if context_chunks:
        context = "\n\n".join(context_chunks)
        system_prompt = (
            "Ты полезный AI-ассистент. "
            "Используй контекст из файлов Google Диска для точных, кратких и понятных ответов.\n\n"
            f"Контекст:\n{context}"
        )
        logger.info("Добавлен контекст (%d чанков)", len(context_chunks))
    else:
        system_prompt = (
            "Ты полезный AI-ассистент. "
            "Отвечай кратко и понятно на основе истории диалога."
        )
        logger.info("Контекст не найден")

    # 💬 Формирование промпта
    prompt = f"<|system|>\n{system_prompt}\n"
    for msg in history:
        prompt += f"<|{msg['role']}|>\n{msg['text'].strip()}\n"
    prompt += "<|assistant|>\n"

    logger.info("Промпт сформирован: %s...", prompt)

    tokenizer, model = get_model()
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)

    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=MAX_NEW_TOKENS,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            do_sample=False,
        )

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
    answer = decoded.split("<|assistant|>")[-1].strip()
    for stop_token in ["<|user|>", "user:", "assistant:", "you:", "ai:"]:
        if stop_token in answer.lower():
            answer = answer.split(stop_token)[0].strip()
    logger.info("PROMPT:\n%s\n\nRESPONSE:\n%s", prompt, answer)
    logger.info("Ответ сгенерирован: %s", answer or "[пусто]")
    return answer or "🤖 Пока не знаю, как ответить."
