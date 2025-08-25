"""
Base model classes for Summary Bot NG.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


@dataclass
class BaseModel:
    """Base model class with common functionality."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert model to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseModel':
        """Create model instance from dictionary."""
        return cls(**data)
    
    @classmethod 
    def from_json(cls, json_str: str) -> 'BaseModel':
        """Create model instance from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class SerializableModel(ABC):
    """Abstract base class for models that need custom serialization."""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        pass
    
    @abstractmethod
    def to_json(self) -> str:
        """Convert to JSON string."""
        pass
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SerializableModel':
        """Create instance from dictionary."""
        pass


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow().replace(microsecond=0)