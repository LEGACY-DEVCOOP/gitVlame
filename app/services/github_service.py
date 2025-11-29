# backend/app/services/github_service.py
import httpx
import os
from typing import List, Dict, Tuple
from urllib.parse import urlparse


class GitHubService:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.graphql_url = "https://api.github.com/graphql"

    def parse_file_url(self, file_url: str) -> Tuple[str, str, str, str]:
        """
        GitHub 파일 URL에서 owner, repo, branch, file_path 추출
        예: https://github.com/owner/repo/blob/branch/path/to/file.py
        """
        parsed = urlparse(file_url)
        if parsed.netloc not in {"github.com", "www.github.com"}:
            raise ValueError("GitHub 도메인의 파일 URL만 지원합니다.")

        segments = parsed.path.strip("/").split("/")
        if len(segments) < 5 or segments[2] != "blob":
            raise ValueError("파일 URL 형식이 올바르지 않습니다. /owner/repo/blob/branch/path 형식이어야 합니다.")

        owner, repo, _, branch, *file_parts = segments
        file_path = "/".join(file_parts)
        if not file_path:
            raise ValueError("파일 경로를 찾을 수 없습니다.")

        return owner, repo, branch, file_path

    async def get_blame_data(self, owner: str, repo: str, file_path: str, branch: str = "main"):
        """GitHub GraphQL로 git blame 데이터 가져오기"""
        query = """
        query($owner: String!, $repo: String!, $expression: String!) {
          repository(owner: $owner, name: $repo) {
            object(expression: $expression) {
              ... on Blob {
                blame(first: 100) {
                  ranges {
                    commit {
                      author {
                        name
                        email
                        date
                      }
                      message
                      oid
                    }
                    startingLine
                    endingLine
                    age
                  }
                }
              }
            }
          }
        }
        """

        variables = {
            "owner": owner,
            "repo": repo,
            "expression": f"{branch}:{file_path}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.graphql_url,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            return response.json()

    async def get_user_repos(self, username: str):
        """사용자 레포지토리 목록"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/users/{username}/repos",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            return response.json()

    async def get_contributors(self, owner: str, repo: str):
        """레포지토리 기여자 통계"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contributors",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            return response.json()

    async def get_commit_history(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_path: str,
        per_page: int = 20,
    ):
        """지정 파일의 커밋 히스토리"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits",
                params={"sha": branch, "path": file_path, "per_page": per_page},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            return response.json()
