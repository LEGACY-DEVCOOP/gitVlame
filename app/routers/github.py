from fastapi import APIRouter, Depends, Query
from typing import List
from app.dependencies import get_current_user
from app.services.github_service import GitHubService
from app.models.schemas import RepoResponse, ContributorResponse, CommitResponse, PaginatedResponse

router = APIRouter()

@router.get("/repos", response_model=PaginatedResponse[RepoResponse])
async def get_repos(
    page: int = 1,
    per_page: int = 30,
    sort: str = "updated",
    current_user = Depends(get_current_user)
):
    service = GitHubService(current_user.access_token)
    result = await service.get_user_repos(page, per_page, sort)
    
    return PaginatedResponse(
        items=result["repos"],
        total=result["total_count"],
        page=page,
        per_page=per_page
    )

@router.get("/repos/{owner}/{repo}/contributors")
async def get_contributors(
    owner: str,
    repo: str,
    current_user = Depends(get_current_user)
):
    service = GitHubService(current_user.access_token)
    result = await service.get_repo_contributors(owner, repo)
    return result

@router.get("/repos/{owner}/{repo}/commits")
async def get_commits(
    owner: str,
    repo: str,
    path: str = None,
    since: str = None,
    until: str = None,
    per_page: int = 100,
    current_user = Depends(get_current_user)
):
    service = GitHubService(current_user.access_token)
    result = await service.get_repo_commits(owner, repo, path, since, until, per_page)
    return result