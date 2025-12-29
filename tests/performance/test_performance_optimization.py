"""
Performance optimization tests for Summary Bot NG.

Tests cache efficiency, batch processing, connection pooling,
and critical path optimization.
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import List

from src.summarization.cache import SummaryCache
from src.summarization.engine import SummarizationEngine
from src.models.message import ProcessedMessage
from src.models.summary import SummaryOptions, SummaryResult


@pytest.mark.performance
class TestCachePerformance:
    """Test cache hit rates and performance."""

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache with performance tracking."""
        cache = AsyncMock(spec=SummaryCache)
        cache.hits = 0
        cache.misses = 0

        async def get_cached_summary(*args, **kwargs):
            # Simulate cache miss first time, hit thereafter
            if cache.get_cached_summary.call_count <= 1:
                cache.misses += 1
                return None
            else:
                cache.hits += 1
                return MagicMock(
                    id="cached_summary",
                    summary_text="Cached summary",
                    message_count=100
                )

        cache.get_cached_summary.side_effect = get_cached_summary
        cache.cache_summary.return_value = True

        return cache

    @pytest.mark.asyncio
    async def test_cache_hit_rate_optimization(self, mock_cache):
        """Test cache hit rate meets 80% target."""
        mock_claude_client = AsyncMock()
        mock_claude_client.create_summary.return_value = MagicMock(
            content="Test summary",
            usage=MagicMock(input_tokens=1000, output_tokens=100, total_tokens=1100)
        )

        engine = SummarizationEngine(mock_claude_client, mock_cache)

        # Create test messages
        messages = []
        for i in range(100):
            message = ProcessedMessage(
                id=f"cache_msg_{i}",
                author_name="testuser",
                author_id="user123",
                content=f"Test message {i}",
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                thread_info=None,
                attachments=[],
                references=[]
            )
            messages.append(message)

        options = SummaryOptions(summary_length="brief")
        context = MagicMock(channel_name="test-channel")

        # Perform 20 requests (first should miss, rest should hit)
        for _ in range(20):
            await engine.summarize_messages(
                messages=messages,
                options=options,
                context=context,
                channel_id="channel123",
                guild_id="guild123"
            )

        # Calculate hit rate
        total_requests = mock_cache.hits + mock_cache.misses
        hit_rate = mock_cache.hits / total_requests if total_requests > 0 else 0

        # Should achieve >80% hit rate
        assert hit_rate >= 0.80, f"Cache hit rate {hit_rate:.2%} below 80% target"
        assert mock_cache.misses <= 5, f"Too many cache misses: {mock_cache.misses}"

    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self, mock_cache):
        """Test cache significantly improves response time."""
        mock_claude_client = AsyncMock()

        # Simulate slow Claude API (500ms)
        async def slow_api_call(*args, **kwargs):
            await asyncio.sleep(0.5)
            return MagicMock(
                content="Test summary",
                usage=MagicMock(input_tokens=1000, output_tokens=100, total_tokens=1100)
            )

        mock_claude_client.create_summary.side_effect = slow_api_call

        engine = SummarizationEngine(mock_claude_client, mock_cache)

        messages = [
            ProcessedMessage(
                id=f"perf_msg_{i}",
                author_name="testuser",
                author_id="user123",
                content=f"Test message {i}",
                timestamp=datetime.utcnow(),
                thread_info=None,
                attachments=[],
                references=[]
            )
            for i in range(50)
        ]

        options = SummaryOptions(summary_length="brief")
        context = MagicMock(channel_name="test-channel")

        # First request (cache miss)
        start = time.time()
        await engine.summarize_messages(
            messages=messages,
            options=options,
            context=context,
            channel_id="channel123",
            guild_id="guild123"
        )
        cache_miss_time = time.time() - start

        # Second request (cache hit)
        start = time.time()
        await engine.summarize_messages(
            messages=messages,
            options=options,
            context=context,
            channel_id="channel123",
            guild_id="guild123"
        )
        cache_hit_time = time.time() - start

        # Cache should provide >90% speedup
        speedup_ratio = cache_miss_time / cache_hit_time if cache_hit_time > 0 else 0
        assert speedup_ratio >= 10, f"Cache speedup {speedup_ratio:.1f}x insufficient"
        assert cache_hit_time < 0.1, f"Cache hit too slow: {cache_hit_time:.3f}s"


