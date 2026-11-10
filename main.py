import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import BOT_TOKEN
from bot.db import db
from bot.handlers import admin, menu, quiz
from bot.questions import bank


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not BOT_TOKEN:
        raise SystemExit("Укажи BOT_TOKEN в файле .env (см. .env.example)")

    bank.load()
    logging.info("Загружено вопросов: %d", bank.total())
    await db.init()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(admin.router, menu.router, quiz.router)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start / Начать / Boshlash"),
            BotCommand(command="menu", description="Menu / Меню / Menyu"),
            BotCommand(command="stats", description="Stats / Статистика / Statistika"),
            BotCommand(command="top", description="Top / Рейтинг / Reyting"),
        ]
    )
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
