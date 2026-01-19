# Stop EventPulse - PowerShell version
Write-Host "🛑 Stopping EventPulse..." -ForegroundColor Yellow

docker-compose down

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ EventPulse stopped successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to stop services!" -ForegroundColor Red
}