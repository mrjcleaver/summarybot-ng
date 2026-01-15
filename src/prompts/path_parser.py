"""
PATH file parser for flexible prompt routing.

Parses PATH files and resolves template patterns to specific file paths
based on context variables.
"""

import re
import hashlib
import logging
from typing import List, Dict, Any, Optional
import yaml

from .models import (
    PromptContext,
    PATHFileConfig,
    PATHFileRoute,
    SchemaVersion,
    ValidationResult
)
from .schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


class PATHFileParser:
    """
    Parses PATH files and resolves prompt templates.

    Features:
    - Template variable substitution: {category}, {channel}, {type}
    - Pattern matching with priority calculation
    - Fallback chain construction
    - Security sanitization
    """

    def __init__(self, validator: Optional[SchemaValidator] = None):
        """
        Initialize the PATH file parser.

        Args:
            validator: Schema validator instance (creates one if not provided)
        """
        self.validator = validator or SchemaValidator()

    def parse(self, path_content: str) -> PATHFileConfig:
        """
        Parse PATH file content into structured configuration.

        Args:
            path_content: Raw YAML content of PATH file

        Returns:
            PATHFileConfig object

        Raises:
            ValueError: If PATH file is invalid
        """
        # Validate first
        validation = self.validator.validate_path_file(path_content)
        if not validation.is_valid:
            error_msg = "; ".join(validation.errors)
            raise ValueError(f"Invalid PATH file: {error_msg}")

        # Parse YAML
        data = yaml.safe_load(path_content)

        # Parse version
        version_str = data['version']
        version = SchemaVersion.V1 if version_str == 'v1' else SchemaVersion.V2

        # Parse routes
        routes = {}
        routes_data = data.get('routes', {})
        for route_name, path_template in routes_data.items():
            routes[route_name] = PATHFileRoute(
                name=route_name,
                path_template=path_template,
                priority=self._calculate_priority(path_template)
            )

        # Parse fallback chain
        fallback_chain = data.get('fallback_chain', list(routes.keys()))

        # Parse variables
        variables = data.get('variables', {})

        # Parse config
        config = data.get('config', {})

        return PATHFileConfig(
            version=version,
            routes=routes,
            fallback_chain=fallback_chain,
            variables=variables,
            config=config
        )

    def resolve_paths(
        self,
        path_config: PATHFileConfig,
        context: PromptContext
    ) -> List[str]:
        """
        Resolve PATH template into ordered list of file paths to try.

        Args:
            path_config: Parsed PATH configuration
            context: Prompt context with variables

        Returns:
            List of file paths in priority order

        Example:
            Template: "prompts/{category}/{channel}.md"
            Context: {category: "meeting", channel: "standup"}

            Returns: [
                "prompts/meeting/standup.md",
                "prompts/meeting/default.md",
                "prompts/default.md"
            ]
        """
        resolved_paths = []
        context_dict = context.to_dict()

        # Try each route in fallback chain order
        for route_name in path_config.fallback_chain:
            if route_name not in path_config.routes:
                logger.warning(f"Route '{route_name}' not found in routes")
                continue

            route = path_config.routes[route_name]

            # Try to resolve this route
            try:
                paths = self._resolve_route(route, context_dict)
                resolved_paths.extend(paths)
            except Exception as e:
                logger.error(
                    f"Failed to resolve route '{route_name}': {e}",
                    exc_info=True
                )

        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in resolved_paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)

        return unique_paths

    def _resolve_route(
        self,
        route: PATHFileRoute,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Resolve a single route to one or more file paths.

        Args:
            route: Route definition
            context: Context variables

        Returns:
            List of resolved file paths (specific to general)
        """
        paths = []
        template = route.path_template

        # Extract variables from template
        variables = re.findall(r'\{([^}]+)\}', template)

        # Generate primary path with all variables substituted
        primary_path = template
        for var in variables:
            value = context.get(var, "")
            if value:
                # Sanitize value (remove special characters, path traversal)
                value = self._sanitize_value(str(value))
                primary_path = primary_path.replace(f"{{{var}}}", value)

        # Only add if all variables were resolved
        if '{' not in primary_path:
            paths.append(primary_path)

        # Generate fallback paths by replacing variables with "default"
        if len(variables) > 0:
            # Try replacing each variable with "default" one at a time
            for i in range(len(variables)):
                fallback_path = template
                for j, var in enumerate(variables):
                    if j < len(variables) - 1 - i:
                        # Use actual value
                        value = context.get(var, "")
                        if value:
                            value = self._sanitize_value(str(value))
                            fallback_path = fallback_path.replace(f"{{{var}}}", value)
                    else:
                        # Use "default"
                        fallback_path = fallback_path.replace(f"{{{var}}}", "default")

                if '{' not in fallback_path and fallback_path not in paths:
                    paths.append(fallback_path)

        return paths

    def _sanitize_value(self, value: str) -> str:
        """
        Sanitize a context value for use in file paths.

        Args:
            value: Raw value

        Returns:
            Sanitized value safe for file paths
        """
        # Convert to lowercase
        value = value.lower()

        # Remove or replace special characters
        value = re.sub(r'[^\w\-]', '_', value)

        # Remove path traversal
        value = value.replace('..', '')
        value = value.replace('/', '_')
        value = value.replace('\\', '_')

        # Limit length
        if len(value) > 100:
            value = value[:100]

        return value

    def _calculate_priority(self, path_template: str) -> int:
        """
        Calculate priority for a path template.

        More specific templates (more variables) get higher priority.

        Args:
            path_template: Template string

        Returns:
            Priority score (higher = more specific)
        """
        # Count number of variables
        variable_count = len(re.findall(r'\{([^}]+)\}', path_template))

        # Count path depth
        path_depth = path_template.count('/')

        # Calculate priority: more variables and deeper paths are higher priority
        priority = (variable_count * 100) + (path_depth * 10)

        return priority

    def compute_context_hash(self, context: PromptContext) -> str:
        """
        Generate stable hash from context for cache key.

        Args:
            context: Prompt context

        Returns:
            SHA256 hash (first 16 chars)
        """
        # Create stable string representation
        context_str = (
            f"{context.category}:"
            f"{context.channel_name or ''}:"
            f"{context.summary_type}:"
            f"{context.guild_id}"
        )

        # Hash it
        hash_obj = hashlib.sha256(context_str.encode())
        return hash_obj.hexdigest()[:16]
