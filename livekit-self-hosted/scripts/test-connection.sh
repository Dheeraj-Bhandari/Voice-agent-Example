#!/bin/bash
# Test LiveKit self-hosted connection

echo "=== LiveKit Connection Test ==="

# Test Redis
echo -n "Redis: "
if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
    echo "✓ Connected"
else
    echo "✗ Not responding"
fi

# Test LiveKit Server
echo -n "LiveKit Server: "
if curl -s http://localhost:7880 > /dev/null 2>&1; then
    echo "✓ Running on port 7880"
else
    echo "✗ Not responding"
fi

# Test SIP port
echo -n "SIP Port (5060): "
if netstat -tuln 2>/dev/null | grep -q ":5060 " || ss -tuln 2>/dev/null | grep -q ":5060 "; then
    echo "✓ Listening"
else
    echo "✗ Not listening"
fi

# Check containers
echo ""
echo "=== Container Status ==="
docker compose ps

echo ""
echo "=== Recent Logs ==="
docker compose logs --tail=5 livekit-server 2>/dev/null || echo "No logs available"
