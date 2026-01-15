"""
Schema validator for PATH files and prompt templates.

Validates:
- PATH file structure and syntax
- Prompt template content
- Security (injection prevention)
- File size and encoding
"""

import re
import logging
from typing import Dict, Any, List, Optional
import yaml

from .models import ValidationResult, SchemaVersion

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates prompt templates and PATH files against versioned schemas."""

    # Security patterns to detect and block
    DANGEROUS_PATTERNS = [
        r'<script',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'on\w+\s*=',  # Event handlers (onclick, onerror, etc.)
        r'\{\{.*\}\}',  # Template injection (Jinja2)
        r'\$\{.*\}',  # Template injection (JS)
        r'eval\(',  # Code evaluation
        r'exec\(',  # Code execution
        r'__import__',  # Python imports
        r'\.\./',  # Path traversal
        r'\.\.//',  # Path traversal (double slash)
    ]

    MAX_FILE_SIZE = 100 * 1024  # 100KB
    MAX_PATH_LENGTH = 500
    ALLOWED_EXTENSIONS = ['.md']

    def __init__(self):
        """Initialize the schema validator."""
        pass

    def validate_path_file(
        self,
        path_content: str,
        version: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate PATH file structure and syntax.

        Args:
            path_content: Raw YAML content of PATH file
            version: Expected schema version (auto-detected if None)

        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResult(is_valid=True)

        # Check file size
        if len(path_content) > self.MAX_FILE_SIZE:
            result.add_error(
                f"PATH file exceeds maximum size ({self.MAX_FILE_SIZE} bytes)"
            )
            return result

        # Parse YAML
        try:
            data = yaml.safe_load(path_content)
        except yaml.YAMLError as e:
            result.add_error(f"Invalid YAML syntax: {e}")
            return result

        if not isinstance(data, dict):
            result.add_error("PATH file must be a YAML object")
            return result

        # Validate version field
        if 'version' not in data:
            result.add_error("Missing required field: version")
            return result

        file_version = data['version']
        if file_version not in ['v1', 'v2']:
            result.add_error(f"Unsupported schema version: {file_version}")
            return result

        if version and file_version != version:
            result.add_error(
                f"Version mismatch: expected {version}, got {file_version}"
            )

        # Validate based on version
        if file_version == 'v1':
            self._validate_v1_schema(data, result)
        elif file_version == 'v2':
            self._validate_v2_schema(data, result)

        return result

    def _validate_v1_schema(self, data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate v1 PATH file schema."""
        # Check required fields
        if 'routes' not in data:
            result.add_error("Missing required field: routes")
            return

        routes = data['routes']
        if not isinstance(routes, dict):
            result.add_error("'routes' must be a dictionary")
            return

        # Validate each route
        for route_name, path_template in routes.items():
            # Route name validation
            if not re.match(r'^[a-z_][a-z0-9_]*$', route_name):
                result.add_error(
                    f"Invalid route name '{route_name}': "
                    "must be lowercase alphanumeric with underscores"
                )

            # Path template validation
            if not isinstance(path_template, str):
                result.add_error(
                    f"Route '{route_name}' path must be a string"
                )
                continue

            self._validate_path_template(path_template, result, route_name)

        # Validate fallback_chain if present
        if 'fallback_chain' in data:
            fallback_chain = data['fallback_chain']
            if not isinstance(fallback_chain, list):
                result.add_error("'fallback_chain' must be a list")
            else:
                for route_ref in fallback_chain:
                    if route_ref not in routes:
                        result.add_error(
                            f"Fallback chain references undefined route: '{route_ref}'"
                        )

        # Validate variables if present
        if 'variables' in data:
            variables = data['variables']
            if not isinstance(variables, dict):
                result.add_error("'variables' must be a dictionary")

    def _validate_v2_schema(self, data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate v2 PATH file schema (future)."""
        result.add_warning("v2 schema validation not fully implemented yet")
        # For now, validate as v1
        self._validate_v1_schema(data, result)

    def _validate_path_template(
        self,
        path_template: str,
        result: ValidationResult,
        route_name: str = ""
    ) -> None:
        """Validate a path template string."""
        # Check length
        if len(path_template) > self.MAX_PATH_LENGTH:
            result.add_error(
                f"Route '{route_name}' path exceeds maximum length ({self.MAX_PATH_LENGTH})"
            )

        # Check for path traversal
        if '..' in path_template:
            result.add_error(
                f"Route '{route_name}' contains path traversal (..)"
            )

        # Check for absolute paths
        if path_template.startswith('/'):
            result.add_error(
                f"Route '{route_name}' must not be an absolute path"
            )

        # Check file extension
        # Extract the part after last {variable} to check extension
        parts = re.split(r'\{[^}]+\}', path_template)
        last_part = parts[-1] if parts else path_template

        if last_part and not any(last_part.endswith(ext) for ext in self.ALLOWED_EXTENSIONS):
            result.add_warning(
                f"Route '{route_name}' should end with {self.ALLOWED_EXTENSIONS[0]} extension"
            )

        # Validate template variables
        variables = re.findall(r'\{([^}]+)\}', path_template)
        for var in variables:
            if not re.match(r'^[a-z_][a-z0-9_]*$', var):
                result.add_error(
                    f"Route '{route_name}' has invalid variable name '{{{var}}}': "
                    "must be lowercase alphanumeric with underscores"
                )

    def validate_prompt_template(
        self,
        template: str,
        version: str = "v1"
    ) -> ValidationResult:
        """
        Validate prompt template content.

        Args:
            template: Prompt template content
            version: Schema version

        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResult(is_valid=True)

        # Check file size
        if len(template) > self.MAX_FILE_SIZE:
            result.add_error(
                f"Template exceeds maximum size ({self.MAX_FILE_SIZE} bytes)"
            )
            return result

        # Check encoding (try to encode as UTF-8)
        try:
            template.encode('utf-8')
        except UnicodeEncodeError as e:
            result.add_error(f"Template contains invalid UTF-8: {e}")
            return result

        # Security checks
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, template, re.IGNORECASE):
                result.add_error(
                    f"Template contains potentially dangerous pattern: {pattern}"
                )

        # Validate template variables
        variables = re.findall(r'\{([^}]+)\}', template)
        for var in variables:
            if not re.match(r'^[a-z_][a-z0-9_]*$', var):
                result.add_warning(
                    f"Template variable '{{{var}}}' uses non-standard naming"
                )

        return result

    def sanitize_template(self, template: str) -> str:
        """
        Remove potentially dangerous content from template.

        Args:
            template: Raw template content

        Returns:
            Sanitized template
        """
        sanitized = template

        # Remove dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

        return sanitized

    def validate_path(self, path: str) -> bool:
        """
        Ensure path is safe (no traversal, no absolute paths).

        Args:
            path: File path to validate

        Returns:
            True if path is safe

        Raises:
            ValueError: If path is invalid
        """
        if '..' in path:
            raise ValueError("Invalid path: path traversal detected")

        if path.startswith('/'):
            raise ValueError("Invalid path: absolute paths not allowed")

        # Ensure path is within allowed directories
        allowed_dirs = ['prompts/', 'variants/', 'includes/']
        if not any(path.startswith(d) for d in allowed_dirs):
            raise ValueError(
                f"Path must start with one of: {allowed_dirs}"
            )

        return True
