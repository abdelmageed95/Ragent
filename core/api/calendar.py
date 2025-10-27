"""
Calendar API endpoints with human-in-the-loop verification
"""

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel
from typing import Optional, List
import json
from tools.google_calendar_tool import calendar_tool

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class CreateEventRequest(BaseModel):
    """Request model for creating calendar event"""
    summary: str
    start_datetime: str
    end_datetime: Optional[str] = None
    duration_minutes: int = 60
    attendees: Optional[List[str]] = None
    description: Optional[str] = None
    location: Optional[str] = None
    add_meet_link: bool = True


class GetEventsRequest(BaseModel):
    """Request model for getting calendar events"""
    date: Optional[str] = None
    days_ahead: int = 7
    max_results: int = 10


class ApprovalRequest(BaseModel):
    """Request model for approving/rejecting proposals"""
    proposal_id: str
    approved: bool
    reason: Optional[str] = None


@router.get("/events")
async def get_events(date: Optional[str] = None, days_ahead: int = 7, max_results: int = 10):
    """
    Get calendar events for a specific date or range

    Args:
        date: Specific date (e.g., "2025-10-20", "tomorrow")
        days_ahead: Number of days to look ahead
        max_results: Maximum number of events

    Returns:
        Calendar events
    """
    try:
        result = calendar_tool.get_events(
            date=date,
            days_ahead=days_ahead,
            max_results=max_results
        )

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/propose")
async def propose_event(request: CreateEventRequest):
    """
    Create a proposal for a new calendar event

    Args:
        request: Event details

    Returns:
        Proposal details awaiting approval
    """
    try:
        result = calendar_tool.create_event_proposal(
            summary=request.summary,
            start_datetime=request.start_datetime,
            end_datetime=request.end_datetime,
            duration_minutes=request.duration_minutes,
            attendees=request.attendees,
            description=request.description,
            location=request.location,
            add_meet_link=request.add_meet_link
        )

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending")
async def get_pending_actions():
    """
    Get all pending actions awaiting approval

    Returns:
        List of pending actions
    """
    try:
        pending = calendar_tool.get_pending_actions()
        return {
            "status": "success",
            "count": len(pending),
            "pending_actions": pending
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve")
async def approve_action(request: ApprovalRequest):
    """
    Approve or reject a pending action

    Args:
        request: Approval/rejection details

    Returns:
        Result of approval/rejection
    """
    try:
        if request.approved:
            result = calendar_tool.approve_action(request.proposal_id)
        else:
            result = calendar_tool.reject_action(request.proposal_id, request.reason)

        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["message"])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/authenticate")
async def authenticate():
    """
    Trigger Google Calendar authentication

    Returns:
        Authentication status
    """
    try:
        success = calendar_tool.authenticate()
        if success:
            return {"status": "success", "message": "Authentication successful"}
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
