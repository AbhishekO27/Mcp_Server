# GitHub Analytics MCP Server

> Expose your GitHub data as AI-accessible tools via the [Model Context Protocol](https://modelcontextprotocol.io/). Ask Claude natural language questions about your repositories, commits, pull requests, issues, CI runs, and more — and get real answers backed by live GitHub API data.

---

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard that lets AI models like Claude call external tools and data sources in a structured, type-safe way. This server implements MCP on top of the GitHub REST API — turning raw API endpoints into 8 well-typed tools that any MCP-compatible AI client can call.

---

## Demo

> **Using MCP Inspector** — no Claude Desktop required.

```bash
npx @modelcontextprotocol/inspector python server.py
```

Open `localhost:5173`, pick a tool, fill in the parameters, and hit **Run**. You'll see live GitHub data returned as structured JSON.

![MCP Inspector Demo](docs/demo.gif)
<!-- Record a short screen capture and drop it here -->

---

## Tools

| Tool | Description | Key parameters |
|------|-------------|----------------|
| `list_repositories` | List all repos for the authenticated user | `sort`, `limit` |
| `get_repository` | Detailed info for a single repo | `repo` |
| `get_commits` | Recent commits for a repo | `repo`, `limit` |
| `get_pull_requests` | Open / closed PRs for a repo | `repo`, `state`, `limit` |
| `get_issues` | Issues for a repo (PRs excluded) | `repo`, `state`, `limit` |
| `get_file_content` | Decoded content of any file | `repo`, `path`, `ref` |
| `get_workflow_runs` | Recent GitHub Actions CI runs | `repo`, `limit` |
| `check_rate_limit` | Current API rate limit status | — |

---

## Architecture

```
Claude / AI client
       │  MCP protocol
       ▼
  server.py  (FastMCP)
  ├── 8 async tool handlers
  ├── Pydantic v2 response models
  └── github_client.py
           │  httpx + tenacity retries
           ▼
     GitHub REST API
     api.github.com
```

**Key design decisions:**

- **Async throughout** — every tool and every HTTP call is `async`, so the server never blocks while waiting on GitHub.
- **Pydantic v2 as a contract layer** — raw GitHub JSON is validated and transformed into typed models before it reaches the AI. Field mismatches raise immediately at the boundary, not silently downstream.
- **Centralised error handling** — `GitHubAuthError`, `GitHubRateLimitError`, and `GitHubNotFoundError` are mapped to descriptive `ValueError` messages that Claude can read and act on.
- **Retry logic via tenacity** — transient network errors are retried up to 3 times with exponential back-off before propagating.
- **Lifespan management** — the `httpx.AsyncClient` is created once at startup and cleanly closed on shutdown, avoiding per-request connection overhead.

---

## Project structure

```
Mcp_Server/
├── server.py           # FastMCP server — tool definitions and handlers
├── github_client.py    # Async GitHub REST API client with error handling
├── models.py           # Pydantic v2 response models
├── pyproject.toml      # Dependencies and project metadata
├── .env.example        # Environment variable template
└── tests/
    ├── conftest.py         # Shared fixtures and sample payloads
    ├── test_server.py      # Tool handler tests (happy path + errors)
    └── test_github_client.py  # Client error-handling unit tests
```

---

## Getting started

### Prerequisites

- Python 3.11+
- A GitHub Personal Access Token with `repo` and `read:user` scopes → [create one here](https://github.com/settings/tokens)

### 1. Clone and install

```bash
git clone https://github.com/AbhishekO27/Mcp_Server.git
cd Mcp_Server
pip install fastmcp httpx pydantic python-dotenv tenacity
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_USERNAME=your_github_username
LOG_LEVEL=INFO
```

### 3. Run the server

```bash
python server.py
```

You should see:

```
Starting GitHub Analytics MCP Server…
```

### 4. Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python server.py
```

Visit `localhost:5173` — all 8 tools are listed and ready to call interactively.

### 5. Or test programmatically

```python
# demo.py
import asyncio
from fastmcp import Client

async def main():
    async with Client("server.py") as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools])

        repos = await client.call_tool("list_repositories", {"limit": 5})
        print(repos)

asyncio.run(main())
```

```bash
python demo.py
```

---

## Running tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=term-missing
```

All tests use mocked GitHub responses — no real API calls are made, no token required.

---

## Connect to Claude Desktop (optional)

If you have Claude Desktop installed, add this to your config file:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "github-analytics": {
      "command": "python",
      "args": ["/absolute/path/to/Mcp_Server/server.py"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token",
        "GITHUB_USERNAME": "AbhishekO27"
      }
    }
  }
}
```

Restart Claude Desktop. You'll see a 🔨 icon in the chat input confirming your tools are live. Then try:

- *"Which of my repos has the most open issues?"*
- *"Show me the last 5 commits on Mcp_Server"*
- *"Did my CI pass on the last push?"*
- *"Are there any open PRs? Summarize what they're changing."*

---

## Example tool responses

**`list_repositories`**
```json
[
  {
    "name": "Mcp_Server",
    "private": false,
    "stars": 0,
    "forks": 0,
    "language": "Python",
    "description": "GitHub Analytics MCP Server",
    "url": "https://github.com/AbhishekO27/Mcp_Server",
    "open_issues": 0,
    "updated_at": "2024-01-15T10:00:00Z"
  }
]
```

**`get_commits`**
```json
[
  {
    "sha": "abc123d",
    "message": "feat: add async GitHub client with retry logic",
    "author": "Abhishek O",
    "author_email": "abhishek@example.com",
    "date": "2024-01-15T09:00:00Z",
    "url": "https://github.com/AbhishekO27/Mcp_Server/commit/abc123d"
  }
]
```

**`check_rate_limit`**
```json
{
  "limit": 5000,
  "remaining": 4823,
  "used": 177,
  "reset": "2024-01-15T11:00:00Z"
}
```

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| MCP framework | [FastMCP](https://github.com/jlowin/fastmcp) |
| HTTP client | [httpx](https://www.python-httpx.org/) (async) |
| Data validation | [Pydantic v2](https://docs.pydantic.dev/) |
| Retry logic | [tenacity](https://tenacity.readthedocs.io/) |
| Environment | [python-dotenv](https://github.com/theskumar/python-dotenv) |
| Testing | [pytest](https://pytest.org/) + [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) |

---

## Error handling

The server maps GitHub API errors to descriptive messages the AI can understand and act on:

| HTTP status | Exception raised | Message |
|-------------|-----------------|---------|
| 401 | `GitHubAuthError` | Check your `GITHUB_TOKEN` |
| 403 | `GitHubRateLimitError` | Rate limit exceeded — shows reset time |
| 404 | `GitHubNotFoundError` | Resource not found — shows URL |
| Network error | Retried 3× with back-off | Then raises `httpx.TransportError` |

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Author

**Abhishek O** · [github.com/AbhishekO27](https://github.com/AbhishekO27)
