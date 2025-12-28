"""
Database migration utilities for Summary Bot NG.

This module provides database migration functionality to manage
schema changes over time.
"""

import aiosqlite
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


class MigrationRunner:
    """Database migration runner."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent

    async def get_current_version(self) -> int:
        """Get the current schema version from the database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT MAX(version) FROM schema_version"
                )
                row = await cursor.fetchone()
                return row[0] if row and row[0] is not None else 0
        except aiosqlite.OperationalError:
            # Table doesn't exist yet
            return 0

    async def get_available_migrations(self) -> List[Path]:
        """Get list of available migration files."""
        migrations = sorted(self.migrations_dir.glob("*.sql"))
        return [m for m in migrations if m.stem != "__init__"]

    async def apply_migration(self, migration_file: Path) -> None:
        """Apply a single migration file."""
        logger.info(f"Applying migration: {migration_file.name}")

        # Read migration SQL
        with open(migration_file, 'r') as f:
            sql = f.read()

        # Apply migration
        async with aiosqlite.connect(self.db_path) as db:
            # Split into individual statements
            statements = [s.strip() for s in sql.split(';') if s.strip()]

            for statement in statements:
                if statement:
                    await db.execute(statement)

            await db.commit()

        logger.info(f"Successfully applied migration: {migration_file.name}")

    async def run_migrations(self) -> None:
        """Run all pending migrations."""
        current_version = await self.get_current_version()
        migrations = await self.get_available_migrations()

        logger.info(f"Current schema version: {current_version}")
        logger.info(f"Found {len(migrations)} migration files")

        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        for migration_file in migrations:
            # Extract version number from filename (e.g., 001_initial_schema.sql)
            try:
                version = int(migration_file.stem.split('_')[0])
            except (ValueError, IndexError):
                logger.warning(f"Skipping invalid migration file: {migration_file.name}")
                continue

            if version > current_version:
                await self.apply_migration(migration_file)
                current_version = version

        logger.info(f"All migrations complete. Current version: {current_version}")

    async def reset_database(self) -> None:
        """Reset the database by dropping all tables and re-running migrations."""
        logger.warning("Resetting database - all data will be lost!")

        async with aiosqlite.connect(self.db_path) as db:
            # Get all tables
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = await cursor.fetchall()

            # Drop all tables
            for table in tables:
                table_name = table[0]
                if table_name != 'sqlite_sequence':
                    await db.execute(f"DROP TABLE IF EXISTS {table_name}")

            await db.commit()

        # Run all migrations
        await self.run_migrations()
        logger.info("Database reset complete")


async def run_migrations(db_path: str) -> None:
    """
    Convenience function to run all pending migrations.

    Args:
        db_path: Path to the SQLite database file
    """
    runner = MigrationRunner(db_path)
    await runner.run_migrations()


async def reset_database(db_path: str) -> None:
    """
    Convenience function to reset the database.

    Args:
        db_path: Path to the SQLite database file
    """
    runner = MigrationRunner(db_path)
    await runner.reset_database()