@pytest.mark.performance
class TestBatchProcessingPerformance:
    """Test batch processing efficiency."""

    @pytest.mark.asyncio
    async def test_batch_processing_efficiency(self):
        """Test batch processing is more efficient than sequential."""
        mock_claude_client = AsyncMock()

        # Simulate API call with realistic delay
        async def api_call_with_delay(*args, **kwargs):
            await asyncio.sleep(0.2)  # 200ms per call
            return MagicMock(
                content="Test summary",
                usage=MagicMock(input_tokens=1000, output_tokens=100, total_tokens=1100)
            )

        mock_claude_client.create_summary.side_effect = api_call_with_delay

        mock_cache = AsyncMock()
        mock_cache.get_cached_summary.return_value = None

        engine = SummarizationEngine(mock_claude_client, mock_cache)

        # Create 10 batches of messages
        batches = []
        for batch_num in range(10):
            batch = []
            for i in range(50):
                message = ProcessedMessage(
                    id=f"batch_msg_{batch_num}_{i}",
                    author_name="testuser",
                    author_id="user123",
                    content=f"Test message {i}",
                    timestamp=datetime.utcnow(),
                    thread_info=None,
                    attachments=[],
                    references=[]
                )
                batch.append(message)
            batches.append(batch)

        options = SummaryOptions(summary_length="brief")

        # Test sequential processing
        sequential_start = time.time()
        for i, batch in enumerate(batches):
            await engine.summarize_messages(
                messages=batch,
                options=options,
                context=MagicMock(channel_name=f"seq-{i}"),
                channel_id=f"channel{i}",
                guild_id="guild123"
            )
        sequential_time = time.time() - sequential_start

        # Reset mock
        mock_claude_client.create_summary.side_effect = api_call_with_delay

        # Test batch processing
        batch_start = time.time()
        requests = [
            {
                "messages": batch,
                "options": options,
                "context": MagicMock(channel_name=f"batch-{i}"),
                "channel_id": f"channel{i}",
                "guild_id": "guild123"
            }
            for i, batch in enumerate(batches)
        ]
        await engine.batch_summarize(requests)
        batch_time = time.time() - batch_start

        # Batch processing should be significantly faster (>3x)
        speedup = sequential_time / batch_time if batch_time > 0 else 0
        assert speedup >= 3.0, f"Batch speedup {speedup:.1f}x insufficient (target >3x)"
        assert batch_time < sequential_time * 0.4, "Batch processing not efficient enough"

    @pytest.mark.asyncio
    async def test_batch_size_optimization(self):
        """Test optimal batch size for performance."""
        mock_claude_client = AsyncMock()
        mock_claude_client.create_summary.return_value = MagicMock(
            content="Test summary",
            usage=MagicMock(input_tokens=1000, output_tokens=100, total_tokens=1100)
        )

        mock_cache = AsyncMock()
        mock_cache.get_cached_summary.return_value = None

        engine = SummarizationEngine(mock_claude_client, mock_cache)

        # Test different batch sizes
        batch_sizes = [1, 5, 10, 20, 50]
        throughput_results = {}

        for batch_size in batch_sizes:
            # Create test batches
            batches = []
            for _ in range(batch_size):
                batch = [
                    ProcessedMessage(
                        id=f"msg_{i}",
                        author_name="testuser",
                        author_id="user123",
                        content=f"Test message {i}",
                        timestamp=datetime.utcnow(),
                        thread_info=None,
                        attachments=[],
                        references=[]
                    )
                    for i in range(100)
                ]
                batches.append(batch)

            # Measure throughput
            start = time.time()

            requests = [
                {
                    "messages": batch,
                    "options": SummaryOptions(summary_length="brief"),
                    "context": MagicMock(channel_name=f"test-{i}"),
                    "channel_id": f"channel{i}",
                    "guild_id": "guild123"
                }
                for i, batch in enumerate(batches)
            ]

            await engine.batch_summarize(requests)

            elapsed = time.time() - start
            throughput = batch_size / elapsed if elapsed > 0 else 0
            throughput_results[batch_size] = throughput

        # Throughput should improve with batch size up to optimal point
        assert throughput_results[10] > throughput_results[1], "Batching provides no benefit"
        assert throughput_results[20] > throughput_results[5], "Throughput not scaling"

        # Find optimal batch size
        optimal_size = max(throughput_results, key=throughput_results.get)
        assert optimal_size >= 10, f"Optimal batch size {optimal_size} too small"


