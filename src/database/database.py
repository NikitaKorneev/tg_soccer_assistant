import os
from dotenv import load_dotenv

from typing import Optional, Union, List

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON, BigInteger
from sqlalchemy.engine.row import Row
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declared_attr, declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv("../../.env")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class PreBase:
    """Abstact model."""
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)


Base = declarative_base(cls=PreBase)


class Chats(Base):
    chat_id = Column(BigInteger, unique=True, nullable=False)
    player_count = Column(BigInteger, unique=False, nullable=True, default=0)

    players = Column(JSON, unique=False, nullable=True, default={})
    is_set = Column(Boolean, unique=False, default=False)

    start_message = Column(BigInteger, unique=False, nullable=False, default=0)


class Admins(Base):
    admin_id = Column(BigInteger, unique=False, nullable=False)
    admin_username = Column(String, unique=False, nullable=True)

    chat_id = Column(BigInteger, unique=True, nullable=False)
    chat_name = Column(String, unique=False, nullable=True)


class Polls(Base):
    timestamp = Column(DateTime, nullable=False)

    chat_id = Column(BigInteger, unique=False, nullable=False)
    poll_id = Column(String, unique=True, nullable=True)
    poll_message_id = Column(BigInteger, unique=False, nullable=False)
    voters = Column(JSON, nullable=True, default={})

    is_closed = Column(Boolean, nullable=False, default=False)


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

    def bulk_update(
            self,
            model,
            filters: dict,
            update_data: dict,
            synchronize_session: bool = False
    ):
        """
        Updates all rows matching filters with the given data.

        :param model: SQLAlchemy model class
        :param filters: dict of filter conditions
        :param update_data: dict of fields to update
        :param synchronize_session: True, False or 'evaluate' (SQLAlchemy option)
        """
        try:
            query = self.session.query(model).filter_by(**filters)
            updated_rows = query.update(update_data, synchronize_session=synchronize_session)
            self.session.commit()
            return updated_rows  # returns number of updated rows
        except SQLAlchemyError as e:
            self.session.rollback()
            print(f"Bulk update error: {e}")
            return 0
