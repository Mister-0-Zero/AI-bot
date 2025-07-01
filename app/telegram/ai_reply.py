from app.llm import get_model
import torch
from app.core.logging_config import get_logger

logger = get_logger(__name__)
MAX_NEW_TOKENS = 120

def generate_reply(user_text: str) -> str:
    logger.info("Получен запрос от пользователя: %s", user_text)

    tokenizer, model = get_model()

    prompt = f"Пользователь: {user_text}\nАссистент:"
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

    # Корректно вырезаем только ответ ассистента
    if "Ассистент:" in decoded:
        answer = decoded.split("Ассистент:")[-1].strip()
    else:
        answer = decoded.strip()

    logger.info("Ответ сгенерирован: %s", answer or '[пусто]')
    return answer or "🤖 Пока не знаю, как ответить."