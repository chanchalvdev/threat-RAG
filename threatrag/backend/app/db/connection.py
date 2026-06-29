from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        s = get_settings()
        _pool = AsyncConnectionPool(
            conninfo=s.database_url,
            min_size=2,
            max_size=10,
            open=False,
        )
        await _pool.open()
        log.info("db_pool_opened")
    return _pool


async def get_db_conn():
    pool = await get_pool()
    async with pool.connection() as conn:
        yield conn


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
