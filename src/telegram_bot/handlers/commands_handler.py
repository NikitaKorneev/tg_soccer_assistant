import datetime
import json
from pprint import pformat

from abc import ABC, abstractmethod
from aiogram import Bot, Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, InputPollOption, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command

from src.database.database import DatabaseManager, Polls, Chats, Admins
from src.telegram_bot.responses import texts

from src.telegram_bot.handlers.callbacks_handler import InitCallback, TeamManagerCallback


async def players_list_extractor(existing_players):
    if isinstance(existing_players, str):
        existing_players_dict = json.loads(existing_players)
    else:
        existing_players_dict = existing_players
    return existing_players_dict

# --- DECORATORS ---

def group_only(func):
    async def wrapper(self, message: Message, *args, **kwargs):
        if not str(message.chat.id).startswith("-"):
            await message.answer("Эта команда работает только в группах.")
            return
        return await func(self, message, *args, **kwargs)

    return wrapper


def admin_only(func):
    async def wrapper(self, message: Message, *args, **kwargs):
        admins = await self.bot.get_chat_administrators(chat_id=message.chat.id)
        admins_list = [admin.user.id for admin in admins if not admin.user.is_bot]
        if message.from_user.id not in admins_list:
            await message.answer("Эта команда доступна только администраторам.")
            return
        return await func(self, message, *args, **kwargs)

    return wrapper


def personal_only(func):
    async def wrapper(self, message: Message, *args, **kwargs):
        if str(message.chat.id).startswith("-"):
            await message.answer("Эта команда доступна только в личном чате с ботом.")
            return
        return await func(self, message, *args, **kwargs)

    return wrapper


def bot_is_admin(func):
    async def wrapper(self, message: Message, *args, **kwargs):
        admins = await self.bot.get_chat_administrators(chat_id=message.chat.id)
        admins_list = [admin.user.id for admin in admins if admin.user.is_bot]
        if message.bot.id not in admins_list:
            await message.answer(texts.make_bot_admin)
            return

        return await func(self, message, *args, **kwargs)

    return wrapper


class BaseCommandHandler(ABC):
    def __init__(self, bot: Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db

    @abstractmethod
    def register(self, router: Router):
        pass


class StartCommandHandler(BaseCommandHandler):
    def register(self, router: Router):
        router.message.register(
            self.handle_group_start, CommandStart(), (F.chat.type == "group") | (F.chat.type == "supergroup")
        )
        router.message.register(
            self.handle_private_start, CommandStart(), (F.chat.type == "private")
        )

    @group_only
    @bot_is_admin
    async def handle_group_start(self, message: Message, *args, **kwargs):
        await self.initial_start(message)

    async def initial_start(self, message: Message):
        """Sends initial message and collects important data regarding chat members"""
        group_data = self.db.get_data(Chats, {"chat_id": message.chat.id})

        if not group_data:

            admin_id, admin_username, admins_list = await self.get_admins_json(message)
            chat_name = message.chat.title

            self.db.upsert(
                Admins,
                {
                    "chat_id": message.chat.id,
                },
                {
                    "admin_id": admin_id,
                    "admin_username": admin_username,
                    "chat_id": message.chat.id,
                    "chat_name": chat_name,

                }
            )

            message_start = texts.first_start
            init_message = await message.answer(
                text=message_start,
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🤙Я ГОТОВ🤙",
                                callback_data=InitCallback(
                                    chat_id=message.chat.id,
                                ).pack()
                            )
                        ]
                    ]
                )
            )

            await self.bot.pin_chat_message(
                chat_id=message.chat.id,
                message_id=init_message.message_id,
            )

            self.db.upsert(
                Chats,
                {"chat_id": message.chat.id},
                {
                    "chat_id": message.chat.id,
                    "start_message": init_message.message_id,

                }
            )

        else:
            await message.answer("Вы уже всё запустили...")

    async def get_admins_json(self, message: Message):
        chat_admins = await message.chat.get_administrators()
        admins_list = [admin.user.id for admin in chat_admins]

        for admin in chat_admins:
            if admin.status == 'creator':
                owner_id = admin.user.id
                owner_username = admin.user.username
                display_name = f"@{owner_username}" if owner_username else "Владелец чата"
                return owner_id, display_name, admins_list

        # На случай, если по какой-то причине не найден владелец
        return None, "Не удалось определить владельца", None

    @personal_only
    async def handle_private_start(self, message: Message, *args, **kwargs):
        # await message.answer(texts.private_start)
        #
        # managed_teams = self.db.get_data(Admins, {"admin_id": message.chat.id}, all_records=True)
        # if managed_teams:
        #     teams_list_inline = [
        #         [
        #             InlineKeyboardButton(
        #                 text=team.chat_name,
        #                 callback_data=TeamManagerCallback(chat_id=team.chat_id).pack()
        #             ) for team in managed_teams
        #         ]
        #     ]
        #
        #     await message.answer(
        #         text="Выбери команду для отладки:",
        #         reply_markup=InlineKeyboardMarkup(inline_keyboard=teams_list_inline),
        #
        #     )

        await message.answer("Пока этот бот работает только в групповых чатах, дружок - пирожок...")


