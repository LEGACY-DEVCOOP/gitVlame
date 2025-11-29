# backend/app/services/blame_analyzer.py
import json
from app.services.github_service import GitHubService
from app.services.claude_service import ClaudeService
from app.models.schemas import BlameRequest, BlameResponse, Suspect


class BlameAnalyzer:
    def __init__(self):
        self.github_service = GitHubService()
        self.claude_service = ClaudeService()

    async def analyze(self, request: BlameRequest) -> BlameResponse:
        """전체 blame 분석 프로세스"""

        # 1. repo 정보 파싱
        owner, repo = request.repo.split("/")

        # 2. GitHub에서 blame 데이터 가져오기
        blame_data = await self.github_service.get_blame_data(
            owner, repo, request.file_path
        )

        # 3. Claude에게 분석 요청
        analysis_result = await self.claude_service.analyze_blame(
            blame_data,
            request.error_description
        )

        # 4. JSON 파싱
        result = json.loads(analysis_result)

        # 5. Response 모델로 변환
        suspects = [Suspect(**s) for s in result["suspects"]]

        return BlameResponse(
            suspects=suspects,
            timeline=[],  # TODO: 커밋 타임라인 구현
            blame_message=result.get("analysis", "")
        )

    async def generate_message(self, suspect: str, intensity: str) -> str:
        """Blame 메시지 생성"""
        context = {
            "commit": "결제 로직 수정",
            "file": "src/api/payment.ts",
            "error": "TypeError"
        }

        message = await self.claude_service.generate_blame_message(
            suspect, intensity, context
        )

        return message