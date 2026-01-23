"""
Error log routes for dashboard API.

Provides endpoints for viewing and managing operational errors.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from ..auth import get_current_user
from ..models import (
    ErrorLogsResponse,
    ErrorLogItem,
    ErrorLogDetail,
    ErrorCountsResponse,
    ResolveErrorRequest,
    ErrorResponse,
)
from . import get_discord_bot

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_error_repository():
    """Get error repository instance."""
    try:
        from ...data import get_error_repository as _get_repo
        return await _get_repo()
    except RuntimeError:
        return None


def _check_guild_access(guild_id: str, user: dict):
    """Check user has access to guild."""
    if guild_id not in user.get("guilds", []):
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "You don't have permission to view this guild"},
        )


def _get_channel_name(guild_id: str, channel_id: Optional[str]) -> Optional[str]:
    """Get channel name from guild."""
    if not channel_id:
        return None
    bot = get_discord_bot()
    if not bot or not bot.client:
        return None
    guild = bot.client.get_guild(int(guild_id))
    if not guild:
        return None
    channel = guild.get_channel(int(channel_id))
    return channel.name if channel else None


def _error_to_list_item(error, guild_id: Optional[str] = None) -> ErrorLogItem:
    """Convert ErrorLog to API list item."""
    channel_name = None
    if guild_id and error.channel_id:
        channel_name = _get_channel_name(guild_id, error.channel_id)

    return ErrorLogItem(
        id=error.id,
        guild_id=error.guild_id,
        channel_id=error.channel_id,
        channel_name=channel_name,
        error_type=error.error_type.value if hasattr(error.error_type, 'value') else error.error_type,
        severity=error.severity.value if hasattr(error.severity, 'value') else error.severity,
        error_code=error.error_code,
        message=error.message,
        operation=error.operation,
        created_at=error.created_at,
        is_resolved=error.is_resolved,
    )


def _error_to_detail(error, guild_id: Optional[str] = None) -> ErrorLogDetail:
    """Convert ErrorLog to API detail response."""
    channel_name = None
    if guild_id and error.channel_id:
        channel_name = _get_channel_name(guild_id, error.channel_id)

    return ErrorLogDetail(
        id=error.id,
        guild_id=error.guild_id,
        channel_id=error.channel_id,
        channel_name=channel_name,
        error_type=error.error_type.value if hasattr(error.error_type, 'value') else error.error_type,
        severity=error.severity.value if hasattr(error.severity, 'value') else error.severity,
        error_code=error.error_code,
        message=error.message,
        details=error.details,
        operation=error.operation,
        user_id=error.user_id,
        stack_trace=error.stack_trace,
        created_at=error.created_at,
        resolved_at=error.resolved_at,
        resolution_notes=error.resolution_notes,
    )


@router.get(
    "/guilds/{guild_id}/errors",
    response_model=ErrorLogsResponse,
    summary="List errors",
    description="Get recent errors for a guild with optional filtering.",
    responses={
        403: {"model": ErrorResponse, "description": "No permission"},
    },
)
async def list_errors(
    guild_id: str = Path(..., description="Discord guild ID"),
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    include_resolved: bool = Query(False, description="Include resolved errors"),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    user: dict = Depends(get_current_user),
):
    """List errors for a guild."""
    _check_guild_access(guild_id, user)

    error_repo = await get_error_repository()
    if not error_repo:
        return ErrorLogsResponse(errors=[], total=0, unresolved_count=0)

    # Convert string filters to enums
    from ...models.error_log import ErrorType, ErrorSeverity
    type_filter = None
    severity_filter = None

    if error_type:
        try:
            type_filter = ErrorType(error_type)
        except ValueError:
            pass

    if severity:
        try:
            severity_filter = ErrorSeverity(severity)
        except ValueError:
            pass

    # Fetch errors
    errors = await error_repo.get_errors_by_guild(
        guild_id=guild_id,
        limit=limit,
        error_type=type_filter,
        severity=severity_filter,
        include_resolved=include_resolved,
    )

    # Count unresolved
    all_errors = await error_repo.get_errors_by_guild(
        guild_id=guild_id,
        limit=1000,
        include_resolved=False,
    )
    unresolved_count = len(all_errors)

    error_items = [_error_to_list_item(e, guild_id) for e in errors]

    return ErrorLogsResponse(
        errors=error_items,
        total=len(errors),
        unresolved_count=unresolved_count,
    )


@router.get(
    "/guilds/{guild_id}/errors/counts",
    response_model=ErrorCountsResponse,
    summary="Get error counts",
    description="Get error counts grouped by type for the last N hours.",
    responses={
        403: {"model": ErrorResponse, "description": "No permission"},
    },
)
async def get_error_counts(
    guild_id: str = Path(..., description="Discord guild ID"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    user: dict = Depends(get_current_user),
):
    """Get error counts by type."""
    _check_guild_access(guild_id, user)

    error_repo = await get_error_repository()
    if not error_repo:
        return ErrorCountsResponse(counts={}, total=0, period_hours=hours)

    counts = await error_repo.get_error_counts(guild_id=guild_id, hours=hours)
    total = sum(counts.values())

    return ErrorCountsResponse(
        counts=counts,
        total=total,
        period_hours=hours,
    )


@router.get(
    "/guilds/{guild_id}/errors/{error_id}",
    response_model=ErrorLogDetail,
    summary="Get error details",
    description="Get full details of a specific error.",
    responses={
        403: {"model": ErrorResponse, "description": "No permission"},
        404: {"model": ErrorResponse, "description": "Error not found"},
    },
)
async def get_error(
    guild_id: str = Path(..., description="Discord guild ID"),
    error_id: str = Path(..., description="Error ID"),
    user: dict = Depends(get_current_user),
):
    """Get error details."""
    _check_guild_access(guild_id, user)

    error_repo = await get_error_repository()
    if not error_repo:
        raise HTTPException(
            status_code=503,
            detail={"code": "DATABASE_UNAVAILABLE", "message": "Database not available"},
        )

    error = await error_repo.get_error(error_id)
    if not error or error.guild_id != guild_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Error not found"},
        )

    return _error_to_detail(error, guild_id)


@router.post(
    "/guilds/{guild_id}/errors/{error_id}/resolve",
    response_model=ErrorLogDetail,
    summary="Resolve error",
    description="Mark an error as resolved with optional notes.",
    responses={
        403: {"model": ErrorResponse, "description": "No permission"},
        404: {"model": ErrorResponse, "description": "Error not found"},
    },
)
async def resolve_error(
    body: ResolveErrorRequest,
    guild_id: str = Path(..., description="Discord guild ID"),
    error_id: str = Path(..., description="Error ID"),
    user: dict = Depends(get_current_user),
):
    """Resolve an error."""
    _check_guild_access(guild_id, user)

    error_repo = await get_error_repository()
    if not error_repo:
        raise HTTPException(
            status_code=503,
            detail={"code": "DATABASE_UNAVAILABLE", "message": "Database not available"},
        )

    # Verify error exists and belongs to guild
    error = await error_repo.get_error(error_id)
    if not error or error.guild_id != guild_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Error not found"},
        )

    # Resolve the error
    success = await error_repo.resolve_error(error_id, body.notes)
    if not success:
        raise HTTPException(
            status_code=500,
            detail={"code": "RESOLVE_FAILED", "message": "Failed to resolve error"},
        )

    # Return updated error
    error = await error_repo.get_error(error_id)
    return _error_to_detail(error, guild_id)
