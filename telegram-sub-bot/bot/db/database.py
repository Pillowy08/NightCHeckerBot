from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

_engine = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    pass


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    if _session_maker is None:
        raise RuntimeError("Database not initialized yet")
    return _session_maker


async def init_db(async_url: str):
    global _engine, _session_maker
    _engine = create_async_engine(async_url, echo=False)
    _session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    if _engine:
        await _engine.dispose()
