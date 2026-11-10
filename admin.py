import asyncio

from aiogram import Bot, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from ..config import ADMIN_IDS
from ..db import db
from ..questions import bank

router = Router()


def _is_admin(m: Message) -> bool:
    return m.from_user and m.from_user.id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(m: Message) -> None:
    if not _is_admin(m):
        return
    per_subject = "\n".join(f"• {s}: {len(v)}" for s, v in sorted(bank.by_subject.items()))
    await m.answer(
        f"🛠 <b>Admin</b>\n👥 Пользователей: <b>{await db.count_users()}</b>\n"
        f"📚 Вопросов: <b>{bank.total()}</b>\n{per_subject}\n\n"
        "/broadcast &lt;текст&gt; — рассылка всем"
    )


@router.message(Command("broadcast"))
async def cmd_broadcast(m: Message, command: CommandObject, bot: Bot) -> None:
    if not _is_admin(m):
        return
    if not command.args:
        return await m.answer("Использование: /broadcast текст")
    sent = failed = 0
    for uid in await db.all_user_ids():
        try:
            await bot.send_message(uid, command.args)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # лимиты Telegram ~30 сообщений/сек
    await m.answer(f"✅ Отправлено: {sent}, ошибок: {failed}")
