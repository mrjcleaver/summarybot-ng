"""
Core configuration data classes for Summary Bot NG.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class SummaryLength(Enum):
    """Summary length options."""
    BRIEF = "brief"
    DETAILED = "detailed" 
    COMPREHENSIVE = "comprehensive"


class LogLevel(Enum):
    """Logging level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class SummaryOptions:
    """Configuration options for summarization behavior."""
    summary_length: SummaryLength = SummaryLength.DETAILED
    include_bots: bool = False
    include_attachments: bool = True
    excluded_users: List[str] = field(default_factory=list)
    min_messages: int = 5
    claude_model: str = "claude-3-sonnet-20240229"
    temperature: float = 0.3
    max_tokens: int = 4000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'summary_length': self.summary_length.value,
            'include_bots': self.include_bots,
            'include_attachments': self.include_attachments,
            'excluded_users': self.excluded_users,
            'min_messages': self.min_messages,
            'claude_model': self.claude_model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }


@dataclass
class PermissionSettings:
    """Permission configuration for a guild."""
    allowed_roles: List[str] = field(default_factory=list)
    allowed_users: List[str] = field(default_factory=list)
    admin_roles: List[str] = field(default_factory=list)
    require_permissions: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'allowed_roles': self.allowed_roles,
            'allowed_users': self.allowed_users,
            'admin_roles': self.admin_roles,
            'require_permissions': self.require_permissions
        }


@dataclass
class GuildConfig:
    """Configuration settings for a specific Discord guild."""
    guild_id: str
    enabled_channels: List[str] = field(default_factory=list)
    excluded_channels: List[str] = field(default_factory=list)
    default_summary_options: SummaryOptions = field(default_factory=SummaryOptions)
    permission_settings: PermissionSettings = field(default_factory=PermissionSettings)
    webhook_enabled: bool = False
    webhook_secret: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'guild_id': self.guild_id,
            'enabled_channels': self.enabled_channels,
            'excluded_channels': self.excluded_channels,
            'default_summary_options': self.default_summary_options.to_dict(),
            'permission_settings': self.permission_settings.to_dict(),
            'webhook_enabled': self.webhook_enabled,
            'webhook_secret': self.webhook_secret
        }


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    url: str
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    
    @classmethod
    def from_url(cls, url: str) -> 'DatabaseConfig':
        """Create database config from URL."""
        return cls(url=url)


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    backend: str = "memory"  # "memory" or "redis"
    redis_url: Optional[str] = None
    default_ttl: int = 3600
    max_size: int = 1000
    
    def is_redis_enabled(self) -> bool:
        """Check if Redis backend is enabled."""
        return self.backend == "redis" and self.redis_url is not None


@dataclass
class WebhookConfig:
    """Webhook server configuration."""
    host: str = "0.0.0.0"
    port: int = 5000
    enabled: bool = True
    cors_origins: List[str] = field(default_factory=list)
    rate_limit: int = 100  # requests per minute
    

@dataclass
class BotConfig:
    """Main configuration for the Summary Bot."""
    discord_token: str
    claude_api_key: str
    guild_configs: Dict[str, GuildConfig] = field(default_factory=dict)
    webhook_config: WebhookConfig = field(default_factory=WebhookConfig)
    database_config: Optional[DatabaseConfig] = None
    cache_config: CacheConfig = field(default_factory=CacheConfig)
    log_level: LogLevel = LogLevel.INFO
    max_message_batch: int = 10000
    cache_ttl: int = 3600
    
    @classmethod
    def load_from_env(cls) -> 'BotConfig':
        """Load configuration from environment variables."""
        from .environment import EnvironmentLoader
        return EnvironmentLoader.load_config()
    
    def get_guild_config(self, guild_id: str) -> GuildConfig:
        """Get configuration for a specific guild."""
        if guild_id not in self.guild_configs:
            # Create default config for new guilds
            self.guild_configs[guild_id] = GuildConfig(guild_id=guild_id)
        return self.guild_configs[guild_id]
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of validation errors."""
        from .validation import ConfigValidator
        return ConfigValidator.validate_config(self)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'discord_token': '***REDACTED***',  # Never expose token
            'claude_api_key': '***REDACTED***',  # Never expose API key
            'guild_configs': {
                guild_id: config.to_dict() 
                for guild_id, config in self.guild_configs.items()
            },
            'webhook_config': {
                'host': self.webhook_config.host,
                'port': self.webhook_config.port,
                'enabled': self.webhook_config.enabled,
                'cors_origins': self.webhook_config.cors_origins,
                'rate_limit': self.webhook_config.rate_limit
            },
            'database_config': {
                'url': '***REDACTED***' if self.database_config else None,
                'pool_size': self.database_config.pool_size if self.database_config else None
            },
            'cache_config': {
                'backend': self.cache_config.backend,
                'redis_url': '***REDACTED***' if self.cache_config.redis_url else None,
                'default_ttl': self.cache_config.default_ttl
            },
            'log_level': self.log_level.value,
            'max_message_batch': self.max_message_batch,
            'cache_ttl': self.cache_ttl
        }