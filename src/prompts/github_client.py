"""
GitHub repository client for fetching prompt files.

Features:
- Fetch files from public/private GitHub repos
- Rate limit handling
- Retry logic with exponential backoff
- Repository validation
"""

import asyncio
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
import aiohttp
import re

from .models import ValidationResult, RepoContents
from .schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


class GitHubRateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""
    pass


class GitHubTimeoutError(Exception):
    """Raised when GitHub API request times out."""
    pass


class GitHubRepositoryClient:
    """
    Fetches prompt files from GitHub repositories.

    Handles:
    - Public and private repositories
    - Rate limiting (5000/hr authenticated, 60/hr unauthenticated)
    - Retries with exponential backoff
    - Content validation
    """

    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

    MAX_FILE_SIZE = 100 * 1024  # 100KB
    TIMEOUT_SECONDS = 10
    MAX_RETRIES = 3
    RATE_LIMIT_BUFFER = 100  # Reserve requests

    def __init__(
        self,
        auth_token: Optional[str] = None,
        validator: Optional[SchemaValidator] = None
    ):
        """
        Initialize GitHub client.

        Args:
            auth_token: Optional GitHub Personal Access Token
            validator: Schema validator instance
        """
        self.auth_token = auth_token
        self.validator = validator or SchemaValidator()
        self._rate_limit_remaining = None
        self._rate_limit_reset_at = None

    async def fetch_file(
        self,
        repo_url: str,
        file_path: str,
        branch: str = "main"
    ) -> Optional[str]:
        """
        Fetch a single file from a GitHub repository.

        Args:
            repo_url: GitHub repository URL
            file_path: Path to file within repo
            branch: Branch name (default: main)

        Returns:
            File content as string, or None if not found

        Raises:
            GitHubRateLimitError: If rate limit exceeded
            GitHubTimeoutError: If request times out
        """
        # Parse repo URL to get owner and repo name
        owner, repo = self._parse_repo_url(repo_url)
        if not owner or not repo:
            logger.error(f"Invalid repository URL: {repo_url}")
            return None

        # Construct raw file URL
        url = f"{self.GITHUB_RAW_BASE}/{owner}/{repo}/{branch}/{file_path}"

        # Fetch with retries
        for attempt in range(self.MAX_RETRIES):
            try:
                content = await self._fetch_with_timeout(url)

                # Validate file size
                if len(content) > self.MAX_FILE_SIZE:
                    logger.error(
                        f"File {file_path} exceeds size limit "
                        f"({len(content)} > {self.MAX_FILE_SIZE})"
                    )
                    return None

                return content

            except asyncio.TimeoutError:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Timeout fetching {file_path}, "
                        f"retrying in {wait_time}s (attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise GitHubTimeoutError(
                        f"Failed to fetch {file_path} after {self.MAX_RETRIES} attempts"
                    )

            except aiohttp.ClientError as e:
                logger.error(f"HTTP error fetching {file_path}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return None

        return None

    async def fetch_repo_contents(
        self,
        repo_url: str,
        branch: str = "main"
    ) -> Optional[RepoContents]:
        """
        Fetch key files from a repository.

        Args:
            repo_url: GitHub repository URL
            branch: Branch name

        Returns:
            RepoContents object with PATH file and prompts
        """
        contents = RepoContents()

        # Fetch PATH file
        path_file = await self.fetch_file(repo_url, "PATH", branch)
        if not path_file:
            logger.warning(f"No PATH file found in {repo_url}")
            return None

        contents.path_file = path_file

        # Fetch schema version file
        schema_version = await self.fetch_file(
            repo_url,
            "schema-version.txt",
            branch
        )
        if schema_version:
            contents.schema_version = schema_version.strip()

        return contents

    async def validate_repo_structure(
        self,
        repo_url: str,
        branch: str = "main"
    ) -> ValidationResult:
        """
        Validate that repository has required structure.

        Args:
            repo_url: GitHub repository URL
            branch: Branch name

        Returns:
            ValidationResult with any errors
        """
        result = ValidationResult(is_valid=True)

        # Check if PATH file exists
        path_file = await self.fetch_file(repo_url, "PATH", branch)
        if not path_file:
            result.add_error("Repository does not contain a PATH file")
            return result

        # Validate PATH file
        path_validation = self.validator.validate_path_file(path_file)
        if not path_validation.is_valid:
            for error in path_validation.errors:
                result.add_error(f"PATH file validation error: {error}")

        return result

    def _parse_repo_url(self, repo_url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse GitHub repository URL to extract owner and repo name.

        Args:
            repo_url: GitHub repository URL

        Returns:
            Tuple of (owner, repo) or (None, None) if invalid

        Examples:
            "https://github.com/owner/repo" -> ("owner", "repo")
            "github.com/owner/repo" -> ("owner", "repo")
            "owner/repo" -> ("owner", "repo")
        """
        # Remove protocol if present
        url = repo_url.replace('https://', '').replace('http://', '')

        # Remove github.com prefix if present
        url = url.replace('github.com/', '')

        # Remove trailing .git if present
        url = url.replace('.git', '')

        # Remove trailing slash
        url = url.rstrip('/')

        # Split into parts
        parts = url.split('/')

        if len(parts) >= 2:
            return parts[0], parts[1]

        return None, None

    async def _fetch_with_timeout(self, url: str) -> str:
        """
        Fetch URL content with timeout.

        Args:
            url: URL to fetch

        Returns:
            Response content as string

        Raises:
            asyncio.TimeoutError: If request times out
            aiohttp.ClientError: If HTTP error occurs
        """
        headers = {}
        if self.auth_token:
            headers['Authorization'] = f'token {self.auth_token}'

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    # Check rate limit headers
                    if 'X-RateLimit-Remaining' in response.headers:
                        self._rate_limit_remaining = int(
                            response.headers['X-RateLimit-Remaining']
                        )

                    if 'X-RateLimit-Reset' in response.headers:
                        reset_timestamp = int(response.headers['X-RateLimit-Reset'])
                        self._rate_limit_reset_at = datetime.fromtimestamp(
                            reset_timestamp
                        )

                    # Check if rate limited
                    if response.status == 403:
                        if self._rate_limit_remaining is not None and self._rate_limit_remaining < self.RATE_LIMIT_BUFFER:
                            raise GitHubRateLimitError(
                                f"Rate limit exceeded. Resets at {self._rate_limit_reset_at}"
                            )

                    response.raise_for_status()
                    return await response.text()

            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching {url}")
                raise

    @property
    def rate_limit_remaining(self) -> Optional[int]:
        """Get remaining GitHub API rate limit."""
        return self._rate_limit_remaining

    @property
    def rate_limit_reset_at(self) -> Optional[datetime]:
        """Get when GitHub API rate limit resets."""
        return self._rate_limit_reset_at
