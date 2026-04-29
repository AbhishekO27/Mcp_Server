"""
GitHub Analytics MCP Server

Exposes GitHub repository data as AI-accessible tools via the
Model Context Protocol (MCP), built with FastMCP.

Tools available:
  - list_repositories       → list all repos for the authenticated user
  - get_repository          → detailed info for a single repo
  - get_commits             → recent commits for a repo
  - get_pull_requests       → open/closed/all PRs for a repo
  - get_issues              → open/closed issues for a repo
  - get_file_content        → raw content of a file in a repo
  - get_workflow_runs       → recent GitHub Actions runs for a repo
  - check_rate_limit        → current API rate limit status
"""

import base64
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastmcp import FastMCP, Context

from github_client import GitHubClient, GitHubNotFoundError, GitHubRateLimitError, GitHubAuthError
from models import (
    Repo, RepoDetail, Commit, PullRequest,
    Issue, FileContent, WorkflowRun, RateLimitInfo,
)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: create / teardown the HTTP client once per server lifetime
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Initialise shared resources and expose them via MCP context."""
    logger.info("Starting GitHub Analytics MCP Server…")
    client = GitHubClient()
    try:
        yield {"github": client}
    finally:
        logger.info("Shutting down — closing HTTP client.")
        await client.close()


# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="GitHub Analytics MCP Server",
    version="2.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helper: consistent error wrapping so Claude gets readable messages
# ---------------------------------------------------------------------------

def _github_error(e: Exception) -> str:
    if isinstance(e, GitHubNotFoundError):
        return f"Not found: {e}"
    if isinstance(e, GitHubRateLimitError):
        return f"Rate limit hit: {e}"
    if isinstance(e, GitHubAuthError):
        return f"Auth error: {e}"
    return f"Unexpected error: {e}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_repositories(
    ctx: Context,
    sort: str = "updated",
    limit: int = 20,
) -> list[Repo]:
    """
    List GitHub repositories for the authenticated user.

    Args:
        sort:  Sort order — 'updated' | 'created' | 'pushed' | 'full_name'.
        limit: Maximum number of repositories to return (1–100).
    """
    github: GitHubClient = ctx.request_context.lifespan_context["github"]
    try:
        raw = await github.get_repositories(sort=sort, per_page=min(limit, 100))
        return [
            Repo(
                name=r["name"],
                private=r["private"],
                stargazers_count=r["stargazers_count"],
                forks_count=r["forks_count"],
                language=r.get("language"),
                description=r.get("description"),
                html_url=r["html_url"],
                open_issues_count=r["open_issues_count"],
                updated_at=r.get("updated_at"),
            )
            for r in raw
        ]
    except Exception as e:
        logger.error("list_repositories failed: %s", e)
        raise ValueError(_github_error(e)) from e


@mcp.tool()
async def get_repository(ctx: Context, repo: str) -> RepoDetail:
    """
    Get detailed information about a single repository.

    Args:
        repo: Repository name (e.g. 'my-project').
    """
    github: GitHubClient = ctx.request_context.lifespan_context["github"]
    try:
        r = await github.get_repository(repo)
        return RepoDetail(
            name=r["name"],
            private=r["private"],
            stargazers_count=r["stargazers_count"],
            forks_count=r["forks_count"],
            language=r.get("language"),
            description=r.get("description"),
            html_url=r["html_url"],
            open_issues_count=r["open_issues_count"],
            updated_at=r.get("updated_at"),
            default_branch=r.get("default_branch", "main"),
            size=r.get("size", 0),
            topics=r.get("topics", []),
            clone_url=r.get("clone_url"),
        )
    except Exception as e:
        logger.error("get_repository(%s) failed: %s", repo, e)
        raise ValueError(_github_error(e)) from e


@mcp.tool()
async def get_commits(
    ctx: Context,
    repo: str,
    limit: int = 10,
) -> list[Commit]:
    """
    Get recent commits for a repository.

    Args:
        repo:  Repository name.
        limit: Number of commits to return (1–100).
    """
    github: GitHubClient = ctx.request_context.lifespan_context["github"]
    try:
        raw = await github.get_commits(repo, per_page=min(limit, 100))
        return [
            Commit(
                sha=c["sha"],
                message=c["commit"]["message"].split("\n")[0],  # first line only
                author=c["commit"]["author"]["name"],
                author_email=c["commit"]["author"]["email"],
                date=c["commit"]["author"]["date"],
                url=c["html_url"],
            )
            for c in raw
        ]
    except Exception as e:
        logger.error("get_commits(%s) failed: %s", repo, e)
        raise ValueError(_github_error(e)) from e


@mcp.tool()
async def get_pull_requests(
    ctx: Context,
    repo: str,
    state: str = "open",
    limit: int = 10,
) -> list[PullRequest]:
    """
    Get pull requests for a repository.

    Args:
        repo:  Repository name.
        state: 'open' | 'closed' | 'all'.
        limit: Number of PRs to return (1–100).
    """
    github: GitHubClient = ctx.request_context.lifespan_context["github"]
    try:
        raw = await github.get_pull_requests(repo, state=state, per_page=min(limit, 100))
        return [
            PullRequest(
                number=p["number"],
                title=p["title"],
                state=p["state"],
                url=p["html_url"],
                author=p["user"]["login"],
                created_at=p["created_at"],
                updated_at=p["updated_at"],
                body=p.get("body"),
                labels=[lbl["name"] for lbl in p.get("labels", [])],
                draft=p.get("draft", False),
            )
            for p in raw
        ]
    except Exception as e:
        logger.error("get_pull_requests(%s) failed: %s", repo, e)
        raise ValueError(_github_error(e)) from e


@mcp.tool()
async def get_issues(
    ctx: Context,
    repo: str,
    state: str = "open",
    limit: int = 10,
) -> list[Issue]:
    """
    Get issues for a repository (pull requests are excluded).

    Args:
        repo:  Repository name.
        state: 'open' | 'closed' | 'all'.
        limit: Number of issues to return (1–100).
    """
    github: GitHubClient = ctx.request_context.lifespan_context["github"]
    try:
        raw = await github.get_issues(repo, state=state, per_page=min(limit, 100))
        return [
            Issue(
                number=i["number"],
                title=i["title"],
                state=i["state"],
                url=i["html_url"],
                author=i["user"]["login"],
                created_at=i["created_at"],
                updated_at=i["updated_at"],
                body=i.get("body"),
                labels=[lbl["name"] for lbl in i.get("labels", [])],
                comments=i.get("comments", 0),
            )
            for i in raw
        ]
    except Exception as e:
        logger.error("get_issues(%s) failed: %s", repo, e)
        raise ValueError(_github_error(e)) from e


@mcp.tool()
async def get_file_content(
    ctx: Context,
    repo: str,
    path: str,
    ref: str = "main",
) -> FileContent:
    """
    Get the decoded text content of a file in a repository.

    Args:
        repo: Repository name.
        path: File path within the repository (e.g. 'src/main.py').
        ref:  Branch, tag, or commit SHA (default: 'main').
    """
    github: GitHubClient = ctx.request_context.lifespan_context["github"]
    try:
        raw = await github.get_file_content(repo, path, ref=ref)
        # Decode base64 content returned by GitHub
        if raw.get("encoding") == "base64":
            raw["content"] = base64.b64decode(raw["content"]).decode("utf-8", errors="replace")
        return FileContent(
            name=raw["name"],
            path=raw["path"],
            sha=raw["sha"],
            size=raw["size"],
            encoding="utf-8",
            content=raw["content"],
            html_url=raw["html_url"],
        )
    except Exception as e:
        logger.error("get_file_content(%s/%s) failed: %s", repo, path, e)
        raise ValueError(_github_error(e)) from e


@mcp.tool()
async def get_workflow_runs(
    ctx: Context,
    repo: str,
    limit: int = 5,
) -> list[WorkflowRun]:
    """
    Get recent GitHub Actions workflow runs for a repository.

    Args:
        repo:  Repository name.
        limit: Number of runs to return (1–100).
    """
    github: GitHubClient = ctx.request_context.lifespan_context["github"]
    try:
        data = await github.get_workflow_runs(repo, per_page=min(limit, 100))
        return [
            WorkflowRun(
                id=r["id"],
                name=r.get("name"),
                status=r["status"],
                conclusion=r.get("conclusion"),
                head_branch=r.get("head_branch", ""),
                head_sha=r.get("head_sha", ""),
                html_url=r["html_url"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in data.get("workflow_runs", [])
        ]
    except Exception as e:
        logger.error("get_workflow_runs(%s) failed: %s", repo, e)
        raise ValueError(_github_error(e)) from e


@mcp.tool()
async def check_rate_limit(ctx: Context) -> RateLimitInfo:
    """
    Check the current GitHub API rate limit status.
    Use this to diagnose 403 errors or plan request-heavy operations.
    """
    github: GitHubClient = ctx.request_context.lifespan_context["github"]
    try:
        data = await github.get_rate_limit()
        core = data["rate"]
        return RateLimitInfo(
            limit=core["limit"],
            remaining=core["remaining"],
            reset=core["reset"],
            used=core["used"],
        )
    except Exception as e:
        logger.error("check_rate_limit failed: %s", e)
        raise ValueError(_github_error(e)) from e


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()