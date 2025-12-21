# gitVlame
# backend/README.md
# GitBlame Backend

## 설치
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 실행
```bash
uvicorn app.main:app --reload --port 8000
```

## API 문서

http://localhost:8000/docs

## Vercel 배포
이 리포지토리는 `vercel.json`으로 Vercel 서버리스 함수 설정이 되어 있습니다. 배포 전 아래를 준비하세요.

1. Vercel CLI 설치 후 로그인  
   ```bash
   npm i -g vercel
   vercel login
   ```
2. 환경 변수 등록 (`.env.example` 참고)  
   ```bash
   vercel env add DATABASE_URL
   vercel env add DIRECT_URL
   vercel env add GITHUB_CLIENT_ID
   vercel env add GITHUB_CLIENT_SECRET
   vercel env add GITHUB_REDIRECT_URI
   vercel env add CLAUDE_API_KEY
   vercel env add SUPABASE_URL
   vercel env add SUPABASE_KEY
   vercel env add SECRET_KEY
   vercel env add FRONTEND_URL
   ```
3. 배포  
   ```bash
   vercel       # 프리뷰
   vercel --prod
   ```

`installCommand`로 `pip install -r requirements.txt && prisma generate`가 자동 실행되며, 모든 요청은 `app/main.py`의 FastAPI 앱으로 라우팅됩니다.
