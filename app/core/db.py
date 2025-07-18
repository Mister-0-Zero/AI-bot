from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import DATABASE_URL
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def init_db():
    engine = create_async_engine(DATABASE_URL, echo=False)
    logger.info("Инициализация базы данных...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Создание таблиц завершено")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
