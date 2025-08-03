from __future__ import annotations

import logging
from typing import Awaitable, Callable, List

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
    "text/csv": "csv",
    "application/vnd.ms-excel": "csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}

MAX_FILES_PER_RUN = 10
MAX_FILE_SIZE = 100 * 1024  # 100 КБ


# ──────────────────────────────────────────────────────────────────────────
# ── public API ───────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────
async def read_files_from_drive(
    access_token: str,
    user_id: int,
    on_progress: Callable[[str], Awaitable[None]],
    selected_names: List[str] | None = None,
) -> List[tuple[str, str, str, int]]:
    """
    Считывает текстовые файлы из Google Drive.

    * selected_names is None  → читаем любые поддерживаемые файлы (до 10 шт.).
    * selected_names = [...]  → читаем только заданные файлы
                                (полное совпадение имени, регистр игнорируется).

    Возвращает список кортежей (file_id, file_name, text, user_id) только
    для успешно распарсенных файлов.
    """
    tok_short = access_token[:10] + "…" if len(access_token) > 10 else access_token
    logger.info("🚀 read_files_from_drive started, token=%s", tok_short)
    await on_progress("🔄 Ищу файлы в Google Диске…")

    # 1️⃣  Получаем полный список файлов
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "pageSize": 1000,
                "fields": "files(id,name,mimeType)",
                "q": "trashed = false",
            },
        )
        resp.raise_for_status()
        files = resp.json().get("files", [])

    logger.info("🗂 Всего найдено %d файлов в Drive", len(files))

    # 2️⃣  Фильтр по имени, если нужно
    if selected_names is not None:
        name_set = {n.lower() for n in selected_names}
        files = [f for f in files if f["name"].lower() in name_set]
        logger.info("🔎 После фильтра по имени: %d файлов", len(files))

    if not files:
        return []  # сигнал вызывающему, что ничего не найдено

    # 3️⃣  Фильтр по MIME и ограничение количества
    candidates = [f for f in files if f["mimeType"] in TEXT_MIME_TYPES][
        :MAX_FILES_PER_RUN
    ]
    logger.info("📄 Подходящих по MIME: %d", len(candidates))

    result: List[tuple[str, str, str, int]] = []

    # 4️⃣  Обработка каждого файла
    for meta in candidates:
        file_id, file_name, mime_type = meta["id"], meta["name"], meta["mimeType"]

        await on_progress(f"🔍 Читаю: {file_name}")
        logger.debug(
            "🔍 Обрабатываю %s (id=%s, mime=%s)", file_name, file_id, mime_type
        )

        text = await _download_and_extract_text(
            file_id=file_id,
            file_name=file_name,
            mime_type=mime_type,
            headers=headers,
        )

        if text:
            result.append((file_id, file_name, text, user_id))
            await on_progress(f"✅ Готово: {file_name}")
        else:
            await on_progress(f"⚠️ Пропущен: {file_name}")

        if len(result) >= MAX_FILES_PER_RUN:
            break  # лимит на один запуск

    await on_progress(f"📥 Успешно считано файлов: {len(result)}")
    logger.info("🏁 read_files_from_drive finished. total=%d", len(result))
    return result


# ──────────────────────────────────────────────────────────────────────────
# ── helpers ───────────────────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────────────────
async def _download_and_extract_text(
    file_id: str,
    file_name: str,
    mime_type: str,
    headers: dict,
) -> str | None:
    """Скачивает файл и извлекает текст. Вернёт None, если >100 КБ или формат не поддерживается."""
    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    async with httpx.AsyncClient() as client:
        # Попытка HEAD для оценки размера
        try:
            head = await client.head(export_url, headers=headers, follow_redirects=True)
            if (cl := head.headers.get("Content-Length")) and int(cl) > MAX_FILE_SIZE:
                logger.info("⏭ %s > 100 КБ (по Content-Length)", file_name)
                return None
        except Exception:
            pass  # HEAD не обязателен

        # GET содержимого
        try:
            resp = await client.get(export_url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            content = resp.content
        except Exception as e:
            logger.warning("❌ Не скачан %s: %s", file_name, e)
            return None

    if len(content) > MAX_FILE_SIZE:
        logger.info("⏭ %s > 100 КБ (факт)", file_name)
        return None

    # Уточняем MIME по содержимому, если Drive прислал неточный
    if mime_type not in TEXT_MIME_TYPES:
        if kind := filetype.guess(content):
            mime_type = kind.mime

    reader = _select_reader(mime_type)
    if not reader:
        logger.debug("⏭ %s — неподдерживаемый MIME %s", file_name, mime_type)
        return None

    try:
        return await reader.read(content)
    except Exception as e:
        logger.warning("⚠️ Ошибка чтения %s: %s", file_name, e)
        return None


def _select_reader(mime_type: str):
    """Возвращает подходящий ридер или None."""
    return {
        "text/plain": TxtReader(),
        "application/pdf": PdfReader(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxReader(),
        "text/csv": CsvReader(),
        "application/vnd.ms-excel": CsvReader(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ExcelReader(),
    }.get(mime_type)
