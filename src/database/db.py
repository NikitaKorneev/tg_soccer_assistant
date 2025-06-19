from typing import List, Optional, Type, Union

from sqlalchemy import Column, Integer, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, create_async_engine
)
from sqlalchemy.orm import declared_attr, sessionmaker, declarative_base

from src.telegram_bot.config import DATABASE_URL


class PreBase:
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)


Base = declarative_base(cls=PreBase)

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def init_db(engine: AsyncEngine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class AsyncDatabaseManager:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def upsert(
        self, model: Type, filters: dict, data: dict
    ) -> Optional[object]:
        """Insert or update a row based on filters."""
        async with self.session_factory() as session:
            try:
                stmt = select(model).filter_by(**filters)
                result = await session.execute(stmt)
                instance = result.scalars().first()

                if instance:
                    for key, value in data.items():
                        setattr(instance, key, value)
                else:
                    instance = model(**data)
                    session.add(instance)

                await session.commit()
                return instance

            except SQLAlchemyError as e:
                await session.rollback()
                print(f"[upsert] Database error: {e}")
                return None

    async def get_data(
        self,
        model: Type,
        filters: dict,
        all_records: bool = False
    ) -> Union[Optional[object], List[object]]:
        """Fetch data by filters."""
        async with self.session_factory() as session:
            try:
                stmt = select(model).filter_by(**filters)
                result = await session.execute(stmt)
                data = result.scalars()
                return data.all() if all_records else data.first()
            except SQLAlchemyError as e:
                print(f"[get_data] Query error: {e}")
                return None

    async def bulk_update(
        self,
        model: Type,
        filters: dict,
        update_data: dict,
        synchronize_session: Union[bool, str] = False
    ) -> int:
        """Update multiple rows based on filters."""
        async with self.session_factory() as session:
            try:
                stmt = (
                    update(model)
                    .filter_by(**filters)
                    .values(**update_data)
                    # .execution_options(
                    #     synchronize_session=synchronize_session
                    # )
                    # Вроде не нужно в асинке, but I am not sure.
                )
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount
            except SQLAlchemyError as e:
                await session.rollback()
                print(f"[bulk_update] Error: {e}")
                return 0
