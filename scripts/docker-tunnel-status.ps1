$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml ps

$logs = docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml logs cloudflared 2>&1 | Out-String
$matches = [regex]::Matches($logs, 'https://[-a-z0-9]+\.trycloudflare\.com')
if ($matches.Count -eq 0) {
  Write-Host "Cloudflare URL not found."
  exit 1
}
$url = $matches[$matches.Count - 1].Value
$webhook = "$url/plugins/pinto/webhook"

Write-Host ""
Write-Host "Cloudflare URL:"
Write-Host $url
Write-Host ""
Write-Host "Pinto Webhook URL:"
Write-Host $webhook
Write-Host ""
Write-Host "Health:"
try { Invoke-RestMethod -Uri "$url/health" -TimeoutSec 15 | ConvertTo-Json -Compress } catch { Write-Host $_.Exception.Message }
Write-Host ""
Write-Host "Webhook health:"
try { Invoke-RestMethod -Uri $webhook -TimeoutSec 15 | ConvertTo-Json -Compress } catch { Write-Host $_.Exception.Message }
