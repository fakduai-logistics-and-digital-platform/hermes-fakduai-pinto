#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"

copy_env_if_missing() {
  if [ ! -f "$ENV_FILE" ]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "Created .env from .env.example"
  fi
}

upsert_env() {
  key="$1"
  value="$2"
  tmp="$ENV_FILE.tmp"

  if grep -q "^${key}=" "$ENV_FILE"; then
    awk -v key="$key" -v value="$value" '
      index($0, key "=") == 1 { print key "=" value; next }
      { print }
    ' "$ENV_FILE" > "$tmp"
  else
    cp "$ENV_FILE" "$tmp"
    printf '\n%s=%s\n' "$key" "$value" >> "$tmp"
  fi

  mv "$tmp" "$ENV_FILE"
}

random_token() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    date "+hermes-%Y%m%d%H%M%S"
  fi
}

current_env_value() {
  key="$1"
  if [ -f "$ENV_FILE" ]; then
    grep "^${key}=" "$ENV_FILE" | tail -n 1 | sed "s/^${key}=//"
  fi
}

ensure_api_server_key() {
  key="$(current_env_value API_SERVER_KEY || true)"
  case "$key" in
    "")
      key="$(random_token)"
      upsert_env API_SERVER_KEY "$key"
      echo "Generated API_SERVER_KEY in .env"
      ;;
  esac
}

prompt() {
  label="$1"
  default_value="${2:-}"

  if [ -n "$default_value" ]; then
    printf "%s [%s]: " "$label" "$default_value"
  else
    printf "%s: " "$label"
  fi

  read -r value
  if [ -z "$value" ]; then
    value="$default_value"
  fi
  printf '%s' "$value"
}

print_next_steps() {
  mode="$1"

  echo
  echo "Saved config to .env"
  echo

  case "$mode" in
    stable)
      echo "Start Hermes with Cloudflare Tunnel:"
      echo "  docker compose -f docker-compose.yml -f docker-compose.cloudflare.yml up -d"
      ;;
    quick)
      echo "Start Hermes with temporary trycloudflare.com URL:"
      echo "  docker compose -f docker-compose.yml -f docker-compose.trycloudflare.yml up -d"
      echo
      echo "Then find the generated URL:"
      echo "  docker compose -f docker-compose.yml -f docker-compose.trycloudflare.yml logs -f cloudflared"
      ;;
    local)
      echo "Start Hermes locally:"
      echo "  docker compose up -d"
      ;;
  esac
}

copy_env_if_missing
ensure_api_server_key

echo "Hermes Pinto Docker Setup"
echo
echo "Choose one:"
echo "  1) Local only"
echo "  2) Cloudflare Tunnel with your own domain (recommended)"
echo "  3) Cloudflare Quick Tunnel without domain (temporary URL)"
echo
printf "Choice [2]: "
read -r choice
choice="${choice:-2}"

case "$choice" in
  1)
    port="$(prompt "Local port" "8642")"
    upsert_env HERMES_GATEWAY_PORT "$port"
    upsert_env PINTO_WEBHOOK_URL "http://127.0.0.1:${port}/plugins/pinto/webhook"
    print_next_steps local
    ;;
  2)
    domain="$(prompt "Public Hermes URL, for example https://hermes.example.com" "")"
    if [ -z "$domain" ]; then
      echo "Public Hermes URL is required." >&2
      exit 1
    fi

    token="$(prompt "Cloudflare Tunnel token" "")"
    if [ -z "$token" ]; then
      echo "Cloudflare Tunnel token is required." >&2
      exit 1
    fi

    domain="${domain%/}"
    upsert_env HERMES_GATEWAY_PORT "8642"
    upsert_env PINTO_WEBHOOK_URL "${domain}/plugins/pinto/webhook"
    upsert_env CLOUDFLARE_TUNNEL_TOKEN "$token"
    print_next_steps stable
    ;;
  3)
    upsert_env HERMES_GATEWAY_PORT "8642"
    upsert_env PINTO_WEBHOOK_URL "https://REPLACE-WITH-TRYCLOUDFLARE-URL/plugins/pinto/webhook"
    print_next_steps quick
    ;;
  *)
    echo "Unknown choice: $choice" >&2
    exit 1
    ;;
esac

echo
echo "Use this Pinto webhook URL:"
grep '^PINTO_WEBHOOK_URL=' "$ENV_FILE" | sed 's/^PINTO_WEBHOOK_URL=/  /'

echo
echo "Use this API Server Key:"
grep '^API_SERVER_KEY=' "$ENV_FILE" | sed 's/^API_SERVER_KEY=/  /'
