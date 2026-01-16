"""
Summary-related data models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

from .base import BaseModel, generate_id, utc_now


class SummaryLength(Enum):
    """Summary length options."""
    BRIEF = "brief"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


class Priority(Enum):
    """Priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ActionItem(BaseModel):
    """Represents an action item extracted from a summary."""
    description: str
    assignee: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    source_message_ids: List[str] = field(default_factory=list)
    completed: bool = False
    
    def to_markdown(self) -> str:
        """Convert to markdown format."""
        priority_emoji = {
            Priority.HIGH: "🔴",
            Priority.MEDIUM: "🟡", 
            Priority.LOW: "🟢"
        }
        
        status = "✅" if self.completed else "⭕"
        assignee_text = f" (@{self.assignee})" if self.assignee else ""
        deadline_text = f" - Due: {self.deadline.strftime('%Y-%m-%d')}" if self.deadline else ""
        
        return f"{status} {priority_emoji[self.priority]} {self.description}{assignee_text}{deadline_text}"


@dataclass
class TechnicalTerm(BaseModel):
    """Represents a technical term with definition."""
    term: str
    definition: str
    context: str
    source_message_id: str
    category: Optional[str] = None
    
    def to_markdown(self) -> str:
        """Convert to markdown format."""
        return f"**{self.term}**: {self.definition}"


@dataclass
class Participant(BaseModel):
    """Represents a conversation participant."""
    user_id: str
    display_name: str
    message_count: int
    key_contributions: List[str] = field(default_factory=list)
    first_message_time: Optional[datetime] = None
    last_message_time: Optional[datetime] = None
    
    def to_markdown(self) -> str:
        """Convert to markdown format."""
        contributions = "\n".join([f"  - {contrib}" for contrib in self.key_contributions])
        return f"**{self.display_name}** ({self.message_count} messages)\n{contributions}"


@dataclass
class SummarizationContext(BaseModel):
    """Context information for summarization."""
    channel_name: str
    guild_name: str
    total_participants: int
    time_span_hours: float
    message_types: Dict[str, int] = field(default_factory=dict)  # e.g., {"text": 45, "image": 3}
    dominant_topics: List[str] = field(default_factory=list)
    thread_count: int = 0


