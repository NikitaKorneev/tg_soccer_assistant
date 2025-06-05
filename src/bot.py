import asyncio
import json
import os
import re
from dotenv import load_dotenv
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, PollAnswer, InputPollOption, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import CallbackQuery

from database import DatabaseManager, Polls, Chats

load_dotenv()
TOKEN = os.getenv("TG_BOT_TOKEN")

Db = DatabaseManager()

dp = Dispatcher()
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        disable_notification=True,

    )
)


@dp.message(CommandStart())
async def handle_start(message: Message):
    is_group = str(message.chat.id).startswith("-")

    if is_group:
        chat_exists, is_set = Db.check_new(message.chat.id)
        chat_member_count = await message.chat.get_member_count()
        chat_admins = await message.chat.get_administrators()

        if not chat_exists:
            Db.upsert(
                Chats,
                {},
                {
                    "chat_id": message.chat.id,
                    "player_count": chat_member_count,
                }
            )

            message_start = f"""Вечер в чай Вам, работяги/работягини.
            
Я бот и я навожу порядок в футбольных чатах.
Очень скоро я смогу организовывать Ваши игры, команды а главное - жестко опускать тех кто не ходит играть в футбол.

Но это потом.

Для начала мне нужно узнать кто тут есть в чате.

Телеграм беспокоится о вашей безопасности - пока вы не нажмете на кнопку ниже Я как бы ХЗ кто есть в этом чате.
Если вы готовы к безудержному веселью:

Как только вас будет достаточно - Я дам знать Вашим админам: что делать далее.

ЖМИТЕ КНОПКУ ВНИЗУ ЕСЛИ ВЫ ФУТБОЛЁРЫ!
"""

            init_message = await message.answer(
                text=message_start,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🤙Я ГОТОВ🤙", callback_data=f"init{message.chat.id}")]
                    ]
                )
            )

            await bot.pin_chat_message(
                chat_id=message.chat.id,
                message_id=init_message.message_id,
            )

        elif is_set:
            await message.answer(
                "Тут уже всё настроили!"
            )

    else:
        await message.answer(
            "Этот бот - для футбольных чатов, дружок-пирожок. Кроме этого тут делать нечего."
        )


def handle_init_button(callback_data: CallbackQuery):
    user_data = callback_data.from_user
    chat_id = callback_data.message.chat.id

    players_json = Db.get_data(Chats, {"chat_id": chat_id}).players
    if players_json == {}:
        players = {}
    else:
        players = json.loads(players_json)

    players[user_data.id] = {
        "username": "@" + user_data.username,
        "skill": 0,
    }

    Db.upsert(
        Chats,
        {"chat_id": chat_id},
        {"players": json.dumps(players)}
    )

    return True if len(players.keys()) > 7 else False


@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    callback_data = callback.data

    if callback_data.startswith("init"):
        handle_init_button(callback)
        callback_response = await bot.send_message(
            chat_id=callback.message.chat.id,
            text=f"😉@{callback.from_user.username}, я вижу тебя, игрок!😉"
        )

        await asyncio.sleep(10)
        await bot.delete_message(callback.message.chat.id, callback_response.message_id)


@dp.message(Command('setup'))
async def handle_players_setup(message: Message):
    admins = await bot.get_chat_administrators(chat_id=message.chat.id)
    admins_list = [admin.user.id for admin in admins if admin.user.is_bot is False]

    if message.from_user.id in admins_list:
        players = Db.get_data(Chats, {"chat_id": message.chat.id}).players
        rate_call = """Скопируй сообщение после этого, вставь его в чат\n\nНО и дай оценку каждому игроку от 1 до 10."""
        example = """Пример:\n\nИгрок 1: 5\nИгрок 2: 7"""
        admins_name = [admin.user.username for admin in admins if admin.user.is_bot is False and admin.user.username is not None]
        print(admins_name)

        if players != {}:
            players = json.loads(players)

        players_list = "\n".join([player['username']+ ": " for k, player in players.items()])

        if len(players.keys()) > 1:  # TODO: Add admins list
            await message.answer(
                f"Пришла пора кому то из админов оценить уровень футболистов в этой "
                f"конфе.\n\n{rate_call}\n\n{example}"
            )
            await message.answer(
                f"Уровень здешних футболёров:\n{players_list}"
            )
    else:
        await message.answer(
            "Такое тут могут делать только админы, дружок-пирожок..."
        )


