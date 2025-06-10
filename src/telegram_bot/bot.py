import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.database.database import DatabaseManager

from src.telegram_bot.handlers.commands_handler import CommandsHandler
from src.telegram_bot.handlers.callbacks_handler import CallbacksHandler
from src.telegram_bot.handlers.poll_answers_handler import PollAnswersHandler

load_dotenv("../.env")
TOKEN = os.getenv("TG_BOT_TOKEN")


# def handle_init_button(callback_data: CallbackQuery):
#     user_data = callback_data.from_user
#     chat_id = callback_data.message.chat.id
#
#     players_json = Db.get_data(Chats, {"chat_id": chat_id}).players
#     if players_json == {}:
#         players = {}
#     else:
#         players = json.loads(players_json)
#
#     players[user_data.id] = {
#         "username": "@" + user_data.username,
#         "skill": 0,
#     }
#
#     Db.upsert(
#         Chats,
#         {"chat_id": chat_id},
#         {"players": json.dumps(players)}
#     )
#
#     return True if len(players.keys()) > 7 else False
#
#
# @dp.callback_query()
# async def handle_callback(callback: CallbackQuery):
#     callback_data = callback.data
#
#     if callback_data.startswith("init"):
#         handle_init_button(callback)
#         callback_response = await bot.send_message(
#             chat_id=callback.message.chat.id,
#             text=f"😉@{callback.from_user.username}, я вижу тебя, игрок!😉",
#             disable_notification=True,
#
#         )
#
#         await asyncio.sleep(5)
#         await bot.delete_message(callback.message.chat.id, callback_response.message_id)


# @dp.poll_answer()
# async def handle_poll_answer(poll: PollAnswer):
#     chat_id, chat_message = Db.get_poll_data(poll.poll_id)
#     selected_option_ids = poll.option_ids
#
#     if not chat_message:
#         return
#
#     if 0 in selected_option_ids:
#         Db.update_poll_vote(poll.poll_id, poll.user.id, poll.user.username, poll.option_ids[0])
#
#     elif 1 in selected_option_ids:
#         Db.update_poll_vote(poll.poll_id, poll.user.id, poll.user.username, poll.option_ids[0])
#
#     vote_count = Db.get_vote_count(poll.poll_id)
#
#     if vote_count == 8:
#         await bot.send_message(
#             chat_id,
#             "Вас уже 8! Уже вполне можно поиграть! Нука забронили, быстро!"
#         )
#
#
# @dp.message(F.text)
# async def handle_text(message: Message):
#     admins = await bot.get_chat_administrators(chat_id=message.chat.id)
#     admins_list = [admin.user.id for admin in admins if admin.user.is_bot is False]
#     if message.from_user.id in admins_list:
#         await handle_players_rating(message)
#
#
# async def handle_players_rating(message):
#     if message.text.startswith("Уровень здешних футболёров:\n"):
#         text = message.text.strip("Уровень здешних футболёров:\n")
#         pattern = r"@(\w+):\s*(\d+)"
#
#         matches = re.findall(pattern, text)
#
#         result = {"@" + username: int(score) for username, score in matches}
#
#         players_json = Db.get_data(Chats, {'chat_id': message.chat.id}).players
#         players = json.loads(players_json)
#         for k, v in players.items():
#             existing_username = v['username']
#             if existing_username in result.keys():
#                 players[k]['skill'] = result[existing_username]
#
#         Db.upsert(Chats, {'chat_id': message.chat.id}, {
#             'players': json.dumps(players),
#             'is_set': True,
#
#         })
#         await message.answer("Замечательно! Я запомнил!\n\n Этот чат готов к каткам.")


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
