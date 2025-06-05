import os
import json
from dotenv import load_dotenv
from datetime import datetime

from typing import Optional, Union, List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON, BigInteger
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

from aiogram.types import Message, Poll, PollAnswer

load_dotenv(".env")

# Database setup
# DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5432/soccer_assistant_bot"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Chats(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)

    chat_id = Column(BigInteger, unique=True, nullable=False)
    player_count = Column(BigInteger, unique=False, nullable=True)

    players = Column(JSON, unique=False, nullable=True, default={})
    is_set = Column(Boolean, unique=False, default=False)


# class Teams(Base):
#     __tablename__ = "players"
#
#     id = Column(BigInteger, primary_key=True, index=True)
#
#     chat_id = Column(String, unique=True, nullable=False)


# class Results(Base):
#     __tablename__ = "matches"
#
#     id = Column(BigInteger, primary_key=True, index=True)
#
#     chat_id = Column(BigInteger, unique=True, nullable=False)
#     teams_composition = Column(JSON, unique=False, nullable=True, )
#
#     team_a_goals = Column(BigInteger, unique=False, nullable=True)
#     team_b_goals = Column(BigInteger, unique=False, nullable=True)


class Polls(Base):
    __tablename__ = "polls"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)

    chat_id = Column(BigInteger, unique=False, nullable=False)
    poll_id = Column(String, unique=True, nullable=True)
    poll_message_id = Column(BigInteger, unique=False, nullable=False)
    voters = Column(JSON, nullable=True, )

    is_closed = Column(Boolean, nullable=False, default=False)


class DatabaseManager:
    def __init__(self):
        Base.metadata.create_all(bind=engine)  # Ensure tables exist
        self.session = SessionLocal()

    def upsert(self, model, filters: dict, data: dict | str):
        """Inserts or updates data in the database"""
        try:
            instance = self.session.query(model).filter_by(**filters).first()
            if instance:
                for key, value in data.items():
                    setattr(instance, key, value)
            else:
                instance = model(**data)
                self.session.add(instance)
            self.session.commit()
            return instance
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Database upsert error: {e}")

    def get_data(self, model, filters: dict, all_records: bool = False) -> Union[Optional[Row], List[Row]]:
        try:
            query = self.session.query(model).filter_by(**filters)
            return query.all() if all_records else query.first()
        except SQLAlchemyError as e:
            print(f"Error in DB query: {e}")
            return None

    def update_poll_vote(self, poll_id: str, user_id: int, username: str, vote_value: int):
        poll = self.session.query(Polls).filter(
            Polls.poll_id == poll_id,
            Polls.is_closed == False,
        ).first()

        if poll:
            print(poll.voters, type(poll.voters))

            # Ensure that poll.voters is properly converted to a dictionary
            participants = poll.voters if poll.voters else {}
            if isinstance(participants, str):
                try:
                    participants = json.loads(participants)
                    print("Converted to Python dict")
                except json.JSONDecodeError:
                    print("Error...jsonEncode")
                    participants = {}

            # Update the vote
            participants[user_id] = {"username": username, "vote": vote_value}

            print("Poll voters after update:", participants, "Participants:", participants)

            # Ensure the dictionary is stored as JSON
            poll.voters = json.dumps(participants)
            self.session.commit()

    def close_all_polls(self, ):
        polls = self.session.query(Polls).all()
        for poll in polls:
            poll.is_closed = True
        self.session.commit()

    def close_poll(self, chat_id: int):
        poll = self.session.query(Polls).filter(
            Polls.chat_id == chat_id,
            Polls.is_closed == False,

        ).first()
        if poll:
            poll.is_closed = True
        self.session.commit()

    def get_pollid(self, chat_id: int):
        poll_id = self.session.query(Polls).filter(Polls.chat_id == chat_id, Polls.is_closed == False).first()
        if poll_id:
            return poll_id.poll_id, poll_id.poll_message_id

    def get_poll_data(self, poll_id: str):
        poll_data = self.session.query(Polls).filter(
            Polls.poll_id == poll_id,
            Polls.is_closed == False,

        ).first()

        return poll_data.chat_id, poll_data.poll_message_id

    def get_vote_count(self, poll_id: str):
        votes = self.session.query(Polls).filter(Polls.poll_id == poll_id, Polls.is_closed == False).first()
        if votes:
            votes_dict = json.loads(votes.voters)
            counter = 0
            for voter in votes_dict.keys():
                if votes_dict[voter]['vote'] == 0:
                    counter += 1
            return counter

    def get_poll_results(self, poll_id):
        results = self.session.query(Polls).filter(
            Polls.poll_id == poll_id
        ).first()

        if results:
            voters_dict = json.loads(results.voters)
            print(voters_dict)
            return voters_dict

    def check_new(self, chat_id: int):
        exists = self.session.query(Chats).filter(
            Chats.chat_id == chat_id
        ).first()

        if exists:
            is_set = exists.is_set
            return True, is_set
        else:
            return False, False
