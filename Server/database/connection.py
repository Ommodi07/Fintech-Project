"""
Database Connection Setup
Async SQLAlchemy configuration for PostgreSQL
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment variable
# Format: postgresql+asyncpg://user:password@host:port/database
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgres@localhost:5432/fintech_db"
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    poolclass=NullPool,  # Use NullPool for async
    future=True
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


async def get_db():
    """
    Dependency for getting database session.
    Use with FastAPI's Depends.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Import models to register them
        from . import models  # noqa
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created successfully")


async def drop_db():
    """Drop all database tables (use with caution)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("✓ Database tables dropped")
