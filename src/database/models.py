from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey, JSON, String
)
from sqlalchemy.orm import relationship

from .db import Base


class Chats(Base):
    chat_id = Column(BigInteger, unique=True, nullable=False)
    player_count = Column(BigInteger, nullable=True, default=0)
    players = Column(JSON, nullable=True, default={})
    is_set = Column(Boolean, default=False)
    start_message = Column(BigInteger, nullable=False, default=0)
    # Обратные связи (один ко многим).
    # Теперь через chat_id можно будет сразу получать доступ к admins и polls.
    admins = relationship("Admins", back_populates="chat")
    polls = relationship("Polls", back_populates="chat")


class Admins(Base):
    admin_id = Column(BigInteger, nullable=False)
    admin_username = Column(String, nullable=True)
    # Внешний ключ на Chats.chat_id.
    chat_id = Column(BigInteger, ForeignKey("chats.chat_id"), nullable=False)
    chat_name = Column(String, nullable=True)
    # Связь с Chats.
    chat = relationship("Chats", back_populates="admins")


class Polls(Base):
    timestamp = Column(DateTime, nullable=False)
    # Внешний ключ на Chats.chat_id.
    chat_id = Column(BigInteger, ForeignKey("chats.chat_id"), nullable=False)
    poll_id = Column(String, unique=True, nullable=True)
    poll_message_id = Column(BigInteger, nullable=False)
    voters = Column(JSON, nullable=True, default={})
    is_closed = Column(Boolean, default=False)
    # Связь с Chats.
    chat = relationship("Chats", back_populates="polls")
