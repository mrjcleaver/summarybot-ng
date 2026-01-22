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
from . import get_discord_bot, get_summarization_engine, get_summary_repository
from ...data.base import SearchCriteria

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
    guild = _get_guild_or_404(guild_id)

    # Query database for summaries
    summary_repo = await get_summary_repository()
    if not summary_repo:
        logger.warning(f"Summary repository not available for guild {guild_id}")
        return SummariesResponse(summaries=[], total=0, limit=limit, offset=offset)

    logger.info(f"Fetching summaries for guild {guild_id}, channel={channel_id}, limit={limit}")

    criteria = SearchCriteria(
        guild_id=guild_id,
        channel_id=channel_id,
        start_time=start_date,
        end_time=end_date,
        limit=limit,
        offset=offset,
        order_by="created_at",
        order_direction="DESC",
    )

    summaries = await summary_repo.find_summaries(criteria)
    total = await summary_repo.count_summaries(criteria)
    logger.info(f"Found {len(summaries)} summaries (total={total}) for guild {guild_id}")

    # Convert to response format
    summary_items = []
    for summary in summaries:
        # Get channel name from guild
        channel_name = None
        if summary.channel_id:
            channel = guild.get_channel(int(summary.channel_id))
            channel_name = channel.name if channel else None

        summary_items.append(
            SummaryListItem(
                id=summary.id,
                channel_id=summary.channel_id,
                channel_name=channel_name,
                start_time=summary.start_time,
                end_time=summary.end_time,
                message_count=summary.message_count,
                preview=summary.summary_text[:200] + "..." if len(summary.summary_text) > 200 else summary.summary_text,
                created_at=summary.created_at,
            )
        )

    return SummariesResponse(
        summaries=summary_items,
        total=total,
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
    guild = _get_guild_or_404(guild_id)

    # Fetch from database
    summary_repo = await get_summary_repository()
    if not summary_repo:
        raise HTTPException(
            status_code=503,
            detail={"code": "DATABASE_UNAVAILABLE", "message": "Database not available"},
        )

    summary = await summary_repo.get_summary(summary_id)
    if not summary or summary.guild_id != guild_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Summary not found"},
        )

    # Get channel name
    channel_name = None
    if summary.channel_id:
        channel = guild.get_channel(int(summary.channel_id))
        channel_name = channel.name if channel else None

    # Convert action items
    action_items = [
        ActionItemResponse(
            description=item.description,
            assignee=item.assignee,
            priority=item.priority.value if hasattr(item.priority, 'value') else item.priority,
            completed=item.completed,
        )
        for item in summary.action_items
    ]

    # Convert technical terms
    technical_terms = [
        TechnicalTermResponse(
            term=term.term,
            definition=term.definition,
            category=term.category,
        )
        for term in summary.technical_terms
    ]

    # Convert participants
    participants = [
        ParticipantResponse(
            user_id=p.user_id,
            display_name=p.display_name,
            message_count=p.message_count,
            key_contributions=p.key_contributions,
        )
        for p in summary.participants
    ]

    # Build metadata
    metadata = SummaryMetadataResponse(
        summary_length=summary.metadata.get("summary_length", "detailed"),
        perspective=summary.metadata.get("perspective", "general"),
        model_used=summary.metadata.get("model_used"),
        tokens_used=summary.metadata.get("tokens_used"),
        generation_time_seconds=summary.metadata.get("generation_time_seconds"),
    )

    return SummaryDetailResponse(
        id=summary.id,
        channel_id=summary.channel_id,
        channel_name=channel_name,
        start_time=summary.start_time,
        end_time=summary.end_time,
        message_count=summary.message_count,
        summary_text=summary.summary_text,
        key_points=summary.key_points,
        action_items=action_items,
        technical_terms=technical_terms,
        participants=participants,
        metadata=metadata,
        created_at=summary.created_at,
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
        logger.info(f"[{task_id}] Starting background summary generation for guild {guild_id}")
        logger.info(f"[{task_id}] Time range: {start_time} to {end_time}")
        logger.info(f"[{task_id}] Channels: {body.channel_ids}")
        try:
            from ...message_processing import MessageProcessor

            # Collect messages from all channels
            all_messages = []
            for channel_id in body.channel_ids:
                channel = guild.get_channel(int(channel_id))
                logger.info(f"[{task_id}] Fetching from channel {channel_id}: {channel.name if channel else 'NOT FOUND'}")
                if channel:
                    msg_count = 0
                    async for message in channel.history(
                        after=start_time,
                        before=end_time,
                        limit=1000,
                    ):
                        all_messages.append(message)
                        msg_count += 1
                    logger.info(f"[{task_id}] Fetched {msg_count} messages from {channel.name}")

            logger.info(f"[{task_id}] Total messages collected: {len(all_messages)}")

            if not all_messages:
                logger.warning(f"[{task_id}] No messages found in time range")
                _generation_tasks[task_id]["status"] = "failed"
                _generation_tasks[task_id]["error"] = "No messages found in time range"
                return

            # Process messages with relaxed minimum for dashboard
            from ...models.summary import SummaryOptions, SummaryLength
            options = SummaryOptions(
                summary_length=SummaryLength(body.options.summary_length if body.options else "detailed"),
                extract_action_items=body.options.include_action_items if body.options else True,
                extract_technical_terms=body.options.include_technical_terms if body.options else True,
                min_messages=1,  # Allow single message summaries from dashboard
            )

            logger.info(f"[{task_id}] Processing {len(all_messages)} messages...")
            processor = MessageProcessor(bot.client)
            processed = await processor.process_messages(all_messages, options)
            logger.info(f"[{task_id}] Processed {len(processed)} messages")

            # Get channel and guild info for context
            primary_channel = guild.get_channel(int(body.channel_ids[0]))
            channel_name = primary_channel.name if primary_channel else "unknown"

            # Calculate time span and participant count
            time_span_hours = (end_time - start_time).total_seconds() / 3600
            unique_authors = {msg.author_id for msg in processed}

            # Create summarization context
            from ...models.summary import SummarizationContext
            context = SummarizationContext(
                channel_name=channel_name,
                guild_name=guild.name,
                total_participants=len(unique_authors),
                time_span_hours=time_span_hours,
            )

            logger.info(f"[{task_id}] Calling summarization engine...")
            result = await engine.summarize_messages(
                messages=processed,
                options=options,
                context=context,
                guild_id=guild_id,
                channel_id=body.channel_ids[0],
            )
            logger.info(f"[{task_id}] Summarization complete, result id: {result.id}")

            # Save summary to database
            logger.info(f"[{task_id}] Getting summary repository...")
            summary_repo = await get_summary_repository()
            if summary_repo:
                logger.info(f"[{task_id}] Saving summary to database...")
                await summary_repo.save_summary(result)
                logger.info(f"[{task_id}] Saved summary {result.id} to database for guild {guild_id}, channel {body.channel_ids[0]}")
            else:
                logger.error(f"[{task_id}] Summary repository not available - summary {result.id} NOT saved!")

            _generation_tasks[task_id]["status"] = "completed"
            _generation_tasks[task_id]["summary_id"] = result.id
            logger.info(f"[{task_id}] Generation task completed successfully")

        except Exception as e:
            logger.error(f"[{task_id}] Summary generation failed: {e}", exc_info=True)
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
