from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

embedder = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-base", cache_folder="../models/embeding_model")
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

async def store_documents_async(file_text_pairs, persist_dir="../data/chroma"):
    texts = []
    metadatas = []
    for file_id, content in file_text_pairs:
        chunks = text_splitter.split_text(content)
        texts.extend(chunks)
        metadatas.extend([{"file_id": file_id}] * len(chunks))

    db = Chroma.from_texts(
        texts=texts,
        embedding=embedder,
        metadatas=metadatas,
        persist_directory=persist_dir
    )
    db.persist()
    return db


def load_vector_db(persist_dir="../data/chroma"):
    return Chroma(
        persist_directory=persist_dir,
        embedding_function=embedder
    )