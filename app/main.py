import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
# ensure the repository root is on sys.path so `app` imports work when running this file directly
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import settings
from app.db import models
from app.db.session import engine
from app.handlers import admin as admin_handlers
from app.handlers import user as user_handlers
from app.middlewares import DbSessionMiddleware

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(dp: Dispatcher):
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield


async def main():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    from app.i18n import I18N

    t_uz = I18N("uz").t
    t_ru = I18N("ru").t
    await bot.set_my_commands(
        [
            BotCommand(command="start", description=t_uz("cmd.start", "Boshlash")),
            BotCommand(
                command="new_review",
                description=t_uz("cmd.new_review", "Yangi sharh"),
            ),
            BotCommand(
                command="new_review",
                description=t_ru("cmd.new_review", "Новый отзыв"),
            ),
        ]
    )

    async with lifespan(dp):
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to‘xtatildi")
