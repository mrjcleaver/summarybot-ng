"""
Dynamic prompt generation for Claude API summarization.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.summary import SummaryOptions, SummaryLength
from ..models.message import ProcessedMessage
from ..models.base import BaseModel


@dataclass
class SummarizationPrompt(BaseModel):
    """A complete summarization prompt."""
    system_prompt: str
    user_prompt: str
    estimated_tokens: int
    metadata: Dict[str, Any]


class PromptBuilder:
    """Builds optimized prompts for Claude API summarization."""
    
    # Token estimation (rough approximation: 1 token ≈ 4 characters)
    CHARS_PER_TOKEN = 4
    
    def __init__(self):
        self.system_prompts = {
            SummaryLength.BRIEF: self._build_brief_system_prompt(),
            SummaryLength.DETAILED: self._build_detailed_system_prompt(), 
            SummaryLength.COMPREHENSIVE: self._build_comprehensive_system_prompt()
        }
    
    def build_summarization_prompt(self,
                                 messages: List[ProcessedMessage],
                                 options: SummaryOptions,
                                 context: Optional[Dict[str, Any]] = None,
                                 custom_system_prompt: Optional[str] = None) -> SummarizationPrompt:
        """Build a complete summarization prompt.

        Args:
            messages: List of processed messages to summarize
            options: Summarization options
            context: Additional context information
            custom_system_prompt: Optional custom system prompt (overrides default)

        Returns:
            Complete prompt ready for Claude API
        """
        context = context or {}

        # Build system prompt (use custom if provided, otherwise default)
        if custom_system_prompt:
            system_prompt = custom_system_prompt
        else:
            system_prompt = self.build_system_prompt(options)
        
        # Build user prompt with messages
        user_prompt = self.build_user_prompt(messages, context, options)
        
        # Estimate token count
        estimated_tokens = self.estimate_token_count(system_prompt + user_prompt)
        
        # Build metadata
        metadata = {
            "message_count": len(messages),
            "time_span": self._calculate_time_span(messages),
            "summary_length": options.summary_length.value,
            "include_actions": options.extract_action_items,
            "include_technical": options.extract_technical_terms,
            "estimated_tokens": estimated_tokens
        }
        
        return SummarizationPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            estimated_tokens=estimated_tokens,
            metadata=metadata
        )
    
    def build_system_prompt(self, options: SummaryOptions) -> str:
        """Build system prompt based on options."""
        base_prompt = self.system_prompts[options.summary_length]
        
        # Add option-specific modifications
        additions = options.get_system_prompt_additions()
        if additions:
            base_prompt += "\n\nAdditional instructions:\n" + "\n".join(f"- {addition}" for addition in additions)
        
        return base_prompt
    
    def build_user_prompt(self, 
                         messages: List[ProcessedMessage],
                         context: Dict[str, Any],
                         options: SummaryOptions) -> str:
        """Build user prompt with message content."""
        prompt_parts = []
        
        # Add context information
        if context:
            prompt_parts.append(self._build_context_section(context))
        
        # Add message formatting instructions
        prompt_parts.append(self._build_format_instructions(options))
        
        # Add messages content
        prompt_parts.append(self._build_messages_section(messages, options))
        
        # Add final instruction
        prompt_parts.append(self._build_final_instruction(options))
        
        return "\n\n".join(prompt_parts)
    
    def optimize_prompt_length(self, 
                             prompt: str, 
                             max_tokens: int,
                             preserve_ratio: float = 0.8) -> str:
        """Optimize prompt length to fit within token limits.
        
        Args:
            prompt: Original prompt
            max_tokens: Maximum allowed tokens
            preserve_ratio: Ratio of content to preserve (0.0-1.0)
            
        Returns:
            Optimized prompt that fits within limits
        """
        current_tokens = self.estimate_token_count(prompt)
        
        if current_tokens <= max_tokens:
            return prompt
        
        # Calculate target length
        target_tokens = int(max_tokens * preserve_ratio)
        target_chars = target_tokens * self.CHARS_PER_TOKEN
        
        # Find message section and truncate it
        messages_start = prompt.find("## Messages to Summarize:")
        if messages_start == -1:
            # Simple truncation if structure not found
            return prompt[:target_chars] + "\n\n[Content truncated to fit limits]"
        
        # Keep everything before messages section
        prefix = prompt[:messages_start]
        remaining_chars = target_chars - len(prefix) - 100  # Buffer for truncation notice
        
        if remaining_chars <= 0:
            return prefix + "\n\n[Content too long to summarize]"
        
        # Truncate messages section
        messages_section = prompt[messages_start:]
        if len(messages_section) > remaining_chars:
            truncated_messages = messages_section[:remaining_chars]
            # Try to end at a message boundary
            last_message_end = truncated_messages.rfind("\n\n**")
            if last_message_end > remaining_chars * 0.5:  # At least half content preserved
                truncated_messages = truncated_messages[:last_message_end]
            
            return prefix + truncated_messages + f"\n\n[Truncated {len(messages_section) - len(truncated_messages)} characters to fit limits]"
        
        return prompt
    
    def estimate_token_count(self, text: str) -> int:
        """Estimate token count for text."""
        return len(text) // self.CHARS_PER_TOKEN
    
    def _build_brief_system_prompt(self) -> str:
        """Build system prompt for brief summaries."""
        return """You are an expert at creating concise, actionable summaries of Discord conversations. Your task is to distill lengthy discussions into their most essential elements.

