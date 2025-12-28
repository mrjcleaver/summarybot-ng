"""
Role-based access control logic for Summary Bot NG.

This module provides role hierarchy management and role-based permission
resolution for Discord servers.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum
import logging
import discord

from ..models.user import PermissionLevel, UserPermissions

logger = logging.getLogger(__name__)


class RoleHierarchy(Enum):
    """
    Role hierarchy levels for permission evaluation.

    Higher values indicate more permissions.
    """
    NONE = 0
    MEMBER = 1
    MODERATOR = 2
    ADMIN = 3
    OWNER = 4


@dataclass
class RolePermissionMapping:
    """Maps Discord roles to permission levels."""

    role_id: str
    role_name: str
    permission_level: PermissionLevel
    hierarchy_level: RoleHierarchy
    allowed_commands: Set[str] = field(default_factory=set)
    allowed_channels: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "permission_level": self.permission_level.value,
            "hierarchy_level": self.hierarchy_level.value,
            "allowed_commands": list(self.allowed_commands),
            "allowed_channels": list(self.allowed_channels)
        }


class RoleManager:
    """
    Manages role-based access control and permission resolution.

    This class handles Discord role evaluation and maps them to bot-specific
    permission levels.
    """

    def __init__(self):
        """Initialize the role manager."""
        self._role_mappings: Dict[str, RolePermissionMapping] = {}
        logger.debug("RoleManager initialized")

    def register_role_mapping(
        self,
        role_id: str,
        role_name: str,
        permission_level: PermissionLevel,
        hierarchy_level: RoleHierarchy,
        allowed_commands: Optional[Set[str]] = None,
        allowed_channels: Optional[Set[str]] = None
    ) -> None:
        """
        Register a role with its permission mapping.

        Args:
            role_id: Discord role ID
            role_name: Human-readable role name
            permission_level: Permission level to grant
            hierarchy_level: Hierarchy level in role structure
            allowed_commands: Optional set of allowed command names
            allowed_channels: Optional set of allowed channel IDs
        """
        mapping = RolePermissionMapping(
            role_id=role_id,
            role_name=role_name,
            permission_level=permission_level,
            hierarchy_level=hierarchy_level,
            allowed_commands=allowed_commands or set(),
            allowed_channels=allowed_channels or set()
        )

        self._role_mappings[role_id] = mapping
        logger.info(
            f"Registered role mapping: {role_name} ({role_id}) -> "
            f"{permission_level.value}"
        )

    def get_role_mapping(self, role_id: str) -> Optional[RolePermissionMapping]:
        """
        Get the permission mapping for a role.

        Args:
            role_id: Discord role ID

        Returns:
            RolePermissionMapping if found, None otherwise
        """
        return self._role_mappings.get(role_id)

    def resolve_member_permissions(
        self,
        member: discord.Member,
        guild_id: str,
        allowed_roles: List[str],
        admin_roles: List[str]
    ) -> UserPermissions:
        """
        Resolve permissions for a Discord member based on their roles.

        This method evaluates all of a member's roles and determines the
        highest permission level they should have.

        Args:
            member: Discord member object
            guild_id: Guild ID for the permissions
            allowed_roles: List of role IDs that grant base permissions
            admin_roles: List of role IDs that grant admin permissions

        Returns:
            UserPermissions object with resolved permissions
        """
        # Start with no permissions
        permissions = UserPermissions(
            user_id=str(member.id),
            guild_id=guild_id,
            level=PermissionLevel.NONE
        )

        # Check if member is the server owner
        if member.guild.owner_id == member.id:
            permissions.level = PermissionLevel.OWNER
            permissions.can_schedule_summaries = True
            permissions.can_use_webhooks = True
            permissions.can_manage_config = True
            logger.debug(f"Member {member.id} is server owner")
            return permissions

        # Check if member has administrator permission
        if member.guild_permissions.administrator:
            permissions.level = PermissionLevel.ADMIN
            permissions.can_schedule_summaries = True
            permissions.can_use_webhooks = True
            permissions.can_manage_config = True
            logger.debug(f"Member {member.id} has administrator permission")
            return permissions

        # Get member's role IDs
        member_role_ids = [str(role.id) for role in member.roles]

        # Check admin roles
        for role_id in admin_roles:
            if role_id in member_role_ids:
                permissions.level = PermissionLevel.ADMIN
                permissions.can_schedule_summaries = True
                permissions.can_use_webhooks = True
                permissions.can_manage_config = True
                logger.debug(
                    f"Member {member.id} has admin role {role_id}"
                )
                return permissions

        # Check allowed roles
        for role_id in allowed_roles:
            if role_id in member_role_ids:
                # Grant at least SUMMARIZE level
                if permissions.level.value < PermissionLevel.SUMMARIZE.value:
                    permissions.level = PermissionLevel.SUMMARIZE
                    logger.debug(
                        f"Member {member.id} has allowed role {role_id}"
                    )

        # Check custom role mappings
        highest_hierarchy = RoleHierarchy.NONE
        for role in member.roles:
            role_id = str(role.id)
            mapping = self.get_role_mapping(role_id)

            if mapping and mapping.hierarchy_level.value > highest_hierarchy.value:
                highest_hierarchy = mapping.hierarchy_level
                permissions.level = mapping.permission_level

                # Update special permissions based on level
                if mapping.permission_level in [PermissionLevel.ADMIN, PermissionLevel.OWNER]:
                    permissions.can_schedule_summaries = True
                    permissions.can_use_webhooks = True
                    permissions.can_manage_config = True

        logger.debug(
            f"Resolved permissions for member {member.id}: {permissions.level.value}"
        )

        return permissions

    def check_role_hierarchy(
        self,
        actor_roles: List[discord.Role],
        target_roles: List[discord.Role]
    ) -> bool:
        """
        Check if actor's roles are higher than target's roles in hierarchy.

        This is useful for validating if a user can manage another user's
        permissions.

        Args:
            actor_roles: Roles of the user performing the action
            target_roles: Roles of the user being acted upon

        Returns:
            True if actor has higher role hierarchy
        """
        # Get highest hierarchy level for each
        actor_highest = max(
            (self._get_hierarchy_level(str(role.id)) for role in actor_roles),
            default=RoleHierarchy.NONE
        )

        target_highest = max(
            (self._get_hierarchy_level(str(role.id)) for role in target_roles),
            default=RoleHierarchy.NONE
        )

        return actor_highest.value > target_highest.value

    def _get_hierarchy_level(self, role_id: str) -> RoleHierarchy:
        """
        Get hierarchy level for a role.

        Args:
            role_id: Discord role ID

        Returns:
            RoleHierarchy level
        """
        mapping = self.get_role_mapping(role_id)
        if mapping:
            return mapping.hierarchy_level
        return RoleHierarchy.NONE

    def get_required_level_for_command(self, command: str) -> PermissionLevel:
        """
        Get the required permission level for a command.

        Args:
            command: Command name

        Returns:
            Required PermissionLevel
        """
        # Define command requirements
        command_requirements = {
            "summarize": PermissionLevel.SUMMARIZE,
            "quick_summary": PermissionLevel.SUMMARIZE,
            "schedule": PermissionLevel.ADMIN,
            "config": PermissionLevel.ADMIN,
            "webhook": PermissionLevel.ADMIN,
            "permissions": PermissionLevel.OWNER,
            "view": PermissionLevel.READ
        }

        return command_requirements.get(command, PermissionLevel.ADMIN)

    def can_execute_command(
        self,
        user_permissions: UserPermissions,
        command: str
    ) -> bool:
        """
        Check if a user can execute a specific command.

        Args:
            user_permissions: User's permissions
            command: Command to check

        Returns:
            True if user can execute the command
        """
        required_level = self.get_required_level_for_command(command)

        # Define hierarchy for comparison
        level_values = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ: 1,
            PermissionLevel.SUMMARIZE: 2,
            PermissionLevel.ADMIN: 3,
            PermissionLevel.OWNER: 4
        }

        user_level_value = level_values.get(user_permissions.level, 0)
        required_level_value = level_values.get(required_level, 0)

        return user_level_value >= required_level_value

    def list_available_commands(
        self,
        user_permissions: UserPermissions
    ) -> List[str]:
        """
        Get list of commands available to a user.

        Args:
            user_permissions: User's permissions

        Returns:
            List of command names the user can execute
        """
        all_commands = [
            "view",
            "summarize",
            "quick_summary",
            "schedule",
            "config",
            "webhook",
            "permissions"
        ]

        return [
            cmd for cmd in all_commands
            if self.can_execute_command(user_permissions, cmd)
        ]
