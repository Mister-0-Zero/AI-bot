from __future__ import annotations

import multiprocessing
from typing import Any, Iterable, List, Optional

from telegram import Update
from telegram.ext import ContextTypes

from app.core.logging_config import get_logger
from app.core.vector_store import store_documents_async
from app.services.google_drive import read_files_from_drive

logger = get_logger(__name__)


def _fetch_token_process(telegram_id: int, conn):
    """Синхронно получаем валидный access_token в отдельном процессе."""
    from app.services.token_refresh_sync import get_valid_access_token_sync

    try:
        token = get_valid_access_token_sync(telegram_id)
        conn.send(token)
    except Exception as e:
        conn.send(e)
    finally:
        try:
            conn.close()
        except Exception:
            pass


async def cmd_load_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /load_drive <all | file1.pdf, file2.docx | Folder1/, Folder2/>
    • без аргументов → показать подсказку
    • all            → считать все поддерживаемые файлы
    • файлы          → считать только их
    • папки (с /)    → считать файлы из этих папок
    • можно комбинировать (файлы + папки)
    """
    telegram_id = update.effective_user.id
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("🚀 /load_drive запущен, telegram_id=%s", telegram_id)

    async def _safe_reply(text: str):
        """Надёжная отправка ответа пользователю (без падений по сетевым ошибкам)."""
        try:
            if update.message:
                await update.message.reply_text(text)
                return
        except Exception as e:
            logger.warning("Проблема при reply_text: %s", e)
        # fallback
        if chat_id is not None:
            try:
                await ctx.bot.send_message(chat_id=chat_id, text=text)
            except Exception:
                logger.exception("Не удалось отправить сообщение пользователю")

    # 1) Разбор аргументов
    raw_text = (update.message.text or "").strip() if update.message else ""
    parts = raw_text.split(maxsplit=1)
    if len(parts) == 1:
        await _safe_reply(
            "ℹ️ Использование:\n"
            "  /load_drive all — считать все файлы\n"
            "  /load_drive file1.pdf, file2.docx — конкретные файлы\n"
            "  /load_drive Папка1/, Папка2/ — все файлы из папок\n"
            "Можно комбинировать: Папка/, отчет.docx"
        )
        return

    arg_str = parts[1].strip()
    if arg_str.lower() == "all":
        file_names: Optional[List[str]] = None
        folder_names: Optional[List[str]] = None
    else:
        items = [i.strip() for i in arg_str.split(",") if i.strip()]
        file_names = [i for i in items if not i.endswith("/")]
        folder_names = [i.rstrip("/") for i in items if i.endswith("/")]
        if not file_names and not folder_names:
            await _safe_reply("⚠️ Не удалось распознать ни файлов, ни папок.")
            return

    # 2) Получаем access_token (блокирующий код — в отдельном процессе)
    parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
    proc = multiprocessing.Process(
        target=_fetch_token_process, args=(telegram_id, child_conn), daemon=True
    )
    proc.start()
    result = parent_conn.recv()
    proc.join(timeout=5)

    if isinstance(result, Exception):
        logger.warning("❌ Токен не получен: %s", result)
        await _safe_reply(
            "❌ Не удалось получить токен Google. Используйте /connect_google"
        )
        return

    access_token: str = str(result or "")
    if not access_token:
        logger.error("❌ Пустой access_token для telegram_id=%s", telegram_id)
        await _safe_reply(
            "❌ Не удалось получить токен Google. Повторите /connect_google"
        )
        return

    logger.info("✅ Токен получен, telegram_id=%s", telegram_id)

    async def progress(text: str):
        logger.info(text)
        await _safe_reply(text)

    await _safe_reply("🔄 Начинаю чтение файлов…")

    # 3) Читаем файлы из Google Drive
    try:
        files = await read_files_from_drive(
            access_token=access_token,
            user_id=telegram_id,
            on_progress=progress,
            file_names=file_names,
            folder_names=folder_names,
        )
    except Exception as e:
        msg = f"{e}"
        logger.error("❌ Ошибка чтения: %s", msg)
        # Частый кейс после смены скоупов: недостаточно прав / нет пересогласия
        if "insufficientPermissions" in msg or "403" in msg:
            await _safe_reply(
                "❌ Недостаточно прав для чтения Google Drive. "
                "Пожалуйста, выполните повторное подключение: /connect_google"
            )
        else:
            await _safe_reply("❌ Произошла ошибка при чтении файлов.")
        return

    # Нормализуем тип: None → []
    if files is None:
        logger.warning("read_files_from_drive вернул None — заменяю на пустой список")
        files = []

    # Проверяем, что это итерируемый контейнер
    if not isinstance(files, Iterable) or isinstance(files, (str, bytes)):
        logger.error("Неверный тип ответа от read_files_from_drive: %r", type(files))
        await _safe_reply(
            "❌ Внутренняя ошибка: неверный формат данных от Google Drive."
        )
        return

    # Удаляем None/пустые элементы
    files_list: List[Any] = [f for f in files if f]
    if not files_list:
        await _safe_reply("⚠️ Файлы не найдены.")
        return

    await _safe_reply(f"📚 Считано файлов: {len(files_list)}")
    await _safe_reply("💾 Сохраняю данные в базу знаний…")

    # 4) Сохраняем в векторное хранилище
    try:
        await store_documents_async(files_list)
        await _safe_reply("✅ Файлы успешно сохранены в базу знаний!")
    except Exception as e:
        logger.error("❌ Ошибка при сохранении: %s", e)
        await _safe_reply("❌ Ошибка при сохранении в базу знаний.")