For BRIEF summaries:
- Focus on the 3-5 most important points
- Extract only the most critical action items
- Keep technical explanations minimal
- Prioritize actionable information over background discussion

Response Format:
Return a JSON object with this structure:
```json
{
  "summary_text": "2-3 sentence overview of the main discussion",
  "key_points": ["point 1", "point 2", "point 3"],
  "action_items": [{"description": "task", "assignee": "user", "priority": "high|medium|low"}],
  "technical_terms": [{"term": "concept", "definition": "brief explanation"}],
  "participants": [{"name": "username", "key_contribution": "their main point"}]
}
```

Keep the summary focused, practical, and under 200 words total."""
    
    def _build_detailed_system_prompt(self) -> str:
        """Build system prompt for detailed summaries."""
        return """You are an expert at creating comprehensive summaries of Discord conversations. Your task is to capture the full scope of discussions while maintaining clarity and organization.

For DETAILED summaries:
- Include all major discussion points and conclusions
- Extract actionable items with context
- Explain technical concepts clearly
- Show how different topics connect
- Highlight key participant contributions

Response Format:
Return a JSON object with this structure:
```json
{
  "summary_text": "Comprehensive overview covering all major aspects of the discussion",
  "key_points": ["detailed point 1", "detailed point 2", "..."],
  "action_items": [{"description": "detailed task", "assignee": "user", "priority": "high|medium|low", "context": "why this matters"}],
  "technical_terms": [{"term": "concept", "definition": "thorough explanation", "context": "how it was used"}],
  "participants": [{"name": "username", "key_contribution": "their main contributions", "message_count": number}]
}
```

Balance thoroughness with readability. Aim for 300-600 words total."""
    
    def _build_comprehensive_system_prompt(self) -> str:
        """Build system prompt for comprehensive summaries."""
        return """You are an expert at creating exhaustive summaries of Discord conversations. Your task is to capture every significant detail while organizing information logically.

For COMPREHENSIVE summaries:
- Document all discussion threads and their outcomes
- Include background context and reasoning
- Extract all actionable items, even minor ones
- Provide detailed technical explanations
- Show conversation evolution and decision-making process
- Highlight all meaningful participant contributions

