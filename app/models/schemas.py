# backend/app/models/schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BlameRequest(BaseModel):
    repo: str                    # "username/repo"
    file_path: str               # "src/api/payment.ts"
    error_description: str
    date_range: int = 7

class Suspect(BaseModel):
    author: str
    percentage: int
    reason: str
    commit: str
    date: str

class Commit(BaseModel):
    sha: str
    author: str
    message: str
    date: datetime

class BlameResponse(BaseModel):
    suspects: List[Suspect]
    timeline: List[Commit]
    blame_message: str

class RepoListResponse(BaseModel):
    name: str
    owner: str
    stars: int
    forks: int
    updated_at: datetime