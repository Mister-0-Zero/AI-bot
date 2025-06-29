import httpx
import logging
from .reader.txt_reader import TxtReader

logger = logging.getLogger(__name__)

# Список MIME-типов, которые считаем "текстовыми"
TEXT_MIME_TYPES = {
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/pdf": "pdf",
}

# Главная функция
async def read_files_from_drive(access_token: str, on_progress: callable) -> list[str]:
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "pageSize": 10,
                "fields": "files(id, name, mimeType)"
            }
        )
        resp.raise_for_status()
        files = resp.json().get("files", [])

    result = []

    for file in files:
        file_name = file["name"]
        mime_type = file["mimeType"]
        file_id = file["id"]

        if mime_type not in TEXT_MIME_TYPES:
            await on_progress(f"⏭️ Пропущен файл: {file_name} ({mime_type})")
            continue

        text = await download_and_extract_text(file_id, mime_type, headers)
        if text:
            await on_progress(f"✅ Считан файл: {file_name}")
            result.append(f"📄 {file_name}:\n{text}...")
        else:
            await on_progress(f"⚠️ Ошибка чтения файла: {file_name}")

    if not files:
        await on_progress("ℹ️ В Google Диске не найдено файлов.")

    return result

# Чтение содержимого файла (пока только .txt)
async def download_and_extract_text(file_id: str, mime_type: str, headers: dict) -> str | None:
    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(export_url, headers=headers)
            resp.raise_for_status()
            content_bytes = resp.content
    except Exception as e:
        logger.warning("Ошибка загрузки файла %s: %s", file_id, e)
        return None

    # Пока обрабатываем только .txt
    if mime_type == "text/plain":
        reader = TxtReader()
        return await reader.read(content_bytes)

    # Заглушки под pdf/docx
    elif mime_type == "application/pdf":
        return "[pdf-файл, чтение пока не реализовано]"

    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "[docx-файл, чтение пока не реализовано]"

    return None
