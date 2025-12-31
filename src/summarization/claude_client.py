"""
Claude API client for AI summarization.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import anthropic
from anthropic import AsyncAnthropic

from ..exceptions import (
    ClaudeAPIError, TokenLimitExceededError, ModelUnavailableError,
    RateLimitError, AuthenticationError, NetworkError, TimeoutError
)
from ..models.base import BaseModel


@dataclass
class ClaudeOptions(BaseModel):
    """Options for Claude API requests."""
    model: str = "claude-3-sonnet-20240229"
    max_tokens: int = 4000
    temperature: float = 0.3
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: List[str] = field(default_factory=list)
    stream: bool = False


@dataclass
class ClaudeResponse(BaseModel):
    """Response from Claude API."""
    content: str
    model: str
    usage: Dict[str, int]
    stop_reason: str
    response_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def input_tokens(self) -> int:
        """Get input token count."""
        return self.usage.get("input_tokens", 0)
    
    @property
    def output_tokens(self) -> int:
        """Get output token count."""
        return self.usage.get("output_tokens", 0)
    
    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.input_tokens + self.output_tokens
    
    def is_complete(self) -> bool:
        """Check if response was completed (not truncated)."""
        return self.stop_reason != "max_tokens"


@dataclass
class UsageStats(BaseModel):
    """Claude API usage statistics."""
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    errors_count: int = 0
    rate_limit_hits: int = 0
    last_request_time: Optional[datetime] = None
    
    def add_request(self, response: ClaudeResponse, cost: float = 0.0):
        """Add a successful request to stats."""
        self.total_requests += 1
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.total_cost_usd += cost
        self.last_request_time = datetime.utcnow()
    
    def add_error(self, is_rate_limit: bool = False):
        """Add an error to stats."""
        self.errors_count += 1
        if is_rate_limit:
            self.rate_limit_hits += 1


class ClaudeClient:
    """Client for interacting with Claude API."""
    
    # Token costs per model (input, output) per 1K tokens in USD
    MODEL_COSTS = {
        "claude-3-sonnet-20240229": (0.003, 0.015),
        "claude-3-opus-20240229": (0.015, 0.075),
        "claude-3-haiku-20240307": (0.00025, 0.00125),
        "claude-3-5-sonnet-20240620": (0.003, 0.015),
    }
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, 
                 default_timeout: int = 120, max_retries: int = 3):
        """Initialize Claude client.
        
        Args:
            api_key: Anthropic API key
            base_url: Optional custom base URL
            default_timeout: Default request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self.usage_stats = UsageStats()
        
        # Initialize async client
        client_kwargs = {"api_key": api_key, "timeout": default_timeout}
        if base_url:
            client_kwargs["base_url"] = base_url
        
        self._client = AsyncAnthropic(**client_kwargs)
        
        # Rate limiting
        self._last_request_time = 0
        self._min_request_interval = 0.1  # Minimum seconds between requests

    async def close(self):
        """Close the Claude client and cleanup resources.

        This is a cleanup method for lifecycle management.
        The AsyncAnthropic client handles its own cleanup internally.
        """
        # The AsyncAnthropic client doesn't require explicit cleanup
        # This method exists for compatibility with container lifecycle
        pass

    async def create_summary(self, 
                            prompt: str,
                            system_prompt: str,
                            options: ClaudeOptions) -> ClaudeResponse:
        """Create a summary using Claude API.
        
        Args:
            prompt: User prompt with content to summarize
            system_prompt: System prompt with instructions
            options: API request options
            
        Returns:
            ClaudeResponse with generated summary
            
        Raises:
            ClaudeAPIError: If API request fails
            TokenLimitExceededError: If response exceeds token limit
            ModelUnavailableError: If requested model is unavailable
        """
        # Apply rate limiting
        await self._apply_rate_limiting()
        
        # Validate model
        if options.model not in self.MODEL_COSTS:
            available_models = ", ".join(self.MODEL_COSTS.keys())
            raise ModelUnavailableError(
                options.model,
                context={"available_models": available_models}
            )
        
        # Prepare request parameters
        request_params = self._build_request_params(prompt, system_prompt, options)
        
        # Execute request with retries
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._make_request(request_params, attempt)
                
                # Process successful response
                claude_response = self._process_response(response, options.model)
                
                # Update usage stats
                cost = self._calculate_cost(claude_response)
                self.usage_stats.add_request(claude_response, cost)
                
                return claude_response
                
            except anthropic.RateLimitError as e:
                self.usage_stats.add_error(is_rate_limit=True)
                
                if attempt < self.max_retries:
                    retry_after = self._extract_retry_after(e)
                    await asyncio.sleep(retry_after)
                    continue
                
                raise RateLimitError(
                    api_name="Claude",
                    retry_after=retry_after,
                    limit_type="requests"
                )
                
            except anthropic.AuthenticationError as e:
                self.usage_stats.add_error()
                raise AuthenticationError("Claude", str(e))
                
            except anthropic.APITimeoutError as e:
                self.usage_stats.add_error()
                
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                raise TimeoutError("Claude", self.default_timeout)
                
            except anthropic.APIConnectionError as e:
                self.usage_stats.add_error()
                
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                
                raise NetworkError("Claude", str(e))
                
            except anthropic.BadRequestError as e:
                self.usage_stats.add_error()
                
                # Check for specific error types
                error_message = str(e)
                if "maximum context length" in error_message.lower():
                    raise ClaudeAPIError(
                        message="Prompt exceeds maximum context length",
                        api_error_code="context_length_exceeded"
                    )
                
                raise ClaudeAPIError(
                    message=f"Bad request: {error_message}",
                    api_error_code="bad_request"
                )
                
            except Exception as e:
                self.usage_stats.add_error()
                
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                
                raise ClaudeAPIError(
                    message=f"Unexpected error: {str(e)}",
                    api_error_code="unexpected_error",
                    cause=e
                )
        
        # Should not reach here due to loop logic
        raise ClaudeAPIError("Max retries exceeded", "max_retries_exceeded")
    
    async def health_check(self) -> bool:
        """Check if Claude API is accessible.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Simple test request
            options = ClaudeOptions(max_tokens=10)
            await self.create_summary(
                prompt="Say hello",
                system_prompt="You are a helpful assistant.",
                options=options
            )
            return True
        except Exception:
            return False
    
    def get_usage_stats(self) -> UsageStats:
        """Get current usage statistics."""
        return self.usage_stats
    
    def estimate_cost(self, input_tokens: int, output_tokens: int, 
                     model: str) -> float:
        """Estimate cost for token usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens  
            model: Model name
            
        Returns:
            Estimated cost in USD
        """
        if model not in self.MODEL_COSTS:
            return 0.0
        
        input_cost, output_cost = self.MODEL_COSTS[model]
        
        # Costs are per 1K tokens
        total_cost = (input_tokens * input_cost + output_tokens * output_cost) / 1000
        return round(total_cost, 6)
    
    async def _apply_rate_limiting(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)
        
        self._last_request_time = time.time()
    
    def _build_request_params(self, prompt: str, system_prompt: str, 
                             options: ClaudeOptions) -> Dict[str, Any]:
        """Build request parameters for Claude API."""
        params = {
            "model": options.model,
            "max_tokens": options.max_tokens,
            "temperature": options.temperature,
            "system": system_prompt,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        if options.top_p is not None:
            params["top_p"] = options.top_p
        
        if options.top_k is not None:
            params["top_k"] = options.top_k
        
        if options.stop_sequences:
            params["stop_sequences"] = options.stop_sequences
        
        if options.stream:
            params["stream"] = True
        
        return params
    
    async def _make_request(self, params: Dict[str, Any], attempt: int) -> Any:
        """Make the actual API request."""
        return await self._client.messages.create(**params)
    
    def _process_response(self, response: Any, model: str) -> ClaudeResponse:
        """Process API response into ClaudeResponse object."""
        # Extract content from response
        content = ""
        if hasattr(response, 'content') and response.content:
            if isinstance(response.content, list) and len(response.content) > 0:
                content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            else:
                content = str(response.content)
        
        # Extract usage information
        usage = {}
        if hasattr(response, 'usage'):
            usage = {
                "input_tokens": getattr(response.usage, 'input_tokens', 0),
                "output_tokens": getattr(response.usage, 'output_tokens', 0)
            }
        
        return ClaudeResponse(
            content=content,
            model=model,
            usage=usage,
            stop_reason=getattr(response, 'stop_reason', 'end_turn'),
            response_id=getattr(response, 'id', '')
        )
    
    def _calculate_cost(self, response: ClaudeResponse) -> float:
        """Calculate cost for a response."""
        return self.estimate_cost(
            response.input_tokens,
            response.output_tokens,
            response.model
        )
    
    def _extract_retry_after(self, error: Exception) -> int:
        """Extract retry-after value from rate limit error."""
        # Try to extract from error message or headers
        error_str = str(error)
        
        # Look for patterns like "retry after 60 seconds"
        import re
        match = re.search(r'retry.+?(\d+).+?second', error_str, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Default retry after
        return 60