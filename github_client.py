"""
GitHub REST API client with async support, rate-limit handling, and retry logic.
"""

import os
import asyncio
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class GitHubRateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""
    pass


class GitHubNotFoundError(Exception):
    """Raised when a GitHub resource is not found."""
    pass


class GitHubAuthError(Exception):
    """Raised when authentication fails."""
    pass


def _handle_response(response: httpx.Response) -> Any:
    """Centralized response handler with meaningful error messages."""
    if response.status_code == 401:
        raise GitHubAuthError(
            "Authentication failed. Check your GITHUB_TOKEN environment variable."
        )
    if response.status_code == 403:
        remaining = response.headers.get("X-RateLimit-Remaining", "unknown")
        reset = response.headers.get("X-RateLimit-Reset", "unknown")
        raise GitHubRateLimitError(
            f"Rate limit exceeded. Remaining: {remaining}. Reset at: {reset}"
        )
    if response.status_code == 404:
        raise GitHubNotFoundError(
            f"Resource not found: {response.url}"
        )
    response.raise_for_status()
    return response.json()


class GitHubClient:
    """
    Async GitHub REST API client.

    Handles authentication, rate limiting, retries, and error normalisation.
    """

    def __init__(self) -> None:
        token = os.getenv("GITHUB_TOKEN")
        self.username = os.getenv("GITHUB_USERNAME")

        if not token:
            raise EnvironmentError("GITHUB_TOKEN environment variable is not set.")
        if not self.username:
            raise EnvironmentError("GITHUB_USERNAME environment variable is not set.")

        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=httpx.Timeout(10.0),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    async def close(self):
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _get(self, path: str, params: dict | None = None) -> Any:
        logger.debug("GET %s params=%s", path, params)
        response = await self._client.get(path, params=params)
        return _handle_response(response)

    # ------------------------------------------------------------------
    # Repositories
    # ------------------------------------------------------------------

    async def get_repositories(self, sort: str = "updated", per_page: int = 30) -> list[dict]:
        """List public repositories for the authenticated user."""
        return await self._get(
            f"/users/{self.username}/repos",
            params={"sort": sort, "per_page": per_page},
        )

    async def get_repository(self, repo: str) -> dict:
        """Get detailed info for a single repository."""
        return await self._get(f"/repos/{self.username}/{repo}")

    # ------------------------------------------------------------------
    # Commits
    # ------------------------------------------------------------------

    async def get_commits(self, repo: str, per_page: int = 20) -> list[dict]:
        """Get recent commits for a repository."""
        return await self._get(
            f"/repos/{self.username}/{repo}/commits",
            params={"per_page": per_page},
        )

    # ------------------------------------------------------------------
    # Pull Requests
    # ------------------------------------------------------------------

    async def get_pull_requests(self, repo: str, state: str = "open", per_page: int = 20) -> list[dict]:
        """Get pull requests for a repository."""
        return await self._get(
            f"/repos/{self.username}/{repo}/pulls",
            params={"state": state, "per_page": per_page},
        )

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    async def get_issues(self, repo: str, state: str = "open", per_page: int = 20) -> list[dict]:
        """Get issues for a repository (excludes pull requests)."""
        data = await self._get(
            f"/repos/{self.username}/{repo}/issues",
            params={"state": state, "per_page": per_page},
        )
        # GitHub issues endpoint returns PRs too — filter them out
        return [i for i in data if "pull_request" not in i]

    # ------------------------------------------------------------------
    # File Content
    # ------------------------------------------------------------------

    async def get_file_content(self, repo: str, path: str, ref: str = "main") -> dict:
        """Get the content of a file in a repository."""
        return await self._get(
            f"/repos/{self.username}/{repo}/contents/{path}",
            params={"ref": ref},
        )

    # ------------------------------------------------------------------
    # Code Search
    # ------------------------------------------------------------------

    async def search_code(self, query: str, repo: str | None = None) -> dict:
        """Search code across GitHub (or within a specific repo)."""
        scoped_query = f"{query} repo:{self.username}/{repo}" if repo else f"{query} user:{self.username}"
        return await self._get(
            "/search/code",
            params={"q": scoped_query, "per_page": 10},
        )

    # ------------------------------------------------------------------
    # GitHub Actions
    # ------------------------------------------------------------------

    async def get_workflow_runs(self, repo: str, per_page: int = 10) -> dict:
        """Get recent GitHub Actions workflow runs for a repository."""
        return await self._get(
            f"/repos/{self.username}/{repo}/actions/runs",
            params={"per_page": per_page},
        )

    # ------------------------------------------------------------------
    # Rate Limit
    # ------------------------------------------------------------------

    async def get_rate_limit(self) -> dict:
        """Get current GitHub API rate limit status."""
        return await self._get("/rate_limit")