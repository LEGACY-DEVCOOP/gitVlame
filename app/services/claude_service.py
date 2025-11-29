# backend/app/services/claude_service.py
import os
from anthropic import Anthropic


class ClaudeService:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def analyze_blame(self, blame_data: dict, error_description: str):
        """Claude에게 blame 데이터 분석 요청"""

        prompt = f"""
다음은 GitHub의 git blame 데이터와 발생한 에러입니다.
각 개발자의 책임 비율을 분석해주세요.

에러 내용:
{error_description}

Git Blame 데이터:
{blame_data}

다음 JSON 형식으로 응답해주세요:
{{
  "suspects": [
    {{
      "author": "개발자 이름",
      "percentage": 52,
      "reason": "해당 파일 마지막 수정자",
      "commit": "커밋 메시지",
      "date": "2024-01-14"
    }}
  ],
  "analysis": "상세 분석 내용"
}}
"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text

    async def generate_blame_message(self, suspect: str, intensity: str, context: dict):
        """Blame 메시지 생성"""

        intensity_prompts = {
            "mild": "부드럽고 친근하게",
            "medium": "직설적이지만 예의있게",
            "spicy": "재치있고 유머러스하게 (하지만 선을 넘지 않게)"
        }

        prompt = f"""
{suspect}님에게 보낼 blame 메시지를 {intensity_prompts[intensity]} 작성해주세요.

상황:
- 커밋: {context.get('commit')}
- 파일: {context.get('file')}
- 에러: {context.get('error')}

한글로 2-3문장 정도로 작성해주세요.
"""

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return message.content[0].text