@dp.message(Command("poll"))
async def handle_poll_creation(message: Message):
    Db.close_all_polls()
    date_time = message.text.strip("/poll ")
    player_count = await message.chat.get_member_count()
    call_to_arms = f"⚽⚽️️Мужчины, собирается очередная катка.\n\n{date_time}\n\n Вижу что вас тут {player_count}.⚽⚽️"

    created_poll = await bot.send_poll(
        chat_id=message.chat.id,
        question=call_to_arms,
        options=[
            InputPollOption(text="✅Я в деле✅"),
            InputPollOption(text="❌Сами пинайте эту хуйню❌")
        ],
        is_anonymous=False,

    )

    Db.upsert(
        Polls,
        {"poll_id": created_poll.poll.id},
        {
            "chat_id": message.chat.id,
            "poll_id": created_poll.poll.id,
            "poll_message_id": created_poll.message_id,
            "timestamp": datetime.now(),
            "voters": json.dumps({}),
            "is_closed": created_poll.poll.is_closed
        }
    )

    await bot.pin_chat_message(created_poll.chat.id, created_poll.message_id)


@dp.message(Command("close_poll"))
async def handle_close_poll(message: Message):
    poll_data = Db.get_data(Polls, {"chat_id": message.chat.id})

    poll_message_id = poll_data.poll_message_id

    if poll_message_id:
        poll_results = await bot.stop_poll(
            message.chat.id,
            poll_message_id

        )

        text = Db.get_poll_results(poll_results.id)
        cool_list = "\n".join(['@' + text[user]['username'] for user in text.keys() if text[user]['vote'] == 0])
        bad_list = "\n".join(['@' + text[user]['username'] for user in text.keys() if text[user]['vote'] == 1])

        await bot.send_message(
            chat_id=message.chat.id,
            text=f"Предлагаю поаплодировать сильным мужчинам: \n{cool_list}"
        )

        await bot.send_message(
            chat_id=message.chat.id,
            text=f"А этим анальным слизням можно только посочувствовать. Фу бля...: \n{bad_list}"
        )

        Db.close_poll(message.chat.id)


@dp.poll_answer()
async def handle_poll_answer(poll: PollAnswer):
    chat_id, chat_message = Db.get_poll_data(poll.poll_id)
    selected_option_ids = poll.option_ids

    if not chat_message:
        return

    if 0 in selected_option_ids:
        Db.update_poll_vote(poll.poll_id, poll.user.id, poll.user.username, poll.option_ids[0])

    elif 1 in selected_option_ids:
        Db.update_poll_vote(poll.poll_id, poll.user.id, poll.user.username, poll.option_ids[0])

    vote_count = Db.get_vote_count(poll.poll_id)

    if vote_count == 8:
        await bot.send_message(
            chat_id,
            "Вас уже 8! Уже вполне можно поиграть! Нука забронили, быстро!"
        )


@dp.message(F.text)
async def handle_text(message: Message):
    admins = await bot.get_chat_administrators(chat_id=message.chat.id)
    admins_list = [admin.user.id for admin in admins if admin.user.is_bot is False]
    if message.from_user.id in admins_list:
        await handle_players_rating(message)


async def handle_players_rating(message):
    if message.text.startswith("Уровень здешних футболёров:\n"):
        text = message.text.strip("Уровень здешних футболёров:\n")
        pattern = r"@(\w+):\s*(\d+)"

        matches = re.findall(pattern, text)

        result = {"@" + username: int(score) for username, score in matches}

        players_json = Db.get_data(Chats, {'chat_id': message.chat.id}).players
        players = json.loads(players_json)
        for k, v in players.items():
            existing_username = v['username']
            if existing_username in result.keys():
                players[k]['skill'] = result[existing_username]

        Db.upsert(Chats, {'chat_id': message.chat.id}, {
            'players': json.dumps(players),
            'is_set': True,

        })
        await message.answer("Замечательно! Я запомнил!\n\n Этот чат готов к каткам.")


async def mainloop():
    await dp.start_polling(bot)
