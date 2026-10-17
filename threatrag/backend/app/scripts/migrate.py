"""Run SQL migrations on startup. Safe to re-run (idempotent)."""
import asyncio
from pathlib import Path

import psycopg

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


async def run_migrations() -> None:
    s = get_settings()
    async with await psycopg.AsyncConnection.connect(s.database_url) as conn:
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = sql_file.read_text()
            await conn.execute(sql.encode())
            log.info("migration_applied", file=sql_file.name)
    log.info("migrations_complete")


if __name__ == "__main__":
    asyncio.run(run_migrations())
