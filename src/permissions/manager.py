"""
Main permission manager for Summary Bot NG.

This module handles permission checks, user access validation, and coordination
with Discord's permission system.
"""

from typing import Optional, List
import discord
import logging

from ..config import BotConfig
from ..models.user import UserPermissions, PermissionLevel
from ..exceptions.discord_errors import DiscordPermissionError, ChannelAccessError
from ..exceptions.base import ErrorContext, create_error_context
from .validators import PermissionValidator, ValidationResult
from .roles import RoleManager
from .cache import PermissionCache

logger = logging.getLogger(__name__)


class PermissionManager:
    """
    Manages user permissions and access control for bot operations.

    This class coordinates permission validation, role-based access control,
    and caching to provide efficient permission checks across the bot.
    """

    def __init__(self, config: BotConfig, cache: Optional[PermissionCache] = None):
        """
        Initialize the permission manager.

        Args:
            config: Bot configuration instance
            cache: Optional permission cache instance
        """
        self.config = config
        self.validator = PermissionValidator()
        self.role_manager = RoleManager()
        self.cache = cache or PermissionCache(ttl=config.cache_ttl)

        logger.info("PermissionManager initialized")

    async def check_channel_access(
        self,
        user_id: str,
        channel_id: str,
        guild_id: str
    ) -> bool:
        """
        Check if a user has access to a specific channel.

        This method validates:
        1. Guild configuration allows the channel
        2. User has appropriate permissions
        3. Channel is not in excluded list

        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            guild_id: Discord guild (server) ID

        Returns:
            True if user has access, False otherwise

        Raises:
            ChannelAccessError: If channel access is denied
        """
        # Check cache first
        cache_key = f"channel_access:{guild_id}:{user_id}:{channel_id}"
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for channel access: {cache_key}")
            return cached_result

        try:
            # Get guild configuration
            guild_config = self.config.get_guild_config(guild_id)

            # Check if channel is excluded
            if channel_id in guild_config.excluded_channels:
                logger.info(
                    f"Channel {channel_id} is excluded in guild {guild_id}"
                )
                await self.cache.set(cache_key, False)
                return False

            # Check if there are enabled channels and this is one of them
            if guild_config.enabled_channels:
                if channel_id not in guild_config.enabled_channels:
                    logger.info(
                        f"Channel {channel_id} not in enabled channels for guild {guild_id}"
                    )
                    await self.cache.set(cache_key, False)
                    return False

            # Get user permissions
            user_perms = await self.get_user_permissions(user_id, guild_id)

            # Check channel-specific access
            has_access = user_perms.has_channel_access(channel_id)

            # Cache the result
            await self.cache.set(cache_key, has_access)

            if not has_access:
                logger.info(
                    f"User {user_id} denied access to channel {channel_id} "
                    f"in guild {guild_id}"
                )

            return has_access

        except Exception as e:
            logger.error(
                f"Error checking channel access for user {user_id}, "
                f"channel {channel_id}, guild {guild_id}: {e}"
            )
            # On error, default to denying access
            return False

    async def check_command_permission(
        self,
        user_id: str,
        command: str,
        guild_id: str
    ) -> bool:
        """
        Check if a user has permission to execute a specific command.

        Args:
            user_id: Discord user ID
            command: Command name (e.g., "summarize", "schedule")
            guild_id: Discord guild ID

        Returns:
            True if user can execute the command, False otherwise

        Raises:
            DiscordPermissionError: If user lacks required permissions
        """
        # Check cache first
        cache_key = f"command_perm:{guild_id}:{user_id}:{command}"
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for command permission: {cache_key}")
            return cached_result

        try:
            # Get user permissions
            user_perms = await self.get_user_permissions(user_id, guild_id)

            # Map commands to actions
            command_action_map = {
                "summarize": "create_summaries",
                "quick_summary": "create_summaries",
                "schedule": "schedule_summaries",
                "config": "manage_config",
                "webhook": "use_webhooks",
                "permissions": "manage_permissions"
            }

            action = command_action_map.get(command, command)
            has_permission = user_perms.can_perform_action(action)

            # Special handling for specific commands
            if command == "schedule" and not user_perms.can_schedule_summaries:
                has_permission = False
            elif command == "webhook" and not user_perms.can_use_webhooks:
                has_permission = False
            elif command == "config" and not user_perms.can_manage_config:
                has_permission = False

            # Cache the result
            await self.cache.set(cache_key, has_permission)

            if not has_permission:
                logger.info(
                    f"User {user_id} denied permission for command '{command}' "
                    f"in guild {guild_id}"
                )

            return has_permission

        except Exception as e:
            logger.error(
                f"Error checking command permission for user {user_id}, "
                f"command '{command}', guild {guild_id}: {e}"
            )
            # On error, default to denying permission
            return False

    async def get_user_permissions(
        self,
        user_id: str,
        guild_id: str
    ) -> UserPermissions:
        """
        Get comprehensive permissions for a user in a guild.

        This method aggregates permissions from:
        1. Guild configuration (role-based)
        2. User-specific permissions
        3. Default permissions

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID

        Returns:
            UserPermissions object with aggregated permissions
        """
        # Check cache first
        cache_key = f"user_perms:{guild_id}:{user_id}"
        cached_perms = await self.cache.get(cache_key)
        if cached_perms is not None:
            logger.debug(f"Cache hit for user permissions: {cache_key}")
            return cached_perms

        try:
            # Get guild configuration
            guild_config = self.config.get_guild_config(guild_id)
            permission_settings = guild_config.permission_settings

            # Initialize with default permissions
            user_perms = UserPermissions(
                user_id=user_id,
                guild_id=guild_id,
                level=PermissionLevel.NONE
            )

            # If permissions are not required, grant basic access
            if not permission_settings.require_permissions:
                user_perms.level = PermissionLevel.SUMMARIZE
                logger.debug(
                    f"Permissions not required for guild {guild_id}, "
                    f"granting SUMMARIZE level"
                )

            # Check if user is in allowed users list
            if user_id in permission_settings.allowed_users:
                user_perms.level = PermissionLevel.SUMMARIZE
                logger.debug(f"User {user_id} in allowed users list")

            # Note: Role-based permissions would require Discord member object
            # This is a basic implementation - full implementation would need
            # Discord client integration to check roles

            # Cache the result
            await self.cache.set(cache_key, user_perms)

            return user_perms

        except Exception as e:
            logger.error(
                f"Error getting user permissions for user {user_id}, "
                f"guild {guild_id}: {e}"
            )
            # Return minimal permissions on error
            return UserPermissions(
                user_id=user_id,
                guild_id=guild_id,
                level=PermissionLevel.NONE
            )

    async def validate_discord_member_permissions(
        self,
        member: discord.Member,
        channel: discord.TextChannel
    ) -> ValidationResult:
        """
        Validate Discord member permissions using Discord's permission system.

        This method checks Discord's native permissions rather than bot-specific
        permissions.

        Args:
            member: Discord member object
            channel: Discord text channel object

        Returns:
            ValidationResult indicating if validation passed and any errors
        """
        return self.validator.validate_summarize_permission(member, channel)

    async def check_bot_permissions(
        self,
        bot_member: discord.Member,
        channel: discord.TextChannel,
        required_permissions: List[str]
    ) -> bool:
        """
        Check if the bot has required permissions in a channel.

        Args:
            bot_member: Discord member object for the bot
            channel: Discord text channel
            required_permissions: List of required permission names

        Returns:
            True if bot has all required permissions
        """
        try:
            permissions = channel.permissions_for(bot_member)

            permission_checks = {
                "read_messages": permissions.read_messages,
                "read_message_history": permissions.read_message_history,
                "send_messages": permissions.send_messages,
                "embed_links": permissions.embed_links,
                "attach_files": permissions.attach_files,
                "manage_messages": permissions.manage_messages,
                "administrator": permissions.administrator
            }

            for perm in required_permissions:
                if perm in permission_checks:
                    if not permission_checks[perm]:
                        logger.warning(
                            f"Bot lacks permission '{perm}' in channel {channel.id}"
                        )
                        return False

            return True

        except Exception as e:
            logger.error(f"Error checking bot permissions: {e}")
            return False

    async def invalidate_cache(
        self,
        user_id: Optional[str] = None,
        guild_id: Optional[str] = None
    ) -> None:
        """
        Invalidate permission cache for a user or entire guild.

        Args:
            user_id: Optional user ID to invalidate (invalidates all if None)
            guild_id: Optional guild ID to invalidate (invalidates all if None)
        """
        if user_id and guild_id:
            pattern = f"*:{guild_id}:{user_id}:*"
        elif guild_id:
            pattern = f"*:{guild_id}:*"
        elif user_id:
            pattern = f"*:*:{user_id}:*"
        else:
            pattern = "*"

        await self.cache.invalidate_pattern(pattern)
        logger.info(f"Invalidated permission cache with pattern: {pattern}")

    async def update_user_permissions(
        self,
        user_id: str,
        guild_id: str,
        permissions: UserPermissions
    ) -> None:
        """
        Update cached permissions for a user.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            permissions: New permissions to cache
        """
        cache_key = f"user_perms:{guild_id}:{user_id}"
        await self.cache.set(cache_key, permissions)

        # Invalidate related caches
        await self.cache.invalidate_pattern(f"*:{guild_id}:{user_id}:*")

        logger.info(f"Updated permissions for user {user_id} in guild {guild_id}")