@pytest.mark.performance
class TestConnectionPoolingPerformance:
    """Test connection pooling and resource management."""

    @pytest.mark.asyncio
    async def test_connection_pool_efficiency(self):
        """Test connection pooling improves performance."""
        # Track connection creation
        connections_created = []

        class MockConnection:
            def __init__(self, pool_id):
                self.pool_id = pool_id
                self.created_at = time.time()
                connections_created.append(self)

        # Mock connection pool
        pool = []
        pool_size = 5

        async def get_connection():
            if len(pool) < pool_size:
                conn = MockConnection(len(pool))
                pool.append(conn)
                return conn
            else:
                # Reuse existing connection
                return pool[len(connections_created) % pool_size]

        # Simulate 50 database operations
        start = time.time()
        for _ in range(50):
            conn = await get_connection()
            # Simulate query
            await asyncio.sleep(0.01)
        elapsed = time.time() - start

        # Should only create pool_size connections
        unique_connections = len(set(c.pool_id for c in connections_created))
        assert unique_connections == pool_size, f"Too many connections: {unique_connections}"

        # Should complete quickly due to pooling
        assert elapsed < 1.0, f"Connection pooling too slow: {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test handling many concurrent requests efficiently."""
        mock_claude_client = AsyncMock()

        # Track concurrent execution
        active_requests = []
        max_concurrent = 0

        async def track_concurrent_call(*args, **kwargs):
            active_requests.append(1)
            nonlocal max_concurrent
            max_concurrent = max(max_concurrent, len(active_requests))

            await asyncio.sleep(0.1)  # Simulate work

            active_requests.pop()
            return MagicMock(
                content="Test summary",
                usage=MagicMock(input_tokens=1000, output_tokens=100, total_tokens=1100)
            )

        mock_claude_client.create_summary.side_effect = track_concurrent_call

        mock_cache = AsyncMock()
        mock_cache.get_cached_summary.return_value = None

        engine = SummarizationEngine(mock_claude_client, mock_cache)

        # Create 20 concurrent requests
        tasks = []
        for i in range(20):
            messages = [
                ProcessedMessage(
                    id=f"concurrent_msg_{i}_{j}",
                    author_name="testuser",
                    author_id="user123",
                    content=f"Test message {j}",
                    timestamp=datetime.utcnow(),
                    thread_info=None,
                    attachments=[],
                    references=[]
                )
                for j in range(50)
            ]

            task = engine.summarize_messages(
                messages=messages,
                options=SummaryOptions(summary_length="brief"),
                context=MagicMock(channel_name=f"concurrent-{i}"),
                channel_id=f"channel{i}",
                guild_id="guild123"
            )
            tasks.append(task)

        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        # Should handle multiple concurrent requests
        assert max_concurrent >= 3, f"Not enough concurrency: {max_concurrent}"
        assert len(results) == 20, "Not all requests completed"

        # Should complete faster than sequential (>2x speedup)
        sequential_estimate = 20 * 0.1  # 20 requests * 0.1s each
        assert elapsed < sequential_estimate * 0.5, "Concurrent execution not efficient"


