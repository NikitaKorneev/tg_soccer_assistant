import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.database.database import DatabaseManager

from src.telegram_bot.handlers.commands_handler import CommandsHandler
from src.telegram_bot.handlers.callbacks_handler import CallbacksHandler
from src.telegram_bot.handlers.poll_answers_handler import PollAnswersHandler

load_dotenv("../.env")
TOKEN = os.getenv("TG_BOT_TOKEN")


async def mainloop():
    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            disable_notification=True,

        )
    )

    Db = DatabaseManager()
    dp = Dispatcher()

    dp.include_routers(
        CommandsHandler(bot, Db).router,
        CallbacksHandler(bot, Db).router,
        PollAnswersHandler(bot, Db).router,


    )

    await dp.start_polling(bot)
