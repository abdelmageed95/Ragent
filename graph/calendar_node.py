"""
Calendar management node for LangGraph workflow
Handles Google Calendar and Meet operations with human-in-the-loop verification
"""

from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import add_messages
from tools.google_calendar_tool import calendar_tool
import json
from datetime import datetime


class CalendarState(TypedDict):
    """State for calendar operations"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    calendar_action: str
    calendar_result: dict
    pending_approval: bool
    proposal_id: str


def calendar_node(state: CalendarState) -> CalendarState:
    """
    Calendar management node - handles calendar operations

    Args:
        state: Current workflow state

    Returns:
        Updated state with calendar results
    """
    messages = state.get("messages", [])

    if not messages:
        return state

    # Get the last message
    last_message = messages[-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)

    # Determine calendar action
    user_input_lower = user_input.lower()

    result = None
    pending_approval = False
    proposal_id = None
    action = "none"

    try:
        # Check for event viewing requests
        if any(keyword in user_input_lower for keyword in ["show", "see", "view", "list", "what's on", "my meetings", "my schedule"]):
            action = "view_events"

            # Parse date from query
            date_param = None
            if "today" in user_input_lower:
                date_param = "today"
            elif "tomorrow" in user_input_lower:
                date_param = "tomorrow"
            elif any(day in user_input_lower for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]):
                for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                    if day in user_input_lower:
                        date_param = f"next {day}"
                        break

            # Get events
            result = calendar_tool.get_events(date=date_param, days_ahead=7, max_results=10)

            # Format response
            if result["status"] == "success":
                events = result.get("events", [])
                if events:
                    response_text = f"I found {len(events)} event(s):\n\n"
                    for i, event in enumerate(events, 1):
                        start = event.get('start', 'Unknown time')
                        summary = event.get('summary', 'No title')
                        attendees = event.get('attendees', [])
                        meet_link = event.get('meet_link')

                        response_text += f"{i}. **{summary}**\n"
                        response_text += f"   Time: {start}\n"
                        if attendees:
                            response_text += f"   Attendees: {', '.join(attendees)}\n"
                        if meet_link:
                            response_text += f"   Meet Link: {meet_link}\n"
                        response_text += "\n"
                else:
                    response_text = "No events found for the specified period."
            else:
                response_text = f"Error retrieving events: {result.get('message', 'Unknown error')}"

        # Check for event creation requests
        elif any(keyword in user_input_lower for keyword in ["create", "schedule", "book", "add meeting", "set up meeting"]):
            action = "create_event"

            # Try to extract event details from natural language
            # This is a simple extraction - you can enhance with NLP
            event_details = extract_event_details(user_input)

            if not event_details.get('summary') or not event_details.get('start_datetime'):
                response_text = (
                    "I need more information to create a meeting. Please provide:\n"
                    "- Meeting title/summary\n"
                    "- Date and time\n"
                    "- Attendees (optional)\n\n"
                    "Example: 'Create a meeting with john@example.com tomorrow at 2 PM for 1 hour about project review'"
                )
            else:
                # Create proposal
                result = calendar_tool.create_event_proposal(
                    summary=event_details['summary'],
                    start_datetime=event_details['start_datetime'],
                    duration_minutes=event_details.get('duration', 60),
                    attendees=event_details.get('attendees'),
                    description=event_details.get('description'),
                    add_meet_link=event_details.get('add_meet_link', True)
                )

                if result["status"] == "pending_approval":
                    pending_approval = True
                    proposal_id = result.get("proposal_id")

                    proposal = result.get("proposal", {})
                    response_text = (
                        "I've prepared a calendar event for your approval:\n\n"
                        f"**Title:** {proposal.get('summary')}\n"
                        f"**Start:** {proposal.get('start')}\n"
                        f"**End:** {proposal.get('end')}\n"
                    )

                    if proposal.get('attendees'):
                        response_text += f"**Attendees:** {', '.join(proposal.get('attendees', []))}\n"

                    if proposal.get('description'):
                        response_text += f"**Description:** {proposal.get('description')}\n"

                    if proposal.get('add_meet_link'):
                        response_text += "**Google Meet:** Will be added\n"

                    response_text += (
                        f"\n**Proposal ID:** `{proposal_id}`\n\n"
                        "Please approve or reject this event:\n"
                        "- To approve: 'Approve proposal [ID]'\n"
                        "- To reject: 'Reject proposal [ID]'"
                    )
                else:
                    response_text = f"Error creating proposal: {result.get('message', 'Unknown error')}"

        # Check for approval/rejection
        elif "approve" in user_input_lower or "reject" in user_input_lower:
            # Extract proposal ID
            words = user_input.split()
            prop_id = None
            for i, word in enumerate(words):
                if "proposal" in word.lower() and i + 1 < len(words):
                    prop_id = words[i + 1].strip('.,!?')
                    break

            if not prop_id:
                response_text = "Please specify the proposal ID to approve or reject."
            else:
                if "approve" in user_input_lower:
                    action = "approve"
                    result = calendar_tool.approve_action(prop_id)

                    if result["status"] == "success":
                        event = result.get("event", {})
                        response_text = (
                            f"Event '{event.get('summary')}' has been created successfully!\n\n"
                            f"**Link:** {event.get('link')}\n"
                        )
                        if event.get('meet_link'):
                            response_text += f"**Google Meet:** {event.get('meet_link')}\n"
                    else:
                        response_text = f"Error approving event: {result.get('message', 'Unknown error')}"
                else:
                    action = "reject"
                    result = calendar_tool.reject_action(prop_id, reason="User rejected")
                    response_text = f"Proposal {prop_id} has been rejected."

        # Check for pending actions
        elif "pending" in user_input_lower or "waiting" in user_input_lower:
            action = "view_pending"
            pending_actions = calendar_tool.get_pending_actions()

            if pending_actions:
                response_text = f"You have {len(pending_actions)} pending action(s):\n\n"
                for action_item in pending_actions:
                    response_text += f"**ID:** `{action_item.get('id')}`\n"
                    response_text += f"**Action:** {action_item.get('action')}\n"
                    if action_item.get('summary'):
                        response_text += f"**Summary:** {action_item.get('summary')}\n"
                    response_text += "\n"
            else:
                response_text = "No pending actions."

        else:
            response_text = (
                "I can help you with:\n"
                "- View your calendar events (e.g., 'Show my meetings today')\n"
                "- Create new meetings (e.g., 'Schedule a meeting with john@example.com tomorrow at 2 PM')\n"
                "- Approve/reject pending actions (e.g., 'Approve proposal_0')\n"
                "- View pending actions (e.g., 'Show pending actions')\n"
            )
            action = "help"

    except Exception as e:
        response_text = f"Error processing calendar request: {str(e)}"
        result = {"status": "error", "message": str(e)}

    # Add AI response to messages
    response_message = AIMessage(content=response_text)

    return {
        "messages": [response_message],
        "calendar_action": action,
        "calendar_result": result or {},
        "pending_approval": pending_approval,
        "proposal_id": proposal_id or ""
    }


def extract_event_details(user_input: str) -> dict:
    """
    Extract event details from natural language input

    Args:
        user_input: User's natural language input

    Returns:
        Dictionary with extracted event details
    """
    import re
    from dateutil import parser

    details = {}

    # Extract email addresses (attendees)
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, user_input)
    if emails:
        details['attendees'] = emails

    # Extract date/time
    # Look for common patterns
    user_lower = user_input.lower()

    # Try to find "at" followed by time
    time_match = re.search(r'at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', user_input, re.IGNORECASE)
    date_str = None

    if "tomorrow" in user_lower:
        date_str = "tomorrow"
    elif "today" in user_lower:
        date_str = "today"
    elif "next monday" in user_lower:
        date_str = "next monday"
    elif "next tuesday" in user_lower:
        date_str = "next tuesday"
    elif "next wednesday" in user_lower:
        date_str = "next wednesday"
    elif "next thursday" in user_lower:
        date_str = "next thursday"
    elif "next friday" in user_lower:
        date_str = "next friday"

    # Combine date and time
    if date_str and time_match:
        time_str = time_match.group(1)
        details['start_datetime'] = f"{date_str} {time_str}"
    elif date_str:
        details['start_datetime'] = date_str

    # Extract duration
    duration_match = re.search(r'for\s+(\d+)\s*(hour|minute|hr|min)', user_input, re.IGNORECASE)
    if duration_match:
        value = int(duration_match.group(1))
        unit = duration_match.group(2).lower()
        if 'hour' in unit or 'hr' in unit:
            details['duration'] = value * 60
        else:
            details['duration'] = value

    # Extract summary/title
    # Look for patterns like "about X" or "for X" or "meeting about X"
    summary_match = re.search(r'(?:about|regarding|for|titled?)\s+([^,\.]+)', user_input, re.IGNORECASE)
    if summary_match:
        details['summary'] = summary_match.group(1).strip()
    else:
        # Fallback: use part of the input as summary
        words = user_input.split()
        # Remove common action words
        filtered = [w for w in words if w.lower() not in ['create', 'schedule', 'book', 'meeting', 'with', 'at', 'on']]
        if filtered:
            details['summary'] = ' '.join(filtered[:5])  # First 5 meaningful words

    # Check if Google Meet should be added
    if "meet" in user_lower or "video" in user_lower:
        details['add_meet_link'] = True
    else:
        details['add_meet_link'] = True  # Default to true

    return details
