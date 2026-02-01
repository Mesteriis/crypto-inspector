from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

# Create async engine with connection pool settings optimized for long-running app
# pool_pre_ping: Check connection validity before using (handles stale connections)
# pool_recycle: Recycle connections after N seconds (avoid stale connections)
# For PgBouncer: use NullPool to let PgBouncer handle pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # Check connection before using
    pool_recycle=300,  # Recycle connections every 5 minutes
    pool_size=5,  # Base pool size
    max_overflow=10,  # Allow up to 10 additional connections
)

async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session
