from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

ZERO_UUID = '00000000-0000-0000-0000-000000000000'


class Base(DeclarativeBase):
    pass


engine = create_async_engine(get_settings().database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def set_scope(session: AsyncSession, tenant_id: UUID | str = ZERO_UUID, user_id: UUID | str = ZERO_UUID) -> None:
    """Transaction-local tenant context. Requires non-BYPASSRLS application DB role."""
    await session.execute(text("SELECT set_config('app.tenant_id', :tenant, true)"), {'tenant': str(tenant_id)})
    await session.execute(text("SELECT set_config('app.user_id', :user, true)"), {'user': str(user_id)})


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        async with session.begin():
            await set_scope(session)
            yield session
