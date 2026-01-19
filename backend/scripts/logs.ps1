# View EventPulse Logs - PowerShell version
param(
    [string]$Service = "all"
)

Write-Host "📋 Viewing logs for: $Service" -ForegroundColor Cyan

if ($Service -eq "all") {
    docker-compose logs -f
} else {
    docker-compose logs -f $Service
}