@dataclass
class SummaryResult(BaseModel):
    """Complete summary result with all extracted information."""
    id: str = field(default_factory=generate_id)
    channel_id: str = ""
    guild_id: str = ""
    start_time: datetime = field(default_factory=utc_now)
    end_time: datetime = field(default_factory=utc_now)
    message_count: int = 0
    key_points: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    technical_terms: List[TechnicalTerm] = field(default_factory=list)
    participants: List[Participant] = field(default_factory=list)
    summary_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    context: Optional[SummarizationContext] = None
    
    def to_embed_dict(self) -> Dict[str, Any]:
        """Convert to Discord embed dictionary."""
        embed = {
            "title": f"📋 Summary for #{self.context.channel_name if self.context else 'Unknown Channel'}",
            "description": self.summary_text[:2048],  # Discord embed description limit
            "color": 0x4A90E2,  # Blue color
            "timestamp": self.created_at.isoformat(),
            "fields": []
        }
        
        # Add key points field
        if self.key_points:
            key_points_text = "\n".join([f"• {point}" for point in self.key_points[:5]])
            if len(key_points_text) > 1024:
                key_points_text = key_points_text[:1020] + "..."
            embed["fields"].append({
                "name": "🎯 Key Points",
                "value": key_points_text,
                "inline": False
            })
        
        # Add action items field
        if self.action_items:
            action_text = "\n".join([item.to_markdown() for item in self.action_items[:3]])
            if len(action_text) > 1024:
                action_text = action_text[:1020] + "..."
            embed["fields"].append({
                "name": "📝 Action Items",
                "value": action_text,
                "inline": False
            })
        
        # Add participants field
        if self.participants:
            top_participants = sorted(self.participants, key=lambda p: p.message_count, reverse=True)[:5]
            participants_text = "\n".join([
                f"• {p.display_name} ({p.message_count} messages)" 
                for p in top_participants
            ])
            embed["fields"].append({
                "name": "👥 Top Participants",
                "value": participants_text,
                "inline": True
            })
        
        # Add technical terms field
        if self.technical_terms:
            terms_text = "\n".join([
                f"• **{term.term}**: {term.definition[:50]}..." 
                if len(term.definition) > 50 else f"• **{term.term}**: {term.definition}"
                for term in self.technical_terms[:3]
            ])
            embed["fields"].append({
                "name": "🔧 Technical Terms",
                "value": terms_text,
                "inline": True
            })
        
        # Add summary statistics
        stats_text = (
            f"📊 {self.message_count} messages\n"
            f"⏱️ {(self.end_time - self.start_time).total_seconds() / 3600:.1f}h timespan\n"
            f"👥 {len(self.participants)} participants"
        )
        embed["fields"].append({
            "name": "📈 Statistics",
            "value": stats_text,
            "inline": True
        })
        
        # Add footer
        embed["footer"] = {
            "text": f"Summary ID: {self.id[:8]}... | Generated by Summary Bot NG"
        }
        
        return embed
    
    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"# 📋 Summary: #{self.context.channel_name if self.context else 'Unknown Channel'}\n\n"
        md += f"**Time Period:** {self.start_time.strftime('%Y-%m-%d %H:%M')} - {self.end_time.strftime('%Y-%m-%d %H:%M')}\n"
        md += f"**Messages:** {self.message_count} | **Participants:** {len(self.participants)}\n\n"
        
        # Main summary
        md += f"## 📖 Summary\n\n{self.summary_text}\n\n"
        
        # Key points
        if self.key_points:
            md += "## 🎯 Key Points\n\n"
            for point in self.key_points:
                md += f"- {point}\n"
            md += "\n"
        
        # Action items
        if self.action_items:
            md += "## 📝 Action Items\n\n"
            for item in self.action_items:
                md += f"- {item.to_markdown()}\n"
            md += "\n"
        
        # Technical terms
        if self.technical_terms:
            md += "## 🔧 Technical Terms\n\n"
            for term in self.technical_terms:
                md += f"- {term.to_markdown()}\n"
            md += "\n"
        
        # Participants
        if self.participants:
            md += "## 👥 Participants\n\n"
            sorted_participants = sorted(self.participants, key=lambda p: p.message_count, reverse=True)
            for participant in sorted_participants:
                md += f"### {participant.display_name} ({participant.message_count} messages)\n"
                if participant.key_contributions:
                    md += "Key contributions:\n"
                    for contribution in participant.key_contributions:
                        md += f"- {contribution}\n"
                md += "\n"
        
        # Metadata
        md += f"---\n*Summary generated on {self.created_at.strftime('%Y-%m-%d at %H:%M UTC')} | ID: {self.id}*\n"
        
        return md
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "id": self.id,
            "message_count": self.message_count,
            "participant_count": len(self.participants),
            "key_points_count": len(self.key_points),
            "action_items_count": len(self.action_items),
            "technical_terms_count": len(self.technical_terms),
            "time_span_hours": (self.end_time - self.start_time).total_seconds() / 3600,
            "words_in_summary": len(self.summary_text.split()),
            "created_at": self.created_at,
            "channel_id": self.channel_id,
            "guild_id": self.guild_id
        }


@dataclass
class SummaryOptions(BaseModel):
    """Options for controlling summarization behavior."""
    summary_length: SummaryLength = SummaryLength.DETAILED
    perspective: str = "general"  # general, developer, marketing, product, finance, executive, support
    include_bots: bool = False
    include_attachments: bool = True
    excluded_users: List[str] = field(default_factory=list)
    min_messages: int = 5
    claude_model: str = "claude-3-sonnet-20240229"
    temperature: float = 0.3
    max_tokens: int = 4000
    extract_action_items: bool = True
    extract_technical_terms: bool = True
    extract_key_points: bool = True
    include_participant_analysis: bool = True
    
    def get_max_tokens_for_length(self) -> int:
        """Get appropriate max tokens based on summary length."""
        token_mapping = {
            SummaryLength.BRIEF: 1000,
            SummaryLength.DETAILED: 4000,
            SummaryLength.COMPREHENSIVE: 8000
        }
        return min(self.max_tokens, token_mapping[self.summary_length])
    
    def get_system_prompt_additions(self) -> List[str]:
        """Get additional system prompt requirements based on options."""
        additions = []
        
        if not self.extract_action_items:
            additions.append("Do not extract action items.")
        
        if not self.extract_technical_terms:
            additions.append("Do not define technical terms.")
        
        if not self.extract_key_points:
            additions.append("Focus on narrative summary only, no bullet points.")
        
        if not self.include_participant_analysis:
            additions.append("Do not analyze individual participant contributions.")
        
        length_instructions = {
            SummaryLength.BRIEF: "Keep the summary concise and focus on the most important points only.",
            SummaryLength.DETAILED: "Provide a balanced summary with good coverage of the discussion.",
            SummaryLength.COMPREHENSIVE: "Provide an extensive summary covering all aspects of the conversation."
        }
        additions.append(length_instructions[self.summary_length])
        
        return additions