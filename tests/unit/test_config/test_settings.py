"""
Unit tests for the configuration module settings.

Tests cover BotConfig, GuildConfig, and ConfigManager functionality
as specified in Phase 3 module specifications.
"""

import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import os
import tempfile

from src.config.settings import BotConfig, GuildConfig, ConfigManager, SummaryOptions
from src.exceptions.validation import ValidationError


@pytest.mark.unit
class TestSummaryOptions:
    """Test SummaryOptions data class."""
    
    def test_summary_options_default_values(self):
        """Test SummaryOptions with default values."""
        options = SummaryOptions(summary_length="standard")
        
        assert options.summary_length == "standard"
        assert options.include_bots is False
        assert options.include_attachments is True
        assert options.excluded_users == []
        assert options.min_messages == 5
        assert options.claude_model == "claude-3-sonnet-20240229"
        assert options.temperature == 0.3
        assert options.max_tokens == 4000
    
    def test_summary_options_custom_values(self):
        """Test SummaryOptions with custom values."""
        options = SummaryOptions(
            summary_length="detailed",
            include_bots=True,
            include_attachments=False,
            excluded_users=["user1", "user2"],
            min_messages=10,
            claude_model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=8000
        )
        
        assert options.summary_length == "detailed"
        assert options.include_bots is True
        assert options.include_attachments is False
        assert options.excluded_users == ["user1", "user2"]
        assert options.min_messages == 10
        assert options.claude_model == "claude-3-opus-20240229"
        assert options.temperature == 0.5
        assert options.max_tokens == 8000


@pytest.mark.unit
class TestGuildConfig:
    """Test GuildConfig data class."""
    
    def test_guild_config_creation(self):
        """Test GuildConfig creation with required fields."""
        summary_options = SummaryOptions(summary_length="standard")
        
        config = GuildConfig(
            guild_id="123456789",
            enabled_channels=["channel1", "channel2"],
            excluded_channels=["excluded1"],
            default_summary_options=summary_options,
            permission_settings={"admin_role": "Admin"}
        )
        
        assert config.guild_id == "123456789"
        assert config.enabled_channels == ["channel1", "channel2"]
        assert config.excluded_channels == ["excluded1"]
        assert config.default_summary_options == summary_options
        assert config.permission_settings == {"admin_role": "Admin"}
    
    def test_guild_config_empty_lists(self):
        """Test GuildConfig with empty channel lists."""
        summary_options = SummaryOptions(summary_length="brief")
        
        config = GuildConfig(
            guild_id="987654321",
            enabled_channels=[],
            excluded_channels=[],
            default_summary_options=summary_options,
            permission_settings={}
        )
        
        assert config.enabled_channels == []
        assert config.excluded_channels == []
        assert config.permission_settings == {}


