from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.core.db import get_session
from app.core.logging_config import get_logger
from app.models.user import User

logger = get_logger(__name__)


def _kb_lang() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Русский", callback_data="setlang:ru"),
                InlineKeyboardButton("English", callback_data="setlang:en"),
            ]
        ]
    )


async def _set_user_lang(telegram_id: int, lang: str) -> None:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if not user:
            user = User(telegram_id=telegram_id, lang=lang)
            session.add(user)
        else:
            user.lang = lang
        await session.commit()


async def cmd_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # единый текст, чтобы отработать даже до выбора языка
    text = "🌐 Выберите язык / Choose language"
    await update.message.reply_text(text, reply_markup=_kb_lang())


async def cb_set_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if not data.startswith("setlang:"):
        return
    lang = data.split(":", 1)[1]
    if lang not in {"ru", "en"}:
        return

    await _set_user_lang(update.effective_user.id, lang)

    if lang == "ru":
        confirm = "✅ Язык интерфейса: Русский.\nТеперь можно использовать /start."
    else:
        confirm = "✅ Interface language: English.\nYou can use /start now."

    # Перерисуем то же сообщение, чтобы не спамить чат
    await q.edit_message_text(confirm)
