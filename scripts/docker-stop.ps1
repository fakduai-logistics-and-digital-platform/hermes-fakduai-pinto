$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml down
