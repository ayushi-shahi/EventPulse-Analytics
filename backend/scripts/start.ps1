# Start EventPulse - PowerShell version
Write-Host "🚀 Starting EventPulse..." -ForegroundColor Green

# Check if Docker is running
$dockerRunning = docker ps 2>$null
if (-not $dockerRunning) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "⏳ Starting services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "📦 Running database migrations..." -ForegroundColor Yellow
docker-compose exec api alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ EventPulse is running!" -ForegroundColor Green
    Write-Host "📚 API Docs: http://localhost:8002/docs" -ForegroundColor Cyan
    Write-Host "💚 Health: http://localhost:8002/api/v1/health/" -ForegroundColor Cyan
} else {
    Write-Host "❌ Migration failed!" -ForegroundColor Red
    docker-compose logs api
}