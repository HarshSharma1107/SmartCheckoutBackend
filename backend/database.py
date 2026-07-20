from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from .config import DATABASE_URL


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args={"timeout": 10},
    # Managed Postgres plans (Aiven's smaller tiers included) cap total
    # connections well below SQLAlchemy's default pool_size=5 + max_overflow=10.
    # Render's rolling deploys briefly run the old and new instance together,
    # so an unbounded pool on each one is what starves the DB of connection
    # slots (asyncpg.exceptions.TooManyConnectionsError). Keep this small and
    # deliberate - it should be sized as (max_connections - reserved) / max
    # concurrent instances, not left to the driver default.
    pool_size=3,
    max_overflow=2,
    pool_recycle=280,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
