# Imports:
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase


# Setups:
DB_URI = 'sqlite+aiosqlite:///./blog.db'
engine = create_async_engine(DB_URI, connect_args={'check_same_thread': False})

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
