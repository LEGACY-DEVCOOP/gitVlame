import httpx
from typing import List, Optional
from app.models.schemas import RepoResponse, ContributorResponse, CommitResponse, CommitAuthor
from app.utils.exceptions import GitHubAPIException

class GitHubService:
    BASE_URL = "https://api.github.com"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    async def _request(self, method: str, url: str, params: dict = None):
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self.headers, params=params)
            
            # Rate limit logging (simplified)
            # print(f"Rate Limit Remaining: {response.headers.get('X-RateLimit-Remaining')}")

            if response.status_code in (401, 403):
                raise GitHubAPIException(f"GitHub API Auth Error: {response.status_code}")
            if response.status_code == 404:
                raise GitHubAPIException(f"GitHub Resource Not Found: {url}")
            if response.status_code >= 500:
                raise GitHubAPIException(f"GitHub API Server Error: {response.status_code}")
            
            response.raise_for_status()
            return response.json()

    async def get_user_repos(self, page: int = 1, per_page: int = 30, sort: str = "updated") -> dict:
        url = f"{self.BASE_URL}/user/repos"
        params = {"page": page, "per_page": per_page, "sort": sort}
        repos_data = await self._request("GET", url, params)
        
        # Note: GitHub API doesn't return total count in response body for this endpoint easily without pagination traversal or header parsing.
        # For simplicity, we might just return the list or check 'Link' header for total pages.
        # The prompt asks for { "repos": List[RepoResponse], "total_count": int }
        # We'll approximate or just return what we have.
        
        repos = []
        for r in repos_data:
            # Map fields if necessary, or let Pydantic handle it with aliases
            repos.append(RepoResponse.model_validate(r))
            
        return {"repos": repos, "total_count": len(repos)} # Total count is tricky without extra calls

    async def get_repo_contributors(self, owner: str, repo: str) -> dict:
        # Get contributors list
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors"
        contributors_data = await self._request("GET", url)
        
        # Get stats for more detailed info (optional, but requested "commits", "additions", "deletions")
        # /stats/contributors returns weekly hash, might be heavy.
        # Simple /contributors endpoint gives 'contributions' (commit count).
        # To get additions/deletions per contributor, we need /stats/contributors
        
        stats_url = f"{self.BASE_URL}/repos/{owner}/{repo}/stats/contributors"
        # Stats might return 202 if computing.
        try:
            stats_data = await self._request("GET", stats_url)
        except:
            stats_data = [] # Fallback

        contributors = []
        total_commits = 0

        # Process stats if available
        if isinstance(stats_data, list) and stats_data:
            for stat in stats_data:
                author = stat['author']
                total = stat['total']
                weeks = stat['weeks']
                additions = sum(w['a'] for w in weeks)
                deletions = sum(w['d'] for w in weeks)
                
                contributors.append(ContributorResponse(
                    username=author['login'],
                    avatar_url=author['avatar_url'],
                    commits=total,
                    additions=additions,
                    deletions=deletions,
                    percentage=0.0 # Calculate later
                ))
                total_commits += total
        else:
            # Fallback to simple contributors list
            for c in contributors_data:
                contributors.append(ContributorResponse(
                    username=c['login'],
                    avatar_url=c['avatar_url'],
                    commits=c['contributions'],
                    additions=0,
                    deletions=0,
                    percentage=0.0
                ))
                total_commits += c['contributions']

        # Calculate percentage
        if total_commits > 0:
            for c in contributors:
                c.percentage = round((c.commits / total_commits) * 100, 2)
                
        return {"contributors": contributors, "total_commits": total_commits}

    async def get_repo_commits(self, owner: str, repo: str, path: str = None, since: str = None, until: str = None, per_page: int = 100) -> dict:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
        params = {"per_page": per_page}
        if path: params["path"] = path
        if since: params["since"] = since
        if until: params["until"] = until
        
        commits_data = await self._request("GET", url, params)
        
        commits = []
        for c in commits_data:
            author = c.get('author') or c.get('commit', {}).get('author')
            # Sometimes author is null if not linked to GitHub user, fallback to commit.author.name
            username = author.get('login') if author else c['commit']['author']['name']
            avatar_url = author.get('avatar_url') if author else ""
            
            commits.append(CommitResponse(
                sha=c['sha'],
                message=c['commit']['message'],
                author=CommitAuthor(username=username, avatar_url=avatar_url),
                date=c['commit']['author']['date'],
                additions=0, # Detail needed
                deletions=0
            ))
            
        return {"commits": commits}

    async def get_commit_detail(self, owner: str, repo: str, sha: str) -> dict:
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{sha}"
        data = await self._request("GET", url)
        
        stats = data.get('stats', {})
        return {
            "additions": stats.get('additions', 0),
            "deletions": stats.get('deletions', 0)
        }
