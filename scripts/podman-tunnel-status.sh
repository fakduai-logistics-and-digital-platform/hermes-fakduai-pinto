#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml ps
URL="$(podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml logs cloudflared 2>&1 | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' | tail -1 || true)"
if [ -n "$URL" ]; then
  WEBHOOK_URL="$URL/plugins/pinto/webhook"
  printf '\nCloudflare URL:\n%s\n\nPinto Webhook URL:\n%s\n\n' "$URL" "$WEBHOOK_URL"
  printf 'Health:\n'
  curl -sS "$URL/health" || true
  printf '\n\nWebhook health:\n'
  curl -sS "$WEBHOOK_URL" || true
  printf '\n'
else
  echo "No Cloudflare Quick Tunnel URL found. Start with scripts/podman-tunnel-start.sh"
fi
