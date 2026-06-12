$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

if (-not (Test-Path ".env")) {
  if (Test-Path ".env.example") { Copy-Item ".env.example" ".env" } else { throw "No .env found" }
}

docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml up -d --build

Write-Host "Waiting for Cloudflare Quick Tunnel URL..."
$url = $null
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 2
  $logs = docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml logs cloudflared 2>&1 | Out-String
  $matches = [regex]::Matches($logs, 'https://[-a-z0-9]+\.trycloudflare\.com')
  if ($matches.Count -gt 0) {
    $url = $matches[$matches.Count - 1].Value
    break
  }
}
if (-not $url) { throw "Cloudflare tunnel URL not found. Run: docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml logs -f cloudflared" }

for ($attempt = 1; $attempt -le 5; $attempt++) {
  try {
    $health = Invoke-RestMethod -Uri "$url/health" -TimeoutSec 15
    if ($health.status -eq "ok") { break }
  } catch {}

  Write-Host "Tunnel $url not ready. Recreating cloudflared..."
  docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml rm -sf cloudflared 2>$null | Out-Null
  docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml up -d cloudflared | Out-Null
  Start-Sleep -Seconds 18
  $logs = docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml logs cloudflared 2>&1 | Out-String
  $matches = [regex]::Matches($logs, 'https://[-a-z0-9]+\.trycloudflare\.com')
  if ($matches.Count -gt 0) { $url = $matches[$matches.Count - 1].Value }
}

try {
  $health = Invoke-RestMethod -Uri "$url/health" -TimeoutSec 15
  if ($health.status -ne "ok") { throw "bad health" }
} catch { throw "Cloudflare tunnel URL is not reachable after retries: $url" }

$webhook = "$url/plugins/pinto/webhook"
$content = Get-Content ".env" -Raw
if ($content -match '(?m)^PINTO_WEBHOOK_URL=') {
  $content = [regex]::Replace($content, '(?m)^PINTO_WEBHOOK_URL=.*$', "PINTO_WEBHOOK_URL=$webhook")
} else {
  $content = $content.TrimEnd() + "`nPINTO_WEBHOOK_URL=$webhook`n"
}
Set-Content -Path ".env" -Value $content -NoNewline

Write-Host ""
Write-Host "Cloudflare URL:"
Write-Host $url
Write-Host ""
Write-Host "Pinto Webhook URL:"
Write-Host $webhook
Write-Host ""
Write-Host "Health:"
Invoke-RestMethod -Uri "$url/health" -TimeoutSec 15 | ConvertTo-Json -Compress
Write-Host ""
Write-Host "Webhook health:"
Invoke-RestMethod -Uri $webhook -TimeoutSec 15 | ConvertTo-Json -Compress
