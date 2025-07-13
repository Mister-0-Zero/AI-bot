from functools import lru_cache

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.core.config import HF_CACHE_DIR, MODEL_ID
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_model():
    logger.info("🔄 Загрузка модели %s", MODEL_ID)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=HF_CACHE_DIR)
    # Важно: установить pad_token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        cache_dir=HF_CACHE_DIR,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto",
    )
    model.eval()

    device = next(model.parameters()).device
    logger.info("✅ Модель загружена и размещена на %s", device)

    return tokenizer, model
