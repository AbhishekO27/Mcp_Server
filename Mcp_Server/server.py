from fastmcp import FastMCP
from dotenv import load_dotenv
from github_client import GitHubClient
from models import Repo, Commit, PullRequest

load_dotenv()

mcp = FastMCP(
    name="GitHub Analytics MCP Server",
    version="1.0.0"
)

github = GitHubClient()


@mcp.tool()
def list_repositories() -> list[Repo]:
    """List GitHub repositories for the authenticated user."""
    repos = github.get_repositories()
    return [
        Repo(
            name=r["name"],
            private=r["private"],
            stars=r["stargazers_count"],
            url=r["html_url"]
        )
        for r in repos
    ]


@mcp.tool()
def get_commits(repo: str) -> list[Commit]:
    """Get recent commits for a repository."""
    commits = github.get_commits(repo)
    return [
        Commit(
            sha=c["sha"],
            message=c["commit"]["message"],
            author=c["commit"]["author"]["name"],
            date=c["commit"]["author"]["date"]
        )
        for c in commits
    ]


@mcp.tool()
def get_pull_requests(
    repo: str,
    state: str = "open"
) -> list[PullRequest]:
    """Get pull requests for a repository."""
    prs = github.get_pull_requests(repo, state)
    return [
        PullRequest(
            number=p["number"],
            title=p["title"],
            state=p["state"],
            url=p["html_url"],
            created_at=p["created_at"]
        )
        for p in prs
    ]


if __name__ == "__main__":
    mcp.run()
