from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple
from uuid import uuid4

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import CHROMA_DIR, EMBEDDING_DIR
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# ── параметры ────────────────────────────────────────────────────────────────
MAX_FILES_PER_USER = 10
embedder = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-base",
    cache_folder=str(EMBEDDING_DIR),
)
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


# ─── публичный загрузчик базы (для импорта из ai_reply и др.) ────────────────
def load_vector_db(persist_dir: Path | str = CHROMA_DIR) -> Chroma:
    """
    Возвращает Chroma-базу: если каталог уже существует — загружает,
    иначе создаёт новый.
    """
    p_dir = Path(persist_dir)
    if p_dir.exists():
        db = Chroma(persist_directory=str(p_dir), embedding_function=embedder)
        logger.info(
            "Chroma загружена (%s), документов: %d", p_dir, db._collection.count()
        )
        return db

    logger.info("Chroma не найдена — создаю новую (%s)", p_dir)
    return Chroma(embedding_function=embedder, persist_directory=str(p_dir))


# ─── внутренний утилити ──────────────────────────────────────────────────────
def _user_file_set(db: Chroma, user_id: int) -> Set[str]:
    """Отдаёт все file_id, сохранённые для указанного пользователя."""
    try:
        res = db.get(where={"user_id": user_id}, include=["metadatas"])
        return {meta["file_id"] for meta in res["metadatas"]}
    except Exception:
        return set()


# ─── основная функция записи документов ──────────────────────────────────────
async def store_documents_async(
    file_text_data: Iterable[Tuple[str, str, str, int]],
    persist_dir: Path | str = CHROMA_DIR,
) -> Chroma | None:
    """
    Обновляет Chroma:
      • максимум 10 файлов на пользователя;
      • повторный file_id → полный перезапис векторов;
      • «лишние» новые файлы (когда лимит достигнут) пропускаются.
    """
    data = list(file_text_data)
    if not data:
        logger.warning("store_documents_async: пустой вход")
        return None

    db = load_vector_db(persist_dir)

    # --- группировка входных файлов по пользователям -------------------------
    per_user: Dict[int, List[Tuple[str, str, str]]] = defaultdict(list)
    for file_id, file_name, text, user_id in file_text_data:
        per_user[user_id].append((file_id, file_name, text))

    # --- обработка каждого пользователя --------------------------------------
    for user_id, files in per_user.items():
        existing = _user_file_set(db, user_id)

        for file_id, file_name, text in files:
            # перезапись, если такой file_id уже был
            if file_id in existing:
                db._collection.delete(where={"file_id": file_id, "user_id": user_id})
                existing.remove(file_id)

            # проверка лимита
            if len(existing) >= MAX_FILES_PER_USER:
                logger.warning(
                    "⏭ user %s: лимит %d файлов, пропускаю %s",
                    user_id,
                    MAX_FILES_PER_USER,
                    file_id,
                )
                continue

            # добавление новых чанков
            header = f"=== FILE: {file_name.lower()} ===\n"
            text_with_header = header + text
            chunks = splitter.split_text(text_with_header)

            ids = [f"{file_id}_{uuid4().hex[:8]}_{i}" for i in range(len(chunks))]
            metadatas = [
                {"file_id": file_id, "file_name": file_name, "user_id": user_id}
            ] * len(chunks)

            db._collection.add(
                ids=ids,
                documents=chunks,
                embeddings=embedder.embed_documents(chunks),
                metadatas=metadatas,
            )
            existing.add(file_id)
            logger.info(
                "✅ user %s: сохранён %s (%d чанков)", user_id, file_id, len(chunks)
            )

    db.persist()
    logger.info("📦 Chroma сохранена")
    return db
