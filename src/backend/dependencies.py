"""
Shared FastAPI dependencies for the High School Management System API
"""

import hashlib
from typing import Any, Dict

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import teachers_collection

_bearer = HTTPBearer()


def _hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a raw token."""
    return hashlib.sha256(token.encode()).hexdigest()


def get_current_teacher(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Dict[str, Any]:
    """
    Validate the Bearer token from the Authorization header and return the
    associated teacher document.

    Raises HTTP 401 when the token is missing or invalid.
    """
    token_hash = _hash_token(credentials.credentials)
    teacher = teachers_collection.find_one({"session_token": token_hash})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return teacher
