from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.telegram_bot.config import BOT_TOKEN
from src.database.db import AsyncDatabaseManager, engine, init_db
from src.telegram_bot.handlers.callbacks_handler import CallbacksHandler
from src.telegram_bot.handlers.commands_handler import CommandsHandler
from src.telegram_bot.handlers.poll_answers_handler import PollAnswersHandler


async def mainloop():
    await init_db(engine)  # Инициализируем базу.

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            disable_notification=True,

        )
    )

    Db = AsyncDatabaseManager()
    dp = Dispatcher()

    dp.include_routers(
        CommandsHandler(bot, Db).router,
        CallbacksHandler(bot, Db).router,
        PollAnswersHandler(bot, Db).router,


    )

    await dp.start_polling(bot)
