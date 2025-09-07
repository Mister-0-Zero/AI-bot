"""
app/services/google_drive.py

Чтение текстовых файлов из Google Drive c поддержкой:
  • all            – все подходящие файлы (до MAX_FILES_PER_RUN)
  • списка файлов  – точное совпадение name
  • списка папок   – все файлы внутри этих папок
  • комбинированного списка (файлы + папки)

Формат возвращаемого списка:
    (file_id, file_name, extracted_text, user_id)
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Sequence

import aiohttp
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

FOLDER_MIME = "application/vnd.google-apps.folder"

MAX_FILES_PER_RUN = 10
MAX_FILE_SIZE = 100 * 1024  # 100 КБ


# ──────────────────────────────────────────────────────────────
# ─── public API ───────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────
async def read_files_from_drive(
    access_token: str,
    user_id: int,
    on_progress: Callable[[str], Awaitable[None]],
    *,
    file_names: Sequence[str] | None = None,
    folder_names: Sequence[str] | None = None,
) -> List[tuple[str, str, str, int]]:
    """
    Читает текстовые файлы из Google Drive.

    Параметры
    ---------
    access_token : str
        OAuth-токен пользователя.
    user_id : int
        Telegram ID — сохраняется в результате.
    on_progress : coroutine(str) -> None
        Callback для вывода статуса пользователю.
    file_names : list[str] | None
        Точные имена файлов (без пути). Если None, режим «читать всё».
    folder_names : list[str] | None
        Точные имена папок. Если заданы, читаем файлы из этих папок.

    Возвращает
    ----------
    list[tuple[file_id, file_name, text, user_id]]
    """
    tok_short = access_token[:10] + "…" if len(access_token) > 10 else access_token
    logger.info("🚀 read_files_from_drive started, token=%s", tok_short)

    read_all_mode = file_names is None and folder_names is None
    if read_all_mode:
        await on_progress("🔄 Ищу все подходящие файлы в Google Диске…")
    else:
        await on_progress("🔄 Ищу указанные файлы/папки в Google Диске…")

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        meta_list: list[dict] = []

        # 1) Режим «читать всё»
        if read_all_mode:
            meta_list = await _list_files(
                client,
                headers,
                q="trashed=false",
                fields="files(id,name,mimeType,parents)",
            )

        # 2) Папки
        if folder_names:
            for folder in folder_names:
                q_folder = (
                    f"trashed=false and mimeType='{FOLDER_MIME}' and name='{folder}'"
                )
                folders = await _list_files(client, headers, q=q_folder, page_size=1)
                if not folders:
                    logger.info("📂 Папка «%s» не найдена", folder)
                    continue

                folder_id = folders[0]["id"]
                q_inside = f"'{folder_id}' in parents and trashed=false"
                files_in_folder = await _list_files(
                    client,
                    headers,
                    q=q_inside,
                    fields="files(id,name,mimeType,parents)",
                )
                meta_list.extend(files_in_folder)

        # 3) Файлы (первое точное совпадение по имени)
        if file_names:
            for name in file_names:
                q_file = (
                    f"trashed=false and name='{name}' and mimeType!='{FOLDER_MIME}'"
                )
                files = await _list_files(
                    client,
                    headers,
                    q=q_file,
                    page_size=1,
                    fields="files(id,name,mimeType,parents)",
                )
                if files:
                    meta_list.append(files[0])
                else:
                    logger.info("📄 Файл «%s» не найден", name)

    if not meta_list:
        logger.info("❌ Ничего не найдено по запросу.")
        return []

    # ── Убираем дубликаты (по id)
    seen: set[str] = set()
    unique_meta = []
    for m in meta_list:
        fid = m.get("id")
        if fid and fid not in seen:
            seen.add(fid)
            unique_meta.append(m)

    # ── Оставляем только поддерживаемые MIME и ограничиваем количество
    candidates = [m for m in unique_meta if m.get("mimeType") in TEXT_MIME_TYPES][
        :MAX_FILES_PER_RUN
    ]
    logger.info("📄 К обработке выбрано %d файлов", len(candidates))

    result: list[tuple[str, str, str, int]] = []

    for meta in candidates:
        file_id = meta.get("id", "")
        file_name = meta.get("name", "")
        mime_type = meta.get("mimeType", "")

        if not file_id or not file_name or not mime_type:
            logger.warning("Пропуск из-за неполных метаданных: %s", meta)
            continue

        await on_progress(f"🔍 Читаю: {file_name}")

        try:
            text = await _download_and_extract_text(
                file_id=file_id,
                file_name=file_name,
                mime_type=mime_type,
                headers=headers,
            )
        except PermissionError as e:
            # Проброс наверх, чтобы cmd_load_drive показал пересогласование
            logger.error("❌ Недостаточно прав при чтении %s: %s", file_name, e)
            raise
        except Exception as e:
            logger.warning("⚠️ Ошибка скачивания/извлечения %s: %s", file_name, e)
            text = ""

        if text:
            result.append((file_id, file_name, text, user_id))
            await on_progress(f"✅ Готово: {file_name}")
        else:
            await on_progress(f"⚠️ Пропущен: {file_name}")

        if len(result) >= MAX_FILES_PER_RUN:
            break

    await on_progress(f"📥 Успешно считано файлов: {len(result)}")
    logger.info("🏁 read_files_from_drive finished. total=%d", len(result))
    return result


# ──────────────────────────────────────────────────────────────
# ─── helpers ──────────────────────────────────────────────────
# ──────────────────────────────────────────────────────────────
async def _list_files(
    client: httpx.AsyncClient,
    headers: dict,
    q: str,
    *,
    page_size: int = 100,
    fields: str = "files(id,name,mimeType)",
) -> list[dict]:
    """Обёртка над Drive files.list (одна страница). Никогда не возвращает None."""
    try:
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "pageSize": page_size,
                "fields": fields,
                "q": q,
                # Явно работаем с личным диском пользователя:
                "corpora": "user",
                "includeItemsFromAllDrives": "false",
                "supportsAllDrives": "false",
                "spaces": "drive",
            },
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else None
        logger.error("Drive list failed (%s): %s", status, e)
        if status in (401, 403):
            # Поднимем предсказуемую ошибку, чтобы хендлер подсказал /connect_google
            raise PermissionError("insufficientPermissions: re-consent required") from e
        raise
    except Exception as e:
        logger.exception("Drive list failed (generic): %s", e)
        return []

    return resp.json().get("files", []) or []


async def _download_and_extract_text(
    file_id: str,
    file_name: str,
    mime_type: str,
    headers: dict,
) -> str:
    """
    Скачивает файл и извлекает текст.
    Всегда возвращает строку: "" при ошибке/слишком большом размере/неподдерживаемом типе.
    """
    export_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"

    # HEAD → оценка размера (если сервер даёт Content-Length)
    try:
        async with httpx.AsyncClient() as client:
            head = await client.head(export_url, headers=headers, follow_redirects=True)
            if head.status_code == 401 or head.status_code == 403:
                raise PermissionError("insufficientPermissions: cannot download")
            cl = head.headers.get("Content-Length")
            if cl and int(cl) > MAX_FILE_SIZE:
                logger.info("⏭ %s > 100 КБ (по Content-Length)", file_name)
                return ""
    except PermissionError:
        raise
    except Exception:
        # HEAD может не поддерживаться — продолжаем
        pass

    # GET → содержимое
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(export_url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            content = resp.content
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else None
        logger.warning("❌ Не скачан %s: %s", file_name, e)
        if status in (401, 403):
            raise PermissionError("insufficientPermissions: cannot download") from e
        return ""
    except Exception as e:
        logger.warning("❌ Не скачан %s: %s", file_name, e)
        return ""

    if len(content) > MAX_FILE_SIZE:
        logger.info("⏭ %s > 100 КБ (факт)", file_name)
        return ""

    # Уточняем MIME, если нестандартный
    if mime_type not in TEXT_MIME_TYPES:
        try:
            kind = filetype.guess(content)
            if kind and kind.mime:
                mime_type = kind.mime
        except Exception:
            pass

    reader = _select_reader(mime_type)
    if not reader:
        logger.debug("⏭ %s — неподдерживаемый MIME %s", file_name, mime_type)
        return ""

    # Чтение содержимого
    try:
        text = await reader.read(content)
        return text or ""
    except Exception as e:
        logger.warning("⚠️ Ошибка чтения %s: %s", file_name, e)
        return ""


def _select_reader(mime_type: str):
    """Подбирает ридер по MIME."""
    return {
        "text/plain": TxtReader(),
        "application/pdf": PdfReader(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxReader(),
        "text/csv": CsvReader(),
        "application/vnd.ms-excel": CsvReader(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ExcelReader(),
    }.get(mime_type)


async def list_drive_children(
    *, access_token: str, folder_id: str = "root", page_size: int = 200
) -> Dict[str, Any]:
    """
    Возвращает элементы текущей папки.
    items: [{id, name, is_folder: bool}]
    """
    url = "https://www.googleapis.com/drive/v3/files"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "q": f"'{folder_id}' in parents and trashed=false",
        "fields": "files(id,name,mimeType)",
        "pageSize": page_size,
        "orderBy": "folder,name",
        "supportsAllDrives": "true",
        "includeItemsFromAllDrives": "true",
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, headers=headers, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()
    items_raw: List[Dict[str, Any]] = data.get("files", [])
    items = [
        {
            "id": it["id"],
            "name": it["name"],
            "is_folder": (it.get("mimeType") == "application/vnd.google-apps.folder"),
        }
        for it in items_raw
    ]
    return {"items": items}
