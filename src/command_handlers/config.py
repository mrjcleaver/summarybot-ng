"""
Configuration command handlers for managing bot settings.
"""

import logging
from typing import Optional, List
import discord

from .base import BaseCommandHandler
from .utils import format_error_response, format_success_response, format_info_response
from ..exceptions import UserError, create_error_context
from ..models.summary import SummaryOptions, SummaryLength

logger = logging.getLogger(__name__)


class ConfigCommandHandler(BaseCommandHandler):
    """Handler for configuration commands."""

    def __init__(self, summarization_engine, permission_manager=None,
                 config_manager=None):
        """
        Initialize config command handler.

        Args:
            summarization_engine: SummarizationEngine instance
            permission_manager: PermissionManager instance (optional)
            config_manager: ConfigManager instance for guild configs
        """
        super().__init__(summarization_engine, permission_manager)
        self.config_manager = config_manager

        # Config commands typically need admin permissions
        self.requires_admin = True

    async def _execute_command(self, interaction: discord.Interaction, **kwargs) -> None:
        """Execute configuration command."""
        pass

    async def _check_admin_permission(self, interaction: discord.Interaction) -> bool:
        """
        Check if user has admin permissions.

        Args:
            interaction: Discord interaction object

        Returns:
            True if user is admin
        """
        if not interaction.guild:
            return False

        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False

        return member.guild_permissions.administrator or member.guild_permissions.manage_guild

    async def handle_config_view(self, interaction: discord.Interaction) -> None:
        """
        Display current configuration for the guild.

        Args:
            interaction: Discord interaction object
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            guild_id = str(interaction.guild_id)

            # Get guild config
            if self.config_manager:
                bot_config = self.config_manager.get_current_config()
                config = bot_config.get_guild_config(guild_id) if bot_config else None
            else:
                config = None

            # Create embed with current settings
            embed = discord.Embed(
                title="⚙️ Current Configuration",
                description=f"Settings for {interaction.guild.name}",
                color=0x4A90E2
            )

            if config:
                # Enabled channels
                if config.enabled_channels:
                    channels_text = "\n".join([f"<#{ch_id}>" for ch_id in config.enabled_channels[:10]])
                    if len(config.enabled_channels) > 10:
                        channels_text += f"\n... and {len(config.enabled_channels) - 10} more"
                else:
                    channels_text = "All channels enabled"

                embed.add_field(
                    name="📝 Enabled Channels",
                    value=channels_text,
                    inline=False
                )

                # Excluded channels
                if config.excluded_channels:
                    excluded_text = "\n".join([f"<#{ch_id}>" for ch_id in config.excluded_channels[:10]])
                    if len(config.excluded_channels) > 10:
                        excluded_text += f"\n... and {len(config.excluded_channels) - 10} more"
                    embed.add_field(
                        name="🚫 Excluded Channels",
                        value=excluded_text,
                        inline=False
                    )

                # Permission settings
                perm_settings = config.permission_settings
                if perm_settings.require_permissions:
                    perm_text = "🔒 **Restricted** - Only allowed users can use commands\n"
                    if perm_settings.allowed_users:
                        perm_text += f"Allowed users: {len(perm_settings.allowed_users)}"
                    else:
                        perm_text += "⚠️ No users allowed - use `/config permissions require:false` to fix"
                else:
                    perm_text = "🔓 **Open** - All users can use commands"

                embed.add_field(
                    name="🔐 Permission Requirements",
                    value=perm_text,
                    inline=False
                )

                # Cross-channel summary role
                if config.cross_channel_summary_role_name:
                    embed.add_field(
                        name="🔀 Cross-Channel Summaries",
                        value=f"✅ Enabled for role: **{config.cross_channel_summary_role_name}**",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="🔀 Cross-Channel Summaries",
                        value="❌ Disabled (use `/config set-cross-channel-role` to enable)",
                        inline=False
                    )

                # Default summary options
                if config.default_summary_options:
                    options = config.default_summary_options
                    options_text = (
                        f"Length: {options.summary_length.value}\n"
                        f"Include bots: {options.include_bots}\n"
                        f"Min messages: {options.min_messages}\n"
                        f"Model: {options.claude_model}"
                    )
                    embed.add_field(
                        name="🎯 Default Summary Options",
                        value=options_text,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Status",
                    value="Using default configuration",
                    inline=False
                )

            embed.set_footer(text="Use /config set to modify settings")

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Failed to view config: {e}")
            await self.send_error_response(interaction, e)

    async def handle_config_set_channels(self,
                                        interaction: discord.Interaction,
                                        action: str,
                                        channels: str) -> None:
        """
        Configure enabled/excluded channels.

        Args:
            interaction: Discord interaction object
            action: "enable" or "exclude"
            channels: Comma-separated channel mentions or IDs
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if action not in ("enable", "exclude"):
                raise UserError(
                    message=f"Invalid action: {action}",
                    error_code="INVALID_ACTION",
                    user_message="Action must be 'enable' or 'exclude'."
                )

            # Parse channel IDs
            channel_ids = []
            for part in channels.split(','):
                part = part.strip()
                # Extract ID from mention or use as-is
                if part.startswith('<#') and part.endswith('>'):
                    channel_id = part[2:-1]
                elif part.isdigit():
                    channel_id = part
                else:
                    continue

                # Verify channel exists
                channel = interaction.guild.get_channel(int(channel_id))
                if channel:
                    channel_ids.append(channel_id)

            if not channel_ids:
                raise UserError(
                    message="No valid channels provided",
                    error_code="NO_CHANNELS",
                    user_message="No valid channels found. Please mention channels or provide channel IDs."
                )

            # Update configuration
            if self.config_manager:
                guild_id = str(interaction.guild_id)
                bot_config = self.config_manager.get_current_config()
                if not bot_config:
                    raise UserError(
                        message="Configuration not loaded",
                        error_code="NO_CONFIG",
                        user_message="Bot configuration is not available."
                    )
                config = bot_config.get_guild_config(guild_id)

                if action == "enable":
                    config.enabled_channels = channel_ids
                    config.excluded_channels = []
                else:  # exclude
                    config.excluded_channels = channel_ids

                await self.config_manager.update_guild_config(guild_id, config)

            # Send success response
            channel_mentions = [f"<#{ch_id}>" for ch_id in channel_ids]
            action_word = "enabled" if action == "enable" else "excluded"

            embed = format_success_response(
                title="Configuration Updated",
                description=f"Successfully {action_word} channels for summaries.",
                fields={
                    "Channels": "\n".join(channel_mentions)
                }
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except UserError as e:
            await self.send_error_response(interaction, e)
        except Exception as e:
            logger.exception(f"Failed to set channels: {e}")
            await self.send_error_response(interaction, e)

    async def handle_config_set_defaults(self,
                                        interaction: discord.Interaction,
                                        length: Optional[str] = None,
                                        include_bots: Optional[bool] = None,
                                        min_messages: Optional[int] = None,
                                        model: Optional[str] = None) -> None:
        """
        Set default summary options for the guild.

        Args:
            interaction: Discord interaction object
            length: Default summary length
            include_bots: Whether to include bot messages by default
            min_messages: Minimum messages required for summary
            model: Claude model to use
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if not self.config_manager:
                raise UserError(
                    message="Config manager not available",
                    error_code="NO_CONFIG_MANAGER",
                    user_message="Configuration management is not available."
                )

            guild_id = str(interaction.guild_id)
            bot_config = self.config_manager.get_current_config()
            if not bot_config:
                raise UserError(
                    message="Configuration not loaded",
                    error_code="NO_CONFIG",
                    user_message="Bot configuration is not available."
                )
            config = bot_config.get_guild_config(guild_id)

            # Update options
            if not config.default_summary_options:
                config.default_summary_options = SummaryOptions()

            updated_fields = []

            if length:
                try:
                    config.default_summary_options.summary_length = SummaryLength(length.lower())
                    updated_fields.append(f"Length: {length}")
                except ValueError:
                    raise UserError(
                        message=f"Invalid length: {length}",
                        error_code="INVALID_LENGTH",
                        user_message="Length must be 'brief', 'detailed', or 'comprehensive'."
                    )

            if include_bots is not None:
                config.default_summary_options.include_bots = include_bots
                updated_fields.append(f"Include bots: {include_bots}")

            if min_messages is not None:
                if min_messages < 1 or min_messages > 1000:
                    raise UserError(
                        message=f"Invalid min_messages: {min_messages}",
                        error_code="INVALID_MIN_MESSAGES",
                        user_message="Minimum messages must be between 1 and 1000."
                    )
                config.default_summary_options.min_messages = min_messages
                updated_fields.append(f"Min messages: {min_messages}")

            if model:
                # Validate model name
                valid_models = [
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307"
                ]
                if model not in valid_models:
                    raise UserError(
                        message=f"Invalid model: {model}",
                        error_code="INVALID_MODEL",
                        user_message=f"Model must be one of: {', '.join(valid_models)}"
                    )
                config.default_summary_options.claude_model = model
                updated_fields.append(f"Model: {model}")

            if not updated_fields:
                raise UserError(
                    message="No fields to update",
                    error_code="NO_UPDATES",
                    user_message="Please specify at least one setting to update."
                )

            # Save configuration
            await self.config_manager.update_guild_config(guild_id, config)

            # Send success response
            embed = format_success_response(
                title="Default Settings Updated",
                description="Successfully updated default summary options.",
                fields={"Updated": "\n".join(updated_fields)}
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except UserError as e:
            await self.send_error_response(interaction, e)
        except Exception as e:
            logger.exception(f"Failed to set defaults: {e}")
            await self.send_error_response(interaction, e)

    async def handle_config_reset(self, interaction: discord.Interaction) -> None:
        """
        Reset guild configuration to defaults.

        Args:
            interaction: Discord interaction object
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if not self.config_manager:
                raise UserError(
                    message="Config manager not available",
                    error_code="NO_CONFIG_MANAGER",
                    user_message="Configuration management is not available."
                )

            guild_id = str(interaction.guild_id)

            # Reset to default configuration
            from ..config.settings import GuildConfig
            default_config = GuildConfig(guild_id=guild_id)

            await self.config_manager.update_guild_config(guild_id, default_config)

            embed = format_success_response(
                title="Configuration Reset",
                description="All settings have been reset to defaults.",
                fields={
                    "Note": "All custom channel settings and default options have been cleared."
                }
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.exception(f"Failed to reset config: {e}")
            await self.send_error_response(interaction, e)

    async def handle_config_set_cross_channel_role(self,
                                                   interaction: discord.Interaction,
                                                   role_name: Optional[str] = None) -> None:
        """
        Set or clear the cross-channel summary role.

        Args:
            interaction: Discord interaction object
            role_name: Name of role allowed to use cross-channel summaries (None to disable)
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if not self.config_manager:
                raise UserError(
                    message="Config manager not available",
                    error_code="NO_CONFIG_MANAGER",
                    user_message="Configuration management is not available."
                )

            guild_id = str(interaction.guild_id)
            bot_config = self.config_manager.get_current_config()
            if not bot_config:
                raise UserError(
                    message="Configuration not loaded",
                    error_code="NO_CONFIG",
                    user_message="Bot configuration is not available."
                )
            config = bot_config.get_guild_config(guild_id)

            # Validate role exists if provided
            if role_name:
                role = discord.utils.get(interaction.guild.roles, name=role_name)
                if not role:
                    raise UserError(
                        message=f"Role not found: {role_name}",
                        error_code="ROLE_NOT_FOUND",
                        user_message=f"Role **{role_name}** not found in this server. Please check the role name."
                    )

                config.cross_channel_summary_role_name = role_name
                status_msg = f"Users with the **{role_name}** role can now summarize other channels."
            else:
                config.cross_channel_summary_role_name = None
                status_msg = "Cross-channel summaries have been disabled."

            # Save configuration
            await self.config_manager.update_guild_config(guild_id, config)

            # Send success response
            embed = format_success_response(
                title="Cross-Channel Configuration Updated",
                description=status_msg,
                fields={
                    "Feature": "Cross-Channel Summaries",
                    "Status": "Enabled" if role_name else "Disabled",
                    "Required Role": role_name or "N/A"
                }
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except UserError as e:
            await self.send_error_response(interaction, e)
        except Exception as e:
            logger.exception(f"Failed to set cross-channel role: {e}")
            await self.send_error_response(interaction, e)

    async def handle_config_permissions(self,
                                       interaction: discord.Interaction,
                                       require: bool) -> None:
        """
        Toggle permission requirements for bot commands.

        Args:
            interaction: Discord interaction
            require: Whether to require permissions (True) or allow everyone (False)
        """
        try:
            # Check admin permission
            if not await self._check_admin_permission(interaction):
                await self.send_permission_error(interaction)
                return

            if not self.config_manager:
                raise UserError(
                    message="Config manager not available",
                    error_code="NO_CONFIG_MANAGER",
                    user_message="Configuration management is not available."
                )

            guild_id = str(interaction.guild_id)
            bot_config = self.config_manager.get_current_config()
            if not bot_config:
                raise UserError(
                    message="Configuration not loaded",
                    error_code="NO_CONFIG",
                    user_message="Bot configuration is not available."
                )
            config = bot_config.get_guild_config(guild_id)

            # Update permission requirement
            config.permission_settings.require_permissions = require

            # Save configuration
            await self.config_manager.update_guild_config(guild_id, config)

            # Send success response
            status_msg = (
                "All users can now use bot commands." if not require
                else "Only allowed users can use bot commands."
            )

            embed = format_success_response(
                title="Permission Requirements Updated",
                description=status_msg,
                fields={
                    "Require Permissions": "Yes" if require else "No",
                    "Effect": "Restricted access" if require else "Open access"
                }
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except UserError as e:
            await self.send_error_response(interaction, e)
        except Exception as e:
            logger.exception(f"Failed to update permission settings: {e}")
            await self.send_error_response(interaction, e)
