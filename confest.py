"""
Shared pytest fixtures for the GitHub Analytics MCP Server test suite.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Sample payloads — mirrors GitHub REST API response shapes
# ---------------------------------------------------------------------------

SAMPLE_REPO = {
    "name": "awesome-project",
    "private": False,
    "stargazers_count": 42,
    "forks_count": 7,
    "language": "Python",
    "description": "An awesome project",
    "html_url": "https://github.com/testuser/awesome-project",
    "open_issues_count": 3,
    "updated_at": "2024-01-15T10:00:00Z",
    "default_branch": "main",
    "size": 1024,
    "topics": ["python", "mcp"],
    "clone_url": "https://github.com/testuser/awesome-project.git",
}

SAMPLE_COMMIT = {
    "sha": "abc123def456",
    "html_url": "https://github.com/testuser/awesome-project/commit/abc123",
    "commit": {
        "message": "feat: add new feature\n\nDetailed description here.",
        "author": {
            "name": "Test User",
            "email": "test@example.com",
            "date": "2024-01-15T09:00:00Z",
        },
    },
}

SAMPLE_PR = {
    "number": 42,
    "title": "Add awesome feature",
    "state": "open",
    "html_url": "https://github.com/testuser/awesome-project/pull/42",
    "user": {"login": "contributor"},
    "created_at": "2024-01-14T08:00:00Z",
    "updated_at": "2024-01-15T09:00:00Z",
    "body": "This PR adds an awesome feature.",
    "labels": [{"name": "enhancement"}],
    "draft": False,
}

SAMPLE_ISSUE = {
    "number": 10,
    "title": "Bug: something is broken",
    "state": "open",
    "html_url": "https://github.com/testuser/awesome-project/issues/10",
    "user": {"login": "reporter"},
    "created_at": "2024-01-13T07:00:00Z",
    "updated_at": "2024-01-14T08:00:00Z",
    "body": "Steps to reproduce…",
    "labels": [{"name": "bug"}],
    "comments": 2,
    # Issues endpoint: no pull_request key → it's a real issue
}

SAMPLE_FILE = {
    "name": "README.md",
    "path": "README.md",
    "sha": "deadbeef",
    "size": 512,
    "encoding": "base64",
    # base64 of "Hello, World!"
    "content": "SGVsbG8sIFdvcmxkIQ==",
    "html_url": "https://github.com/testuser/awesome-project/blob/main/README.md",
}

SAMPLE_WORKFLOW_RUNS = {
    "workflow_runs": [
        {
            "id": 1001,
            "name": "CI",
            "status": "completed",
            "conclusion": "success",
            "head_branch": "main",
            "head_sha": "abc123",
            "html_url": "https://github.com/testuser/awesome-project/actions/runs/1001",
            "created_at": "2024-01-15T08:00:00Z",
            "updated_at": "2024-01-15T08:05:00Z",
        }
    ]
}

SAMPLE_RATE_LIMIT = {
    "rate": {
        "limit": 5000,
        "remaining": 4800,
        "reset": 1705316400,
        "used": 200,
    }
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_github_client():
    """Return a fully mocked GitHubClient with realistic return values."""
    client = AsyncMock()
    client.username = "testuser"

    client.get_repositories.return_value = [SAMPLE_REPO]
    client.get_repository.return_value = SAMPLE_REPO
    client.get_commits.return_value = [SAMPLE_COMMIT]
    client.get_pull_requests.return_value = [SAMPLE_PR]
    client.get_issues.return_value = [SAMPLE_ISSUE]
    client.get_file_content.return_value = SAMPLE_FILE
    client.get_workflow_runs.return_value = SAMPLE_WORKFLOW_RUNS
    client.get_rate_limit.return_value = SAMPLE_RATE_LIMIT

    return client


@pytest.fixture
def mock_ctx(mock_github_client):
    """Return a mock MCP Context with a lifespan_context containing the client."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = {"github": mock_github_client}
    return ctx