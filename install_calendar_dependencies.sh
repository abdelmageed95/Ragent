#!/bin/bash
# Install Google Calendar integration dependencies

echo "📦 Installing Google Calendar & Meet integration dependencies..."

pip install google-auth-oauthlib>=1.0.0
pip install google-api-python-client>=2.100.0
pip install google-auth>=2.23.0
pip install python-dateutil

echo "✅ Google Calendar dependencies installed!"
echo ""
echo "Next steps:"
echo "1. Go to https://console.cloud.google.com/"
echo "2. Create a new project"
echo "3. Enable Google Calendar API"
echo "4. Create OAuth 2.0 credentials"
echo "5. Download as 'credentials.json' and place in project root"
echo ""
echo "📚 See docs/GOOGLE_CALENDAR_SETUP.md for detailed instructions"
