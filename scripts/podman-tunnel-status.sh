#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml ps
URL="$(podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml logs cloudflared 2>&1 | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' | tail -1 || true)"
if [ -n "$URL" ]; then
  WEBHOOK_URL="$URL/plugins/pinto/webhook"
  for env_file in .env hermes-config/.env; do
    if [ -f "$env_file" ]; then
      if grep -q '^PINTO_WEBHOOK_URL=' "$env_file"; then
        tmp="$(mktemp)"
        sed "s|^PINTO_WEBHOOK_URL=.*|PINTO_WEBHOOK_URL=$WEBHOOK_URL|" "$env_file" > "$tmp"
        mv "$tmp" "$env_file"
      else
        printf '\nPINTO_WEBHOOK_URL=%s\n' "$WEBHOOK_URL" >> "$env_file"
      fi
    fi
  done
  printf '\nCloudflare URL:\n%s\n\nPinto Developer Console values:\nWebhook URL: %s\nWebhook Secret: open Hermes Dashboard > Pinto Chat > Configure > reveal/copy Webhook Secret\n\n' "$URL" "$WEBHOOK_URL"
  printf 'Health:\n'
  curl -sS "$URL/health" || true
  printf '\n\nWebhook health:\n'
  curl -sS "$WEBHOOK_URL" || true
  printf '\n'
else
  echo "No Cloudflare Quick Tunnel URL found. Start with scripts/podman-tunnel-start.sh"
fi
