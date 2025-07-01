from functools import lru_cache
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from app.core.logging_config import get_logger

logger = get_logger(__name__)

MODEL_ID = "Unbabel/Tower-Plus-2B"
HF_CACHE_DIR = os.getenv("HF_HOME", "/mnt/models")

@lru_cache(maxsize=1)
def get_model():
    logger.info("Начало загрузки модели %s", MODEL_ID)

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        cache_dir=HF_CACHE_DIR
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        cache_dir=HF_CACHE_DIR,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float32  
    )

    model.eval()

    logger.info("✅ Модель и токенизатор успешно загружены")
    return tokenizer, model
