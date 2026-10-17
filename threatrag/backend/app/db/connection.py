from collections.abc import AsyncIterator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
_pool: AsyncConnectionPool | None = None


async def open_pool() -> bool:
    """Open the pool at startup. Returns False (degraded mode) if Postgres is unreachable."""
    global _pool
    s = get_settings()
    pool = AsyncConnectionPool(conninfo=s.database_url, min_size=2, max_size=10, open=False)
    try:
        await pool.open(wait=True, timeout=5)
    except Exception as exc:
        log.warning("db_unavailable", error=str(exc))
        await pool.close()
        return False
    _pool = pool
    log.info("db_pool_opened")
    return True


def is_db_ready() -> bool:
    return _pool is not None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Database pool not initialised")
    return _pool


async def get_db_conn() -> AsyncIterator[AsyncConnection]:
    async with get_pool().connection() as conn:
        yield conn


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
