"""
Feed configuration models for RSS/Atom distribution.
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from .base import BaseModel, generate_id, utc_now


class FeedType(Enum):
    """Type of feed format."""
    RSS = "rss"
    ATOM = "atom"


@dataclass
class FeedConfig(BaseModel):
    """Configuration for an RSS/Atom feed.

    Attributes:
        id: Unique feed identifier
        guild_id: Discord guild this feed belongs to
        channel_id: Specific channel (None = all channels in guild)
        feed_type: RSS or ATOM format
        is_public: Whether feed requires authentication
        token: Secret token for private feeds
        title: Custom feed title (auto-generated if None)
        description: Custom feed description
        max_items: Maximum number of items in feed (1-100)
        include_full_content: Include full summary or just excerpt
        created_at: When the feed was created
        created_by: Discord user ID who created the feed
        last_accessed: Last time the feed was accessed
        access_count: Number of times feed has been accessed
    """
    id: str = field(default_factory=generate_id)
    guild_id: str = ""
    channel_id: Optional[str] = None
    feed_type: FeedType = FeedType.RSS
    is_public: bool = False
    token: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    max_items: int = 50
    include_full_content: bool = True
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    last_accessed: Optional[datetime] = None
    access_count: int = 0

    def __post_init__(self):
        """Generate token for private feeds if not provided."""
        if not self.is_public and not self.token:
            self.token = self.generate_token()

        # Convert string to enum if needed
        if isinstance(self.feed_type, str):
            self.feed_type = FeedType(self.feed_type)

    @staticmethod
    def generate_token() -> str:
        """Generate a secure, URL-safe feed token."""
        return secrets.token_urlsafe(32)

    def regenerate_token(self) -> str:
        """Regenerate the feed token."""
        self.token = self.generate_token()
        return self.token

    def get_feed_url(self, base_url: str) -> str:
        """Get the full URL for this feed.

        Args:
            base_url: Base URL of the API (e.g., https://summarybot-ng.fly.dev)

        Returns:
            Full feed URL with extension
        """
        ext = "rss" if self.feed_type == FeedType.RSS else "atom"
        url = f"{base_url.rstrip('/')}/feeds/{self.id}.{ext}"

        if not self.is_public and self.token:
            url += f"?token={self.token}"

        return url

    def get_content_type(self) -> str:
        """Get the Content-Type header for this feed."""
        if self.feed_type == FeedType.RSS:
            return "application/rss+xml; charset=utf-8"
        return "application/atom+xml; charset=utf-8"

    def record_access(self) -> None:
        """Record that the feed was accessed."""
        self.last_accessed = utc_now()
        self.access_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "id": self.id,
            "guild_id": self.guild_id,
            "channel_id": self.channel_id,
            "feed_type": self.feed_type.value if isinstance(self.feed_type, FeedType) else self.feed_type,
            "is_public": self.is_public,
            "token": self.token,
            "title": self.title,
            "description": self.description,
            "max_items": self.max_items,
            "include_full_content": self.include_full_content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedConfig':
        """Create instance from dictionary."""
        # Handle datetime conversion
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("last_accessed"), str) and data["last_accessed"]:
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])

        # Handle enum conversion
        if isinstance(data.get("feed_type"), str):
            data["feed_type"] = FeedType(data["feed_type"])

        return cls(**data)
