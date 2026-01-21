"""
Summary routes for dashboard API.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from ..auth import get_current_user
from ..models import (
    SummariesResponse,
    SummaryListItem,
    SummaryDetailResponse,
    ActionItemResponse,
    TechnicalTermResponse,
    ParticipantResponse,
    SummaryMetadataResponse,
    GenerateSummaryRequest,
    GenerateSummaryResponse,
    TaskStatusResponse,
    ErrorResponse,
)
from . import get_discord_bot, get_summarization_engine

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory task tracking (replace with proper task queue in production)
_generation_tasks: dict[str, dict] = {}


def _check_guild_access(guild_id: str, user: dict):
    """Check user has access to guild."""
    if guild_id not in user.get("guilds", []):
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "You don't have permission to manage this guild"},
        )


def _get_guild_or_404(guild_id: str):
    """Get guild from bot or raise 404."""
    bot = get_discord_bot()
    if not bot or not bot.client:
        raise HTTPException(
            status_code=503,
            detail={"code": "BOT_UNAVAILABLE", "message": "Discord bot not available"},
        )

    guild = bot.client.get_guild(int(guild_id))
    if not guild:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Guild not found"},
        )

    return guild


@router.get(
    "/guilds/{guild_id}/summaries",
    response_model=SummariesResponse,
    summary="List summaries",
    description="Get paginated list of summaries for a guild.",
    responses={
        403: {"model": ErrorResponse, "description": "No permission"},
        404: {"model": ErrorResponse, "description": "Guild not found"},
    },
)
async def list_summaries(
    guild_id: str = Path(..., description="Discord guild ID"),
    channel_id: Optional[str] = Query(None, description="Filter by channel ID"),
    start_date: Optional[datetime] = Query(None, description="Filter from date"),
    end_date: Optional[datetime] = Query(None, description="Filter to date"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    user: dict = Depends(get_current_user),
):
    """List summaries for a guild."""
    _check_guild_access(guild_id, user)
    _get_guild_or_404(guild_id)

    # TODO: Fetch from database
    # For now, return empty list
    return SummariesResponse(
        summaries=[],
        total=0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/guilds/{guild_id}/summaries/{summary_id}",
    response_model=SummaryDetailResponse,
    summary="Get summary details",
    description="Get full details of a specific summary.",
    responses={
        403: {"model": ErrorResponse, "description": "No permission"},
        404: {"model": ErrorResponse, "description": "Summary not found"},
    },
)
async def get_summary(
    guild_id: str = Path(..., description="Discord guild ID"),
    summary_id: str = Path(..., description="Summary ID"),
    user: dict = Depends(get_current_user),
):
    """Get summary details."""
    _check_guild_access(guild_id, user)

    # TODO: Fetch from database
    raise HTTPException(
        status_code=404,
        detail={"code": "NOT_FOUND", "message": "Summary not found"},
    )


@router.post(
    "/guilds/{guild_id}/summaries/generate",
    response_model=GenerateSummaryResponse,
    summary="Generate summary",
    description="Start generating a new summary for specified channels.",
    responses={
        403: {"model": ErrorResponse, "description": "No permission"},
        404: {"model": ErrorResponse, "description": "Guild not found"},
    },
)
async def generate_summary(
    body: GenerateSummaryRequest,
    guild_id: str = Path(..., description="Discord guild ID"),
    user: dict = Depends(get_current_user),
):
    """Generate a new summary."""
    _check_guild_access(guild_id, user)
    guild = _get_guild_or_404(guild_id)
    bot = get_discord_bot()
    engine = get_summarization_engine()

    if not engine:
        raise HTTPException(
            status_code=503,
            detail={"code": "ENGINE_UNAVAILABLE", "message": "Summarization engine not available"},
        )

    # Validate channels exist in guild
    guild_channels = {str(c.id) for c in guild.text_channels}
    invalid_channels = set(body.channel_ids) - guild_channels
    if invalid_channels:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_CHANNELS",
                "message": f"Invalid channel IDs: {', '.join(invalid_channels)}",
            },
        )

    # Create task ID
    import secrets
    task_id = f"gen_{secrets.token_urlsafe(16)}"

    # Calculate time range
    now = datetime.utcnow()
    if body.time_range.type == "hours":
        start_time = now - timedelta(hours=body.time_range.value or 24)
        end_time = now
    elif body.time_range.type == "days":
        start_time = now - timedelta(days=body.time_range.value or 1)
        end_time = now
    else:
        start_time = body.time_range.start or (now - timedelta(hours=24))
        end_time = body.time_range.end or now

    # Store task info
    _generation_tasks[task_id] = {
        "status": "processing",
        "guild_id": guild_id,
        "channel_ids": body.channel_ids,
        "started_at": now,
        "summary_id": None,
        "error": None,
    }

    # Start generation in background
    async def run_generation():
        try:
            from ...message_processing import MessageProcessor

            # Collect messages from all channels
            all_messages = []
            for channel_id in body.channel_ids:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    async for message in channel.history(
                        after=start_time,
                        before=end_time,
                        limit=1000,
                    ):
                        all_messages.append(message)

            if not all_messages:
                _generation_tasks[task_id]["status"] = "failed"
                _generation_tasks[task_id]["error"] = "No messages found in time range"
                return

            # Process messages
            processor = MessageProcessor(bot.client)
            processed = await processor.process_messages(all_messages)

            # Generate summary
            from ...models.summary import SummaryOptions, SummaryLength
            options = SummaryOptions(
                summary_length=SummaryLength(body.options.summary_length if body.options else "detailed"),
                extract_action_items=body.options.include_action_items if body.options else True,
                extract_technical_terms=body.options.include_technical_terms if body.options else True,
            )

            result = await engine.summarize(
                messages=processed,
                options=options,
                guild_id=guild_id,
                channel_id=body.channel_ids[0],  # Primary channel
            )

            _generation_tasks[task_id]["status"] = "completed"
            _generation_tasks[task_id]["summary_id"] = result.id

        except Exception as e:
            logger.error(f"Summary generation failed: {e}", exc_info=True)
            _generation_tasks[task_id]["status"] = "failed"
            _generation_tasks[task_id]["error"] = str(e)

    # Start background task
    asyncio.create_task(run_generation())

    return GenerateSummaryResponse(
        task_id=task_id,
        status="processing",
    )


@router.get(
    "/guilds/{guild_id}/summaries/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Check generation status",
    description="Check the status of a summary generation task.",
    responses={
        403: {"model": ErrorResponse, "description": "No permission"},
        404: {"model": ErrorResponse, "description": "Task not found"},
    },
)
async def get_task_status(
    guild_id: str = Path(..., description="Discord guild ID"),
    task_id: str = Path(..., description="Task ID"),
    user: dict = Depends(get_current_user),
):
    """Get task status."""
    _check_guild_access(guild_id, user)

    task = _generation_tasks.get(task_id)
    if not task or task["guild_id"] != guild_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Task not found"},
        )

    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        summary_id=task.get("summary_id"),
        error=task.get("error"),
    )
