# Google Calendar Integration - Quick Start

## 🚀 5-Minute Setup

### 1. Get Google Calendar Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable **Google Calendar API**
4. Create **OAuth 2.0 Desktop credentials**
5. Download as `credentials.json` → place in project root

### 2. Install Dependencies

```bash
pip install google-auth-oauthlib google-api-python-client google-auth python-dateutil
```

### 3. Start Using

Run your application and try:

```
"Show my meetings today"
"Schedule a meeting with john@example.com tomorrow at 2 PM"
```

First use will open a browser for Google authentication.

---

## 📋 Common Commands

### View Calendar
- "Show my meetings today"
- "What's on my calendar tomorrow?"
- "List events for next Monday"

### Create Meetings (Requires Approval)
- "Schedule a meeting with [email] at [time]"
- "Create a 1-hour meeting about [topic] with [email] at [time]"
- "Book a video call with [email] [date] at [time]"

### Manage Proposals
- "Approve proposal_0" - Create the event
- "Reject proposal_0" - Cancel the proposal
- "Show pending actions" - See what's waiting

---

## 🔒 Human-in-the-Loop

**All calendar changes require your approval!**

1. AI creates a **proposal** (not on calendar yet)
2. You review the details
3. You approve or reject
4. Only approved events are created

This prevents accidental meetings and gives you full control.

---

## 🛠️ Troubleshooting

**"Credentials not found"**
→ Place `credentials.json` in project root

**"Authentication failed"**
→ Delete `token.json` and try again

**"API not enabled"**
→ Enable Google Calendar API in Cloud Console

---

## 📚 Full Documentation

See [GOOGLE_CALENDAR_SETUP.md](./GOOGLE_CALENDAR_SETUP.md) for complete setup guide.

---

## 🎯 Example Workflow

```
You: "Schedule a meeting with alice@example.com tomorrow at 3 PM for 1 hour"

AI: "I've prepared a calendar event for your approval:

     Title: Meeting with alice@example.com
     Start: 2025-10-19 15:00:00
     End: 2025-10-19 16:00:00
     Attendees: alice@example.com
     Google Meet: Will be added

     Proposal ID: proposal_0

     To approve: 'Approve proposal_0'
     To reject: 'Reject proposal_0'"

You: "Approve proposal_0"

AI: "✅ Event 'Meeting with alice@example.com' has been created!

     📅 Event Details:
     - Start: 2025-10-19T15:00:00Z
     - End: 2025-10-19T16:00:00Z
     - Calendar Link: https://calendar.google.com/...
     - Google Meet: https://meet.google.com/..."
```

---

**That's it! You're ready to manage your calendar with AI assistance.**
