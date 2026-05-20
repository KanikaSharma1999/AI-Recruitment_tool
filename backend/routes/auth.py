from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from datetime import datetime
from database import users_col
from models import UserCreate, UserUpdate, UserLogin, Token
from auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    get_current_user
)
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/setup-check")
async def check_setup():
    """Checks if setup is complete. Always returns True to disable setup prompt/signup."""
    return {"is_setup": True}

@router.put("/profile")
async def update_profile(update: UserUpdate, current_user=Depends(get_current_user)):
    """Updates the current user's profile or password."""
    update_data = {}
    if update.name:
        update_data["name"] = update.name
    if update.email:
        # Check if new email is taken
        if update.email != current_user["email"]:
            raise HTTPException(status_code=400, detail="Recruiter email cannot be modified in single-admin mode.")
    
    if update.password:
        update_data["password"] = hash_password(update.password)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    await users_col.update_one(
        {"email": current_user["email"]},
        {"$set": update_data}
    )
    
    return {"message": "Profile updated successfully"}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != "sandhyagowda506@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to authorized recruiter."
        )
    # SafeCollection raises 503 if DB is offline
    user = await users_col.find_one({"email": form_data.username})
    
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": user["email"], "role": "admin"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "name": user["name"],
        "role": "admin",
        "email": user["email"],
    }
