import httpx
from typing import List, Optional
from app.models.schemas import RepoResponse, ContributorResponse, CommitResponse, CommitAuthor, FileTreeResponse, FileTreeItem
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
        async with httpx.AsyncClient(timeout=30.0) as client:
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

    async def _request_paginated(self, method: str, url: str, params: dict = None, max_pages: int = 10):
        """Fetch all pages from a paginated endpoint"""
        all_results = []
        page = 1
        
        # Copy params to avoid mutation
        request_params = params.copy() if params else {}
        
        while page <= max_pages:
            request_params['page'] = page
            request_params.setdefault('per_page', 100)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, headers=self.headers, params=request_params)
                
                if response.status_code in (401, 403):
                    raise GitHubAPIException(f"GitHub API Auth Error: {response.status_code}")
                if response.status_code == 404:
                    raise GitHubAPIException(f"GitHub Resource Not Found: {url}")
                if response.status_code >= 500:
                    raise GitHubAPIException(f"GitHub API Server Error: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                if not data or not isinstance(data, list):
                    break
                    
                all_results.extend(data)
                
                # Check if there are more pages
                if len(data) < request_params['per_page']:
                    break
                    
                page += 1
        
        return all_results

    async def get_user_repos(self, page: int = 1, per_page: int = 100, sort: str = "updated") -> dict:
        # 1. 사용자의 개인 및 협업 레포지토리 (기본)
        user_repos_url = f"{self.BASE_URL}/user/repos"
        params = {
            "sort": sort,
            "affiliation": "owner,collaborator,organization_member",
            "per_page": 100
        }
        
        # 전체를 다 가져오기 위해 paginated 요청 사용 (최대 500개까지)
        repos_data = await self._request_paginated("GET", user_repos_url, params, max_pages=5)
        
        # 2. 명시적으로 조직 레포지토리들을 더 확인 (혹시 누락된 것들 대비)
        try:
            orgs_url = f"{self.BASE_URL}/user/orgs"
            orgs_data = await self._request("GET", orgs_url)
            
            for org in orgs_data:
                org_name = org['login']
                org_repos_url = f"{self.BASE_URL}/orgs/{org_name}/repos"
                try:
                    # 해당 조직의 레포지토리 목록 명시적 호출
                    org_repos = await self._request_paginated("GET", org_repos_url, {"per_page": 100}, max_pages=3)
                    
                    # 중복 제거하며 추가
                    existing_ids = {r['id'] for r in repos_data}
                    for r in org_repos:
                        if r['id'] not in existing_ids:
                            repos_data.append(r)
                except:
                    continue 
        except:
            pass 
            
        # 정렬 (수정일 순)
        repos_data.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        # 페이지네이션 처리 (반환용)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_repos = repos_data[start:end]
        
        repos = []
        for r in paginated_repos:
            repos.append(RepoResponse.model_validate(r))
            
        return {"repos": repos, "total_count": len(repos_data)}

    async def get_repo_contributors(self, owner: str, repo: str) -> dict:
        # Get contributors list
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contributors"
        contributors_data = await self._request_paginated("GET", url)
        
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
        
        commits_data = await self._request_paginated("GET", url, params)
        
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

    async def get_repo_tree(self, owner: str, repo: str, branch: str = "main") -> FileTreeResponse:
        """
        Get the file tree for a repository

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: "main")

        Returns:
            FileTreeResponse containing the file tree
        """
        # First, get the branch to find the tree SHA
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/git/trees/{branch}"

        try:
            # Try with the specified branch
            data = await self._request("GET", url, params={"recursive": "1"})
        except GitHubAPIException as e:
            # If branch not found, try with "master"
            if "404" in str(e) and branch == "main":
                url = f"{self.BASE_URL}/repos/{owner}/{repo}/git/trees/master"
                data = await self._request("GET", url, params={"recursive": "1"})
            else:
                raise

        # Parse the tree items
        tree_items = []
        for item in data.get("tree", []):
            tree_items.append(FileTreeItem(
                path=item["path"],
                type=item["type"],
                sha=item["sha"],
                size=item.get("size"),
                url=item["url"]
            ))

        return FileTreeResponse(
            sha=data["sha"],
            url=data["url"],
            tree=tree_items,
            truncated=data.get("truncated", False)
        )
