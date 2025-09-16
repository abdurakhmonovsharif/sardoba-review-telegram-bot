import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import settings
from app.handlers import user as user_handlers
from app.handlers import admin as admin_handlers
from app.db.session import get_session, engine
from app.db import models

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from app.middlewares import DbSessionMiddleware

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(dp: Dispatcher):
    # DB init (jadval yaratish)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import settings
from app.handlers import user as user_handlers
from app.handlers import admin as admin_handlers
from app.db.session import engine
from app.db import models

logging.basicConfig(level=logging.INFO)

async def main():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    from app.i18n import I18N
    t_uz = I18N("uz").t
    t_ru = I18N("ru").t
    await bot.set_my_commands([
        BotCommand(command="start", description=t_uz("cmd.start", "Boshlash")),
        BotCommand(command="admin", description=t_uz("cmd.admin", "Admin menyu")),
        BotCommand(command="yangi_sharh", description=t_uz("cmd.new_review", "Yangi sharh")),
        BotCommand(command="novyy_otzyv", description=t_ru("cmd.new_review", "Новый отзыв")),
    ])

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to‘xtatildi")
async def main():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # DB session middleware
    @dp.update.outer_middleware()
    async def db_session_mw(handler, event, data):
        async for session in get_session():
            data["session"]: AsyncSession = session # type: ignore
            return await handler(event, data)

    # Routerlarni ulash
    dp.include_router(user_handlers.router)
    dp.include_router(admin_handlers.router)

    # Bot buyruqlari
    from app.i18n import I18N
    t_uz = I18N("uz").t
    t_ru = I18N("ru").t
    await bot.set_my_commands([
        BotCommand(command="start", description=t_uz("cmd.start", "Boshlash")),
        BotCommand(command="new_review", description=t_uz("cmd.new_review", "Yangi sharh")),
        BotCommand(command="new_review", description=t_ru("cmd.new_review", "Новый отзыв")),
        ])

    async with lifespan(dp):
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to‘xtatildi")
