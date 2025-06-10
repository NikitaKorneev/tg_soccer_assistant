from abc import ABC, abstractmethod

from aiogram import Bot, Router, F
from aiogram.types import Message

from src.database.database import DatabaseManager


class BaseTextHandler(ABC):
    def __init__(self, bot: Bot, db: DatabaseManager):
        self.bot = bot
        self.db = db

    @abstractmethod
    def register(self, router: Router):
        pass

