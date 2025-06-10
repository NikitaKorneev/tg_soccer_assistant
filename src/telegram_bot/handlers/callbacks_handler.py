import asyncio
import json

from abc import ABC, abstractmethod
from typing import Optional
from pprint import pformat

from aiogram import Bot, Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, InputPollOption
from aiogram.types import CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData

from src.database.database import DatabaseManager, Polls, Chats, Admins
from src.telegram_bot.responses import texts


# --- DECORATORS ---
def init_only(func):
    async def wrapper(self, callback: CallbackQuery, *args, **kwargs):
        is_init = self.db.get_data(Chats, {"chat_id": callback.message.chat.id})
        if not is_init:
            await self.bot.send_message(callback.message.chat.id, "Сначала запустите бота через /start")
            return
        return await func(self, callback, *args, **kwargs)

    return wrapper


class InitCallback(CallbackData, prefix="init"):
    chat_id: int


class TeamManagerCallback(CallbackData, prefix="tm"):
    chat_id: int


class BaseCallbackHandler(ABC):
    def __init__(self, bot: Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db

    @abstractmethod
    def register(self, router: Router):
        pass


async def players_list_extractor(existing_players):
    if isinstance(existing_players, str):
        existing_players_dict = json.loads(existing_players)
    else:
        existing_players_dict = existing_players
    return existing_players_dict


class InitCallbackHandler(BaseCallbackHandler):
    def register(self, router: Router):
        router.callback_query.register(self.handle, InitCallback.filter())

    # @init_only
    async def handle(self, callback_query: CallbackQuery, callback_data: InitCallback, *args, **kwargs):
        chat_id = callback_data.chat_id
        user_id = callback_query.from_user.id
        user_name = callback_query.from_user.username or None

        existing_players = self.db.get_data(Chats, {"chat_id": chat_id}).players

        existing_players_dict = await players_list_extractor(existing_players)

        existing_players_dict[user_id] = {
            "username": f"@{user_name}" if user_name else "_",
            "skill_level": 0
        }

        current_player_count = int(self.db.get_data(Chats, {"chat_id": chat_id}).player_count)
        new_count = current_player_count + 1

        self.db.upsert(
            Chats,
            {"chat_id": chat_id},
            {
                "players": json.dumps(existing_players_dict),
                "player_count": new_count,

            }
        )

        await callback_query.answer("Я вижу тебя, Футболист! Ожидай")

        acknowledge_message = await self.bot.send_message(
            chat_id=chat_id,
            text=f"@{user_name} Я вижу тебя, Футболист!",
            disable_notification=True,
        )

        await asyncio.sleep(3)
        await self.bot.delete_message(chat_id, acknowledge_message.message_id)


class TeamManagementHandler(BaseCallbackHandler):
    def register(self, router: Router):
        router.callback_query.register(self.handle, TeamManagerCallback.filter())

    async def handle(self, callback_query: CallbackQuery, callback_data: TeamManagerCallback, *args, **kwargs):
        chat_data = self.db.get_data(
            Chats,
            {"chat_id": callback_data.chat_id}
        )
        if chat_data:
            existing_players = await players_list_extractor(chat_data.players)
            team_data = {
                "Колличество игроков": chat_data.player_count,
                "Игроки": existing_players,
            }

            team_data = pformat(team_data, compact=True)
            await self.bot.send_message(callback_query.message.chat.id, team_data)
        else:
            await self.bot.send_message(callback_query.message.chat.id, "Произошла ошибка. Бригада скорой помощи уже выехала")


class CallbacksHandler:
    def __init__(self, bot: Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db
        self.router = Router()

        self.handlers = [
            InitCallbackHandler(self.bot, self.db),
            # TeamManagementHandler(self.bot, self.db),

        ]

        for handler in self.handlers:
            handler.register(self.router)
