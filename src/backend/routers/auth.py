"""
Authentication endpoints for the High School Management System API
"""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict

from ..database import teachers_collection, verify_password
from ..dependencies import get_current_teacher, _hash_token

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


@router.post("/login")
def login(username: str, password: str) -> Dict[str, Any]:
    """Login a teacher account and return a session token."""
    teacher = teachers_collection.find_one({"_id": username})

    if not teacher or not verify_password(teacher.get("password", ""), password):
        raise HTTPException(
            status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    teachers_collection.update_one(
        {"_id": username},
        {"$set": {"session_token": _hash_token(token)}},
    )

    return {
        "username": teacher["username"],
        "display_name": teacher["display_name"],
        "role": teacher["role"],
        "token": token,
    }


@router.post("/logout")
def logout(teacher: Dict[str, Any] = Depends(get_current_teacher)) -> Dict[str, Any]:
    """Invalidate the current session token."""
    teachers_collection.update_one(
        {"_id": teacher["_id"]},
        {"$unset": {"session_token": ""}},
    )
    return {"message": "Logged out successfully"}


@router.get("/check-session")
def check_session(teacher: Dict[str, Any] = Depends(get_current_teacher)) -> Dict[str, Any]:
    """Validate the current Bearer token and return teacher info."""
    return {
        "username": teacher["username"],
        "display_name": teacher["display_name"],
        "role": teacher["role"],
    }
