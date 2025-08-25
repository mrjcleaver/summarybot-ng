"""
Performance and load testing for Summary Bot NG.

Tests cover system performance under various load conditions,
memory usage, and response time benchmarks.
"""

import pytest
import asyncio
import time
import psutil
import gc
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from typing import List

from src.summarization.engine import SummarizationEngine
from src.models.message import ProcessedMessage
from src.models.summary import SummaryOptions


@pytest.mark.performance
class TestSummarizationPerformance:
    """Test summarization engine performance characteristics."""
    
    @pytest.fixture
    def large_message_batch(self):
        """Create large batch of messages for performance testing."""
        messages = []
        base_time = datetime.utcnow() - timedelta(hours=24)
        
        for i in range(10000):  # 10K messages
            message = ProcessedMessage(
                id=f"perf_msg_{i}",
                author_name=f"user_{i % 100}",  # 100 different users
                author_id=f"user_id_{i % 100}",
                content=f"Performance test message {i+1}. This message contains sufficient content "
                       f"to simulate realistic Discord messages with multiple sentences and various "
                       f"topics including technical discussions, casual conversation, and planning.",
                timestamp=base_time + timedelta(minutes=i * 0.1),  # ~16 hours of conversation
                thread_info=None,
                attachments=[],
                references=[]
            )
            messages.append(message)
        
        return messages
    
    @pytest.fixture
    def performance_monitor(self):
        """Performance monitoring utility."""
        class PerformanceMonitor:
            def __init__(self):
                self.start_time = None
                self.end_time = None
                self.start_memory = None
                self.end_memory = None
                self.process = psutil.Process()
            
            def start(self):
                gc.collect()  # Clean up before measurement
                self.start_time = time.time()
                self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            def stop(self):
                self.end_time = time.time()
                self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            @property
            def duration(self):
                if self.start_time and self.end_time:
                    return self.end_time - self.start_time
                return None
            
            @property
            def memory_delta(self):
                if self.start_memory and self.end_memory:
                    return self.end_memory - self.start_memory
                return None
        
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_large_batch_summarization_performance(
        self, 
        large_message_batch, 
        performance_monitor
    ):
        """Test performance with large message batches."""
        # Setup mock engine
        mock_claude_client = AsyncMock()
        mock_claude_client.create_summary.return_value = MagicMock(
            content="Large batch summary with comprehensive analysis.",
            usage=MagicMock(input_tokens=50000, output_tokens=2000, total_tokens=52000)
        )
        
        mock_cache = AsyncMock()
        mock_cache.get_cached_summary.return_value = None
        
        engine = SummarizationEngine(mock_claude_client, mock_cache)
        
        options = SummaryOptions(
            summary_length="standard",
            include_bots=False,
            max_tokens=4000
        )
        
        # Performance test
        performance_monitor.start()
        
        result = await engine.summarize_messages(
            messages=large_message_batch,
            options=options,
            context=MagicMock()
        )
        
        performance_monitor.stop()
        
        # Verify performance requirements
        assert performance_monitor.duration < 30.0, f"Processing took {performance_monitor.duration}s, should be < 30s"
        assert performance_monitor.memory_delta < 500, f"Memory increase of {performance_monitor.memory_delta}MB too high"
        
        # Verify result quality
        assert result is not None
        assert result.message_count == len(large_message_batch)
    
    @pytest.mark.asyncio
    async def test_concurrent_summarization_performance(self, performance_monitor):
        """Test performance under concurrent load."""
        # Create multiple smaller batches for concurrent processing
        batch_size = 1000
        num_batches = 10
        
        batches = []
        for batch_num in range(num_batches):
            batch = []
            for i in range(batch_size):
                message = ProcessedMessage(
                    id=f"concurrent_msg_{batch_num}_{i}",
                    author_name=f"user_{i % 20}",
                    author_id=f"user_id_{i % 20}",
                    content=f"Concurrent test message {i+1} in batch {batch_num+1}.",
                    timestamp=datetime.utcnow() - timedelta(minutes=i),
                    thread_info=None,
                    attachments=[],
                    references=[]
                )
                batch.append(message)
            batches.append(batch)
        
        # Setup mock engines
        engines = []
        for _ in range(num_batches):
            mock_claude_client = AsyncMock()
            mock_claude_client.create_summary.return_value = MagicMock(
                content="Concurrent batch summary.",
                usage=MagicMock(input_tokens=5000, output_tokens=200, total_tokens=5200)
            )
            
            mock_cache = AsyncMock()
            mock_cache.get_cached_summary.return_value = None
            
            engine = SummarizationEngine(mock_claude_client, mock_cache)
            engines.append(engine)
        
        options = SummaryOptions(summary_length="brief")
        
        # Execute concurrent summarizations
        performance_monitor.start()
        
        tasks = []
        for i, (engine, batch) in enumerate(zip(engines, batches)):
            task = engine.summarize_messages(
                messages=batch,
                options=options,
                context=MagicMock(channel_name=f"test-channel-{i}")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        performance_monitor.stop()
        
        # Verify concurrent performance
        assert performance_monitor.duration < 45.0, f"Concurrent processing took {performance_monitor.duration}s"
        assert len(results) == num_batches
        assert all(result.message_count == batch_size for result in results)
        
        # Memory usage should be reasonable even with concurrent processing
        assert performance_monitor.memory_delta < 1000  # Less than 1GB increase
    
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, performance_monitor):
        """Test for memory leaks during repeated operations."""
        # Setup mock engine
        mock_claude_client = AsyncMock()
        mock_claude_client.create_summary.return_value = MagicMock(
            content="Memory test summary.",
            usage=MagicMock(input_tokens=1000, output_tokens=100, total_tokens=1100)
        )
        
        mock_cache = AsyncMock()
        mock_cache.get_cached_summary.return_value = None
        
        engine = SummarizationEngine(mock_claude_client, mock_cache)
        
        # Create reusable message batch
        messages = []
        for i in range(500):
            message = ProcessedMessage(
                id=f"memory_msg_{i}",
                author_name=f"user_{i % 10}",
                author_id=f"user_id_{i % 10}",
                content=f"Memory leak test message {i+1}.",
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                thread_info=None,
                attachments=[],
                references=[]
            )
            messages.append(message)
        
        options = SummaryOptions(summary_length="brief")
        
        performance_monitor.start()
        
        # Perform multiple summarization cycles
        for cycle in range(20):  # 20 cycles
            await engine.summarize_messages(
                messages=messages,
                options=options,
                context=MagicMock(channel_name=f"memory-test-{cycle}")
            )
            
            # Force garbage collection every few cycles
            if cycle % 5 == 0:
                gc.collect()
        
        performance_monitor.stop()
        
        # Memory growth should be minimal after garbage collection
        gc.collect()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        # Memory increase should be reasonable (less than 200MB for 20 cycles)
        memory_per_cycle = performance_monitor.memory_delta / 20
        assert memory_per_cycle < 10, f"Memory per cycle: {memory_per_cycle}MB, indicates potential leak"
    
    @pytest.mark.asyncio
    async def test_response_time_percentiles(self):
        """Test response time distribution and percentiles."""
        # Setup mock engine
        mock_claude_client = AsyncMock()
        mock_cache = AsyncMock()
        mock_cache.get_cached_summary.return_value = None
        
        engine = SummarizationEngine(mock_claude_client, mock_cache)
        
        # Simulate variable response times from Claude API
        response_times = [0.5, 0.8, 1.2, 0.9, 2.1, 1.5, 0.7, 3.2, 1.1, 0.6]  # Seconds
        
        async def mock_create_summary(*args, **kwargs):
            # Simulate API call delay
            delay = response_times[mock_claude_client.create_summary.call_count % len(response_times)]
            await asyncio.sleep(delay)
            return MagicMock(
                content="Performance test summary.",
                usage=MagicMock(input_tokens=1000, output_tokens=100, total_tokens=1100)
            )
        
        mock_claude_client.create_summary.side_effect = mock_create_summary
        
        # Create test messages
        messages = []
        for i in range(100):
            message = ProcessedMessage(
                id=f"perf_msg_{i}",
                author_name="perfuser",
                author_id="perfuser_id",
                content=f"Performance test message {i+1}.",
                timestamp=datetime.utcnow() - timedelta(minutes=i),
                thread_info=None,
                attachments=[],
                references=[]
            )
            messages.append(message)
        
        options = SummaryOptions(summary_length="brief")
        
        # Measure response times for multiple requests
        response_times_measured = []
        
        for i in range(50):  # 50 requests
            start_time = time.time()
            
            await engine.summarize_messages(
                messages=messages[i:i+10],  # 10 messages per request
                options=options,
                context=MagicMock(channel_name=f"perf-test-{i}")
            )
            
            end_time = time.time()
            response_times_measured.append(end_time - start_time)
        
        # Calculate percentiles
        response_times_measured.sort()
        
        p50 = response_times_measured[len(response_times_measured) // 2]
        p95 = response_times_measured[int(len(response_times_measured) * 0.95)]
        p99 = response_times_measured[int(len(response_times_measured) * 0.99)]
        
        # Verify performance targets
        assert p50 < 5.0, f"P50 response time {p50}s exceeds 5s target"
        assert p95 < 15.0, f"P95 response time {p95}s exceeds 15s target"  
        assert p99 < 30.0, f"P99 response time {p99}s exceeds 30s target"
    
    def test_cost_estimation_performance(self):
        """Test performance of cost estimation calculations."""
        # Setup engine
        mock_claude_client = AsyncMock()
        mock_cache = AsyncMock()
        
        engine = SummarizationEngine(mock_claude_client, mock_cache)
        
        # Create large message batch
        messages = []
        for i in range(50000):  # 50K messages
            message = ProcessedMessage(
                id=f"cost_msg_{i}",
                author_name=f"user_{i % 1000}",
                author_id=f"user_id_{i % 1000}",
                content=f"Cost estimation test message {i+1} with substantial content for token calculation.",
                timestamp=datetime.utcnow() - timedelta(minutes=i * 0.01),
                thread_info=None,
                attachments=[],
                references=[]
            )
            messages.append(message)
        
        options = SummaryOptions(
            summary_length="detailed",
            claude_model="claude-3-opus-20240229"
        )
        
        # Measure cost estimation performance
        start_time = time.time()
        
        estimate = engine.estimate_cost(messages, options)
        
        end_time = time.time()
        estimation_time = end_time - start_time
        
        # Cost estimation should be fast even for large batches
        assert estimation_time < 1.0, f"Cost estimation took {estimation_time}s, should be < 1s"
        
        # Verify estimate quality
        assert estimate.estimated_tokens > 100000  # Should be substantial for 50K messages
        assert estimate.estimated_cost > 0
        assert estimate.processing_time_estimate.total_seconds() > 0


@pytest.mark.performance
class TestSystemPerformance:
    """Test overall system performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_discord_bot_startup_performance(self):
        """Test Discord bot startup time."""
        from src.discord_bot.bot import SummaryBot
        from src.config.settings import BotConfig
        from unittest.mock import patch
        
        # Create minimal config
        config = BotConfig(
            discord_token="test_token",
            claude_api_key="test_api_key", 
            guild_configs={}
        )
        
        # Mock service container
        services = MagicMock()
        services.configure_services.return_value = None
        
        start_time = time.time()
        
        with patch('discord.Client.__init__', return_value=None):
            bot = SummaryBot(config, services)
            await bot.setup_commands()
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        # Bot startup should be fast
        assert startup_time < 2.0, f"Bot startup took {startup_time}s, should be < 2s"
    
    @pytest.mark.asyncio
    async def test_webhook_server_performance(self):
        """Test webhook server response performance."""
        from src.webhook_service.server import WebhookServer
        from fastapi.testclient import TestClient
        import statistics
        
        # Create mock webhook server
        config = MagicMock()
        config.webhook_port = 5000
        
        mock_engine = AsyncMock()
        mock_engine.summarize_messages.return_value = MagicMock(
            to_dict=MagicMock(return_value={"id": "webhook_summary", "summary_text": "Test summary"})
        )
        
        with patch('src.webhook_service.server.WebhookServer.__init__', return_value=None):
            server = WebhookServer(config, mock_engine)
            server.config = config
            server.summarization_engine = mock_engine
            
            # Mock FastAPI app
            from fastapi import FastAPI
            app = FastAPI()
            server.get_app = MagicMock(return_value=app)
            
            # Add test endpoint
            @app.post("/test-summary")
            async def test_summary():
                return {"status": "success", "processing_time": 0.5}
            
            # Performance test
            response_times = []
            
            with TestClient(app) as client:
                for _ in range(100):  # 100 requests
                    start_time = time.time()
                    response = client.post("/test-summary")
                    end_time = time.time()
                    
                    assert response.status_code == 200
                    response_times.append(end_time - start_time)
            
            # Analyze performance
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            
            assert avg_response_time < 0.1, f"Average response time {avg_response_time}s too high"
            assert max_response_time < 0.5, f"Max response time {max_response_time}s too high"
    
    @pytest.mark.asyncio 
    async def test_database_query_performance(self):
        """Test database operation performance."""
        from src.data.repositories.summary_repository import SummaryRepository
        from unittest.mock import AsyncMock
        
        # Mock database connection
        mock_db = AsyncMock()
        repository = SummaryRepository(mock_db)
        
        # Create test summary data
        test_summaries = []
        for i in range(1000):
            summary = MagicMock()
            summary.id = f"db_summary_{i}"
            summary.guild_id = "123456789"
            summary.channel_id = f"channel_{i % 10}"
            test_summaries.append(summary)
        
        # Mock database responses
        mock_db.execute.return_value = AsyncMock()
        mock_db.fetchall.return_value = test_summaries
        
        # Test query performance
        start_time = time.time()
        
        # Simulate complex search query
        results = await repository.find_summaries(MagicMock(
            guild_id="123456789",
            start_date=datetime.utcnow() - timedelta(days=30),
            limit=100
        ))
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Database queries should be fast
        assert query_time < 0.5, f"Database query took {query_time}s, should be < 0.5s"