"""
Unit tests for summary models.

Tests cover SummaryResult, SummaryOptions, and related model functionality
as specified in Phase 3 module specifications.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json
import discord

from src.models.summary import SummaryResult, SummaryOptions, ActionItem, TechnicalTerm, Participant
from src.models.base import BaseModel


@pytest.mark.unit
class TestActionItem:
    """Test ActionItem model."""
    
    def test_action_item_creation(self):
        """Test ActionItem creation with required fields."""
        action = ActionItem(
            description="Complete the documentation",
            assignee="john_doe",
            due_date=datetime(2024, 12, 31, 23, 59),
            priority="high"
        )
        
        assert action.description == "Complete the documentation"
        assert action.assignee == "john_doe"
        assert action.due_date == datetime(2024, 12, 31, 23, 59)
        assert action.priority == "high"
    
    def test_action_item_optional_fields(self):
        """Test ActionItem with optional fields."""
        action = ActionItem(
            description="Review code",
            assignee=None,
            due_date=None,
            priority="medium"
        )
        
        assert action.assignee is None
        assert action.due_date is None


@pytest.mark.unit
class TestTechnicalTerm:
    """Test TechnicalTerm model."""
    
    def test_technical_term_creation(self):
        """Test TechnicalTerm creation."""
        term = TechnicalTerm(
            term="API",
            definition="Application Programming Interface",
            context="Used for service communication"
        )
        
        assert term.term == "API"
        assert term.definition == "Application Programming Interface"
        assert term.context == "Used for service communication"
    
    def test_technical_term_no_context(self):
        """Test TechnicalTerm without context."""
        term = TechnicalTerm(
            term="REST",
            definition="Representational State Transfer",
            context=None
        )
        
        assert term.context is None


@pytest.mark.unit
class TestParticipant:
    """Test Participant model."""
    
    def test_participant_creation(self):
        """Test Participant creation."""
        participant = Participant(
            user_id="123456789",
            username="testuser",
            display_name="Test User",
            message_count=15,
            first_message_time=datetime(2024, 1, 1, 10, 0),
            last_message_time=datetime(2024, 1, 1, 12, 0)
        )
        
        assert participant.user_id == "123456789"
        assert participant.username == "testuser"
        assert participant.display_name == "Test User"
        assert participant.message_count == 15
        assert participant.first_message_time == datetime(2024, 1, 1, 10, 0)
        assert participant.last_message_time == datetime(2024, 1, 1, 12, 0)
    
    def test_participant_activity_duration(self):
        """Test participant activity duration calculation."""
        participant = Participant(
            user_id="123456789",
            username="testuser",
            display_name="Test User",
            message_count=5,
            first_message_time=datetime(2024, 1, 1, 10, 0),
            last_message_time=datetime(2024, 1, 1, 11, 30)
        )
        
        duration = participant.activity_duration()
        assert duration == timedelta(hours=1, minutes=30)
    
    def test_participant_messages_per_hour(self):
        """Test participant messages per hour calculation."""
        participant = Participant(
            user_id="123456789",
            username="testuser",
            display_name="Test User",
            message_count=10,
            first_message_time=datetime(2024, 1, 1, 10, 0),
            last_message_time=datetime(2024, 1, 1, 12, 0)
        )
        
        messages_per_hour = participant.messages_per_hour()
        assert messages_per_hour == 5.0  # 10 messages over 2 hours


@pytest.mark.unit
class TestSummaryResult:
    """Test SummaryResult model and methods."""
    
    def test_summary_result_creation(self):
        """Test SummaryResult creation with required fields."""
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 0)
        created_at = datetime(2024, 1, 1, 12, 1)
        
        participants = [
            Participant(
                user_id="123456789",
                username="testuser",
                display_name="Test User",
                message_count=10,
                first_message_time=start_time,
                last_message_time=end_time
            )
        ]
        
        action_items = [
            ActionItem(
                description="Complete task",
                assignee="testuser",
                due_date=datetime(2024, 1, 2),
                priority="high"
            )
        ]
        
        technical_terms = [
            TechnicalTerm(
                term="API",
                definition="Application Programming Interface",
                context="Service communication"
            )
        ]
        
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=start_time,
            end_time=end_time,
            message_count=10,
            key_points=["Point 1", "Point 2", "Point 3"],
            action_items=action_items,
            technical_terms=technical_terms,
            participants=participants,
            summary_text="This is a comprehensive summary of the conversation.",
            metadata={"model": "claude-3-sonnet", "tokens": 1200},
            created_at=created_at
        )
        
        assert summary.id == "summary_123"
        assert summary.channel_id == "987654321"
        assert summary.guild_id == "123456789"
        assert summary.message_count == 10
        assert len(summary.key_points) == 3
        assert len(summary.action_items) == 1
        assert len(summary.technical_terms) == 1
        assert len(summary.participants) == 1
        assert "comprehensive summary" in summary.summary_text
    
    def test_summary_result_to_dict(self):
        """Test SummaryResult to_dict method."""
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 0)
        
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=start_time,
            end_time=end_time,
            message_count=5,
            key_points=["Point 1"],
            action_items=[],
            technical_terms=[],
            participants=[],
            summary_text="Test summary",
            metadata={"test": "value"},
            created_at=datetime(2024, 1, 1, 12, 1)
        )
        
        result_dict = summary.to_dict()
        
        assert result_dict["id"] == "summary_123"
        assert result_dict["channel_id"] == "987654321"
        assert result_dict["message_count"] == 5
        assert result_dict["key_points"] == ["Point 1"]
        assert result_dict["metadata"]["test"] == "value"
        
        # Check datetime serialization
        assert isinstance(result_dict["start_time"], str)
        assert isinstance(result_dict["end_time"], str)
    
    @patch('discord.Embed')
    def test_summary_result_to_embed(self, mock_embed):
        """Test SummaryResult to_embed method."""
        mock_embed_instance = MagicMock()
        mock_embed.return_value = mock_embed_instance
        
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 0)
        
        participants = [
            Participant(
                user_id="123456789",
                username="testuser",
                display_name="Test User",
                message_count=5,
                first_message_time=start_time,
                last_message_time=end_time
            )
        ]
        
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=start_time,
            end_time=end_time,
            message_count=5,
            key_points=["Key point 1", "Key point 2"],
            action_items=[],
            technical_terms=[],
            participants=participants,
            summary_text="Test summary text",
            metadata={},
            created_at=datetime(2024, 1, 1, 12, 1)
        )
        
        result = summary.to_embed()
        
        # Verify embed was created
        mock_embed.assert_called_once()
        
        # Verify embed methods were called
        assert mock_embed_instance.add_field.call_count >= 3  # At minimum: key points, participants, duration
        
        # Verify return value
        assert result == mock_embed_instance
    
    def test_summary_result_to_markdown(self):
        """Test SummaryResult to_markdown method."""
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 0)
        
        participants = [
            Participant(
                user_id="123456789",
                username="testuser",
                display_name="Test User",
                message_count=5,
                first_message_time=start_time,
                last_message_time=end_time
            )
        ]
        
        action_items = [
            ActionItem(
                description="Complete documentation",
                assignee="testuser",
                due_date=datetime(2024, 1, 2),
                priority="high"
            )
        ]
        
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=start_time,
            end_time=end_time,
            message_count=5,
            key_points=["Key point 1", "Key point 2"],
            action_items=action_items,
            technical_terms=[],
            participants=participants,
            summary_text="Test summary text",
            metadata={},
            created_at=datetime(2024, 1, 1, 12, 1)
        )
        
        markdown = summary.to_markdown()
        
        # Verify markdown structure
        assert "# Conversation Summary" in markdown
        assert "## Summary" in markdown
        assert "## Key Points" in markdown
        assert "## Action Items" in markdown
        assert "## Participants" in markdown
        assert "Test summary text" in markdown
        assert "Key point 1" in markdown
        assert "Complete documentation" in markdown
        assert "testuser" in markdown
    
    def test_summary_result_to_json(self):
        """Test SummaryResult to_json method."""
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 0)
        
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=start_time,
            end_time=end_time,
            message_count=5,
            key_points=["Point 1"],
            action_items=[],
            technical_terms=[],
            participants=[],
            summary_text="Test summary",
            metadata={},
            created_at=datetime(2024, 1, 1, 12, 1)
        )
        
        json_str = summary.to_json()
        
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        
        assert parsed["id"] == "summary_123"
        assert parsed["channel_id"] == "987654321"
        assert parsed["message_count"] == 5
        assert parsed["summary_text"] == "Test summary"
    
    def test_summary_result_duration_calculation(self):
        """Test summary duration calculation."""
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 30)
        
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=start_time,
            end_time=end_time,
            message_count=10,
            key_points=[],
            action_items=[],
            technical_terms=[],
            participants=[],
            summary_text="Test",
            metadata={},
            created_at=datetime.now()
        )
        
        duration = summary.duration()
        assert duration == timedelta(hours=2, minutes=30)
    
    def test_summary_result_messages_per_hour(self):
        """Test messages per hour calculation."""
        start_time = datetime(2024, 1, 1, 10, 0)
        end_time = datetime(2024, 1, 1, 12, 0)
        
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=start_time,
            end_time=end_time,
            message_count=20,
            key_points=[],
            action_items=[],
            technical_terms=[],
            participants=[],
            summary_text="Test",
            metadata={},
            created_at=datetime.now()
        )
        
        messages_per_hour = summary.messages_per_hour()
        assert messages_per_hour == 10.0  # 20 messages over 2 hours
    
    def test_summary_result_is_recent(self):
        """Test is_recent method for recent summary."""
        recent_time = datetime.now() - timedelta(minutes=30)
        
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=recent_time,
            end_time=recent_time,
            message_count=5,
            key_points=[],
            action_items=[],
            technical_terms=[],
            participants=[],
            summary_text="Test",
            metadata={},
            created_at=recent_time
        )
        
        assert summary.is_recent(hours=1) is True
        assert summary.is_recent(minutes=15) is False
    
    def test_summary_result_word_count(self):
        """Test word count calculation."""
        summary = SummaryResult(
            id="summary_123",
            channel_id="987654321",
            guild_id="123456789",
            start_time=datetime.now(),
            end_time=datetime.now(),
            message_count=5,
            key_points=[],
            action_items=[],
            technical_terms=[],
            participants=[],
            summary_text="This is a test summary with exactly ten words total.",
            metadata={},
            created_at=datetime.now()
        )
        
        word_count = summary.word_count()
        assert word_count == 10