@pytest.mark.unit
class TestBotConfig:
    """Test BotConfig data class and methods."""
    
    def test_bot_config_creation(self):
        """Test BotConfig creation with default values."""
        guild_config = GuildConfig(
            guild_id="123456789",
            enabled_channels=["channel1"],
            excluded_channels=[],
            default_summary_options=SummaryOptions(summary_length="standard"),
            permission_settings={}
        )
        
        config = BotConfig(
            discord_token="test_token",
            claude_api_key="test_api_key",
            guild_configs={"123456789": guild_config}
        )
        
        assert config.discord_token == "test_token"
        assert config.claude_api_key == "test_api_key"
        assert config.webhook_port == 5000
        assert config.max_message_batch == 10000
        assert config.cache_ttl == 3600
        assert "123456789" in config.guild_configs
    
    def test_bot_config_custom_values(self):
        """Test BotConfig with custom values."""
        config = BotConfig(
            discord_token="custom_token",
            claude_api_key="custom_api_key",
            guild_configs={},
            webhook_port=8080,
            max_message_batch=5000,
            cache_ttl=7200
        )
        
        assert config.webhook_port == 8080
        assert config.max_message_batch == 5000
        assert config.cache_ttl == 7200
    
    @patch.dict(os.environ, {
        'DISCORD_TOKEN': 'env_discord_token',
        'CLAUDE_API_KEY': 'env_claude_key',
        'WEBHOOK_PORT': '9000',
        'MAX_MESSAGE_BATCH': '20000',
        'CACHE_TTL': '1800'
    })
    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        config = BotConfig.load_from_env()
        
        assert config.discord_token == "env_discord_token"
        assert config.claude_api_key == "env_claude_key"
        assert config.webhook_port == 9000
        assert config.max_message_batch == 20000
        assert config.cache_ttl == 1800
    
    @patch.dict(os.environ, {}, clear=True)
    def test_load_from_env_missing_required(self):
        """Test loading configuration with missing required environment variables."""
        with pytest.raises(KeyError):
            BotConfig.load_from_env()
    
    def test_get_guild_config_existing(self):
        """Test getting existing guild configuration."""
        guild_config = GuildConfig(
            guild_id="123456789",
            enabled_channels=["channel1"],
            excluded_channels=[],
            default_summary_options=SummaryOptions(summary_length="standard"),
            permission_settings={}
        )
        
        config = BotConfig(
            discord_token="test_token",
            claude_api_key="test_api_key",
            guild_configs={"123456789": guild_config}
        )
        
        result = config.get_guild_config("123456789")
        assert result == guild_config
    
    def test_get_guild_config_nonexistent(self):
        """Test getting non-existent guild configuration."""
        config = BotConfig(
            discord_token="test_token",
            claude_api_key="test_api_key",
            guild_configs={}
        )
        
        result = config.get_guild_config("nonexistent")
        assert result is None
    
    def test_validate_configuration_valid(self):
        """Test validation of valid configuration."""
        guild_config = GuildConfig(
            guild_id="123456789",
            enabled_channels=["channel1"],
            excluded_channels=[],
            default_summary_options=SummaryOptions(summary_length="standard"),
            permission_settings={}
        )
        
        config = BotConfig(
            discord_token="valid_token_with_sufficient_length",
            claude_api_key="valid_api_key_with_sufficient_length",
            guild_configs={"123456789": guild_config}
        )
        
        errors = config.validate_configuration()
        assert len(errors) == 0
    
    def test_validate_configuration_invalid_token(self):
        """Test validation with invalid Discord token."""
        config = BotConfig(
            discord_token="",  # Empty token
            claude_api_key="valid_api_key",
            guild_configs={}
        )
        
        errors = config.validate_configuration()
        assert len(errors) > 0
        assert any("discord_token" in error.field for error in errors)
    
    def test_validate_configuration_invalid_api_key(self):
        """Test validation with invalid Claude API key."""
        config = BotConfig(
            discord_token="valid_token",
            claude_api_key="",  # Empty API key
            guild_configs={}
        )
        
        errors = config.validate_configuration()
        assert len(errors) > 0
        assert any("claude_api_key" in error.field for error in errors)
    
    def test_validate_configuration_invalid_ports(self):
        """Test validation with invalid port values."""
        config = BotConfig(
            discord_token="valid_token",
            claude_api_key="valid_api_key",
            guild_configs={},
            webhook_port=-1  # Invalid port
        )
        
        errors = config.validate_configuration()
        assert len(errors) > 0
        assert any("webhook_port" in error.field for error in errors)


