# Google Calendar & Meet Integration Setup Guide

This guide will help you set up Google Calendar and Google Meet integration with human-in-the-loop verification for your AI assistant.

## Table of Contents
1. [Features](#features)
2. [Prerequisites](#prerequisites)
3. [Google Cloud Setup](#google-cloud-setup)
4. [Installation](#installation)
5. [Authentication](#authentication)
6. [Usage Examples](#usage-examples)
7. [API Endpoints](#api-endpoints)
8. [Human-in-the-Loop Workflow](#human-in-the-loop-workflow)
9. [Troubleshooting](#troubleshooting)

---

## Features

- **View Calendar Events**: Check your schedule for specific dates or ranges
- **Create Meeting Proposals**: AI creates meeting proposals that require your approval
- **Google Meet Integration**: Automatically add Google Meet links to meetings
- **Human-in-the-Loop Verification**: All calendar modifications require explicit user approval
- **Natural Language Processing**: Create meetings using conversational commands
- **Email Invitations**: Automatically invite attendees to meetings

---

## Prerequisites

Before you begin, ensure you have:

1. A Google account with Google Calendar access
2. Python 3.8 or higher installed
3. Access to [Google Cloud Console](https://console.cloud.google.com/)

---

## Google Cloud Setup

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter a project name (e.g., "AI Calendar Assistant")
4. Click **"Create"**

### Step 2: Enable Google Calendar API

1. In your project, go to **"APIs & Services"** → **"Library"**
2. Search for **"Google Calendar API"**
3. Click on it and press **"Enable"**

### Step 3: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. If prompted, configure the OAuth consent screen:
   - Choose **"External"** user type
   - Fill in required fields:
     - App name: "AI Calendar Assistant"
     - User support email: Your email
     - Developer contact: Your email
   - Click **"Save and Continue"**
   - Add scopes:
     - `https://www.googleapis.com/auth/calendar.readonly`
     - `https://www.googleapis.com/auth/calendar.events`
   - Click **"Save and Continue"**
   - Add test users (your Google account email)
   - Click **"Save and Continue"**

4. Back in **"Credentials"**, click **"Create Credentials"** → **"OAuth client ID"**
5. Choose **"Desktop app"** as application type
6. Name it (e.g., "Calendar Desktop Client")
7. Click **"Create"**

### Step 4: Download Credentials

1. After creating the OAuth client, click the **Download** icon (⬇️) next to your client ID
2. Save the file as `credentials.json` in your project root directory

---

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install the specific packages:

```bash
pip install google-auth-oauthlib google-api-python-client google-auth python-dateutil
```

### 2. Place Credentials File

Ensure your `credentials.json` file is in the project root:

```
agentic-rag/
├── credentials.json          ← Place it here
├── main.py
├── tools/
│   └── google_calendar_tool.py
└── ...
```

---

## Authentication

### First-Time Authentication

1. Start your application:
   ```bash
   python main.py
   ```

2. The first time you use a calendar feature, a browser window will open
3. Sign in with your Google account
4. Grant the requested permissions:
   - View and edit events on all your calendars
5. After approval, a `token.json` file will be created automatically

### Token Management

- **`credentials.json`**: Your OAuth client credentials (never share!)
- **`token.json`**: Your access and refresh tokens (created automatically)
- **Security**: Add both files to `.gitignore` to prevent accidental commits

```bash
# Add to .gitignore
echo "credentials.json" >> .gitignore
echo "token.json" >> .gitignore
```

---

## Usage Examples

### Conversational Commands

The AI assistant can understand natural language for calendar operations:

#### View Calendar Events

```
"Show my meetings today"
"What's on my calendar tomorrow?"
"List my events for next Monday"
"What meetings do I have this week?"
```

#### Create Meeting Proposals

```
"Schedule a meeting with john@example.com tomorrow at 2 PM"
"Create a 1-hour meeting about project review with team@company.com at 3 PM today"
"Book a meeting with alice@example.com next Friday at 10 AM for 30 minutes"
"Set up a video call with bob@example.com tomorrow at 11 AM"
```

#### Approve/Reject Proposals

After the AI creates a proposal, you'll receive a proposal ID. Use:

```
"Approve proposal_0"
"Reject proposal_0"
```

#### Check Pending Actions

```
"Show pending actions"
"What's waiting for my approval?"
```

---

## API Endpoints

### Get Calendar Events

**Endpoint**: `GET /api/calendar/events`

**Parameters**:
- `date` (optional): Specific date (e.g., "2025-10-20", "tomorrow")
- `days_ahead` (optional): Number of days to look ahead (default: 7)
- `max_results` (optional): Maximum events to return (default: 10)

**Example**:
```bash
curl "http://localhost:8000/api/calendar/events?date=tomorrow"
```

### Create Event Proposal

**Endpoint**: `POST /api/calendar/events/propose`

**Body**:
```json
{
  "summary": "Team Meeting",
  "start_datetime": "tomorrow 2 PM",
  "duration_minutes": 60,
  "attendees": ["john@example.com", "jane@example.com"],
  "description": "Weekly team sync",
  "add_meet_link": true
}
```

### Get Pending Actions

**Endpoint**: `GET /api/calendar/pending`

**Example**:
```bash
curl "http://localhost:8000/api/calendar/pending"
```

### Approve/Reject Action

**Endpoint**: `POST /api/calendar/approve`

**Body**:
```json
{
  "proposal_id": "proposal_0",
  "approved": true,
  "reason": "Optional rejection reason"
}
```

---

## Human-in-the-Loop Workflow

### How It Works

1. **User Request**: "Create a meeting with john@example.com tomorrow at 2 PM"

2. **AI Processing**:
   - Extracts meeting details from natural language
   - Creates a proposal (not yet on calendar)
   - Generates a unique proposal ID

3. **Proposal Presentation**:
   ```
   I've prepared a calendar event for your approval:

   Title: Meeting with john@example.com
   Start: 2025-10-19 14:00:00
   End: 2025-10-19 15:00:00
   Attendees: john@example.com
   Google Meet: Will be added

   Proposal ID: proposal_0

   Please approve or reject this event:
   - To approve: 'Approve proposal_0'
   - To reject: 'Reject proposal_0'
   ```

4. **User Approval**: User says "Approve proposal_0"

5. **Event Creation**:
   - Event is created on Google Calendar
   - Invitations sent to attendees
   - Google Meet link generated
   - Confirmation sent to user

### Why Human-in-the-Loop?

- **Safety**: Prevents accidental meeting creation
- **Control**: You review all details before committing
- **Corrections**: Catch errors in date/time/attendees before sending
- **Privacy**: Ensure sensitive meetings are handled correctly

---

## Troubleshooting

### Issue: "Credentials file not found"

**Solution**:
- Ensure `credentials.json` is in the project root
- Re-download from Google Cloud Console if needed

### Issue: "Authentication failed"

**Solution**:
1. Delete `token.json`
2. Re-run the application
3. Complete the authentication flow again

### Issue: "Insufficient permissions"

**Solution**:
1. Go to Google Cloud Console
2. Check OAuth consent screen scopes
3. Ensure these scopes are added:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/calendar.events`

### Issue: "API not enabled"

**Solution**:
1. Go to Google Cloud Console
2. Navigate to "APIs & Services" → "Library"
3. Search for "Google Calendar API"
4. Click "Enable"

### Issue: "Token expired"

**Solution**:
- The tool automatically refreshes tokens
- If issues persist, delete `token.json` and re-authenticate

### Issue: "Meet link not created"

**Solution**:
1. Ensure you have Google Workspace (not personal Gmail)
2. Or use a Google account with Google Meet access
3. Some Google accounts may have restrictions on Meet link creation

---

## Security Best Practices

### Credentials Protection

1. **Never commit credentials**:
   ```bash
   # .gitignore
   credentials.json
   token.json
   ```

2. **Restrict file permissions**:
   ```bash
   chmod 600 credentials.json
   chmod 600 token.json
   ```

3. **Use environment-specific credentials**:
   - Development: One OAuth client
   - Production: Separate OAuth client with stricter controls

### OAuth Consent Screen

- Keep your app in "Testing" mode for personal use
- Add only trusted users as test users
- For production, complete app verification process

### Token Storage

- Current implementation stores tokens in `token.json`
- For production, consider:
  - Encrypted token storage
  - Database-backed token management
  - Per-user token isolation

---

## Advanced Configuration

### Custom Token Storage

Modify `google_calendar_tool.py` to use custom token storage:

```python
calendar_tool = GoogleCalendarTool(
    credentials_path="path/to/credentials.json",
    token_path="path/to/token.json"
)
```

### Timezone Handling

By default, times are in UTC. To use local timezone:

```python
from datetime import timezone
import pytz

# Set your timezone
local_tz = pytz.timezone('America/New_York')
```

### Calendar Selection

To use a specific calendar (not primary):

Modify the `service.events().list()` call in `google_calendar_tool.py`:

```python
events_result = self.service.events().list(
    calendarId='your-calendar-id@group.calendar.google.com',
    # ... other parameters
).execute()
```

---

## Next Steps

1. ✅ Complete Google Cloud setup
2. ✅ Install dependencies
3. ✅ Place credentials file
4. ✅ Test authentication
5. ✅ Try viewing calendar events
6. ✅ Create a test meeting proposal
7. ✅ Approve/reject the proposal
8. 🚀 Integrate into your workflow!

---

## Support & Resources

- **Google Calendar API Docs**: https://developers.google.com/calendar/api
- **OAuth 2.0 Guide**: https://developers.google.com/identity/protocols/oauth2
- **Python Quickstart**: https://developers.google.com/calendar/api/quickstart/python

---

**Note**: This integration is designed for personal or internal team use. For public applications serving multiple users, additional OAuth verification and security measures are required.