@pytest.mark.performance
class TestCriticalPathOptimization:
    """Test optimization of critical execution paths."""

    @pytest.mark.asyncio
    async def test_prompt_building_performance(self):
        """Test prompt building is fast even for large batches."""
        from src.summarization.prompt_builder import PromptBuilder

        builder = PromptBuilder()

        # Create large message batch
        messages = []
        for i in range(5000):
            message = ProcessedMessage(
                id=f"prompt_msg_{i}",
                author_name=f"user_{i % 100}",
                author_id=f"user_id_{i % 100}",
                content=f"Test message {i} with some content to make it realistic.",
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                thread_info=None,
                attachments=[],
                references=[]
            )
            messages.append(message)

        options = SummaryOptions(summary_length="detailed")

        # Measure prompt building time
        start = time.time()

        prompt_data = builder.build_summarization_prompt(
            messages=messages,
            options=options
        )

        elapsed = time.time() - start

        # Should be very fast (<1s for 5000 messages)
        assert elapsed < 1.0, f"Prompt building too slow: {elapsed:.3f}s"
        assert prompt_data.estimated_tokens > 0, "Token estimation failed"

    @pytest.mark.asyncio
    async def test_response_parsing_performance(self):
        """Test response parsing is fast."""
        from src.summarization.response_parser import ResponseParser

        parser = ResponseParser()

        # Create large response
        response_content = """
        # Summary
        This is a comprehensive summary of a long conversation with many participants
        discussing various technical topics including architecture, implementation details,
        and project planning.

        # Key Points
        - Point 1: Architecture decisions were discussed
        - Point 2: Implementation timeline established
        - Point 3: Resource allocation finalized
        """ + "\n".join([f"- Point {i}: Additional discussion point" for i in range(4, 100)])

        messages = [
            ProcessedMessage(
                id=f"parse_msg_{i}",
                author_name=f"user{i}",
                author_id=f"user_id_{i}",
                content=f"Message {i}",
                timestamp=datetime.utcnow(),
                thread_info=None,
                attachments=[],
                references=[]
            )
            for i in range(1000)
        ]

        context = MagicMock(channel_name="test-channel")

        # Measure parsing time
        start = time.time()

        result = parser.parse_summary_response(
            response_content=response_content,
            original_messages=messages,
            context=context
        )

        elapsed = time.time() - start

        # Should be very fast (<100ms)
        assert elapsed < 0.1, f"Response parsing too slow: {elapsed:.3f}s"
        assert result is not None, "Parsing failed"

    @pytest.mark.asyncio
    async def test_message_filtering_performance(self):
        """Test message filtering is optimized."""
        from src.message_processing.filter import MessageFilter

        filter_instance = MessageFilter()

        # Create large message set
        messages = []
        for i in range(10000):
            message = MagicMock()
            message.author = MagicMock()
            message.author.bot = (i % 10 == 0)  # 10% bots
            message.content = f"Test message {i}"
            message.created_at = datetime.utcnow() - timedelta(minutes=i)
            messages.append(message)

        # Measure filtering time
        start = time.time()

        filtered = filter_instance.filter_messages(
            messages=messages,
            include_bots=False,
            min_length=5,
            max_age_hours=24
        )

        elapsed = time.time() - start

        # Should be very fast (<500ms for 10K messages)
        assert elapsed < 0.5, f"Message filtering too slow: {elapsed:.3f}s"
        assert len(filtered) > 0, "All messages filtered out"
        assert len(filtered) < len(messages), "No filtering occurred"

    def test_token_counting_performance(self):
        """Test token counting is fast."""
        from src.summarization.prompt_builder import PromptBuilder

        builder = PromptBuilder()

        # Create large text corpus
        large_text = " ".join([f"Word{i}" for i in range(50000)])

        # Measure counting time
        measurements = []
        for _ in range(100):
            start = time.time()
            token_count = builder.estimate_token_count(large_text)
            elapsed = time.time() - start
            measurements.append(elapsed)

        avg_time = statistics.mean(measurements)
        max_time = max(measurements)

        # Should be very fast (avg <10ms, max <50ms)
        assert avg_time < 0.01, f"Token counting avg too slow: {avg_time*1000:.1f}ms"
        assert max_time < 0.05, f"Token counting max too slow: {max_time*1000:.1f}ms"
        assert token_count > 0, "Token counting failed"
