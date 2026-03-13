"""
Announcement endpoints for the High School Management System API
"""

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson import ObjectId

from ..database import announcements_collection
from ..dependencies import get_current_teacher

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    """Payload for creating announcements."""

    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=1500)
    expiration_date: str = Field(
        description="Expiration date in YYYY-MM-DD format")
    start_date: Optional[str] = Field(
        default=None,
        description="Optional start date in YYYY-MM-DD format",
    )


class AnnouncementUpdate(BaseModel):
    """Payload for updating announcements."""

    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=1500)
    expiration_date: str = Field(
        description="Expiration date in YYYY-MM-DD format")
    start_date: Optional[str] = Field(
        default=None,
        description="Optional start date in YYYY-MM-DD format",
    )


def _parse_iso_date(date_value: Optional[str], field_name: str) -> Optional[date]:
    """Parse date string in YYYY-MM-DD format and raise a 400 error if invalid."""
    if date_value in (None, ""):
        return None

    try:
        return date.fromisoformat(date_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}. Use YYYY-MM-DD format.",
        ) from exc


def _serialize_announcement(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Mongo document into API response payload."""
    return {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "message": doc["message"],
        "start_date": doc.get("start_date"),
        "expiration_date": doc["expiration_date"],
    }


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def list_active_announcements() -> List[Dict[str, Any]]:
    """
    Get active announcements visible to everyone.

    An announcement is active when:
    - expiration_date is today or later
    - start_date is not set OR start_date is today or earlier
    """
    today = date.today().isoformat()

    query = {
        "expiration_date": {"$gte": today},
        "$or": [
            {"start_date": None},
            {"start_date": {"$lte": today}},
        ],
    }

    docs = announcements_collection.find(query).sort("expiration_date", 1)
    return [_serialize_announcement(doc) for doc in docs]


@router.get("/manage", response_model=List[Dict[str, Any]])
def list_all_announcements(current_teacher: Dict[str, Any] = Depends(get_current_teacher)) -> List[Dict[str, Any]]:
    """Get all announcements for management. Requires a signed-in user."""
    docs = announcements_collection.find({}).sort("expiration_date", 1)
    return [_serialize_announcement(doc) for doc in docs]


@router.post("", response_model=Dict[str, Any])
def create_announcement(payload: AnnouncementCreate, current_teacher: Dict[str, Any] = Depends(get_current_teacher)) -> Dict[str, Any]:
    """Create a new announcement. Requires a signed-in user."""
    start_date = _parse_iso_date(payload.start_date, "start_date")
    expiration_date = _parse_iso_date(payload.expiration_date, "expiration_date")

    if expiration_date is None:
        raise HTTPException(status_code=400, detail="expiration_date is required")

    if start_date and start_date > expiration_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be later than expiration_date",
        )

    stripped_title = payload.title.strip()
    stripped_message = payload.message.strip()

    if not stripped_title:
        raise HTTPException(
            status_code=422,
            detail="title must not be empty or whitespace",
        )

    if not stripped_message:
        raise HTTPException(
            status_code=422,
            detail="message must not be empty or whitespace",
        )

    announcement = {
        "title": stripped_title,
        "message": stripped_message,
        "start_date": start_date.isoformat() if start_date else None,
        "expiration_date": expiration_date.isoformat(),
    }

    result = announcements_collection.insert_one(announcement)
    return {
        "message": "Announcement created",
        "id": str(result.inserted_id),
    }


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    payload: AnnouncementUpdate,
    current_teacher: Dict[str, Any] = Depends(get_current_teacher),
) -> Dict[str, Any]:
    """Update an existing announcement. Requires a signed-in user."""
    if not ObjectId.is_valid(announcement_id):
        raise HTTPException(status_code=404, detail="Announcement not found")

    start_date = _parse_iso_date(payload.start_date, "start_date")
    expiration_date = _parse_iso_date(payload.expiration_date, "expiration_date")

    if expiration_date is None:
        raise HTTPException(status_code=400, detail="expiration_date is required")

    if start_date and start_date > expiration_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be later than expiration_date",
        )

    stripped_title = payload.title.strip()
    stripped_message = payload.message.strip()

    if not stripped_title:
        raise HTTPException(
            status_code=422,
            detail="title must not be empty or whitespace",
        )

    if not stripped_message:
        raise HTTPException(
            status_code=422,
            detail="message must not be empty or whitespace",
        )

    result = announcements_collection.update_one(
        {"_id": ObjectId(announcement_id)},
        {
            "$set": {
                "title": stripped_title,
                "message": stripped_message,
                "start_date": start_date.isoformat() if start_date else None,
                "expiration_date": expiration_date.isoformat(),
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement updated"}


@router.delete("/{announcement_id}", response_model=Dict[str, Any])
def delete_announcement(announcement_id: str, current_teacher: Dict[str, Any] = Depends(get_current_teacher)) -> Dict[str, Any]:
    """Delete an announcement. Requires a signed-in user."""
    if not ObjectId.is_valid(announcement_id):
        raise HTTPException(status_code=404, detail="Announcement not found")

    result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted"}
