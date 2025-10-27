"""
Google Calendar and Google Meet Integration Tool
Provides calendar management with human-in-the-loop verification
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.tools import tool

# If modifying these scopes, delete the file token.json
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]


class GoogleCalendarTool:
    """Google Calendar integration with human-in-the-loop verification"""

    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        """
        Initialize Google Calendar tool

        Args:
            credentials_path: Path to OAuth2 credentials JSON file
            token_path: Path to store access token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None
        self.pending_actions = []

    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API

        Returns:
            bool: True if authentication successful
        """
        creds = None

        # Check if token file exists
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Credentials file not found at {self.credentials_path}. "
                        "Please download it from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        try:
            self.service = build('calendar', 'v3', credentials=creds)
            return True
        except Exception as e:
            print(f"Error building service: {e}")
            return False

    def parse_datetime(self, date_str: str, time_str: Optional[str] = None) -> datetime:
        """
        Parse date and time strings into datetime object

        Args:
            date_str: Date string (e.g., "2025-10-20", "tomorrow", "next Monday")
            time_str: Time string (e.g., "14:00", "2:00 PM")

        Returns:
            datetime object
        """
        from dateutil import parser
        from dateutil.relativedelta import relativedelta

        now = datetime.now()

        # Handle relative dates
        date_str_lower = date_str.lower()
        if date_str_lower == "today":
            target_date = now.date()
        elif date_str_lower == "tomorrow":
            target_date = (now + timedelta(days=1)).date()
        elif "next" in date_str_lower and "monday" in date_str_lower:
            days_ahead = 0 - now.weekday() + 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next" in date_str_lower and "tuesday" in date_str_lower:
            days_ahead = 1 - now.weekday() + 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next" in date_str_lower and "wednesday" in date_str_lower:
            days_ahead = 2 - now.weekday() + 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next" in date_str_lower and "thursday" in date_str_lower:
            days_ahead = 3 - now.weekday() + 7
            target_date = (now + timedelta(days=days_ahead)).date()
        elif "next" in date_str_lower and "friday" in date_str_lower:
            days_ahead = 4 - now.weekday() + 7
            target_date = (now + timedelta(days=days_ahead)).date()
        else:
            # Try to parse as date
            target_date = parser.parse(date_str).date()

        # Parse time if provided
        if time_str:
            target_time = parser.parse(time_str).time()
            return datetime.combine(target_date, target_time)
        else:
            return datetime.combine(target_date, datetime.min.time())

    def get_events(
        self,
        date: Optional[str] = None,
        days_ahead: int = 7,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Get calendar events for a specific date or range

        Args:
            date: Specific date (e.g., "2025-10-20", "tomorrow")
            days_ahead: Number of days to look ahead if no date specified
            max_results: Maximum number of events to return

        Returns:
            Dict with status and events list
        """
        if not self.service:
            if not self.authenticate():
                return {"status": "error", "message": "Authentication failed"}

        try:
            # Set time range
            if date:
                start_time = self.parse_datetime(date)
                end_time = start_time + timedelta(days=1)
            else:
                start_time = datetime.now()
                end_time = start_time + timedelta(days=days_ahead)

            # Call the Calendar API
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            # Format events
            formatted_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                formatted_event = {
                    'id': event['id'],
                    'summary': event.get('summary', 'No title'),
                    'start': start,
                    'end': end,
                    'location': event.get('location', 'No location'),
                    'description': event.get('description', 'No description'),
                    'attendees': [a.get('email') for a in event.get('attendees', [])],
                    'meet_link': event.get('hangoutLink', None)
                }
                formatted_events.append(formatted_event)

            return {
                "status": "success",
                "count": len(formatted_events),
                "events": formatted_events
            }

        except HttpError as error:
            return {"status": "error", "message": f"API error: {error}"}

    def create_event_proposal(
        self,
        summary: str,
        start_datetime: str,
        end_datetime: Optional[str] = None,
        duration_minutes: int = 60,
        attendees: Optional[List[str]] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        add_meet_link: bool = True
    ) -> Dict[str, Any]:
        """
        Create a proposal for a new calendar event (requires human approval)

        Args:
            summary: Event title
            start_datetime: Start date and time
            end_datetime: End date and time (optional if duration provided)
            duration_minutes: Duration in minutes if end_datetime not provided
            attendees: List of attendee email addresses
            description: Event description
            location: Event location
            add_meet_link: Whether to add Google Meet link

        Returns:
            Dict with proposal details and approval ID
        """
        try:
            # Parse start time
            start = self.parse_datetime(start_datetime)

            # Calculate end time
            if end_datetime:
                end = self.parse_datetime(end_datetime)
            else:
                end = start + timedelta(minutes=duration_minutes)

            # Create proposal
            proposal = {
                'action': 'create_event',
                'summary': summary,
                'start': start.isoformat(),
                'end': end.isoformat(),
                'attendees': attendees or [],
                'description': description or '',
                'location': location or '',
                'add_meet_link': add_meet_link,
                'timestamp': datetime.now().isoformat()
            }

            # Generate proposal ID
            proposal_id = f"proposal_{len(self.pending_actions)}"
            proposal['id'] = proposal_id

            # Add to pending actions
            self.pending_actions.append(proposal)

            return {
                "status": "pending_approval",
                "proposal_id": proposal_id,
                "proposal": proposal,
                "message": "Event proposal created. Awaiting human approval."
            }

        except Exception as e:
            return {"status": "error", "message": f"Error creating proposal: {str(e)}"}

    def approve_action(self, proposal_id: str) -> Dict[str, Any]:
        """
        Approve and execute a pending action

        Args:
            proposal_id: ID of the proposal to approve

        Returns:
            Dict with execution result
        """
        if not self.service:
            if not self.authenticate():
                return {"status": "error", "message": "Authentication failed"}

        # Find proposal
        proposal = None
        for action in self.pending_actions:
            if action.get('id') == proposal_id:
                proposal = action
                break

        if not proposal:
            return {"status": "error", "message": f"Proposal {proposal_id} not found"}

        try:
            if proposal['action'] == 'create_event':
                # Build event object
                event = {
                    'summary': proposal['summary'],
                    'location': proposal.get('location', ''),
                    'description': proposal.get('description', ''),
                    'start': {
                        'dateTime': proposal['start'],
                        'timeZone': 'UTC',
                    },
                    'end': {
                        'dateTime': proposal['end'],
                        'timeZone': 'UTC',
                    },
                    'attendees': [{'email': email} for email in proposal.get('attendees', [])],
                    'reminders': {
                        'useDefault': False,
                        'overrides': [
                            {'method': 'email', 'minutes': 24 * 60},
                            {'method': 'popup', 'minutes': 10},
                        ],
                    },
                }

                # Add Google Meet link if requested
                if proposal.get('add_meet_link', False):
                    event['conferenceData'] = {
                        'createRequest': {
                            'requestId': f"meet_{proposal_id}",
                            'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                        }
                    }

                # Create the event
                created_event = self.service.events().insert(
                    calendarId='primary',
                    body=event,
                    conferenceDataVersion=1 if proposal.get('add_meet_link') else 0,
                    sendUpdates='all'  # Send email invitations to all attendees
                ).execute()

                # Remove from pending actions
                self.pending_actions.remove(proposal)

                return {
                    "status": "success",
                    "message": "Event created successfully",
                    "event": {
                        'id': created_event['id'],
                        'summary': created_event['summary'],
                        'start': created_event['start'].get('dateTime'),
                        'end': created_event['end'].get('dateTime'),
                        'link': created_event.get('htmlLink'),
                        'meet_link': created_event.get('hangoutLink')
                    }
                }

        except HttpError as error:
            return {"status": "error", "message": f"API error: {error}"}
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}

    def reject_action(self, proposal_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Reject a pending action

        Args:
            proposal_id: ID of the proposal to reject
            reason: Optional reason for rejection

        Returns:
            Dict with rejection status
        """
        # Find and remove proposal
        for action in self.pending_actions:
            if action.get('id') == proposal_id:
                self.pending_actions.remove(action)
                return {
                    "status": "rejected",
                    "proposal_id": proposal_id,
                    "reason": reason or "Rejected by user",
                    "message": "Action rejected and removed from pending list"
                }

        return {"status": "error", "message": f"Proposal {proposal_id} not found"}

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """
        Get all pending actions awaiting approval

        Returns:
            List of pending actions
        """
        return self.pending_actions

    def update_event_proposal(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_datetime: Optional[str] = None,
        end_datetime: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a proposal to update an existing event (requires human approval)

        Args:
            event_id: ID of the event to update
            summary: New event title
            start_datetime: New start date and time
            end_datetime: New end date and time
            description: New description

        Returns:
            Dict with proposal details
        """
        try:
            # Create update proposal
            proposal = {
                'action': 'update_event',
                'event_id': event_id,
                'updates': {},
                'timestamp': datetime.now().isoformat()
            }

            if summary:
                proposal['updates']['summary'] = summary
            if start_datetime:
                proposal['updates']['start'] = self.parse_datetime(start_datetime).isoformat()
            if end_datetime:
                proposal['updates']['end'] = self.parse_datetime(end_datetime).isoformat()
            if description:
                proposal['updates']['description'] = description

            # Generate proposal ID
            proposal_id = f"proposal_{len(self.pending_actions)}"
            proposal['id'] = proposal_id

            # Add to pending actions
            self.pending_actions.append(proposal)

            return {
                "status": "pending_approval",
                "proposal_id": proposal_id,
                "proposal": proposal,
                "message": "Update proposal created. Awaiting human approval."
            }

        except Exception as e:
            return {"status": "error", "message": f"Error creating update proposal: {str(e)}"}


# Tool instance for reuse across the application (MUST be before functions)
calendar_tool = GoogleCalendarTool()


# Convenience functions for LangGraph integration
@tool
def get_calendar_events(date: Optional[str] = None, days_ahead: int = 7) -> str:
    """
    Get calendar events - convenience function for agent use

    Args:
        date: Specific date or relative (e.g., "tomorrow", "2025-10-20")
        days_ahead: Days to look ahead if no date specified

    Returns:
        JSON string with events
    """
    # Use the singleton instance
    result = calendar_tool.get_events(date=date, days_ahead=days_ahead)
    return json.dumps(result, indent=2)


@tool
def create_calendar_event(
    summary: str,
    start_datetime: str,
    attendees: Optional[str] = None,
    duration_minutes: int = 60,
    description: Optional[str] = None,
    add_meet_link: bool = True
) -> str:
    """
    Create a calendar event proposal - convenience function for agent use

    Args:
        summary: Event title
        start_datetime: Start date and time
        attendees: Comma-separated email addresses
        duration_minutes: Duration in minutes
        description: Event description
        add_meet_link: Whether to add Google Meet link

    Returns:
        JSON string with proposal details
    """
    # Parse attendees
    attendee_list = None
    if attendees:
        attendee_list = [email.strip() for email in attendees.split(',')]

    # Use the singleton instance
    result = calendar_tool.create_event_proposal(
        summary=summary,
        start_datetime=start_datetime,
        duration_minutes=duration_minutes,
        attendees=attendee_list,
        description=description,
        add_meet_link=add_meet_link
    )
    return json.dumps(result, indent=2)
