import logging
from typing import Awaitable, Callable, Union

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


MAX_FILE_SIZE = 10 * 1024


async def read_files_from_drive(
    access_token: str, user_id: int, on_progress: Callable[[str], Awaitable[None]]
) -> list[tuple[str, str, int]]:
    logger.info("🚀 Старт read_files_from_drive, access_token=%s...", access_token[:10])
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "pageSize": 100,  # Запрашиваем больше файлов, чтобы отфильтровать неподходящие
                "fields": "files(id, name, mimeType)",
                "q": "trashed = false",
            },
        )
        resp.raise_for_status()
        files = resp.json().get("files", [])

    logger.info("🗂 Получено %d файлов из Drive", len(files))
    result: list[tuple[str, str, int]] = []

    for file in files:
        if len(result) >= 5:
            break  # Считано достаточно подходящих файлов

        file_name = file["name"]
        mime_type = file["mimeType"]
        file_id = file["id"]

        if mime_type not in TEXT_MIME_TYPES:
            continue  # Пропускаем неподдерживаемые форматы

        logger.info("🔍 Обрабатываю %s (id=%s, mime=%s)", file_name, file_id, mime_type)
        text = await download_and_extract_text(file_id, mime_type, headers, file_name)

        if text:
            logger.info("✅ Прочитал %s", file_name)
            await on_progress(f"✅ Считан файл: {file_name}")
            result.append((file_name, text, user_id))
        else:
            logger.warning("⚠️ Не удалось прочитать %s", file_name)
            await on_progress(
                f"⚠️ Ошибка чтения файла: {file_name}, поддерживаются только txt, pdf, docx"
            )

    if not result:
        await on_progress("ℹ️ Подходящих файлов не найдено в Google Диске.")
    else:
        await on_progress(f"📥 Успешно считано файлов: {len(result)}")

    logger.info("🏁 Завершил read_files_from_drive, всего прочитано: %d", len(result))
    return result


async def download_and_extract_text(
    file_id: str, mime_type: str, headers: dict, file_name: str
) -> str | None:
    """
    Скачивает файл (≤10 КБ), безопасно извлекает текст.
    При неизвестном mime_type пытается определить его по содержимому (через filetype).
    """
    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    try:
        async with httpx.AsyncClient() as client:
            # Проверка размера файла
            head_resp = await client.head(export_url, headers=headers)
            head_resp.raise_for_status()
            size_str = head_resp.headers.get("Content-Length")
            if size_str and int(size_str) > MAX_FILE_SIZE:
                logger.warning("Файл %s превышает 10 КБ (%s байт)", file_id, size_str)
                return None

            # Скачивание файла
            resp = await client.get(export_url, headers=headers)
            resp.raise_for_status()
            content_bytes = resp.content

    except Exception as e:
        logger.warning("Ошибка загрузки файла %s: %s", file_id, e)
        return None

    # Автоопределение MIME
    if mime_type not in TEXT_MIME_TYPES:
        kind = filetype.guess(content_bytes)
        if kind:
            guessed_mime = kind.mime
            logger.info(
                "🔎 MIME от Drive: %s → определён как %s", mime_type, guessed_mime
            )
            mime_type = guessed_mime
        else:
            logger.info(
                "❓ Не удалось определить MIME файла %s по содержимому", file_name
            )

    # Выбор подходящего ридера
    ReaderType = Union[TxtReader, PdfReader, DocxReader, CsvReader, ExcelReader]
    reader: ReaderType | None = None

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

    if not reader:
        logger.info("⏭ Пропускаю %s — неподдерживаемый MIME (%s)", file_name, mime_type)
        return None

    try:
        return await reader.read(content_bytes)
    except Exception as e:
        logger.warning("Ошибка чтения %s (%s): %s", file_name, mime_type, e)
        return None
