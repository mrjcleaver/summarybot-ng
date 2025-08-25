"""
Main summarization engine coordinating all components.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from .claude_client import ClaudeClient, ClaudeOptions
from .prompt_builder import PromptBuilder
from .response_parser import ResponseParser
from .cache import SummaryCache
from ..models.summary import SummaryResult, SummaryOptions, SummarizationContext
from ..models.message import ProcessedMessage
from ..exceptions import (
    SummarizationError, InsufficientContentError, PromptTooLongError,
    create_error_context
)


class SummarizationEngine:
    """Main engine for AI-powered summarization."""
    
    def __init__(self, 
                 claude_client: ClaudeClient,
                 cache: Optional[SummaryCache] = None,
                 max_prompt_tokens: int = 100000):
        """Initialize summarization engine.
        
        Args:
            claude_client: Claude API client
            cache: Optional summary cache
            max_prompt_tokens: Maximum tokens allowed in prompt
        """
        self.claude_client = claude_client
        self.cache = cache
        self.max_prompt_tokens = max_prompt_tokens
        
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
    
    async def summarize_messages(self,
                               messages: List[ProcessedMessage],
                               options: SummaryOptions,
                               context: SummarizationContext,
                               channel_id: str = "",
                               guild_id: str = "") -> SummaryResult:
        """Summarize a list of messages.
        
        Args:
            messages: List of processed messages
            options: Summarization options
            context: Context information
            channel_id: Discord channel ID
            guild_id: Discord guild ID
            
        Returns:
            Complete summary result
            
        Raises:
            InsufficientContentError: Not enough content to summarize
            SummarizationError: Summarization process failed
        """
        # Validate input
        if len(messages) < options.min_messages:
            raise InsufficientContentError(
                message_count=len(messages),
                min_required=options.min_messages,
                context=create_error_context(
                    channel_id=channel_id,
                    guild_id=guild_id,
                    operation="summarize_messages"
                )
            )
        
        # Check cache if available
        if self.cache:
            start_time = min(msg.timestamp for msg in messages)
            end_time = max(msg.timestamp for msg in messages)
            
            cached_summary = await self.cache.get_cached_summary(
                channel_id=channel_id,
                start_time=start_time,
                end_time=end_time,
                options_hash=self._hash_options(options)
            )
            
            if cached_summary:
                return cached_summary
        
        try:
            # Build summarization prompt
            prompt_data = self.prompt_builder.build_summarization_prompt(
                messages=messages,
                options=options,
                context=context.to_dict() if context else None
            )
            
            # Check if prompt is too long
            if prompt_data.estimated_tokens > self.max_prompt_tokens:
                # Try to optimize
                optimized_user_prompt = self.prompt_builder.optimize_prompt_length(
                    prompt_data.user_prompt,
                    self.max_prompt_tokens - self.prompt_builder.estimate_token_count(prompt_data.system_prompt)
                )
                
                if self.prompt_builder.estimate_token_count(optimized_user_prompt + prompt_data.system_prompt) > self.max_prompt_tokens:
                    raise PromptTooLongError(
                        prompt_length=prompt_data.estimated_tokens,
                        max_length=self.max_prompt_tokens,
                        context=create_error_context(
                            channel_id=channel_id,
                            guild_id=guild_id,
                            operation="prompt_building",
                            message_count=len(messages)
                        )
                    )
                
                prompt_data.user_prompt = optimized_user_prompt
            
            # Configure Claude options
            claude_options = ClaudeOptions(
                model=options.claude_model,
                max_tokens=options.get_max_tokens_for_length(),
                temperature=options.temperature
            )
            
            # Call Claude API
            response = await self.claude_client.create_summary(
                prompt=prompt_data.user_prompt,
                system_prompt=prompt_data.system_prompt,
                options=claude_options
            )
            
            # Parse response
            parsed_summary = self.response_parser.parse_summary_response(
                response_content=response.content,
                original_messages=messages,
                context=context
            )
            
            # Create final summary result
            start_time = min(msg.timestamp for msg in messages) if messages else datetime.utcnow()
            end_time = max(msg.timestamp for msg in messages) if messages else datetime.utcnow()
            
            summary_result = self.response_parser.extract_summary_result(
                parsed=parsed_summary,
                channel_id=channel_id,
                guild_id=guild_id,
                start_time=start_time,
                end_time=end_time,
                message_count=len(messages),
                context=context
            )
            
            # Add API usage metadata
            summary_result.metadata.update({
                "claude_model": response.model,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.total_tokens,
                "api_response_id": response.response_id,
                "processing_time": (datetime.utcnow() - summary_result.created_at).total_seconds()
            })
            
            # Cache result if cache is available
            if self.cache:
                await self.cache.cache_summary(summary_result)
            
            return summary_result
            
        except Exception as e:
            if isinstance(e, (InsufficientContentError, PromptTooLongError)):
                raise
            
            # Wrap other exceptions
            raise SummarizationError(
                message=f"Summarization failed: {str(e)}",
                error_code="SUMMARIZATION_FAILED",
                context=create_error_context(
                    channel_id=channel_id,
                    guild_id=guild_id,
                    operation="summarize_messages",
                    message_count=len(messages)
                ),
                retryable=True,
                cause=e
            )
    
    async def batch_summarize(self,
                            requests: List[Dict[str, Any]]) -> List[SummaryResult]:
        """Summarize multiple message sets in batch.
        
        Args:
            requests: List of summarization requests, each containing:
                - messages: List[ProcessedMessage]
                - options: SummaryOptions
                - context: SummarizationContext
                - channel_id: str
                - guild_id: str
                
        Returns:
            List of summary results in same order as requests
        """
        # Process requests concurrently with limited concurrency
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        
        async def process_single_request(request: Dict[str, Any]) -> SummaryResult:
            async with semaphore:
                return await self.summarize_messages(
                    messages=request["messages"],
                    options=request["options"],
                    context=request["context"],
                    channel_id=request.get("channel_id", ""),
                    guild_id=request.get("guild_id", "")
                )
        
        tasks = [process_single_request(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Create error summary
                error_summary = SummaryResult(
                    channel_id=requests[i].get("channel_id", ""),
                    guild_id=requests[i].get("guild_id", ""),
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    message_count=len(requests[i]["messages"]),
                    summary_text=f"Error: {str(result)}",
                    metadata={"error": True, "error_type": type(result).__name__}
                )
                final_results.append(error_summary)
            else:
                final_results.append(result)
        
        return final_results
    
    def estimate_cost(self,
                     messages: List[ProcessedMessage],
                     options: SummaryOptions) -> Dict[str, Any]:
        """Estimate cost for summarizing messages.
        
        Args:
            messages: Messages to be summarized
            options: Summarization options
            
        Returns:
            Cost estimation with breakdown
        """
        # Build prompt to estimate tokens
        try:
            prompt_data = self.prompt_builder.build_summarization_prompt(
                messages=messages,
                options=options
            )
            
            input_tokens = prompt_data.estimated_tokens
            output_tokens = options.get_max_tokens_for_length()
            
            cost = self.claude_client.estimate_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=options.claude_model
            )
            
            return {
                "estimated_cost_usd": cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "model": options.claude_model,
                "message_count": len(messages)
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "estimated_cost_usd": 0.0,
                "message_count": len(messages)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of summarization engine.
        
        Returns:
            Health status information
        """
        health_info = {
            "status": "healthy",
            "claude_api": False,
            "cache": False,
            "components": {
                "prompt_builder": True,
                "response_parser": True
            },
            "usage_stats": self.claude_client.get_usage_stats().to_dict()
        }
        
        # Check Claude API
        try:
            health_info["claude_api"] = await self.claude_client.health_check()
        except Exception:
            health_info["claude_api"] = False
            health_info["status"] = "degraded"
        
        # Check cache
        if self.cache:
            try:
                health_info["cache"] = await self.cache.health_check()
            except Exception:
                health_info["cache"] = False
        else:
            health_info["cache"] = None  # Cache not configured
        
        # Overall status
        if not health_info["claude_api"]:
            health_info["status"] = "unhealthy"
        elif health_info["cache"] is False:
            health_info["status"] = "degraded"
        
        return health_info
    
    def _hash_options(self, options: SummaryOptions) -> str:
        """Create hash of options for caching."""
        import hashlib
        
        options_str = f"{options.summary_length.value}-{options.claude_model}-{options.temperature}-{options.max_tokens}"
        return hashlib.md5(options_str.encode()).hexdigest()[:16]