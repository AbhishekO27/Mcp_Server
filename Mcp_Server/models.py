from pydantic import BaseModel
from datetime import datetime

class Repo(BaseModel):
    name: str
    private: bool
    stars: int
    url: str

class Commit(BaseModel):
    sha: str
    message: str
    author: str
    date: datetime

class PullRequest(BaseModel):
    number: int
    title: str
    state: str
    url: str
    created_at: datetime
