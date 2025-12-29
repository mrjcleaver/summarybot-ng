"""
Unit tests for request validators (validators.py).

Tests Pydantic model validation, field constraints,
and error messages for all request/response models.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.webhook_service.validators import (
    SummaryType,
    OutputFormat,
    ScheduleFrequency,
    TimeRangeModel,
    SummaryRequestModel,
    SummaryResponseModel,
    ScheduleRequestModel,
    ScheduleResponseModel,
    ErrorResponseModel,
    ActionItemModel,
    TechnicalTermModel,
    ParticipantModel
)


class TestEnums:
    """Test enumeration types."""

    def test_summary_type_enum(self):
        """Test SummaryType enum values."""
        assert SummaryType.BRIEF == "brief"
        assert SummaryType.DETAILED == "detailed"
        assert SummaryType.COMPREHENSIVE == "comprehensive"
        assert SummaryType.TECHNICAL == "technical"
        assert SummaryType.EXECUTIVE == "executive"

    def test_output_format_enum(self):
        """Test OutputFormat enum values."""
        assert OutputFormat.JSON == "json"
        assert OutputFormat.MARKDOWN == "markdown"
        assert OutputFormat.HTML == "html"
        assert OutputFormat.PLAIN_TEXT == "plain_text"

    def test_schedule_frequency_enum(self):
        """Test ScheduleFrequency enum values."""
        assert ScheduleFrequency.HOURLY == "hourly"
        assert ScheduleFrequency.DAILY == "daily"
        assert ScheduleFrequency.WEEKLY == "weekly"
        assert ScheduleFrequency.MONTHLY == "monthly"


class TestTimeRangeModel:
    """Test TimeRangeModel validation."""

    def test_valid_time_range(self):
        """Test creating valid time range."""
        start = datetime.utcnow() - timedelta(hours=2)
        end = datetime.utcnow() - timedelta(hours=1)

        time_range = TimeRangeModel(start=start, end=end)

        assert time_range.start == start
        assert time_range.end == end

    def test_end_before_start_fails(self):
        """Test validation fails when end is before start."""
        start = datetime.utcnow() - timedelta(hours=1)
        end = datetime.utcnow() - timedelta(hours=2)

        with pytest.raises(ValidationError) as exc_info:
            TimeRangeModel(start=start, end=end)

        assert "end time must be after start time" in str(exc_info.value)

    def test_end_equal_to_start_fails(self):
        """Test validation fails when end equals start."""
        time_point = datetime.utcnow() - timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            TimeRangeModel(start=time_point, end=time_point)

        assert "end time must be after start time" in str(exc_info.value)

    def test_future_start_time_fails(self):
        """Test validation fails for future start time."""
        future_start = datetime.utcnow() + timedelta(hours=1)
        future_end = datetime.utcnow() + timedelta(hours=2)

        with pytest.raises(ValidationError) as exc_info:
            TimeRangeModel(start=future_start, end=future_end)

        assert "cannot be in the future" in str(exc_info.value)

    def test_future_end_time_fails(self):
        """Test validation fails for future end time."""
        past_start = datetime.utcnow() - timedelta(hours=1)
        future_end = datetime.utcnow() + timedelta(hours=1)

        with pytest.raises(ValidationError) as exc_info:
            TimeRangeModel(start=past_start, end=future_end)

        assert "cannot be in the future" in str(exc_info.value)


class TestSummaryRequestModel:
    """Test SummaryRequestModel validation."""

    def test_minimal_valid_request(self):
        """Test creating request with minimal required fields."""
        request = SummaryRequestModel(channel_id="123456789012345678")

        assert request.channel_id == "123456789012345678"
        assert request.summary_type == SummaryType.DETAILED
        assert request.output_format == OutputFormat.JSON
        assert request.max_length == 4000
        assert request.include_threads is True
        assert request.exclude_bots is True

    def test_empty_channel_id_fails(self):
        """Test validation fails for empty channel_id."""
        with pytest.raises(ValidationError) as exc_info:
            SummaryRequestModel(channel_id="")

        errors = exc_info.value.errors()
        assert any("channel_id" in str(error) for error in errors)

    def test_missing_channel_id_fails(self):
        """Test validation fails for missing channel_id."""
        with pytest.raises(ValidationError):
            SummaryRequestModel()

    def test_all_summary_types(self):
        """Test all summary type values."""
        for summary_type in SummaryType:
            request = SummaryRequestModel(
                channel_id="123456789",
                summary_type=summary_type
            )
            assert request.summary_type == summary_type

    def test_all_output_formats(self):
        """Test all output format values."""
        for output_format in OutputFormat:
            request = SummaryRequestModel(
                channel_id="123456789",
                output_format=output_format
            )
            assert request.output_format == output_format

    def test_max_length_constraints(self):
        """Test max_length field constraints."""
        # Valid values
        for length in [100, 1000, 4000, 10000]:
            request = SummaryRequestModel(
                channel_id="123456789",
                max_length=length
            )
            assert request.max_length == length

        # Too small
        with pytest.raises(ValidationError) as exc_info:
            SummaryRequestModel(channel_id="123456789", max_length=50)

        assert "greater than or equal to 100" in str(exc_info.value)

        # Too large
        with pytest.raises(ValidationError) as exc_info:
            SummaryRequestModel(channel_id="123456789", max_length=20000)

        assert "less than or equal to 10000" in str(exc_info.value)

    def test_temperature_constraints(self):
        """Test temperature field constraints."""
        # Valid values
        for temp in [0.0, 0.3, 0.5, 1.0]:
            request = SummaryRequestModel(
                channel_id="123456789",
                temperature=temp
            )
            assert request.temperature == temp

        # Too low
        with pytest.raises(ValidationError) as exc_info:
            SummaryRequestModel(channel_id="123456789", temperature=-0.1)

        assert "greater than or equal to 0" in str(exc_info.value)

        # Too high
        with pytest.raises(ValidationError) as exc_info:
            SummaryRequestModel(channel_id="123456789", temperature=1.5)

        assert "less than or equal to 1" in str(exc_info.value)

    def test_custom_prompt_max_length(self):
        """Test custom_prompt max length constraint."""
        # Valid length
        request = SummaryRequestModel(
            channel_id="123456789",
            custom_prompt="A" * 1000
        )
        assert len(request.custom_prompt) == 1000

        # Too long
        with pytest.raises(ValidationError) as exc_info:
            SummaryRequestModel(
                channel_id="123456789",
                custom_prompt="A" * 3000
            )

        assert "2000" in str(exc_info.value)

    def test_optional_fields(self):
        """Test optional fields have correct defaults."""
        request = SummaryRequestModel(channel_id="123456789")

        assert request.guild_id is None
        assert request.time_range is None
        assert request.webhook_url is None
        assert request.custom_prompt is None
        assert request.model is None

    def test_boolean_flags(self):
        """Test boolean flag fields."""
        request = SummaryRequestModel(
            channel_id="123456789",
            include_threads=False,
            exclude_bots=False,
            include_technical_terms=False,
            include_action_items=False
        )

        assert request.include_threads is False
        assert request.exclude_bots is False
        assert request.include_technical_terms is False
        assert request.include_action_items is False

    def test_webhook_url_validation(self):
        """Test webhook_url validates as URL."""
        # Valid URLs
        for url in ["https://example.com/webhook", "http://localhost:8000/hook"]:
            request = SummaryRequestModel(
                channel_id="123456789",
                webhook_url=url
            )
            assert str(request.webhook_url) == url

        # Invalid URL
        with pytest.raises(ValidationError):
            SummaryRequestModel(
                channel_id="123456789",
                webhook_url="not-a-url"
            )

    def test_full_request_with_all_fields(self):
        """Test creating request with all fields."""
        start = datetime.utcnow() - timedelta(hours=2)
        end = datetime.utcnow() - timedelta(hours=1)

        request = SummaryRequestModel(
            channel_id="123456789012345678",
            guild_id="987654321098765432",
            time_range=TimeRangeModel(start=start, end=end),
            summary_type=SummaryType.TECHNICAL,
            output_format=OutputFormat.MARKDOWN,
            max_length=5000,
            include_threads=False,
            exclude_bots=True,
            include_technical_terms=True,
            include_action_items=True,
            webhook_url="https://example.com/webhook",
            custom_prompt="Custom summarization instructions",
            model="claude-3-opus-20240229",
            temperature=0.5
        )

        assert request.channel_id == "123456789012345678"
        assert request.guild_id == "987654321098765432"
        assert request.summary_type == SummaryType.TECHNICAL
        assert request.temperature == 0.5


class TestSummaryResponseModel:
    """Test SummaryResponseModel validation."""

    def test_minimal_valid_response(self):
        """Test creating response with minimal fields."""
        now = datetime.utcnow()
        response = SummaryResponseModel(
            id="sum_123",
            channel_id="123456789",
            summary_text="This is a summary",
            message_count=10,
            start_time=now - timedelta(hours=1),
            end_time=now,
            created_at=now
        )

        assert response.id == "sum_123"
        assert response.summary_text == "This is a summary"
        assert response.message_count == 10

    def test_optional_fields_defaults(self):
        """Test optional fields have correct defaults."""
        now = datetime.utcnow()
        response = SummaryResponseModel(
            id="sum_123",
            channel_id="123456789",
            summary_text="Summary",
            message_count=10,
            start_time=now - timedelta(hours=1),
            end_time=now,
            created_at=now
        )

        assert response.guild_id is None
        assert response.key_points == []
        assert response.action_items == []
        assert response.technical_terms == []
        assert response.participants == []
        assert response.metadata == {}

    def test_with_action_items(self):
        """Test response with action items."""
        now = datetime.utcnow()
        action_item = ActionItemModel(
            description="Implement feature X",
            assignee="user_123",
            priority="high",
            deadline=now + timedelta(days=7)
        )

        response = SummaryResponseModel(
            id="sum_123",
            channel_id="123456789",
            summary_text="Summary",
            message_count=10,
            start_time=now - timedelta(hours=1),
            end_time=now,
            created_at=now,
            action_items=[action_item]
        )

        assert len(response.action_items) == 1
        assert response.action_items[0].description == "Implement feature X"

    def test_with_technical_terms(self):
        """Test response with technical terms."""
        now = datetime.utcnow()
        term = TechnicalTermModel(
            term="JWT",
            definition="JSON Web Token",
            context="Used for authentication"
        )

        response = SummaryResponseModel(
            id="sum_123",
            channel_id="123456789",
            summary_text="Summary",
            message_count=10,
            start_time=now - timedelta(hours=1),
            end_time=now,
            created_at=now,
            technical_terms=[term]
        )

        assert len(response.technical_terms) == 1
        assert response.technical_terms[0].term == "JWT"

    def test_with_participants(self):
        """Test response with participants."""
        now = datetime.utcnow()
        participant = ParticipantModel(
            user_id="user_123",
            display_name="Alice",
            message_count=15,
            key_contributions=["Proposed solution", "Fixed bug"]
        )

        response = SummaryResponseModel(
            id="sum_123",
            channel_id="123456789",
            summary_text="Summary",
            message_count=10,
            start_time=now - timedelta(hours=1),
            end_time=now,
            created_at=now,
            participants=[participant]
        )

        assert len(response.participants) == 1
        assert response.participants[0].display_name == "Alice"


class TestActionItemModel:
    """Test ActionItemModel validation."""

    def test_minimal_action_item(self):
        """Test creating action item with only description."""
        item = ActionItemModel(description="Do something")

        assert item.description == "Do something"
        assert item.assignee is None
        assert item.priority == "medium"
        assert item.deadline is None

    def test_full_action_item(self):
        """Test creating action item with all fields."""
        deadline = datetime.utcnow() + timedelta(days=7)
        item = ActionItemModel(
            description="Implement feature",
            assignee="user_123",
            priority="high",
            deadline=deadline
        )

        assert item.description == "Implement feature"
        assert item.assignee == "user_123"
        assert item.priority == "high"
        assert item.deadline == deadline


class TestTechnicalTermModel:
    """Test TechnicalTermModel validation."""

    def test_minimal_technical_term(self):
        """Test creating term with required fields."""
        term = TechnicalTermModel(
            term="API",
            definition="Application Programming Interface"
        )

        assert term.term == "API"
        assert term.definition == "Application Programming Interface"
        assert term.context is None

    def test_term_with_context(self):
        """Test creating term with context."""
        term = TechnicalTermModel(
            term="REST",
            definition="Representational State Transfer",
            context="Used for web service architecture"
        )

        assert term.context == "Used for web service architecture"


class TestParticipantModel:
    """Test ParticipantModel validation."""

    def test_minimal_participant(self):
        """Test creating participant with required fields."""
        participant = ParticipantModel(
            user_id="user_123",
            display_name="Alice",
            message_count=10
        )

        assert participant.user_id == "user_123"
        assert participant.display_name == "Alice"
        assert participant.message_count == 10
        assert participant.key_contributions == []

    def test_participant_with_contributions(self):
        """Test creating participant with contributions."""
        participant = ParticipantModel(
            user_id="user_123",
            display_name="Alice",
            message_count=10,
            key_contributions=["Fixed bug", "Wrote tests"]
        )

        assert len(participant.key_contributions) == 2


class TestScheduleRequestModel:
    """Test ScheduleRequestModel validation."""

    def test_minimal_schedule_request(self):
        """Test creating schedule request with required fields."""
        request = ScheduleRequestModel(
            channel_id="123456789",
            frequency=ScheduleFrequency.DAILY
        )

        assert request.channel_id == "123456789"
        assert request.frequency == ScheduleFrequency.DAILY
        assert request.summary_type == SummaryType.DETAILED
        assert request.enabled is True

    def test_missing_frequency_fails(self):
        """Test validation fails without frequency."""
        with pytest.raises(ValidationError):
            ScheduleRequestModel(channel_id="123456789")

    def test_all_frequencies(self):
        """Test all frequency values."""
        for frequency in ScheduleFrequency:
            request = ScheduleRequestModel(
                channel_id="123456789",
                frequency=frequency
            )
            assert request.frequency == frequency

    def test_full_schedule_request(self):
        """Test creating schedule with all fields."""
        request = ScheduleRequestModel(
            channel_id="123456789",
            guild_id="987654321",
            frequency=ScheduleFrequency.WEEKLY,
            summary_type=SummaryType.BRIEF,
            webhook_url="https://example.com/webhook",
            enabled=False
        )

        assert request.guild_id == "987654321"
        assert request.webhook_url is not None
        assert request.enabled is False


class TestScheduleResponseModel:
    """Test ScheduleResponseModel validation."""

    def test_valid_schedule_response(self):
        """Test creating schedule response."""
        now = datetime.utcnow()
        response = ScheduleResponseModel(
            schedule_id="sch_123",
            channel_id="123456789",
            frequency=ScheduleFrequency.DAILY,
            summary_type=SummaryType.DETAILED,
            next_run=now + timedelta(days=1),
            enabled=True,
            created_at=now
        )

        assert response.schedule_id == "sch_123"
        assert response.frequency == ScheduleFrequency.DAILY
        assert response.enabled is True


class TestErrorResponseModel:
    """Test ErrorResponseModel validation."""

    def test_minimal_error_response(self):
        """Test creating error response with required fields."""
        error = ErrorResponseModel(
            error="VALIDATION_ERROR",
            message="Invalid input"
        )

        assert error.error == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert error.details is None
        assert error.request_id is None

    def test_full_error_response(self):
        """Test creating error response with all fields."""
        error = ErrorResponseModel(
            error="VALIDATION_ERROR",
            message="Invalid input",
            details={"field": "channel_id", "reason": "too short"},
            request_id="req_123"
        )

        assert error.details is not None
        assert error.details["field"] == "channel_id"
        assert error.request_id == "req_123"


class TestModelSerialization:
    """Test model serialization and examples."""

    def test_summary_request_example(self):
        """Test summary request example schema."""
        example = SummaryRequestModel.Config.schema_extra["example"]

        # Should be valid according to model
        request = SummaryRequestModel(**example)
        assert request.channel_id == example["channel_id"]

    def test_summary_response_example(self):
        """Test summary response example schema."""
        example = SummaryResponseModel.Config.schema_extra["example"]

        # Parse datetime strings
        example["start_time"] = datetime.fromisoformat(example["start_time"].replace("Z", "+00:00"))
        example["end_time"] = datetime.fromisoformat(example["end_time"].replace("Z", "+00:00"))
        example["created_at"] = datetime.fromisoformat(example["created_at"].replace("Z", "+00:00"))

        # Should be valid
        response = SummaryResponseModel(**example)
        assert response.id == example["id"]

    def test_schedule_request_example(self):
        """Test schedule request example schema."""
        example = ScheduleRequestModel.Config.schema_extra["example"]

        request = ScheduleRequestModel(**example)
        assert request.channel_id == example["channel_id"]

    def test_error_response_example(self):
        """Test error response example schema."""
        example = ErrorResponseModel.Config.schema_extra["example"]

        error = ErrorResponseModel(**example)
        assert error.error == example["error"]
