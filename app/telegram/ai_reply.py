from app.llm import get_model
import torch

MAX_NEW_TOKENS = 120

def generate_reply(user_text: str) -> str:      # ← убрали async
    tok, model = get_model()
    prompt = f"Пользователь: {user_text}\nМодель:"
    inputs = tok(prompt, return_tensors="pt")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            pad_token_id=tok.eos_token_id,
            do_sample=True, top_p=0.9, temperature=0.8,
        )
    full = tok.decode(outputs[0], skip_special_tokens=True)
    return full.split("Модель:")[-1].strip() or "🤖 …"