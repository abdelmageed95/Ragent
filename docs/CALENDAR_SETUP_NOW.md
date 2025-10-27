# ⚡ Google Calendar Setup - Quick Action Required

## 🚨 Current Status

Your calendar integration is **almost ready** but needs authentication!

### What's Working:
✅ Dependencies installed
✅ Code integrated
✅ credentials.json exists
✅ API routes ready

### What's Missing:
❌ Google Calendar API not enabled yet
❌ OAuth2 authentication not completed
❌ token.json not created

---

## 🚀 Complete Setup in 3 Steps

### Step 1: Enable Google Calendar API (2 minutes)

1. Go to **[Google Cloud Console](https://console.cloud.google.com/)**
2. Select your project: `meta-triode-374809`
3. Navigate to **APIs & Services → Library**
4. Search for **"Google Calendar API"**
5. Click **"Enable"**

### Step 2: Configure OAuth Consent (3 minutes)

1. Go to **APIs & Services → OAuth consent screen**
2. If not configured:
   - Choose **External** user type
   - App name: "AI Assistant Calendar"
   - Your email for support
   - Your email for developer contact
   - Click **Save and Continue**

3. **Add Scopes**:
   - Click **Add or Remove Scopes**
   - Find and add:
     - `https://www.googleapis.com/auth/calendar.readonly`
     - `https://www.googleapis.com/auth/calendar.events`
   - Click **Update** → **Save and Continue**

4. **Add Test Users**:
   - Click **Add Users**
   - Add your Google account email
   - Click **Add** → **Save and Continue**

### Step 3: Authenticate (1 minute)

Run the authentication test:

```bash
python3 test_calendar_auth.py
```

This will:
1. Open your browser
2. Ask you to sign in with Google
3. Request calendar permissions
4. Save authentication token
5. Test by fetching your events

---

## 📝 What Happens After Authentication

Once authenticated, you can use natural language:

### View Calendar
```
"Show my meetings today"
"What's on my calendar tomorrow?"
```

### Create Meetings (2-Step Process)

**Step 1 - Request:**
```
"Schedule a meeting with john@example.com tomorrow at 2 PM"
```

**AI Response:**
```
I've created a proposal:

Title: Meeting with john@example.com
Start: 2025-10-19 14:00:00
Attendees: john@example.com
Google Meet: Yes

Proposal ID: proposal_0

Say "approve" or "yes" to create this event
```

**Step 2 - Approve:**
```
"yes"  or  "approve"  or  "approved"
```

**AI Response:**
```
✅ Event created!
📅 Calendar Link: https://calendar.google.com/...
📹 Meet Link: https://meet.google.com/...
```

---

## 🔧 Troubleshooting

### "API not enabled"
→ Complete Step 1 above

### "Authentication failed"
→ Complete Step 2 (OAuth consent + test users)

### "Access denied"
→ Make sure you added your email as a test user

### "Browser doesn't open"
→ Copy the URL from terminal and open manually

### "Invalid credentials"
→ Re-download credentials.json from Google Cloud Console

---

## 🎯 Quick Test Commands

After authentication, try these:

1. **View events:**
   ```
   Show my meetings this week
   ```

2. **Create test meeting:**
   ```
   Schedule a test meeting tomorrow at 3 PM for 30 minutes
   ```

3. **Approve it:**
   ```
   yes
   ```

4. **Check Google Calendar** - your event should be there!

---

## 📚 Full Documentation

- **Complete Setup Guide**: `docs/GOOGLE_CALENDAR_SETUP.md`
- **Quick Start**: `docs/CALENDAR_QUICK_START.md`
- **Implementation Details**: `docs/CALENDAR_INTEGRATION_SUMMARY.md`

---

## ⚠️ Important Notes

1. **Human Approval Required**: All calendar changes need your approval
2. **Test Mode**: Your app is in testing mode, only works for test users
3. **Token Expiry**: Tokens refresh automatically, no manual action needed
4. **Privacy**: All credentials stored locally, not in database

---

## 🎉 Ready to Go!

After completing the 3 steps above:

1. Run: `python3 test_calendar_auth.py`
2. Complete authentication in browser
3. Start using calendar in your chat!

**Questions?** Check the full setup guide in `docs/GOOGLE_CALENDAR_SETUP.md`
