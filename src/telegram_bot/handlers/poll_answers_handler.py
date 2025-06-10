import asyncio
import json

from abc import ABC, abstractmethod

from aiogram import Bot, Router
from aiogram.types import Message, PollAnswer

from src.database.database import DatabaseManager, Polls, Chats, Admins
from src.telegram_bot.responses import texts


async def players_list_extractor(existing_players):
    if isinstance(existing_players, str):
        existing_players_dict = json.loads(existing_players)
    else:
        existing_players_dict = existing_players
    return existing_players_dict


class BasePollAnswerHandler(ABC):
    def __init__(self, bot: Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db

    @abstractmethod
    def register(self, router: Router):
        pass


class PollAnswerHandler(BasePollAnswerHandler):
    def register(self, router: Router):
        router.poll_answer.register(self.handle)

    async def handle(self, answer: PollAnswer, *args, **kwargs):
        poll_for_answer = self.db.get_data(
            Polls,
            {"poll_id": answer.poll_id}
        )

        if poll_for_answer:
            voters = await players_list_extractor(poll_for_answer.voters)
            username = (
                f"@{answer.user.username}"
                if answer.user.username
                else answer.user.first_name
            )
            vote = answer.option_ids[0] if answer.option_ids else 2

            voters[username] = vote

            self.db.upsert(
                Polls,
                {
                    "poll_id": answer.poll_id
                },
                {
                    "voters": json.dumps(voters)
                }
            )


class PollAnswersHandler:

    def __init__(self, tg_bot: Bot, db: DatabaseManager):
        self.bot = tg_bot
        self.db = db
        self.router = Router()

        self._handlers = [
            PollAnswerHandler(self.bot, self.db),

        ]

        for handler in self._handlers:
            handler.register(self.router)
