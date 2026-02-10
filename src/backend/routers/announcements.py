"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def is_authenticated(username: Optional[str]) -> bool:
    """Check if a user is authenticated"""
    if not username:
        return False
    teacher = teachers_collection.find_one({"_id": username})
    return teacher is not None


def is_announcement_active(announcement: Dict[str, Any]) -> bool:
    """Check if an announcement is currently active based on dates"""
    today = datetime.now().date()
    
    # Check expiration date (required)
    exp_date = datetime.fromisoformat(announcement["expiration_date"]).date()
    if today > exp_date:
        return False
    
    # Check start date (optional)
    if "start_date" in announcement and announcement["start_date"]:
        start_date = datetime.fromisoformat(announcement["start_date"]).date()
        if today < start_date:
            return False
    
    return True


@router.get("")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (public endpoint)"""
    all_announcements = announcements_collection.find({})
    
    # Filter to only active announcements
    active_announcements = [
        ann for ann in all_announcements if is_announcement_active(ann)
    ]
    
    # Sort by creation date, newest first
    active_announcements.sort(
        key=lambda x: x.get("created_at", ""), 
        reverse=True
    )
    
    return active_announcements


@router.get("/all")
def get_all_announcements(username: Optional[str] = Query(None)) -> List[Dict[str, Any]]:
    """Get all announcements (authenticated users only)"""
    if not is_authenticated(username):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    all_announcements = announcements_collection.find({})
    
    # Sort by creation date, newest first
    all_announcements.sort(
        key=lambda x: x.get("created_at", ""), 
        reverse=True
    )
    
    return all_announcements


@router.post("")
def create_announcement(
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create a new announcement (authenticated users only)"""
    if not is_authenticated(username):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date)
        if start_date:
            start = datetime.fromisoformat(start_date)
            if start > exp_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Start date cannot be after expiration date"
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Create new announcement
    new_announcement = {
        "_id": str(uuid.uuid4()),
        "message": message,
        "start_date": start_date if start_date else None,
        "expiration_date": expiration_date,
        "created_by": username,
        "created_at": datetime.now().isoformat()
    }
    
    announcements_collection.insert_one(new_announcement)
    
    return new_announcement


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update an existing announcement (authenticated users only)"""
    if not is_authenticated(username):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if announcement exists
    existing = announcements_collection.find_one({"_id": announcement_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Validate dates
    try:
        exp_date = datetime.fromisoformat(expiration_date)
        if start_date:
            start = datetime.fromisoformat(start_date)
            if start > exp_date:
                raise HTTPException(
                    status_code=400, 
                    detail="Start date cannot be after expiration date"
                )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Update announcement
    result = announcements_collection.update_one(
        {"_id": announcement_id},
        {
            "$set": {
                "message": message,
                "start_date": start_date if start_date else None,
                "expiration_date": expiration_date
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update announcement")
    
    # Return updated announcement
    updated = announcements_collection.find_one({"_id": announcement_id})
    return updated


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """Delete an announcement (authenticated users only)"""
    if not is_authenticated(username):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if announcement exists
    existing = announcements_collection.find_one({"_id": announcement_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Delete announcement
    result = announcements_collection.delete_one({"_id": announcement_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete announcement")
    
    return {"message": "Announcement deleted successfully"}
