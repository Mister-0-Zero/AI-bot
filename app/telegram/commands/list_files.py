from telegram import Update
from telegram.ext import ContextTypes

from app.core.vector_store import load_vector_db


async def cmd_list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = load_vector_db()
    if db is None:
        await update.message.reply_text("❌ Векторная база данных не найдена.")
        return

    try:
        results = db._collection.get(include=["metadatas"], where={"user_id": user_id})
        metadatas = results.get("metadatas", [])

        file_names = sorted(
            {meta.get("file_name") or meta["file_id"] for meta in metadatas}
        )

        if not file_names:
            await update.message.reply_text("ℹ️ Вы ещё не загружали файлы.")
        else:
            text = "📂 Ваши загруженные файлы:\n\n" + "\n".join(
                f"• {name}" for name in file_names
            )
            await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text("⚠️ Ошибка при получении списка файлов.")
        raise e
