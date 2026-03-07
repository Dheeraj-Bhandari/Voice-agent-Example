#!/bin/bash
# Setup SIP trunk for LiveKit self-hosted

set -e

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
LIVEKIT_URL=${LIVEKIT_URL:-"http://localhost:7880"}
LIVEKIT_API_KEY=${LIVEKIT_API_KEY:-"devkey"}
LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET:-"secret"}

echo "=== LiveKit SIP Trunk Setup ==="
echo "LiveKit URL: $LIVEKIT_URL"
echo ""

# Check if livekit-cli is installed
if ! command -v livekit-cli &> /dev/null; then
    echo "livekit-cli not found. Install from:"
    echo "https://github.com/livekit/livekit-cli/releases"
    exit 1
fi

# Get SIP provider details
read -p "SIP Provider Address (e.g., xxxxx.sip.vobiz.ai): " SIP_ADDRESS
read -p "Phone Number (E.164 format, e.g., +911171366938): " PHONE_NUMBER
read -p "SIP Username: " SIP_USERNAME
read -s -p "SIP Password: " SIP_PASSWORD
echo ""

# Create outbound trunk
echo ""
echo "Creating outbound SIP trunk..."

TRUNK_RESULT=$(livekit-cli sip trunk create \
    --address "$SIP_ADDRESS" \
    --numbers "$PHONE_NUMBER" \
    --username "$SIP_USERNAME" \
    --password "$SIP_PASSWORD" \
    2>&1)

echo "$TRUNK_RESULT"

# Extract trunk ID
TRUNK_ID=$(echo "$TRUNK_RESULT" | grep -oP 'ST_[a-zA-Z0-9]+' | head -1)

if [ -n "$TRUNK_ID" ]; then
    echo ""
    echo "=== SUCCESS ==="
    echo "Trunk ID: $TRUNK_ID"
    echo ""
    echo "Add to your .env file:"
    echo "SIP_OUTBOUND_TRUNK_ID=$TRUNK_ID"
else
    echo "Failed to create trunk. Check the output above."
    exit 1
fi
