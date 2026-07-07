from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from datetime import datetime
from database import users_col
from models import UserCreate, UserUpdate, UserLogin, Token, UserRegister
from auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/setup-check")
async def check_setup():
    """Checks if setup is complete. Always returns True to disable setup prompt."""
    return {"is_setup": True}

@router.post("/register")
async def register(req: UserRegister):
    email = req.email.strip().lower()
    
    # Check email uniqueness
    existing = await users_col.find_one({"email": email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )
        
    hashed = hash_password(req.password)
    
    user_doc = {
        "email": email,
        "password": hashed,
        "name": req.name,
        "company_name": req.company_name,
        "role": "recruiter",
        "created_at": datetime.utcnow()
    }
    
    await users_col.insert_one(user_doc)
    return {"message": "Registration successful. You can now log in."}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username.strip().lower()
    user = await users_col.find_one({"email": email})
    
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": user["email"], "role": user.get("role", "recruiter")})
    return {
        "access_token": token,
        "token_type": "bearer",
        "name": user["name"],
        "role": user.get("role", "recruiter"),
        "email": user["email"],
        "company_name": user.get("company_name", ""),
    }

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """Retrieve logged-in user profile details for frontend session restore."""
    return {
        "email": current_user["email"],
        "name": current_user.get("name"),
        "role": current_user.get("role", "recruiter"),
        "company_name": current_user.get("company_name", "")
    }

@router.put("/profile")
async def update_profile(update: UserUpdate, current_user=Depends(get_current_user)):
    """Updates the current user's profile or password."""
    update_data = {}
    if update.name:
        update_data["name"] = update.name
    if update.role:
        update_data["role"] = update.role
    if update.company_name:
        update_data["company_name"] = update.company_name
    if update.email:
        if update.email != current_user["email"]:
            raise HTTPException(status_code=400, detail="Recruiter email cannot be modified after registration.")
    
    if update.password:
        update_data["password"] = hash_password(update.password)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    await users_col.update_one(
        {"email": current_user["email"]},
        {"$set": update_data}
    )
    
    return {"message": "Profile updated successfully"}
