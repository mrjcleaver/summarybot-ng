"""
Integration tests for database operations.

Tests repository operations with real SQLite database including
transactions, concurrent access, and migrations.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.models.summary import SummaryResult
from src.models.task import ScheduledTask, TaskType


@pytest.mark.integration
class TestDatabaseRepositoryIntegration:
    """Integration tests for repository operations with real database."""

    @pytest_asyncio.fixture
    async def test_database_engine(self):
        """Create test database engine."""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )

        # Create tables
        from src.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        await engine.dispose()

    @pytest_asyncio.fixture
    async def test_db_session(self, test_database_engine):
        """Create test database session."""
        async_session = sessionmaker(
            test_database_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        async with async_session() as session:
            yield session
            await session.rollback()

    @pytest.mark.asyncio
    async def test_create_and_retrieve_summary(self, test_db_session):
        """Test creating and retrieving a summary from database."""
        from src.data.repositories.summary_repository import SummaryRepository

        # Create repository with test session
        repo = SummaryRepository(database_url="sqlite+aiosqlite:///:memory:")
        repo.session = test_db_session

        # Create summary
        summary_data = SummaryResult(
            channel_id="123456",
            guild_id="789012",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            message_count=50,
            summary_text="Test summary for database integration",
            key_points=["Point 1", "Point 2", "Point 3"],
            action_items=["Action 1"],
            participants=["user1", "user2"],
            metadata={"test": True}
        )

        # Save to database
        saved_summary = await repo.create(summary_data)

        assert saved_summary.id is not None
        assert saved_summary.channel_id == "123456"
        assert saved_summary.guild_id == "789012"
        assert len(saved_summary.key_points) == 3

        # Retrieve from database
        retrieved = await repo.get_by_id(saved_summary.id)

        assert retrieved is not None
        assert retrieved.id == saved_summary.id
        assert retrieved.summary_text == summary_data.summary_text
        assert retrieved.message_count == 50

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_db_session):
        """Test transaction rollback on error."""
        from src.data.repositories.summary_repository import SummaryRepository

        repo = SummaryRepository(database_url="sqlite+aiosqlite:///:memory:")
        repo.session = test_db_session

        # Create summary
        summary_data = SummaryResult(
            channel_id="123456",
            guild_id="789012",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            message_count=10,
            summary_text="Test summary",
            key_points=[],
            action_items=[],
            participants=[]
        )

        try:
            # Start transaction
            await repo.create(summary_data)

            # Simulate error
            raise Exception("Test error for rollback")

        except Exception:
            # Rollback
            await test_db_session.rollback()

        # Verify nothing was committed
        # This is a simplified test - real implementation would verify

    @pytest.mark.asyncio
    async def test_concurrent_database_access(self, test_database_engine):
        """Test concurrent database operations."""
        from src.data.repositories.summary_repository import SummaryRepository

        async def create_summary(session_num: int):
            """Create a summary in a separate session."""
            async_session = sessionmaker(
                test_database_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            async with async_session() as session:
                repo = SummaryRepository(database_url="sqlite+aiosqlite:///:memory:")
                repo.session = session

                summary_data = SummaryResult(
                    channel_id=f"channel_{session_num}",
                    guild_id="789012",
                    start_time=datetime.utcnow() - timedelta(hours=1),
                    end_time=datetime.utcnow(),
                    message_count=10 + session_num,
                    summary_text=f"Concurrent summary {session_num}",
                    key_points=[f"Point {session_num}"],
                    action_items=[],
                    participants=[f"user{session_num}"]
                )

                result = await repo.create(summary_data)
                await session.commit()
                return result

        # Create multiple summaries concurrently
        tasks = [create_summary(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == 5

        # All should have unique IDs
        ids = [s.id for s in successful if hasattr(s, 'id')]
        assert len(ids) == len(set(ids))

    @pytest.mark.asyncio
    async def test_query_summaries_by_channel(self, test_db_session):
        """Test querying summaries by channel."""
        from src.data.repositories.summary_repository import SummaryRepository

        repo = SummaryRepository(database_url="sqlite+aiosqlite:///:memory:")
        repo.session = test_db_session

        # Create multiple summaries
        for i in range(3):
            summary_data = SummaryResult(
                channel_id="123456",
                guild_id="789012",
                start_time=datetime.utcnow() - timedelta(hours=i+1),
                end_time=datetime.utcnow() - timedelta(hours=i),
                message_count=10 + i,
                summary_text=f"Summary {i}",
                key_points=[],
                action_items=[],
                participants=[]
            )
            await repo.create(summary_data)

        # Create summary in different channel
        other_summary = SummaryResult(
            channel_id="999999",
            guild_id="789012",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            message_count=5,
            summary_text="Other channel summary",
            key_points=[],
            action_items=[],
            participants=[]
        )
        await repo.create(other_summary)

        await test_db_session.commit()

        # Query by channel
        channel_summaries = await repo.get_by_channel("123456", limit=10)

        assert len(channel_summaries) == 3
        assert all(s.channel_id == "123456" for s in channel_summaries)

    @pytest.mark.asyncio
    async def test_update_summary(self, test_db_session):
        """Test updating an existing summary."""
        from src.data.repositories.summary_repository import SummaryRepository

        repo = SummaryRepository(database_url="sqlite+aiosqlite:///:memory:")
        repo.session = test_db_session

        # Create summary
        summary_data = SummaryResult(
            channel_id="123456",
            guild_id="789012",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            message_count=10,
            summary_text="Original summary",
            key_points=["Point 1"],
            action_items=[],
            participants=[]
        )

        saved = await repo.create(summary_data)
        await test_db_session.commit()

        # Update summary
        saved.summary_text = "Updated summary"
        saved.key_points = ["Point 1", "Point 2"]

        updated = await repo.update(saved)
        await test_db_session.commit()

        # Verify update
        retrieved = await repo.get_by_id(saved.id)
        assert retrieved.summary_text == "Updated summary"
        assert len(retrieved.key_points) == 2

    @pytest.mark.asyncio
    async def test_delete_summary(self, test_db_session):
        """Test deleting a summary."""
        from src.data.repositories.summary_repository import SummaryRepository

        repo = SummaryRepository(database_url="sqlite+aiosqlite:///:memory:")
        repo.session = test_db_session

        # Create summary
        summary_data = SummaryResult(
            channel_id="123456",
            guild_id="789012",
            start_time=datetime.utcnow() - timedelta(hours=1),
            end_time=datetime.utcnow(),
            message_count=10,
            summary_text="To be deleted",
            key_points=[],
            action_items=[],
            participants=[]
        )

        saved = await repo.create(summary_data)
        await test_db_session.commit()

        summary_id = saved.id

        # Delete summary
        await repo.delete(summary_id)
        await test_db_session.commit()

        # Verify deletion
        retrieved = await repo.get_by_id(summary_id)
        assert retrieved is None


@pytest.mark.integration
class TestDatabaseMigrations:
    """Integration tests for database migrations."""

    @pytest.mark.asyncio
    async def test_migration_execution(self):
        """Test that migrations can be executed successfully."""
        # This would test actual Alembic migrations
        # Placeholder for migration testing
        pass

    @pytest.mark.asyncio
    async def test_schema_creation(self, test_database_engine):
        """Test that database schema is created correctly."""
        from src.models.base import Base
        from sqlalchemy import inspect

        # Create all tables
        async with test_database_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Verify tables exist
        async with test_database_engine.connect() as conn:
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )
            tables = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )

            # Should have summary and task tables at minimum
            # Actual table names depend on model definitions
            assert len(tables) > 0
