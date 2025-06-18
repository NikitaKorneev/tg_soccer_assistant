from abc import ABC, abstractmethod

from aiogram import Bot, Router, F
from aiogram.types import Message

from src.database.db import AsyncDatabaseManager


class BaseTextHandler(ABC):
    def __init__(self, bot: Bot, db: AsyncDatabaseManager):
        self.bot = bot
        self.db = db

    @abstractmethod
    def register(self, router: Router):
        pass

