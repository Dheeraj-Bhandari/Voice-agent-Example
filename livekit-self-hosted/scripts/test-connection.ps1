# Test LiveKit self-hosted connection (Windows)

Write-Host "=== LiveKit Connection Test ===" -ForegroundColor Cyan

# Test Redis
Write-Host -NoNewline "Redis: "
try {
    $result = docker compose exec -T redis redis-cli ping 2>$null
    if ($result -match "PONG") {
        Write-Host "Connected" -ForegroundColor Green
    } else {
        Write-Host "Not responding" -ForegroundColor Red
    }
} catch {
    Write-Host "Not responding" -ForegroundColor Red
}

# Test LiveKit Server
Write-Host -NoNewline "LiveKit Server: "
try {
    $response = Invoke-WebRequest -Uri "http://localhost:7880" -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Host "Running on port 7880" -ForegroundColor Green
} catch {
    Write-Host "Not responding" -ForegroundColor Red
}

# Check containers
Write-Host ""
Write-Host "=== Container Status ===" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "=== Recent Logs ===" -ForegroundColor Cyan
docker compose logs --tail=5 livekit-server 2>$null
