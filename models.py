"""
Pydantic models for GitHub API responses.

All models use strict typing and field aliases to map GitHub's snake_case
JSON keys directly, keeping the parsing logic in server.py minimal.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Repo(BaseModel):
    name: str
    private: bool
    stars: int = Field(alias="stargazers_count", default=0)
    forks: int = Field(alias="forks_count", default=0)
    language: Optional[str] = None
    description: Optional[str] = None
    url: str = Field(alias="html_url")
    open_issues: int = Field(alias="open_issues_count", default=0)
    updated_at: Optional[datetime] = None

    model_config = {"populate_by_name": True}


class RepoDetail(Repo):
    """Extended repository info returned by the single-repo endpoint."""
    default_branch: str = "main"
    size_kb: int = Field(alias="size", default=0)
    topics: list[str] = []
    clone_url: Optional[str] = None

    model_config = {"populate_by_name": True}


class Commit(BaseModel):
    sha: str
    message: str
    author: str
    author_email: str
    date: datetime
    url: str

    @field_validator("sha")
    @classmethod
    def abbreviate_sha(cls, v: str) -> str:
        return v[:7]


class PullRequest(BaseModel):
    number: int
    title: str
    state: str
    url: str
    author: str
    created_at: datetime
    updated_at: datetime
    body: Optional[str] = None
    labels: list[str] = []
    draft: bool = False

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        allowed = {"open", "closed", "all"}
        if v not in allowed:
            raise ValueError(f"state must be one of {allowed}")
        return v


class Issue(BaseModel):
    number: int
    title: str
    state: str
    url: str
    author: str
    created_at: datetime
    updated_at: datetime
    body: Optional[str] = None
    labels: list[str] = []
    comments: int = 0


class FileContent(BaseModel):
    name: str
    path: str
    sha: str
    size: int
    encoding: str
    content: str  # base64-encoded by default from GitHub
    url: str = Field(alias="html_url")

    model_config = {"populate_by_name": True}


class CodeSearchResult(BaseModel):
    total_count: int
    items: list[dict]  # Keep raw; too varied to model strictly


class WorkflowRun(BaseModel):
    id: int
    name: Optional[str]
    status: str          # queued | in_progress | completed
    conclusion: Optional[str]  # success | failure | cancelled | skipped
    branch: str = Field(alias="head_branch", default="")
    commit_sha: str = Field(alias="head_sha", default="")
    url: str = Field(alias="html_url")
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class RateLimitInfo(BaseModel):
    limit: int
    remaining: int
    reset: datetime
    used: int