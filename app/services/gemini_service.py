import google.generativeai as genai
import json
import asyncio
from app.config import settings
from app.utils.exceptions import GeminiAPIException

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def analyze_commits(self, params: dict) -> dict:
        prompt = f"""
        당신은 Git 커밋 히스토리를 분석하여 버그/장애의 책임자를 판단하는 AI입니다.
        
        [사건 정보]
        제목: {params['title']}
        에러 내용: {params['description']}
        관련 파일: {params['file_path']}
        
        [커밋 히스토리]
        {json.dumps(params['commits'], indent=2, ensure_ascii=False)}
        
        위 정보를 분석하여 각 개발자의 책임 비율을 판단해주세요.
        
        판단 기준:
        1. 해당 파일/기능의 마지막 수정자 (가장 높은 책임)
        2. 에러와 관련된 코드의 작성자
        3. 최근 커밋일수록 책임 비율 높음
        4. 커밋 메시지와 에러 내용의 연관성
        
        반드시 다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
        {{
          "suspects": [
            {{
              "username": "개발자명",
              "responsibility": 책임비율(0-100 정수),
              "reason": "책임 사유 (한국어, 1-2문장)"
            }}
          ]
        }}
        
        주의:
        - 책임 비율의 합은 반드시 100이어야 합니다
        - 최소 1명, 최대 5명까지 선정
        - responsibility가 높은 순으로 정렬
        """
        
        retries = 2
        for attempt in range(retries + 1):
            try:
                # Run sync call in executor
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                if not response.text:
                    raise ValueError("Empty response from Gemini")
                    
                return json.loads(response.text)
                
            except Exception as e:
                if attempt == retries:
                    raise GeminiAPIException(f"Gemini Analysis Failed: {str(e)}")
                await asyncio.sleep(1)

    async def generate_blame_message(self, params: dict, intensity: str) -> str:
        prompt = f"""
        다음 상황에 맞는 Blame 메시지를 작성해주세요.

        프로젝트: {params['repo_name']}
        사건: {params['title']}
        범인: {params['target_username']}
        책임도: {params['responsibility']}%
        관련 커밋: {params['last_commit_msg']}
        책임 사유: {params['reason']}

        강도: {intensity}
        - mild (순한맛): 정중하고 부드럽게 요청하는 톤 ("확인 부탁드려요~", "시간 되실 때 봐주세요")
        - medium (중간): 유머러스하게 ("커피 한 잔 사주세요 ☕", "다음엔 테스트 코드 좀...")
        - spicy (매운맛): 직설적이고 재미있게 ("야 이거 누가 짠 거야", "책임지세요 선배님")

        메시지는 2-3문장으로, 마지막에 적절한 이모지 1-2개를 추가해주세요.
        메시지만 출력하세요 (다른 설명 없이).
        """
        
        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )
            return response.text.strip()
        except Exception as e:
            raise GeminiAPIException(f"Gemini Message Generation Failed: {str(e)}")