import os
import httpx

class GitHubClient:
    def __init__(self):
        self.username = os.getenv("GITHUB_USERNAME")
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
                "Accept": "application/vnd.github+json"
            }
        )

    def get_repositories(self):
        r = self.client.get(f"/users/{self.username}/repos")
        r.raise_for_status()
        return r.json()

    def get_commits(self, repo: str):
        r = self.client.get(f"/repos/{self.username}/{repo}/commits")
        r.raise_for_status()
        return r.json()

    def get_pull_requests(self, repo: str, state: str = "open"):
        r = self.client.get(
            f"/repos/{self.username}/{repo}/pulls",
            params={"state": state}
        )
        r.raise_for_status()
        return r.json()
