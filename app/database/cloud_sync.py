"""Turso Cloud Synchronization Service.

Provides resilient hybrid storage:
- High-speed local SQLite (microsecond reads/writes, zero latency for bot & mini app)
- Automatic background replication to Turso Cloud (libSQL)
- Seamless disaster recovery (pulls state from Turso if Render container wipes on restart)
- Graceful offline/network tolerance (local changes persist even if cloud has a network blip)
"""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TursoSyncService:
    """Manages replication between local SQLite and remote Turso libSQL database."""

    def __init__(self) -> None:
        self._sync_task: Optional[asyncio.Task] = None
        self._is_syncing: bool = False

    @property
    def is_configured(self) -> bool:
        """Check if Turso credentials are provided."""
        from app.core.config import settings
        return bool(settings.turso_database_url and settings.turso_auth_token)

    def _get_clean_url(self) -> str:
        """Ensure the URL uses https:// protocol for the HTTP pipeline API."""
        from app.core.config import settings
        url = settings.turso_database_url.strip()
        if url.startswith("libsql://"):
            url = url.replace("libsql://", "https://", 1)
        elif not url.startswith("https://") and not url.startswith("http://"):
            url = f"https://{url}"
        return url

    def _get_client(self):
        """Create a Turso libsql client."""
        import libsql_client
        from app.core.config import settings

        url = self._get_clean_url()
        return libsql_client.create_client(url=url, auth_token=settings.turso_auth_token.strip())

    async def restore_from_cloud_if_needed(self) -> bool:
        """If local SQLite has no tables (e.g. Render cold start), restore from Turso.

        If remote Turso is empty and local SQLite has tables, seed Turso with local data.
        Returns True if a cloud restore occurred.
        """
        if not self.is_configured:
            return False

        from app.core.config import settings

        local_db_path = settings.sqlite_db_path
        local_db_path.parent.mkdir(parents=True, exist_ok=True)

        local_conn = sqlite3.connect(local_db_path)
        cur = local_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%'")
        local_tables = [r[0] for r in cur.fetchall()]

        # Check total rows in local user tables
        local_total_rows = 0
        for table in local_tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            local_total_rows += cur.fetchone()[0]

        try:
            client = self._get_client()
            async with client:
                rs = await client.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%'")
                remote_tables = [(r[0], r[1]) for r in rs.rows]

                # Check total rows on remote
                remote_total_rows = 0
                for r_name, _ in remote_tables:
                    cnt_rs = await client.execute(f"SELECT COUNT(*) FROM {r_name}")
                    if cnt_rs.rows:
                        remote_total_rows += cnt_rs.rows[0][0]

                logger.info(
                    "Cloud sync state check: local_tables=%d, local_rows=%d | remote_tables=%d, remote_rows=%d",
                    len(local_tables),
                    local_total_rows,
                    len(remote_tables),
                    remote_total_rows,
                )

                # Scenario 1: Local is empty, but remote has data -> RESTORE!
                if local_total_rows == 0 and remote_total_rows > 0:
                    logger.warning("Local database is empty, but Turso has %d rows. Restoring from Turso...", remote_total_rows)

                    # Get remote indexes
                    idx_rs = await client.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")
                    remote_indexes = [(r[0], r[1]) for r in idx_rs.rows]

                    for name, sql in remote_tables:
                        cur.execute(sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1))

                    for name, sql in remote_indexes:
                        try:
                            cur.execute(sql.replace("CREATE INDEX", "CREATE INDEX IF NOT EXISTS", 1).replace("CREATE UNIQUE INDEX", "CREATE UNIQUE INDEX IF NOT EXISTS", 1))
                        except Exception:
                            pass

                    # Pull rows
                    restored_rows = 0
                    for name, _ in remote_tables:
                        rs_data = await client.execute(f"SELECT * FROM {name}")
                        if not rs_data.rows:
                            continue
                        cols = rs_data.columns
                        placeholders = ", ".join(["?"] * len(cols))
                        insert_sql = f"INSERT OR REPLACE INTO {name} ({', '.join(cols)}) VALUES ({placeholders})"
                        for row in rs_data.rows:
                            cur.execute(insert_sql, row)
                            restored_rows += 1

                    local_conn.commit()
                    logger.info("Successfully restored %d rows across %d tables from Turso!", restored_rows, len(remote_tables))
                    return True

                # Scenario 2: Remote is empty or has fewer tables -> PUSH SEED!
                if local_tables and (len(remote_tables) == 0 or remote_total_rows == 0):
                    logger.info("Turso remote is empty. Initializing Turso schema from local database...")
                    local_conn.close()
                    await self.sync_push()
                    return False

        except Exception as e:
            logger.error("Error communicating with Turso on startup: %s", e)
        finally:
            local_conn.close()

        return False

    async def sync_push(self) -> bool:
        """Push all local tables and data to Turso cloud using INSERT OR REPLACE."""
        if not self.is_configured:
            return False

        if self._is_syncing:
            return False

        self._is_syncing = True
        try:
            from app.core.config import settings

            local_db_path = settings.sqlite_db_path
            if not local_db_path.exists():
                return False

            local_conn = sqlite3.connect(local_db_path)
            local_conn.row_factory = sqlite3.Row
            cur = local_conn.cursor()

            # 1. Fetch tables
            cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'alembic_%'")
            tables = cur.fetchall()

            # 2. Fetch indexes
            cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL AND name NOT LIKE 'sqlite_%'")
            indexes = cur.fetchall()

            client = self._get_client()
            async with client:
                # Ensure schemas exist
                for name, sql in tables:
                    sql_fixed = sql.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)
                    await client.execute(sql_fixed)

                for name, sql in indexes:
                    sql_fixed = sql.replace("CREATE INDEX", "CREATE INDEX IF NOT EXISTS", 1).replace("CREATE UNIQUE INDEX", "CREATE UNIQUE INDEX IF NOT EXISTS", 1)
                    try:
                        await client.execute(sql_fixed)
                    except Exception:
                        pass

                # Replicate table rows
                total_synced = 0
                for name, _ in tables:
                    cur.execute(f"SELECT * FROM {name}")
                    rows = cur.fetchall()
                    if not rows:
                        continue

                    col_names = [d[0] for d in cur.description]
                    placeholders = ", ".join(["?"] * len(col_names))
                    insert_sql = f"INSERT OR REPLACE INTO {name} ({', '.join(col_names)}) VALUES ({placeholders})"

                    for r in rows:
                        values = [r[c] for c in col_names]
                        await client.execute(insert_sql, values)
                        total_synced += 1

                logger.debug("Turso cloud sync complete: synced %d rows across %d tables.", total_synced, len(tables))
                return True

        except Exception as e:
            logger.warning("Turso cloud sync failed (will retry on next cycle): %s", e)
            return False
        finally:
            self._is_syncing = False
            try:
                local_conn.close()
            except Exception:
                pass

    async def _background_sync_loop(self) -> None:
        """Periodic background task that syncs to Turso cloud."""
        from app.core.config import settings
        interval = max(10, settings.turso_sync_interval_seconds)
        logger.info("Turso background sync loop started (interval=%d seconds)", interval)

        while True:
            try:
                await asyncio.sleep(interval)
                await self.sync_push()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Unexpected error in Turso sync loop: %s", e)

    def start_background_sync(self) -> None:
        """Start the periodic sync task if configured."""
        if not self.is_configured:
            logger.info("Turso credentials not configured; cloud sync disabled (running in local mode).")
            return

        if self._sync_task is None or self._sync_task.done():
            self._sync_task = asyncio.create_task(self._background_sync_loop())

    async def shutdown(self) -> None:
        """Stop background sync and perform a final flush push."""
        if self._sync_task and not self._sync_task.done():
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        if self.is_configured:
            logger.info("Performing final Turso cloud sync before shutdown...")
            await self.sync_push()


# Global singleton instance
turso_sync = TursoSyncService()
