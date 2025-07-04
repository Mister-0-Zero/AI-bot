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


def generate_reply(user_text: str) -> str:
    logger.info("Получен запрос от пользователя: %s", user_text)

    prompt = "Ты AI-ассистент, который дает ответы пользователям \
              на основе файлов, загруженных с google disk пользователей. \
              Твои ответы должны быть краткими и четкими.\n\n"
    # 🔍 Поиск знаний в векторной БД
    context_chunks = search_knowledge(user_text)
    if context_chunks:
        context = "\n\n".join(context_chunks)
        prompt += f"Контекст:\n{context}\n\nПользователь: {user_text}\nАссистент:"
        logger.info("Добавлен контекст из БД (%d чанков)", len(context_chunks))
    else:
        prompt += f"Пользователь: {user_text}\nАссистент:"
        logger.info("Контекст не найден, используется только вопрос")

    tokenizer, model = get_model()
    inputs = tokenizer(prompt, return_tensors="pt")

    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=MAX_NEW_TOKENS,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True,
            top_p=0.9,
            temperature=0.7,
        )

    decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)

    if "Ассистент:" in decoded:
        answer = decoded.split("Ассистент:")[-1].strip()
    else:
        answer = decoded.strip()

    logger.info("Ответ сгенерирован: %s", answer or "[пусто]")
    return answer or "🤖 Пока не знаю, как ответить."