@pytest.mark.unit
class TestConfigManager:
    """Test ConfigManager functionality."""
    
    def test_config_manager_initialization(self, temp_dir):
        """Test ConfigManager initialization."""
        config_path = os.path.join(temp_dir, "config.json")
        manager = ConfigManager(config_path)
        
        assert manager.config_path == config_path
    
    def test_config_manager_default_path(self):
        """Test ConfigManager with default path."""
        manager = ConfigManager()
        
        assert manager.config_path is not None
        assert "config" in manager.config_path.lower()
    
    @pytest.mark.asyncio
    async def test_load_config_file_exists(self, temp_dir):
        """Test loading configuration from existing file."""
        config_path = os.path.join(temp_dir, "config.json")
        config_data = {
            "discord_token": "file_token",
            "claude_api_key": "file_api_key",
            "webhook_port": 6000,
            "guild_configs": {}
        }
        
        with open(config_path, "w") as f:
            import json
            json.dump(config_data, f)
        
        manager = ConfigManager(config_path)
        config = await manager.load_config()
        
        assert config.discord_token == "file_token"
        assert config.claude_api_key == "file_api_key"
        assert config.webhook_port == 6000
    
    @pytest.mark.asyncio
    async def test_load_config_file_not_exists(self, temp_dir):
        """Test loading configuration when file doesn't exist."""
        config_path = os.path.join(temp_dir, "nonexistent.json")
        manager = ConfigManager(config_path)
        
        with patch.dict(os.environ, {
            'DISCORD_TOKEN': 'env_token',
            'CLAUDE_API_KEY': 'env_key'
        }):
            config = await manager.load_config()
            assert config.discord_token == "env_token"
            assert config.claude_api_key == "env_key"
    
    @pytest.mark.asyncio
    async def test_save_config(self, temp_dir):
        """Test saving configuration to file."""
        config_path = os.path.join(temp_dir, "config.json")
        manager = ConfigManager(config_path)
        
        guild_config = GuildConfig(
            guild_id="123456789",
            enabled_channels=["channel1"],
            excluded_channels=[],
            default_summary_options=SummaryOptions(summary_length="standard"),
            permission_settings={}
        )
        
        config = BotConfig(
            discord_token="save_test_token",
            claude_api_key="save_test_api_key",
            guild_configs={"123456789": guild_config}
        )
        
        await manager.save_config(config)
        
        # Verify file was created and contains correct data
        assert os.path.exists(config_path)
        
        with open(config_path, "r") as f:
            import json
            saved_data = json.load(f)
            assert saved_data["discord_token"] == "save_test_token"
            assert saved_data["claude_api_key"] == "save_test_api_key"
    
    @pytest.mark.asyncio
    async def test_reload_config(self, temp_dir):
        """Test reloading configuration."""
        config_path = os.path.join(temp_dir, "config.json")
        manager = ConfigManager(config_path)
        
        # Create initial config
        initial_data = {
            "discord_token": "initial_token",
            "claude_api_key": "initial_key",
            "guild_configs": {}
        }
        
        with open(config_path, "w") as f:
            import json
            json.dump(initial_data, f)
        
        config1 = await manager.load_config()
        assert config1.discord_token == "initial_token"
        
        # Modify file
        updated_data = {
            "discord_token": "updated_token",
            "claude_api_key": "updated_key",
            "guild_configs": {}
        }
        
        with open(config_path, "w") as f:
            json.dump(updated_data, f)
        
        config2 = await manager.reload_config()
        assert config2.discord_token == "updated_token"
    
    def test_validate_config_valid(self):
        """Test configuration validation with valid config."""
        manager = ConfigManager()
        
        guild_config = GuildConfig(
            guild_id="123456789",
            enabled_channels=["channel1"],
            excluded_channels=[],
            default_summary_options=SummaryOptions(summary_length="standard"),
            permission_settings={}
        )
        
        config = BotConfig(
            discord_token="valid_token_with_sufficient_length",
            claude_api_key="valid_api_key_with_sufficient_length",
            guild_configs={"123456789": guild_config}
        )
        
        result = manager.validate_config(config)
        assert result is True
    
    def test_validate_config_invalid(self):
        """Test configuration validation with invalid config."""
        manager = ConfigManager()
        
        config = BotConfig(
            discord_token="",  # Invalid empty token
            claude_api_key="valid_api_key",
            guild_configs={}
        )
        
        result = manager.validate_config(config)
        assert result is False