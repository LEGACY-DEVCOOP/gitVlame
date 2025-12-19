from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
import httpx
import jwt
from datetime import datetime, timedelta
from app.config import settings
from app.database import db
from app.models.schemas import UserResponse, Token
from app.dependencies import get_current_user

router = APIRouter()

def create_jwt_token(user_id: str, username: str) -> str:
    payload = {
        "sub": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

@router.get("/github/login")
async def github_login():
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=read:user,repo"
    )

@router.get("/github/callback")
async def github_callback(code: str):
    # Exchange code for access token
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
            },
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        # Get user info
        user_res = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        user_data = user_res.json()
        
        # Upsert user
        github_id = str(user_data["id"])
        username = user_data["login"]
        avatar_url = user_data.get("avatar_url")
        
        user = await db.user.upsert(
            where={"github_id": github_id},
            data={
                "create": {
                    "github_id": github_id,
                    "username": username,
                    "avatar_url": avatar_url,
                    "access_token": access_token,
                },
                "update": {
                    "username": username,
                    "avatar_url": avatar_url,
                    "access_token": access_token,
                },
            },
        )
        
        # Create JWT
        token = create_jwt_token(user.id, user.username)
        
        # Redirect to frontend
        # Redirect to frontend root with token
        return RedirectResponse(f"{settings.FRONTEND_URL}?token={token}")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    return current_user

@router.post("/logout")
async def logout():
    # Client side should delete token
    return {"message": "Logged out"}
