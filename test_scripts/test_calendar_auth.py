#!/usr/bin/env python3
"""
Test script to authenticate with Google Calendar
Run this once to complete OAuth2 authentication
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.google_calendar_tool import GoogleCalendarTool

def main():
    print("🔐 Google Calendar Authentication Test")
    print("=" * 50)
    print()

    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("❌ Error: credentials.json not found!")
        print()
        print("Please follow these steps:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable Google Calendar API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download as 'credentials.json'")
        print("6. Place in project root")
        print()
        print("📚 See docs/GOOGLE_CALENDAR_SETUP.md for details")
        return 1

    print("✅ Found credentials.json")
    print()

    # Initialize calendar tool
    print("🔄 Initializing calendar tool...")
    tool = GoogleCalendarTool()

    # Authenticate (will open browser first time)
    print("🔐 Authenticating with Google Calendar...")
    print("   (Browser will open for first-time authentication)")
    print()

    try:
        success = tool.authenticate()
        if success:
            print("✅ Authentication successful!")
            print()

            # Try to get events
            print("📅 Testing: Fetching calendar events...")
            result = tool.get_events(days_ahead=7, max_results=5)

            if result["status"] == "success":
                count = result.get("count", 0)
                print(f"✅ Successfully retrieved {count} events!")
                print()

                if count > 0:
                    print("Recent events:")
                    for event in result["events"][:3]:
                        print(f"  - {event.get('summary', 'No title')}")
                        print(f"    Start: {event.get('start')}")
                        if event.get('meet_link'):
                            print(f"    Meet: {event.get('meet_link')}")
                        print()

                print("=" * 50)
                print("🎉 Calendar integration is ready!")
                print()
                print("You can now:")
                print("  - View events: 'Show my meetings today'")
                print("  - Create events: 'Schedule meeting with ...'")
                print()
                return 0
            else:
                print(f"❌ Error fetching events: {result.get('message')}")
                return 1
        else:
            print("❌ Authentication failed!")
            print()
            print("Troubleshooting:")
            print("  - Check credentials.json is valid")
            print("  - Enable Google Calendar API in Cloud Console")
            print("  - Add your email as a test user")
            return 1

    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("   Make sure credentials.json is in the project root")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print()
        print("Check docs/GOOGLE_CALENDAR_SETUP.md for help")
        return 1

if __name__ == "__main__":
    sys.exit(main())