Response Format:
Return a JSON object with this structure:
```json
{
  "summary_text": "Exhaustive overview covering all aspects, context, and implications",
  "key_points": ["comprehensive point 1", "comprehensive point 2", "..."],
  "action_items": [{"description": "detailed task with full context", "assignee": "user", "priority": "high|medium|low", "deadline": "if mentioned", "context": "full background"}],
  "technical_terms": [{"term": "concept", "definition": "complete explanation", "context": "usage context", "related_concepts": ["other terms"]}],
  "participants": [{"name": "username", "key_contribution": "all their contributions", "message_count": number, "expertise_shown": "domain knowledge displayed"}]
}
```

Leave nothing important out. Aim for 600-1000+ words as needed."""
    
    def _build_context_section(self, context: Dict[str, Any]) -> str:
        """Build context section of prompt."""
        parts = ["## Context Information"]
        
        if "channel_name" in context:
            parts.append(f"**Channel**: #{context['channel_name']}")
        
        if "guild_name" in context:
            parts.append(f"**Server**: {context['guild_name']}")
        
        if "time_range" in context:
            parts.append(f"**Time Period**: {context['time_range']}")
        
        if "total_participants" in context:
            parts.append(f"**Participants**: {context['total_participants']} users")
        
        return "\n".join(parts)
    
    def _build_format_instructions(self, options: SummaryOptions) -> str:
        """Build format-specific instructions."""
        instructions = ["## Summary Instructions"]
        
        instructions.append(f"- Summary length: {options.summary_length.value}")
        
        if options.include_bots:
            instructions.append("- Include bot messages in analysis")
        else:
            instructions.append("- Ignore bot messages unless critically relevant")
        
        if not options.extract_action_items:
            instructions.append("- Do not extract action items")
        
        if not options.extract_technical_terms:
            instructions.append("- Do not define technical terms")
        
        return "\n".join(instructions)
    
    def _build_messages_section(self, messages: List[ProcessedMessage], 
                               options: SummaryOptions) -> str:
        """Build messages section with formatted content."""
        parts = ["## Messages to Summarize:"]
        
        for i, message in enumerate(messages, 1):
            # Skip empty messages unless they have attachments
            if not message.has_substantial_content():
                continue
            
            message_parts = [f"**{message.author_name}** ({message.timestamp.strftime('%H:%M')})"]
            
            # Add message content
            if message.content:
                clean_content = message.clean_content()
                message_parts.append(clean_content)
            
            # Add attachment info
            if message.attachments and options.include_attachments:
                attachment_summaries = [att.get_summary_text() for att in message.attachments]
                message_parts.append(f"[Attachments: {', '.join(attachment_summaries)}]")
            
            # Add code blocks
            if message.code_blocks:
                for block in message.code_blocks:
                    lang = f" ({block.language})" if block.language else ""
                    message_parts.append(f"[Code Block{lang}: {len(block.code)} chars]")
            
            # Add thread info
            if message.thread_info:
                message_parts.append(f"[Thread: {message.thread_info.thread_name}]")
            
            parts.append("\n".join(message_parts))
            parts.append("")  # Empty line between messages
        
        return "\n".join(parts)
    
    def _build_final_instruction(self, options: SummaryOptions) -> str:
        """Build final instruction section."""
        instruction = f"""## Final Instructions

Analyze the above messages and create a {options.summary_length.value} summary following the specified JSON format. 

Key requirements:
- Be accurate and objective
- Preserve important context
- Use clear, professional language
- Structure information logically
- Return valid JSON only"""
        
        return instruction
    
    def _calculate_time_span(self, messages: List[ProcessedMessage]) -> str:
        """Calculate time span of messages."""
        if not messages:
            return "Unknown"
        
        start_time = min(msg.timestamp for msg in messages)
        end_time = max(msg.timestamp for msg in messages)
        
        duration = end_time - start_time
        
        if duration.total_seconds() < 3600:
            return f"{int(duration.total_seconds() / 60)} minutes"
        elif duration.total_seconds() < 86400:
            return f"{duration.total_seconds() / 3600:.1f} hours"
        else:
            return f"{duration.days} days, {duration.seconds // 3600} hours"