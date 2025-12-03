from fastapi import APIRouter, Depends, HTTPException
from app.database import db
from app.dependencies import get_current_user
from app.models.schemas import BlameCreate, BlameResponse
from app.services.gemini_service import GeminiService
from app.services.image_service import ImageService
from app.utils.exceptions import ForbiddenException

router = APIRouter()

@router.post("/{judgment_id}/blame", response_model=BlameResponse)
async def create_blame(
    judgment_id: str,
    blame_in: BlameCreate,
    current_user = Depends(get_current_user)
):
    judgment = await db.judgment.find_unique(
        where={"id": judgment_id},
        include={"suspects": True, "blame": True}
    )
    
    if not judgment:
        raise HTTPException(status_code=404, detail="Judgment not found")
    if judgment.user_id != current_user.id:
        raise ForbiddenException()
    if judgment.status != "completed":
        raise HTTPException(status_code=400, detail="Judgment not completed")
    if not judgment.suspects:
        raise HTTPException(status_code=400, detail="No suspects found")
        
    # Find main suspect
    target = max(judgment.suspects, key=lambda x: x.responsibility)
    
    # Generate Message
    gemini_service = GeminiService()
    message = await gemini_service.generate_blame_message({
        "repo_name": judgment.repo_name,
        "title": judgment.title,
        "target_username": target.username,
        "responsibility": target.responsibility,
        "reason": target.reason,
        "last_commit_msg": target.last_commit_msg
    }, blame_in.intensity)
    
    # Upsert Blame
    blame = await db.blame.upsert(
        where={"judgment_id": judgment.id},
        data={
            "create": {
                "judgment_id": judgment.id,
                "target_username": target.username,
                "target_avatar": target.avatar_url,
                "responsibility": target.responsibility,
                "reason": target.reason,
                "message": message,
                "intensity": blame_in.intensity,
            },
            "update": {
                "target_username": target.username,
                "target_avatar": target.avatar_url,
                "responsibility": target.responsibility,
                "reason": target.reason,
                "message": message,
                "intensity": blame_in.intensity,
            }
        }
    )
    
    return blame

@router.get("/{judgment_id}/blame", response_model=BlameResponse)
async def get_blame(
    judgment_id: str,
    current_user = Depends(get_current_user)
):
    blame = await db.blame.find_unique(where={"judgment_id": judgment_id})
    if not blame:
        raise HTTPException(status_code=404, detail="Blame not found")
        
    # Check ownership via judgment
    judgment = await db.judgment.find_unique(where={"id": judgment_id})
    if judgment.user_id != current_user.id:
        raise ForbiddenException()
        
    return blame

@router.post("/{judgment_id}/blame/image")
async def generate_blame_image(
    judgment_id: str,
    current_user = Depends(get_current_user)
):
    judgment = await db.judgment.find_unique(
        where={"id": judgment_id},
        include={"blame": True, "suspects": True} # suspects needed for commit msg if not in blame? Blame has it? No blame doesn't have commit msg.
        # Wait, Blame model doesn't have last_commit_msg. But ImageService needs it.
        # We can get it from the suspect that matches target_username.
    )
    
    if not judgment or not judgment.blame:
        raise HTTPException(status_code=404, detail="Blame not found")
    if judgment.user_id != current_user.id:
        raise ForbiddenException()
        
    # Find suspect for commit msg
    suspect = next((s for s in judgment.suspects if s.username == judgment.blame.target_username), None)
    last_commit_msg = suspect.last_commit_msg if suspect else "Unknown commit"

    image_service = ImageService()
    image_url = await image_service.generate_blame_image({
        "judgment_id": judgment.id,
        "repo_name": judgment.repo_name,
        "title": judgment.title,
        "created_at": judgment.created_at,
        "target_username": judgment.blame.target_username,
        "target_avatar": judgment.blame.target_avatar,
        "responsibility": judgment.blame.responsibility,
        "last_commit_msg": last_commit_msg
    })
    
    await db.blame.update(
        where={"id": judgment.blame.id},
        data={"image_url": image_url}
    )
    
    return {"image_url": image_url}
