import logging
from typing import Awaitable, Callable

import filetype
import httpx

from app.services.reader.csv_reader import CsvReader
from app.services.reader.docx_reader import DocxReader
from app.services.reader.excel_reader import ExcelReader
from app.services.reader.pdf_reader import PdfReader
from app.services.reader.txt_reader import TxtReader

logger = logging.getLogger(__name__)

TEXT_MIME_TYPES = {
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/pdf": "pdf",
    "text/csv": "csv",  # ← CSV
    "application/vnd.ms-excel": "csv",  # .csv в Drive
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",  # .xlsx
}


MAX_FILES_PER_RUN = 10


async def read_files_from_drive(
    access_token: str,
    user_id: int,
    on_progress: Callable[[str], Awaitable[None]],
) -> list[tuple[str, str, str, int]]:
    """
    Считывает до 10 текстовых файлов из Google Drive.
    Возвращает список (file_id, text, user_id) только для успешно распарсенных.
    """
    logger.info("🚀 read_files_from_drive started, token=%s...", access_token[:10])
    await on_progress("🔄 Ищу файлы в Google Диске…")

    # --- 1. Получаем список файлов
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "pageSize": 100,
                "fields": "files(id,name,mimeType)",
                "q": "trashed = false",
            },
        )
        resp.raise_for_status()
        files = resp.json().get("files", [])

    logger.info("🗂 Найдено %d файлов в Drive", len(files))

    # --- 2. Фильтрация: оставляем только поддерживаемые MIME
    candidates = [f for f in files if f["mimeType"] in TEXT_MIME_TYPES][
        :MAX_FILES_PER_RUN
    ]
    logger.info("📄 Подходящих файлов: %d", len(candidates))

    result: list[tuple[str, str, str, int]] = []

    # --- 3. Обрабатываем каждый файл
    for meta in candidates:
        file_id = meta["id"]
        file_name = meta["name"]
        mime_type = meta["mimeType"]

        await on_progress(f"🔍 Читаю: {file_name}")
        logger.info("🔍 Обрабатываю %s (id=%s, mime=%s)", file_name, file_id, mime_type)

        text = await download_and_extract_text(file_id, mime_type, headers, file_name)

        if text:
            result.append((file_id, file_name, text, user_id))
            await on_progress(f"✅ Готово: {file_name}")
        else:
            await on_progress(f"⚠️ Пропущен: {file_name}")

        if len(result) >= MAX_FILES_PER_RUN:
            break  # лимит на один запуск

    # --- 4. Итог
    await on_progress(f"📥 Успешно считано файлов: {len(result)}")
    logger.info("🏁 read_files_from_drive finished. total=%d", len(result))
    return result


MAX_FILE_SIZE = 100 * 1024


async def download_and_extract_text(
    file_id: str,
    mime_type: str,
    headers: dict,
    file_name: str,
) -> str | None:
    """
    Скачивает файл, дважды контролируя лимит 10 КБ, а затем извлекает текст.
    Возвращает None, если файл превышает лимит или формат не поддерживается.
    """
    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    async with httpx.AsyncClient() as client:
        # ── Предварительный HEAD-запрос (может не сработать, но пробуем)
        try:
            head = await client.head(export_url, headers=headers, follow_redirects=True)
            size_hdr = head.headers.get("Content-Length")
            if size_hdr and int(size_hdr) > MAX_FILE_SIZE:
                logger.warning(
                    "⏭ %s > 100 КБ (по Content-Length: %s байт)", file_name, size_hdr
                )
                return None
        except Exception as e:
            logger.debug("HEAD %s не удался: %s (продолжаю)", file_name, e)

        # ── Скачиваем файл
        try:
            resp = await client.get(export_url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            content_bytes = resp.content
        except Exception as e:
            logger.warning("❌ Ошибка загрузки %s: %s", file_name, e)
            return None

    # ── Финальная проверка фактического размера
    if len(content_bytes) > MAX_FILE_SIZE:
        logger.warning(
            "⏭ %s > 100 КБ (фактически: %d байт)", file_name, len(content_bytes)
        )
        return None

    # ── Уточняем MIME по содержимому, если нужно
    if mime_type not in TEXT_MIME_TYPES:
        kind = filetype.guess(content_bytes)
        if kind:
            mime_type = kind.mime

    # ── Выбираем ридер
    reader: TxtReader | PdfReader | DocxReader | CsvReader | ExcelReader | None = None
    if mime_type == "text/plain":
        reader = TxtReader()
    elif mime_type == "application/pdf":
        reader = PdfReader()
    elif (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        reader = DocxReader()
    elif mime_type in {"text/csv", "application/vnd.ms-excel"}:
        reader = CsvReader()
    elif (
        mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        reader = ExcelReader()
    else:
        logger.info("⏭ %s — неподдерживаемый MIME (%s)", file_name, mime_type)
        return None

    # ── Читаем текст
    try:
        return await reader.read(content_bytes)
    except Exception as e:
        logger.warning("⚠️ Ошибка чтения %s: %s", file_name, e)
        return None
