# app/telegram/handlers/drive.py
import multiprocessing

from telegram import Update
from telegram.ext import ContextTypes

from app.core.logging_config import get_logger
from app.core.vector_store import store_documents_async
from app.services.google_drive import read_files_from_drive

logger = get_logger(__name__)


def _fetch_token_process(telegram_id: int, conn):
    from app.services.token_refresh_sync import get_valid_access_token_sync

    try:
        conn.send(get_valid_access_token_sync(telegram_id))
    except Exception as e:
        conn.send(e)
    finally:
        conn.close()


async def cmd_load_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /load_drive <all | file1.pdf, file2.docx | Folder1/, Folder2/>
    • если аргументов НЕТ → ничего не считываем, выводим подсказку
    • all                → считываем все поддерживаемые файлы
    • имена файлов       → считываем только их
    • имена папок (slash)→ считываем файлы из этих папок
    • можно комбинировать (файлы + папки)
    """
    telegram_id = update.effective_user.id
    logger.info("🚀 /load_drive запущен, telegram_id=%s", telegram_id)

    # 1️⃣  Разбор аргументов
    raw_parts = (update.message.text or "").split(maxsplit=1)
    if len(raw_parts) == 1:  # пользователь не передал аргументы
        await update.message.reply_text(
            "ℹ️ Использование:\n"
            "  /load_drive all — считать все файлы\n"
            "  /load_drive file1.pdf, file2.docx — конкретные файлы\n"
            "  /load_drive Папка1/, Папка2/ — все файлы из папок\n"
            "Можно комбинировать: Папка/, отчет.docx"
        )
        return

    arg_str = raw_parts[1].strip()
    if arg_str.lower() == "all":
        file_names = folder_names = None
    else:
        items = [i.strip() for i in arg_str.split(",") if i.strip()]
        file_names = [i for i in items if not i.endswith("/")]
        folder_names = [i.rstrip("/") for i in items if i.endswith("/")]
        if not file_names and not folder_names:
            await update.message.reply_text(
                "⚠️ Не удалось распознать ни файлов, ни папок."
            )
            return

    # 2️⃣  Получаем access_token (блокирующий код в отдельном процессе)
    parent_conn, child_conn = multiprocessing.Pipe()
    proc = multiprocessing.Process(
        target=_fetch_token_process, args=(telegram_id, child_conn)
    )
    proc.start()
    result = parent_conn.recv()
    proc.join()

    if isinstance(result, Exception):
        logger.warning("❌ Токен не получен: %s", result)
        await update.message.reply_text(
            "❌ Не удалось получить токен Google. Используй /connect_google"
        )
        return

    access_token: str = result
    logger.info("✅ Токен получен, telegram_id=%s", telegram_id)

    async def progress(text: str):
        logger.info(text)
        await update.message.reply_text(text)

    await update.message.reply_text("🔄 Начинаю чтение файлов…")

    # 3️⃣  Читаем файлы
    try:
        files = await read_files_from_drive(
            access_token=access_token,
            user_id=telegram_id,
            on_progress=progress,
            file_names=file_names,
            folder_names=folder_names,
        )
    except Exception as e:
        logger.error("❌ Ошибка чтения: %s", e)
        await update.message.reply_text("❌ Произошла ошибка при чтении файлов.")
        return

    if not files:
        await update.message.reply_text("⚠️ Файлы не найдены.")
        return

    await update.message.reply_text(f"📚 Считано файлов: {len(files)}")
    await update.message.reply_text("💾 Сохраняю данные в базу знаний…")

    # 4️⃣  Сохраняем в векторное хранилище
    try:
        await store_documents_async(files)
        await update.message.reply_text("✅ Файлы успешно сохранены в базу знаний!")
    except Exception as e:
        logger.error("❌ Ошибка при сохранении: %s", e)
        await update.message.reply_text("❌ Ошибка при сохранении в базу знаний.")
