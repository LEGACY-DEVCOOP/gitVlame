# backend/app/routers/github.py
from fastapi import APIRouter, Depends
from app.models.schemas import RepoListResponse
from app.services.github_service import GitHubService

router = APIRouter()

@router.get("/repos")
async def get_repositories(
    username: str,
    github_service: GitHubService = Depends()
):
    """사용자의 레포지토리 목록 조회"""
    repos = await github_service.get_user_repos(username)
    return repos

@router.get("/repos/{owner}/{repo}/contributors")
async def get_contributors(
    owner: str,
    repo: str,
    github_service: GitHubService = Depends()
):
    """레포지토리 기여자 통계"""
    contributors = await github_service.get_contributors(owner, repo)
    return contributors