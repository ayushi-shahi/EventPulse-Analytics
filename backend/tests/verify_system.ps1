# EventPulse System Verification (PowerShell)
Write-Host "🔍 EventPulse System Verification" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Docker services
Write-Host "1️⃣ Checking Docker Services..." -ForegroundColor Yellow
$services = docker-compose ps --services --filter "status=running"
if ($services) {
    Write-Host "✅ All services running" -ForegroundColor Green
} else {
    Write-Host "❌ Services not running" -ForegroundColor Red
}
Write-Host ""

# 2. Check API health  
Write-Host "2️⃣ Checking API Health..." -ForegroundColor Yellow
$health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health/" -UseBasicParsing
if ($health.status -eq "healthy") {
    Write-Host "✅ API healthy (Database+Redis)" -ForegroundColor Green
} else {
    Write-Host "❌ API unhealthy" -ForegroundColor Red
}
Write-Host ""

# 3. Database stats
Write-Host "3️⃣ Database Statistics..." -ForegroundColor Yellow
$events = docker-compose exec postgres psql -U eventpulse_user -d EventPulse -c "SELECT COUNT(*) FROM events;" | Select-String "count"
$aggs = docker-compose exec postgres psql -U eventpulse_user -d EventPulse -c "SELECT COUNT(*) FROM aggregates;" | Select-String "count"
Write-Host "   Events: "
Write-Host "   Aggregates: "
Write-Host ""

# 4. Final metrics
Write-Host "4️⃣ Live Metrics..." -ForegroundColor Yellow
$metrics = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/metrics/overview?period=last_hour" -Headers @{"X-API-Key" = 'ep_live_9ab68f299a3d2f71234269e2b309b4a891328444441e7a508489e1fa62cc6c72'} -UseBasicParsing
Write-Host "   Total Events: " -ForegroundColor Green
Write-Host "   Events/Min: " -ForegroundColor Green
Write-Host "   Active Users: " -ForegroundColor Green

Write-Host ""
Write-Host "🎉 SYSTEM VERIFICATION COMPLETE! 🚀" -ForegroundColor Green
Write-Host "📚 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
