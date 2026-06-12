#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml up -d
printf 'Waiting for Cloudflare Quick Tunnel URL...\n'
URL=""
i=0
while [ "$i" -lt 60 ]; do
  URL="$(podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml logs cloudflared 2>&1 | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' | tail -1 || true)"
  if [ -n "$URL" ]; then
    break
  fi
  i=$((i + 1))
  sleep 2
done
if [ -z "$URL" ]; then
  echo "Cloudflare tunnel URL not found. Check logs:"
  echo "podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml logs -f cloudflared"
  exit 1
fi

# Quick Tunnel sometimes prints a hostname before Cloudflare DNS/proxy is ready.
# If it does not become reachable, recreate cloudflared until /health returns 200.
attempt=1
while [ "$attempt" -le 5 ]; do
  code="$(curl -sS -o /tmp/hermes-tunnel-health.out -w '%{http_code}' --connect-timeout 15 "$URL/health" 2>/dev/null || true)"
  if [ "$code" = "200" ]; then
    break
  fi
  echo "Tunnel $URL not ready (HTTP $code). Recreating cloudflared..."
  podman rm -f hermes-fakduai-pinto_cloudflared_1 >/dev/null 2>&1 || true
  podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml up -d cloudflared >/dev/null 2>&1 || true
  sleep 18
  URL="$(podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml logs cloudflared 2>&1 | grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' | tail -1 || true)"
  attempt=$((attempt + 1))
done

code="$(curl -sS -o /tmp/hermes-tunnel-health.out -w '%{http_code}' --connect-timeout 15 "$URL/health" 2>/dev/null || true)"
if [ "$code" != "200" ]; then
  echo "Cloudflare tunnel URL is not reachable after retries: $URL (HTTP $code)"
  exit 1
fi

WEBHOOK_URL="$URL/plugins/pinto/webhook"
if [ -f .env ]; then
  if grep -q '^PINTO_WEBHOOK_URL=' .env; then
    tmp="$(mktemp)"
    sed "s|^PINTO_WEBHOOK_URL=.*|PINTO_WEBHOOK_URL=$WEBHOOK_URL|" .env > "$tmp"
    mv "$tmp" .env
  else
    printf '\nPINTO_WEBHOOK_URL=%s\n' "$WEBHOOK_URL" >> .env
  fi
fi
printf '\nCloudflare URL:\n%s\n\nPinto Webhook URL:\n%s\n\n' "$URL" "$WEBHOOK_URL"
printf 'Health:\n'
curl -sS "$URL/health" || true
printf '\n\nWebhook health:\n'
curl -sS "$WEBHOOK_URL" || true
printf '\n'