class SetupCommandHandler(BaseCommandHandler):
    def register(self, router: Router):
        router.message.register(self.handle, Command("setup"))

    @group_only
    @admin_only
    async def handle(self, message: Message):
        admins = await self.bot.get_chat_administrators(chat_id=message.chat.id)
        admins_list = [admin.user.id for admin in admins if not admin.user.is_bot]

        if message.from_user.id in admins_list:
            players = self.db.get_data(Chats, {"chat_id": message.chat.id}).players
            if players != {}:
                players = json.loads(players)

            if len(players.keys()) > 1:
                players_list = "\n".join([player['username'] + ": " for k, player in players.items()])
                await message.answer(
                    "Пришла пора кому то из админов оценить уровень футболистов в этой конфе.\n\n"
                    "Скопируй сообщение после этого, вставь его в чат\n\n"
                    "НО и дай оценку каждому игроку от 1 до 10.\n\n"
                    "Пример:\n\nИгрок 1: 5\nИгрок 2: 7"
                )
                await message.answer(f"Уровень здешних футболёров:\n{players_list}")
        else:
            await message.answer("Такое тут могут делать только админы, дружок-пирожок...")


class PollOpenCommandHandler(BaseCommandHandler):
    def register(self, router: Router):
        router.message.register(self.handle, Command("start_poll"))

    @group_only
    @bot_is_admin
    @admin_only
    async def handle(self, message: Message, *args, **kwargs):
        all_polls = self.db.get_data(
            Polls,
            {
                "chat_id": message.chat.id,
                "is_closed": False,

            },
            all_records=True
        )

        for poll in all_polls:
            await self.bot.delete_message(
                chat_id=message.chat.id,
                message_id=poll.poll_message_id
            )

        self.db.bulk_update(
            Polls,
            {"chat_id": message.chat.id},
            {"is_closed": True},

        )

        call_to_arms = f'''‼️Мужчины‼️ Многоуважаемым @{message.from_user.username} созывается спортивная сессия‼️


        📍Время, место и дисциплина⌚️:{message.text.strip('/start_poll')}📍
'''

        soccer_poll = await self.bot.send_poll(
            chat_id=message.chat.id,
            question=call_to_arms,
            options=[InputPollOption(text="Я готов"), InputPollOption(text="Не в этот раз")],
            is_anonymous=False,
        )

        await self.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=soccer_poll.message_id
        )

        self.db.upsert(
            Polls,
            {"poll_id": soccer_poll.poll.id},
            {
                "poll_id": soccer_poll.poll.id,
                "chat_id": message.chat.id,
                "poll_message_id": soccer_poll.message_id,
                "timestamp": datetime.datetime.now(),

            }
        )


class PollFinishCommandHandler(BaseCommandHandler):
    def register(self, router: Router):
        router.message.register(self.handle_stop, Command("stop_poll"))
        router.message.register(self.handle_who, Command('who'))

    @admin_only
    async def handle_stop(self, message: Message, *args, **kwargs):
        existing_poll = self.db.get_data(
            Polls,
            {
                "chat_id": message.chat.id,
                "is_closed": False,
             }
        )

        if existing_poll:
            closed_poll = await self.bot.stop_poll(
                chat_id=message.chat.id,
                message_id=existing_poll.poll_message_id,

            )

            self.db.upsert(
                Polls,
                {
                    "poll_id": closed_poll.id,

                },
                {"is_closed": True}
            )

            poll_data = self.db.get_data(
                Polls,
                {"poll_id": closed_poll.id}
            )
            players = await players_list_extractor(poll_data.voters)

            good_guys = []
            bad_guys = []
            worst_guys = []
            for player in players.keys():
                if players[player] == 0:
                    good_guys.append(player)
                elif players[player] == 1:
                    bad_guys.append(player)
                elif players[player] == 2:
                    worst_guys.append(player)

            good_guys = '\n'.join(good_guys) if good_guys else "в этот раз таких нет..."
            bad_guys = '\n'.join(bad_guys) if bad_guys else "в этот раз таких нет..."
            worst_guys = '\n'.join(worst_guys) if worst_guys else "в этот раз таких нет..."

            final_speech = f"""
И так, вот список сильных личностей, говноедов и нерешительных людей:\n\n
Сильные футболеры которые в деле:
{good_guys}

Слабые, но волевые люди которые забили/запили:
{bad_guys}

И нерешительные, безвольные животные которые сначала что то выбрали а потом убрали голос:
{worst_guys}"""
            await message.answer(final_speech)

    async def handle_who(self, message: Message, *args, **kwargs):
        existing_poll = self.db.get_data(
            Polls,
            {
                "chat_id": message.chat.id,
                "is_closed": False,
            }
        )

        if existing_poll:
            players = await players_list_extractor(existing_poll.voters)

            good_guys = []
            bad_guys = []
            worst_guys = []
            for player in players.keys():
                if players[player] == 0:
                    good_guys.append(player)
                elif players[player] == 1:
                    bad_guys.append(player)
                elif players[player] == 2:
                    worst_guys.append(player)

            good_guys = '\n'.join(good_guys) if good_guys else "пока что таких нет..."
            bad_guys = '\n'.join(bad_guys) if bad_guys else "пока что таких нет..."
            worst_guys = '\n'.join(worst_guys) if worst_guys else "пока что таких нет..."

            final_speech = f"""
На данный момент вот список сильных личностей, говноедов и нерешительных людей:\n\n
Сильные футболеры которые точно в деле:
{good_guys}

Слабые, но волевые люди которые забили/запили:
{bad_guys}

И нерешительные, безвольные животные которые сначала что то выбрали а потом убрали голос:
{worst_guys}"""

            await message.answer(final_speech)


class CommandsHandler:
    def __init__(self, tg_bot: Bot, db: DatabaseManager):
        self.bot = tg_bot
        self.db = db
        self.router = Router()

        self._handlers = [
            StartCommandHandler(self.bot, self.db),
            PollOpenCommandHandler(self.bot, self.db),
            PollFinishCommandHandler(self.bot, self.db),

        ]

        for handler in self._handlers:
            handler.register(self.router)
