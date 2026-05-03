"""
Tests for the GitHub Analytics MCP Server tools.

Each tool is tested for:
  - Happy path (correct data returned)
  - Error propagation (client errors become ValueError)
"""

import pytest
from unittest.mock import AsyncMock

from server import (
    list_repositories,
    get_repository,
    get_commits,
    get_pull_requests,
    get_issues,
    get_file_content,
    get_workflow_runs,
    check_rate_limit,
)
from github_client import GitHubNotFoundError, GitHubRateLimitError


# ---------------------------------------------------------------------------
# list_repositories
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_repositories_returns_repos(mock_ctx):
    result = await list_repositories(mock_ctx)
    assert len(result) == 1
    assert result[0].name == "awesome-project"
    assert result[0].stars == 42
    assert result[0].language == "Python"


@pytest.mark.asyncio
async def test_list_repositories_propagates_error(mock_ctx):
    mock_ctx.request_context.lifespan_context["github"].get_repositories.side_effect = (
        GitHubRateLimitError("Rate limit exceeded")
    )
    with pytest.raises(ValueError, match="Rate limit"):
        await list_repositories(mock_ctx)


# ---------------------------------------------------------------------------
# get_repository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_repository_returns_detail(mock_ctx):
    result = await get_repository(mock_ctx, repo="awesome-project")
    assert result.name == "awesome-project"
    assert result.default_branch == "main"
    assert "python" in result.topics


@pytest.mark.asyncio
async def test_get_repository_not_found(mock_ctx):
    mock_ctx.request_context.lifespan_context["github"].get_repository.side_effect = (
        GitHubNotFoundError("Not found")
    )
    with pytest.raises(ValueError, match="Not found"):
        await get_repository(mock_ctx, repo="nonexistent")


# ---------------------------------------------------------------------------
# get_commits
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_commits_returns_commits(mock_ctx):
    result = await get_commits(mock_ctx, repo="awesome-project")
    assert len(result) == 1
    assert result[0].sha == "abc123d"        # abbreviated to 7 chars
    assert result[0].message == "feat: add new feature"  # first line only
    assert result[0].author == "Test User"


@pytest.mark.asyncio
async def test_get_commits_error(mock_ctx):
    mock_ctx.request_context.lifespan_context["github"].get_commits.side_effect = (
        GitHubNotFoundError("Repo not found")
    )
    with pytest.raises(ValueError):
        await get_commits(mock_ctx, repo="missing-repo")


# ---------------------------------------------------------------------------
# get_pull_requests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_pull_requests_open(mock_ctx):
    result = await get_pull_requests(mock_ctx, repo="awesome-project", state="open")
    assert len(result) == 1
    assert result[0].number == 42
    assert result[0].state == "open"
    assert result[0].labels == ["enhancement"]
    assert result[0].draft is False


@pytest.mark.asyncio
async def test_get_pull_requests_error(mock_ctx):
    mock_ctx.request_context.lifespan_context["github"].get_pull_requests.side_effect = (
        GitHubRateLimitError("Rate limit hit")
    )
    with pytest.raises(ValueError, match="Rate limit"):
        await get_pull_requests(mock_ctx, repo="awesome-project")


# ---------------------------------------------------------------------------
# get_issues
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_issues_excludes_prs(mock_ctx):
    result = await get_issues(mock_ctx, repo="awesome-project")
    assert len(result) == 1
    assert result[0].number == 10
    assert result[0].labels == ["bug"]


@pytest.mark.asyncio
async def test_get_issues_error(mock_ctx):
    mock_ctx.request_context.lifespan_context["github"].get_issues.side_effect = (
        GitHubNotFoundError("Repo not found")
    )
    with pytest.raises(ValueError):
        await get_issues(mock_ctx, repo="missing")


# ---------------------------------------------------------------------------
# get_file_content
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_file_content_decodes_base64(mock_ctx):
    result = await get_file_content(mock_ctx, repo="awesome-project", path="README.md")
    assert result.name == "README.md"
    assert result.content == "Hello, World!"
    assert result.encoding == "utf-8"


@pytest.mark.asyncio
async def test_get_file_content_not_found(mock_ctx):
    mock_ctx.request_context.lifespan_context["github"].get_file_content.side_effect = (
        GitHubNotFoundError("File not found")
    )
    with pytest.raises(ValueError, match="Not found"):
        await get_file_content(mock_ctx, repo="awesome-project", path="missing.txt")


# ---------------------------------------------------------------------------
# get_workflow_runs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_workflow_runs(mock_ctx):
    result = await get_workflow_runs(mock_ctx, repo="awesome-project")
    assert len(result) == 1
    assert result[0].name == "CI"
    assert result[0].status == "completed"
    assert result[0].conclusion == "success"


@pytest.mark.asyncio
async def test_get_workflow_runs_error(mock_ctx):
    mock_ctx.request_context.lifespan_context["github"].get_workflow_runs.side_effect = (
        GitHubNotFoundError("Repo not found")
    )
    with pytest.raises(ValueError):
        await get_workflow_runs(mock_ctx, repo="missing")


# ---------------------------------------------------------------------------
# check_rate_limit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_rate_limit(mock_ctx):
    result = await check_rate_limit(mock_ctx)
    assert result.limit == 5000
    assert result.remaining == 4800
    assert result.used == 200


@pytest.mark.asyncio
async def test_check_rate_limit_auth_error(mock_ctx):
    from github_client import GitHubAuthError
    mock_ctx.request_context.lifespan_context["github"].get_rate_limit.side_effect = (
        GitHubAuthError("Bad credentials")
    )
    with pytest.raises(ValueError, match="Auth error"):
        await check_rate_limit(mock_ctx)