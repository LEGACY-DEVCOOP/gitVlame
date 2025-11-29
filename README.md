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