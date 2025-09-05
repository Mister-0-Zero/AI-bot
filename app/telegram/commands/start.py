from pathlib import Path
from typing import Literal, Optional, cast

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from app.core.db import get_session
from app.core.logging_config import get_logger
from app.models.user import User
from app.telegram.commands.help import HELP_TEXT  # используем тексты /help

logger = get_logger(__name__)
Lang = Literal["ru", "en"]

TEXTS = {
    "pick_lang": {
        "ru": "🌐 <b>Выберите язык интерфейса</b>",
        "en": "🌐 <b>Choose your language</b>",
    },
    "title": {"ru": "👋 <b>Добро пожаловать!</b>", "en": "👋 <b>Welcome!</b>"},
    "subtitle": {
        "ru": (
            "Этот бот подключается к Google Диску, читает ваши файлы и отвечает "
            "на вопросы на основе их содержимого."
        ),
        "en": (
            "This bot connects to your Google Drive, reads your files, and answers "
            "questions based on their content."
        ),
    },
    "menu_home": {"ru": "🏠 Главное", "en": "🏠 Home"},
    "menu_help": {"ru": "🛟 Команды", "en": "🛟 Commands"},
    "menu_instruction": {"ru": "📘 Инструкция", "en": "📘 Instruction"},
    "menu_connect": {"ru": "🔗 Подключить Google", "en": "🔗 Connect Google"},
    "instruction_text": {
        "ru": (
            "📘 <b>Как начать</b>\n\n"
            "1) Введите /connect_google и пройдите авторизацию.\n"
            "2) Введите /load_drive (или /load_drive all), чтобы считать файлы.\n"
            "3) Задавайте вопросы по содержимому документов.\n"
        ),
        "en": (
            "📘 <b>Getting started</b>\n\n"
            "1) Use /connect_google and authorize access.\n"
            "2) Use /load_drive (or /load_drive all) to index files.\n"
            "3) Ask questions based on your documents.\n"
        ),
    },
    "connect_text": {
        "ru": "🔗 <b>Подключение Google</b>\n\nНажмите /connect_google и завершите авторизацию. Затем используйте /load_drive.",
        "en": "🔗 <b>Google connection</b>\n\nRun /connect_google and complete authorization. Then use /load_drive.",
    },
}


def t(key: str, lang: Lang) -> str:
    return TEXTS[key][lang]


# ── Клавиатуры ───────────────────────────────────────────────────────────────
def kb_start_lang() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Русский", callback_data="start:setlang:ru"),
                InlineKeyboardButton("English", callback_data="start:setlang:en"),
            ]
        ]
    )


def kb_main(lang: Lang) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t("menu_instruction", lang), callback_data="menu:instruction"
                )
            ],
            [InlineKeyboardButton(t("menu_help", lang), callback_data="menu:help")],
            [
                InlineKeyboardButton(
                    t("menu_connect", lang), callback_data="menu:connect"
                )
            ],
        ]
    )


def kb_home(lang: Lang) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("menu_home", lang), callback_data="menu:home")]]
    )


# ── DB ───────────────────────────────────────────────────────────────────────
async def _get_or_create_user(telegram_id: int) -> User:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if not user:
            user = User(telegram_id=telegram_id)  # lang='ru' по умолчанию
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def _set_user_lang(telegram_id: int, lang: Lang) -> None:
    async with get_session() as session:
        user = await session.get(User, telegram_id)
        if not user:
            user = User(telegram_id=telegram_id, lang=lang)
            session.add(user)
        else:
            user.lang = lang
        await session.commit()


def _to_lang(val: Optional[str]) -> Lang:
    # Строго приводим к Literal — всё, что не 'en', считаем 'ru'
    return cast(Lang, ("en" if val == "en" else "ru"))


# ── Рендеры ─────────────────────────────────────────────────────────────────
async def _render_home(update: Update, lang: Lang, *, edit: bool):
    text = f"{t('title', lang)}\n\n{t('subtitle', lang)}"
    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb_main(lang)
            )
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise
    else:
        em = update.effective_message
        await em.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb_main(lang))


async def _render_view(update: Update, lang: Lang, view: str):
    if view == "help":
        text = HELP_TEXT[lang]
    elif view == "instruction":
        text = TEXTS["instruction_text"][lang]
    elif view == "connect":
        text = TEXTS["connect_text"][lang]
    else:
        text = "…"
    await update.callback_query.edit_message_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=kb_home(lang),
        disable_web_page_preview=True,
    )


# ── /start ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    em = update.effective_message

    # Картинка (если есть) + спрятать старую reply-клавиатуру без "…"
    image_path = Path("app/assets/welcome.png")
    if image_path.exists():
        with open(image_path, "rb") as image:
            await em.reply_photo(photo=image, reply_markup=ReplyKeyboardRemove())

    # 1) сначала выбор языка
    await em.reply_text(
        "🌐 Выберите язык / Choose language",
        parse_mode=ParseMode.HTML,
        reply_markup=kb_start_lang(),
    )


# ── Колбэк: выбор языка из /start ───────────────────────────────────────────
async def cb_start_set_language(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if not data.startswith("start:setlang:"):
        return
    raw = data.split(":", 2)[2]
    if raw not in ("ru", "en"):
        return
    lang = cast(Lang, raw)  # <- приводим к Literal
    await _set_user_lang(update.effective_user.id, lang)
    await _render_home(update, lang, edit=True)


# ── Колбэк: перелистывание меню ─────────────────────────────────────────────
async def cb_start_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = (q.data or "").strip()

    user = await _get_or_create_user(update.effective_user.id)
    lang = _to_lang(getattr(user, "lang", None))  # <- всегда Lang

    if data == "menu:home":
        await _render_home(update, lang, edit=True)
    elif data == "menu:help":
        await _render_view(update, lang, "help")
    elif data == "menu:instruction":
        await _render_view(update, lang, "instruction")
    elif data == "menu:connect":
        await _render_view(update, lang, "connect")
