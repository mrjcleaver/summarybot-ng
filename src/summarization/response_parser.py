"""
Claude response parsing and processing.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.summary import (
    SummaryResult, ActionItem, TechnicalTerm, Participant,
    SummarizationContext, Priority
)
from ..models.message import ProcessedMessage
from ..models.base import BaseModel, generate_id
from ..exceptions import SummarizationError

logger = logging.getLogger(__name__)


@dataclass
class ParsedSummary(BaseModel):
    """Parsed and structured summary from Claude response."""
    summary_text: str
    key_points: List[str]
    action_items: List[ActionItem]
    technical_terms: List[TechnicalTerm]
    participants: List[Participant]
    raw_response: str
    parsing_metadata: Dict[str, Any]


class ResponseParser:
    """Parses and processes Claude API responses into structured summaries."""
    
    def __init__(self):
        self.fallback_parsers = [
            self._parse_json_response,
            self._parse_markdown_response,
            self._parse_freeform_response
        ]
    
    def parse_summary_response(self,
                             response_content: str,
                             original_messages: List[ProcessedMessage],
                             context: Optional[SummarizationContext] = None) -> ParsedSummary:
        """Parse Claude response into structured summary.
        
        Args:
            response_content: Raw response from Claude
            original_messages: Original messages that were summarized
            context: Additional context information
            
        Returns:
            Parsed and structured summary
            
        Raises:
            SummarizationError: If parsing fails completely
        """
        parsing_metadata = {
            "response_length": len(response_content),
            "parsing_method": None,
            "extraction_stats": {},
            "warnings": []
        }

        # Log response preview for debugging
        logger.debug(f"Parsing Claude response (length={len(response_content)})")
        logger.debug(f"Response preview: {response_content[:500]}...")

        # Try each parser in order
        for parser_method in self.fallback_parsers:
            try:
                logger.debug(f"Trying parser: {parser_method.__name__}")
                parsed = parser_method(response_content, parsing_metadata)
                if parsed:
                    logger.debug(f"Parser {parser_method.__name__} succeeded")
                    # Enhance with message analysis
                    enhanced = self._enhance_with_message_analysis(
                        parsed, original_messages, context
                    )

                    # Validate and clean up
                    validated = self._validate_and_clean(enhanced, parsing_metadata)

                    return validated
                else:
                    logger.debug(f"Parser {parser_method.__name__} returned None")

            except Exception as e:
                error_msg = f"{parser_method.__name__}: {str(e)}"
                parsing_metadata["warnings"].append(error_msg)
                logger.warning(f"Parser {parser_method.__name__} failed: {str(e)}")
                continue

        # All parsers failed - log full details
        logger.error(f"All parsers failed for response. Warnings: {parsing_metadata['warnings']}")
        logger.error(f"Full response content: {response_content}")

        raise SummarizationError(
            message="Failed to parse Claude response with any available parser",
            error_code="RESPONSE_PARSE_FAILED",
            context={
                "response_preview": response_content[:200],
                "parsing_metadata": parsing_metadata
            }
        )
    
    def extract_summary_result(self,
                             parsed: ParsedSummary,
                             channel_id: str,
                             guild_id: str,
                             start_time: datetime,
                             end_time: datetime,
                             message_count: int,
                             context: Optional[SummarizationContext] = None) -> SummaryResult:
        """Convert parsed summary to SummaryResult object."""
        return SummaryResult(
            id=generate_id(),
            channel_id=channel_id,
            guild_id=guild_id,
            start_time=start_time,
            end_time=end_time,
            message_count=message_count,
            key_points=parsed.key_points,
            action_items=parsed.action_items,
            technical_terms=parsed.technical_terms,
            participants=parsed.participants,
            summary_text=parsed.summary_text,
            metadata=parsed.parsing_metadata,
            created_at=datetime.utcnow(),
            context=context
        )
    
    def _parse_json_response(self, content: str, metadata: Dict[str, Any]) -> Optional[ParsedSummary]:
        """Parse JSON-formatted response."""
        metadata["parsing_method"] = "json"
        
        # Extract JSON from response (handle code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_start = content.find('{')
            json_end = content.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_str = content[json_start:json_end + 1]
            else:
                return None
        
        try:
            data = json.loads(json_str)
            
            # Extract components
            summary_text = data.get("summary_text", "")
            key_points = data.get("key_points", [])
            
            # Parse action items
            action_items = []
            for item_data in data.get("action_items", []):
                if isinstance(item_data, dict):
                    priority = Priority.MEDIUM  # default
                    if "priority" in item_data:
                        try:
                            priority = Priority(item_data["priority"].lower())
                        except ValueError:
                            pass
                    
                    action_items.append(ActionItem(
                        description=item_data.get("description", ""),
                        assignee=item_data.get("assignee"),
                        priority=priority
                    ))
                elif isinstance(item_data, str):
                    action_items.append(ActionItem(description=item_data))
            
            # Parse technical terms
            technical_terms = []
            for term_data in data.get("technical_terms", []):
                if isinstance(term_data, dict):
                    technical_terms.append(TechnicalTerm(
                        term=term_data.get("term", ""),
                        definition=term_data.get("definition", ""),
                        context=term_data.get("context", ""),
                        source_message_id=""  # Will be filled later if possible
                    ))
            
            # Parse participants
            participants = []
            for participant_data in data.get("participants", []):
                if isinstance(participant_data, dict):
                    participants.append(Participant(
                        user_id="",  # Will be filled from message analysis
                        display_name=participant_data.get("name", ""),
                        message_count=participant_data.get("message_count", 0),
                        key_contributions=self._ensure_list(participant_data.get("key_contribution", []))
                    ))
            
            metadata["extraction_stats"] = {
                "key_points": len(key_points),
                "action_items": len(action_items),
                "technical_terms": len(technical_terms),
                "participants": len(participants)
            }
            
            return ParsedSummary(
                summary_text=summary_text,
                key_points=key_points,
                action_items=action_items,
                technical_terms=technical_terms,
                participants=participants,
                raw_response=content,
                parsing_metadata=metadata.copy()
            )
            
        except json.JSONDecodeError as e:
            metadata["warnings"].append(f"JSON parse error: {str(e)}")
            return None
    
    def _parse_markdown_response(self, content: str, metadata: Dict[str, Any]) -> Optional[ParsedSummary]:
        """Parse markdown-formatted response."""
        metadata["parsing_method"] = "markdown"
        
        # Extract sections using regex
        summary_text = self._extract_markdown_section(content, r"(?:## )?Summary", r"(?=##|$)")
        key_points = self._extract_markdown_list(content, r"(?:## )?Key Points?")
        action_items_text = self._extract_markdown_list(content, r"(?:## )?Action Items?")
        technical_terms_text = self._extract_markdown_list(content, r"(?:## )?Technical Terms?")
        participants_text = self._extract_markdown_list(content, r"(?:## )?Participants?")
        
        # Convert to objects
        action_items = [ActionItem(description=item) for item in action_items_text]
        
        technical_terms = []
        for term_text in technical_terms_text:
            # Parse "term: definition" format
            if ':' in term_text:
                term, definition = term_text.split(':', 1)
                technical_terms.append(TechnicalTerm(
                    term=term.strip(),
                    definition=definition.strip(),
                    context="",
                    source_message_id=""
                ))
        
        participants = []
        for participant_text in participants_text:
            # Parse "Name (X messages): contribution" format
            match = re.match(r'([^(]+)(?:\((\d+)\s+messages?\))?\s*:?\s*(.*)', participant_text)
            if match:
                name, msg_count, contribution = match.groups()
                participants.append(Participant(
                    user_id="",
                    display_name=name.strip(),
                    message_count=int(msg_count) if msg_count else 0,
                    key_contributions=[contribution.strip()] if contribution.strip() else []
                ))
        
        return ParsedSummary(
            summary_text=summary_text,
            key_points=key_points,
            action_items=action_items,
            technical_terms=technical_terms,
            participants=participants,
            raw_response=content,
            parsing_metadata=metadata.copy()
        )
    
    def _parse_freeform_response(self, content: str, metadata: Dict[str, Any]) -> Optional[ParsedSummary]:
        """Parse freeform text response as fallback."""
        metadata["parsing_method"] = "freeform"
        
        # Use the entire content as summary text
        summary_text = content.strip()
        
        # Try to extract some structure with simple heuristics
        lines = content.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            # Look for bullet points or numbered lists
            if re.match(r'^[-*•]\s+|^\d+\.\s+', line):
                key_points.append(re.sub(r'^[-*•]\s+|^\d+\.\s+', '', line))
        
        # If no bullet points found, split summary into sentences as key points
        if not key_points and summary_text:
            sentences = re.split(r'[.!?]+', summary_text)
            key_points = [s.strip() for s in sentences if len(s.strip()) > 10][:5]
        
        return ParsedSummary(
            summary_text=summary_text,
            key_points=key_points,
            action_items=[],  # Can't reliably extract from freeform
            technical_terms=[],  # Can't reliably extract from freeform
            participants=[],  # Will be filled from message analysis
            raw_response=content,
            parsing_metadata=metadata.copy()
        )
    
    def _enhance_with_message_analysis(self,
                                     parsed: ParsedSummary,
                                     messages: List[ProcessedMessage],
                                     context: Optional[SummarizationContext]) -> ParsedSummary:
        """Enhance parsed summary with analysis of original messages."""
        # Count actual participants from messages
        participant_counts = {}
        participant_contributions = {}
        
        for message in messages:
            author = message.author_name
            participant_counts[author] = participant_counts.get(author, 0) + 1
            
            if message.has_substantial_content():
                if author not in participant_contributions:
                    participant_contributions[author] = []
                
                # Add substantial messages as contributions
                content_summary = message.get_content_summary(50)
                if content_summary and content_summary != "[Empty message]":
                    participant_contributions[author].append(content_summary)
        
        # Update or create participant objects
        updated_participants = []
        existing_names = {p.display_name.lower(): p for p in parsed.participants}
        
        for author, count in participant_counts.items():
            if author.lower() in existing_names:
                # Update existing participant
                participant = existing_names[author.lower()]
                participant.message_count = count
                if author in participant_contributions:
                    participant.key_contributions = participant_contributions[author][:3]  # Top 3
                updated_participants.append(participant)
            else:
                # Create new participant
                updated_participants.append(Participant(
                    user_id="",  # Would need Discord API to resolve
                    display_name=author,
                    message_count=count,
                    key_contributions=participant_contributions.get(author, [])[:3]
                ))
        
        # Sort by message count
        updated_participants.sort(key=lambda p: p.message_count, reverse=True)
        
        parsed.participants = updated_participants
        return parsed
    
    def _validate_and_clean(self, parsed: ParsedSummary, metadata: Dict[str, Any]) -> ParsedSummary:
        """Validate and clean up parsed summary."""
        # Ensure summary text exists
        if not parsed.summary_text.strip():
            logger.warning(f"Parsed summary has empty text. Parsing metadata: {metadata}")
            logger.warning(f"Raw response: {parsed.raw_response[:1000]}")
            parsed.summary_text = "Summary could not be extracted from response."
        
        # Limit lengths to prevent excessive content
        parsed.summary_text = parsed.summary_text[:2000]  # Discord embed limit
        parsed.key_points = parsed.key_points[:10]  # Max 10 points
        parsed.action_items = parsed.action_items[:20]  # Max 20 actions
        parsed.technical_terms = parsed.technical_terms[:15]  # Max 15 terms
        
        # Clean up empty or too-short items
        parsed.key_points = [point for point in parsed.key_points if len(point.strip()) > 5]
        
        metadata["final_stats"] = {
            "summary_length": len(parsed.summary_text),
            "key_points": len(parsed.key_points),
            "action_items": len(parsed.action_items),
            "technical_terms": len(parsed.technical_terms),
            "participants": len(parsed.participants)
        }
        
        return parsed
    
    def _extract_markdown_section(self, content: str, header_pattern: str, 
                                 end_pattern: str = r"(?=##|$)") -> str:
        """Extract a markdown section by header."""
        pattern = f"{header_pattern}[:\n]+(.*?){end_pattern}"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def _extract_markdown_list(self, content: str, header_pattern: str) -> List[str]:
        """Extract items from a markdown list section."""
        section = self._extract_markdown_section(content, header_pattern)
        if not section:
            return []
        
        items = []
        for line in section.split('\n'):
            line = line.strip()
            if re.match(r'^[-*•]\s+|^\d+\.\s+', line):
                item = re.sub(r'^[-*•]\s+|^\d+\.\s+', '', line).strip()
                if item:
                    items.append(item)
        
        return items
    
    def _ensure_list(self, value) -> List[str]:
        """Ensure value is a list of strings."""
        if isinstance(value, list):
            return [str(item) for item in value]
        elif isinstance(value, str):
            return [value] if value else []
        else:
            return [str(value)] if value else []