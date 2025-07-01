from functools import lru_cache
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "sberbank-ai/rugpt3small_based_on_gpt2"
HF_CACHE_DIR = os.getenv("HF_HOME", "/mnt/models")

@lru_cache(maxsize=1)
def get_model():
    """
    Загружает токенизатор и INT8-квантованную модель при первом вызове,
    затем кэширует результат в памяти процесса.
    """
    tok = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=HF_CACHE_DIR)

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        cache_dir=HF_CACHE_DIR,
        low_cpu_mem_usage=True,         # экономия RAM
        torch_dtype=torch.float32,      # безопасный CPU-режим
    )

    # 💡 динамическое квантование только Linear-слоёв (экономия памяти)
    quant_model = torch.quantization.quantize_dynamic(
        base_model, {torch.nn.Linear}, dtype=torch.qint8
    )
    quant_model.eval()

    return tok, quant_model