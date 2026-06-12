#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
podman-compose -f docker-compose.podman.yml ps
printf '\nHermes health:\n'
curl -sS http://127.0.0.1:8642/health || true
printf '\n\nPinto webhook:\n'
curl -sS http://127.0.0.1:8642/plugins/pinto/webhook || true
printf '\n'
