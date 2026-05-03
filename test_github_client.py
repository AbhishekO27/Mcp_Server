"""
Unit tests for GitHubClient error handling and response parsing.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from github_client import (
    GitHubClient,
    GitHubAuthError,
    GitHubRateLimitError,
    GitHubNotFoundError,
    _handle_response,
)


# ---------------------------------------------------------------------------
# _handle_response unit tests (no I/O needed)
# ---------------------------------------------------------------------------

def _make_response(status_code: int, headers: dict | None = None) -> httpx.Response:
    """Helper to build a minimal httpx.Response for testing."""
    return httpx.Response(
        status_code=status_code,
        headers=headers or {},
        json={"message": "test"},
        request=httpx.Request("GET", "https://api.github.com/test"),
    )


def test_handle_response_401_raises_auth_error():
    resp = _make_response(401)
    with pytest.raises(GitHubAuthError):
        _handle_response(resp)


def test_handle_response_403_raises_rate_limit_error():
    resp = _make_response(403, headers={
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1705316400",
    })
    with pytest.raises(GitHubRateLimitError, match="Rate limit exceeded"):
        _handle_response(resp)


def test_handle_response_404_raises_not_found():
    resp = _make_response(404)
    with pytest.raises(GitHubNotFoundError):
        _handle_response(resp)


def test_handle_response_200_returns_json():
    resp = httpx.Response(
        status_code=200,
        json={"name": "awesome"},
        request=httpx.Request("GET", "https://api.github.com/test"),
    )
    result = _handle_response(resp)
    assert result == {"name": "awesome"}


# ---------------------------------------------------------------------------
# GitHubClient env-var validation
# ---------------------------------------------------------------------------

def test_client_raises_if_no_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_USERNAME", "testuser")
    with pytest.raises(EnvironmentError, match="GITHUB_TOKEN"):
        GitHubClient()


def test_client_raises_if_no_username(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    monkeypatch.delenv("GITHUB_USERNAME", raising=False)
    with pytest.raises(EnvironmentError, match="GITHUB_USERNAME"):
        GitHubClient()