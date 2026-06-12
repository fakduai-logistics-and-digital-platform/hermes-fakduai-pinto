$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

if (-not (Test-Path ".env")) {
  if (Test-Path ".env.example") {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
  } else {
    Write-Host "No .env found. Create one before starting."
    exit 1
  }
}

docker compose -f docker-compose.docker.yml up -d --build

Write-Host ""
Write-Host "Gateway:   http://127.0.0.1:8642/health"
Write-Host "Webhook:   http://127.0.0.1:8642/plugins/pinto/webhook"
Write-Host "Dashboard: http://127.0.0.1:9119/"
