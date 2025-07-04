import os
from functools import lru_cache

import torch
from huggingface_hub import login
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.core.config import MODEL_ID, MODEL_TOKEN
from app.core.logging_config import get_logger

login(token=MODEL_TOKEN)

logger = get_logger(__name__)

HF_CACHE_DIR = os.getenv("HF_HOME", "/mnt/models")


@lru_cache(maxsize=1)
def get_model():
    logger.info("🔄 Начало загрузки модели %s", MODEL_ID)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=HF_CACHE_DIR)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, cache_dir=HF_CACHE_DIR, torch_dtype=torch.float16, device_map="auto"
    )

    model.eval()

    device = next(model.parameters()).device
    logger.info("✅ Модель и токенизатор успешно загружены на %s", device)
    return tokenizer, model
