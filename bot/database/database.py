from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
)


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


db_url = "sqlite+aiosqlite:///db.db"
engine = create_async_engine(url=db_url)
sessionmaker = get_sessionmaker(engine)
