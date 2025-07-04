from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.logging_config import get_logger

logger = get_logger(__name__)

embedder = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-base", cache_folder="../models/embeding_model"
)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


async def store_documents_async(file_text_data, persist_dir="../data/chroma"):
    logger.info(f"Начало сохранения документов. persist_dir = {persist_dir}")
    if not file_text_data:
        logger.warning("file_text_data пустой, документы не будут сохранены.")
        return None

    texts = []
    metadatas = []

    for file_id, content, user_id in file_text_data:
        chunks = text_splitter.split_text(content)
        logger.info(f"Файл {file_id}: разбит на {len(chunks)} чанков.")
        texts.extend(chunks)
        metadatas.extend([{"file_id": file_id, "user_id": user_id}] * len(chunks))

    logger.info(f"Всего чанков для сохранения: {len(texts)}")

    try:
        db = Chroma.from_texts(
            texts=texts,
            embedding=embedder,
            metadatas=metadatas,
            persist_directory=persist_dir,
        )
        logger.info(
            f"Документы добавлены в Chroma. Всего документов: {db._collection.count()}"
        )
    except Exception:
        logger.exception("Ошибка при создании Chroma из текстов")
        return None

    try:
        db.persist()
        logger.info(f"База успешно сохранена в {persist_dir}")
    except Exception:
        logger.exception("Ошибка при сохранении Chroma на диск")
        return None

    return db


def load_vector_db(persist_dir="../data/chroma"):
    logger.info(f"Загрузка векторной базы из {persist_dir}")
    try:
        db = Chroma(persist_directory=persist_dir, embedding_function=embedder)
        logger.info(
            f"База успешно загружена. Кол-во документов: {db._collection.count()}"
        )
        return db
    except Exception:
        logger.exception("Ошибка при загрузке Chroma из persist_directory")
        return None
