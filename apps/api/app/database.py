from collections.abc import AsyncGenerator

import asyncpg
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

# Note: pgvector.sqlalchemy's Vector type does its own text-format (de)serialization
# via bind/result processors — it does NOT need (and conflicts with) asyncpg's binary
# `register_vector` codec, so we deliberately don't register that here.
engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def _ensure_vector_extension() -> None:
    url = make_url(settings.database_url)
    conn = await asyncpg.connect(
        user=url.username, password=url.password, host=url.host, port=url.port, database=url.database
    )
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    finally:
        await conn.close()


async def init_models() -> None:
    await _ensure_vector_extension()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
