from functools import lru_cache
import os
import torch                                  # ← добавь
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID     = "sberbank-ai/rugpt3small_based_on_gpt2"
HF_CACHE_DIR = os.getenv("HF_HOME", "/mnt/models")

@lru_cache(maxsize=1)
def get_model():
    """
    Загружает токенизатор и INT8-квантованную модель при первом вызове,
    затем кэширует в памяти процесса.
    """
    tok = AutoTokenizer.from_pretrained(MODEL_ID, cache_dir=HF_CACHE_DIR)

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        cache_dir=HF_CACHE_DIR,
        device_map="cpu",
        low_cpu_mem_usage=True,      # потоковая загрузка — меньше RAM-пик
    )

    # —— динамическое квантование до int8 только Linear-слоёв ——
    quant_model = torch.quantization.quantize_dynamic(
        base_model, {torch.nn.Linear}, dtype=torch.qint8
    )
    quant_model.eval()

    return tok, quant_model