import httpx
import logging
from .reader.txt_reader import TxtReader

logger = logging.getLogger(__name__)

TEXT_MIME_TYPES = {
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/pdf": "pdf",
}

async def read_files_from_drive(access_token: str, on_progress: callable) -> list[str]:
    logger.info("🚀 Старт read_files_from_drive, access_token=%s...", access_token[:10])
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={"pageSize": 10, "fields": "files(id, name, mimeType)"},
        )
        resp.raise_for_status()
        files = resp.json().get("files", [])
    logger.info("🗂 Получено %d файлов из Drive", len(files))

    result: list[str] = []

    for file in files:
        file_name = file["name"]
        mime_type = file["mimeType"]
        file_id = file["id"]
        logger.info("🔍 Обрабатываю %s (id=%s, mime=%s)", file_name, file_id, mime_type)

        if mime_type not in TEXT_MIME_TYPES:
            logger.info("⏭ Пропускаю %s — неподдерживаемый MIME", file_name)
            await on_progress(f"⏭️ Пропущен файл: {file_name} ({mime_type})")
            continue

        text = await download_and_extract_text(file_id, mime_type, headers)
        if text:
            logger.info("✅ Прочитал %s", file_name)
            await on_progress(f"✅ Считан файл: {file_name}")
            result.append(f"📄 {file_name}:\n{text}...")
        else:
            logger.warning("⚠️ Не удалось прочитать %s", file_name)
            await on_progress(f"⚠️ Ошибка чтения файла: {file_name}")

    if not files:
        logger.info("ℹ️ Нет файлов для чтения")
        await on_progress("ℹ️ В Google Диске не найдено файлов.")

    logger.info("🏁 Завершил read_files_from_drive, всего прочитано: %d", len(result))
    return result

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

async def download_and_extract_text(file_id: str, mime_type: str, headers: dict) -> str | None:
    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    try:
        async with httpx.AsyncClient() as client:
            # 1. HEAD-запрос — узнаём размер
            head_resp = await client.head(export_url, headers=headers)
            head_resp.raise_for_status()
            size_str = head_resp.headers.get("Content-Length")

            if size_str and int(size_str) > MAX_FILE_SIZE:
                logger.warning("Файл %s превышает размер в 10 МБ (%s байт)", file_id, size_str)
                return None

            # 2. Загружаем файл, если не превышен
            resp = await client.get(export_url, headers=headers)
            resp.raise_for_status()
            content_bytes = resp.content

    except Exception as e:
        logger.warning("Ошибка загрузки файла %s: %s", file_id, e)
        return None

    if mime_type == "text/plain":
        reader = TxtReader()
        return await reader.read(content_bytes)

    elif mime_type == "application/pdf":
        return "[pdf-файл, чтение пока не реализовано]"

    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return "[docx-файл, чтение пока не реализовано]"

    return None
