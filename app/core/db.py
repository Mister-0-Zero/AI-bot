from typing import AsyncGenerator
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager 
from app.core.config import DATABASE_URL
from app.core.logging_config import get_logger

logger = get_logger(__name__)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    logger.info("Инициализация базы данных...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Создание таблиц завершено")

@asynccontextmanager  
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session