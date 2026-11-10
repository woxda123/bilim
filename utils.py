import html

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, User

from .db import db


async def user_of(u: User):
    """Строка пользователя из БД (создаётся, если её ещё нет)."""
    row = await db.get_user(u.id)
    return row or await db.ensure_user(u.id, u.full_name)


async def show(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None = None) -> None:
    """Редактирует сообщение с кнопкой; если нельзя — отправляет новое."""
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest as e:
        if "not modified" in str(e):
            return
        await cb.message.answer(text, reply_markup=kb)


def esc(text: str) -> str:
    return html.escape(text or "", quote=False)


def short_name(name: str, limit: int = 18) -> str:
    name = (name or "—").strip()
    return esc(name if len(name) <= limit else name[: limit - 1] + "…")
