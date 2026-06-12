$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

docker compose -f docker-compose.docker.yml ps

Write-Host ""
Write-Host "Gateway health:"
try { Invoke-RestMethod -Uri "http://127.0.0.1:8642/health" -TimeoutSec 10 | ConvertTo-Json -Compress } catch { Write-Host $_.Exception.Message }

Write-Host ""
Write-Host "Webhook health:"
try { Invoke-RestMethod -Uri "http://127.0.0.1:8642/plugins/pinto/webhook" -TimeoutSec 10 | ConvertTo-Json -Compress } catch { Write-Host $_.Exception.Message }

Write-Host ""
Write-Host "Dashboard: http://127.0.0.1:9119/"
