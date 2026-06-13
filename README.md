# Hermes + Pinto Chatbot

Run **Hermes Agent** as a chatbot behind **Pinto**, with optional public webhook URL from **Cloudflare Quick Tunnel**.

This repo supports:

- macOS / Linux + **Podman**
- macOS / Linux + **Docker**
- Windows + **Docker Desktop** + PowerShell

You will end with:

```text
Pinto Chatbot  ->  Cloudflare URL  ->  Hermes Gateway  ->  AI Provider
```

---

## What you need

### Option A: Podman users

Install:

```bash
podman
podman-compose
curl
python3
```

Check:

```bash
podman --version
podman-compose --version
```

### Option B: Docker users

Install Docker Desktop or Docker Engine.

Check:

```bash
docker --version
docker compose version
```

### Option C: Windows users

Use **Docker Desktop** and run commands in **PowerShell**.

Check:

```powershell
docker --version
docker compose version
```

No WSL shell required.

---

## Ports

```text
Hermes Gateway / Pinto webhook: http://127.0.0.1:8642
Hermes Dashboard:              http://127.0.0.1:9119
Pinto webhook path:            /plugins/pinto/webhook
```

Local webhook:

```text
http://127.0.0.1:8642/plugins/pinto/webhook
```

Public webhook will look like:

```text
https://xxxx.trycloudflare.com/plugins/pinto/webhook
```

---

## Files

```text
Podman:
  Dockerfile.podman
  docker-compose.podman.yml
  scripts/podman-start.sh
  scripts/podman-status.sh
  scripts/podman-stop.sh
  scripts/podman-tunnel-start.sh
  scripts/podman-tunnel-status.sh
  scripts/podman-tunnel-stop.sh

Docker:
  Dockerfile
  docker-compose.docker.yml
  scripts/docker-start.ps1
  scripts/docker-status.ps1
  scripts/docker-stop.ps1
  scripts/docker-tunnel-start.ps1
  scripts/docker-tunnel-status.ps1
  scripts/docker-tunnel-stop.ps1

Shared:
  docker-compose.trycloudflare.yml
  docker-compose.cloudflare.yml
  scripts/bootstrap-hermes-config.py
  scripts/patch-api-server-for-pinto-podman.py
  scripts/patch-pinto-for-podman.py
```

---

# Step 1: Clone repo

```bash
git clone <this-repo-url>
cd hermes-fakduai-pinto
```

Windows PowerShell:

```powershell
git clone <this-repo-url>
cd hermes-fakduai-pinto
```

---

# Step 2: Create `.env`

Copy example file:

macOS / Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Open `.env` in your editor.

---

# Step 3: Set Pinto bot ID

In `.env`, set your Pinto bot ID:

```env
PINTO_BOT_ID=your_pinto_bot_id_here
```

Example:

```env
PINTO_BOT_ID=xjOltYhGtY9nDKp
```

You get this from Pinto Developer Console / bot settings.

---

# Step 4: Generate Hermes API server key

Run:

macOS / Linux:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
```

Windows PowerShell:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Put result in `.env`:

```env
API_SERVER_KEY=paste_generated_key_here
```

---

# Step 5: Configure AI provider

Hermes needs an AI provider to answer messages.

This repo is set up for OpenAI-compatible APIs.

In `.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=http://your-ai-server:port/v1
HERMES_PROVIDER=openai-api
HERMES_MODEL=your_model_name
```

Example:

```env
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=http://45.136.254.176:20128/v1
HERMES_PROVIDER=openai-api
HERMES_MODEL=codex
```

## BytePlus ARK example

BytePlus ARK also exposes an OpenAI-compatible Chat Completions API.

Use the base API path, not the full `/responses` path:

```env
ARK_API_KEY=your_ark_api_key_here
BYTEPLUS_ARK_BASE_URL=https://ark.ap-southeast.bytepluses.com/api/v3
BYTEPLUS_ARK_MODEL=seed-2-0-pro-260328
```

Then configure Hermes custom provider in `hermes-config/config.yaml`:

```yaml
model:
  provider: custom:byteplus-ark
  model: seed-2-0-pro-260328
  default: seed-2-0-pro-260328
  base_url: https://ark.ap-southeast.bytepluses.com/api/v3
  api_mode: chat_completions

providers:
  byteplus-ark:
    name: byteplus-ark
    base_url: https://ark.ap-southeast.bytepluses.com/api/v3
    key_env: ARK_API_KEY
    api_mode: chat_completions
    model: seed-2-0-pro-260328
```

Why `chat_completions`?

- ARK `/responses` can work with direct curl.
- Hermes Responses-mode may send extra fields that ARK rejects, such as `summary`.
- ARK `/chat/completions` works cleanly with Hermes.

Test:

```bash
podman exec -it hermes-fakduai-pinto_hermes-gateway_1 \
  hermes -z "reply only: ok" \
  --provider custom:byteplus-ark \
  --model seed-2-0-pro-260328
```

Expected:

```text
ok
```

Do not commit `.env`. It contains secrets.

---

# Step 6: Start locally

## Podman: macOS / Linux

```bash
scripts/podman-start.sh
```

Check:

```bash
scripts/podman-status.sh
```

Stop:

```bash
scripts/podman-stop.sh
```

## Docker: macOS / Linux

```bash
docker compose -f docker-compose.docker.yml up -d --build
```

Check:

```bash
docker compose -f docker-compose.docker.yml ps
curl http://127.0.0.1:8642/health
curl http://127.0.0.1:8642/plugins/pinto/webhook
```

Stop:

```bash
docker compose -f docker-compose.docker.yml down
```

## Docker Desktop: Windows PowerShell

```powershell
.\scripts\docker-start.ps1
```

Check:

```powershell
.\scripts\docker-status.ps1
```

Stop:

```powershell
.\scripts\docker-stop.ps1
```

---

# Step 7: Verify local services

Gateway health:

```bash
curl http://127.0.0.1:8642/health
```

Expected:

```json
{"status":"ok","platform":"hermes-agent"}
```

Pinto webhook health:

```bash
curl http://127.0.0.1:8642/plugins/pinto/webhook
```

Expected:

```json
{"ok":true,"channel":"pinto"}
```

Dashboard:

```text
http://127.0.0.1:9119/
```

Open in browser.

---

# Step 8: Get public Cloudflare webhook URL

Pinto cannot call your local `127.0.0.1` URL.

Use Cloudflare Quick Tunnel to get public HTTPS URL.

## Podman: macOS / Linux

```bash
scripts/podman-tunnel-start.sh
```

Output will show:

```text
Cloudflare URL:
https://xxxx.trycloudflare.com

Pinto Webhook URL:
https://xxxx.trycloudflare.com/plugins/pinto/webhook
```

Copy the **Pinto Webhook URL**.

Check again later:

```bash
scripts/podman-tunnel-status.sh
```

Stop tunnel:

```bash
scripts/podman-tunnel-stop.sh
```

## Docker: macOS / Linux

```bash
docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml up -d --build
```

Get URL:

```bash
docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml logs cloudflared
```

Look for:

```text
https://xxxx.trycloudflare.com
```

Your Pinto webhook URL is:

```text
https://xxxx.trycloudflare.com/plugins/pinto/webhook
```

## Docker Desktop: Windows PowerShell

```powershell
.\scripts\docker-tunnel-start.ps1
```

Output will show:

```text
Cloudflare URL:
https://xxxx.trycloudflare.com

Pinto Webhook URL:
https://xxxx.trycloudflare.com/plugins/pinto/webhook
```

Copy the **Pinto Webhook URL**.

Check again later:

```powershell
.\scripts\docker-tunnel-status.ps1
```

Stop tunnel:

```powershell
.\scripts\docker-tunnel-stop.ps1
```

---

# Step 9: Put webhook URL in Pinto

Open Pinto Developer Console.

Find your bot webhook setting.

Paste:

```text
https://xxxx.trycloudflare.com/plugins/pinto/webhook
```

Save.

Now Pinto can send chat messages to Hermes.

---

# Step 10: Chat with Hermes through Pinto

Open Pinto app / chat UI.

Send a message to your bot, for example:

```text
hello
```

Flow:

```text
Pinto chat message
  -> Pinto webhook
  -> Cloudflare Quick Tunnel
  -> Hermes Gateway
  -> AI provider
  -> Hermes reply
  -> Pinto chat
```

If configured correctly, bot replies in Pinto.

---

# Step 11: Test AI provider manually

If webhook works but bot does not answer, test Hermes AI provider directly.

## Podman

```bash
podman exec -it hermes-fakduai-pinto_hermes-gateway_1 hermes -z "reply only: ok" --provider openai-api --model "$HERMES_MODEL"
```

If `$HERMES_MODEL` is not available in your shell, use model name directly:

```bash
podman exec -it hermes-fakduai-pinto_hermes-gateway_1 hermes -z "reply only: ok" --provider openai-api --model codex
```

Expected:

```text
ok
```

## Docker

Find container name:

```bash
docker ps
```

Then run:

```bash
docker exec -it <gateway-container-name> hermes -z "reply only: ok" --provider openai-api --model codex
```

Windows PowerShell:

```powershell
docker ps

docker exec -it <gateway-container-name> hermes -z "reply only: ok" --provider openai-api --model codex
```

Expected:

```text
ok
```

---

# Quick Tunnel warning

Cloudflare Quick Tunnel URLs are temporary.

If you:

- stop containers
- restart cloudflared
- reboot machine
- run `down`

URL may change.

If URL changes:

1. Run tunnel start/status script again.
2. Copy new Pinto Webhook URL.
3. Update webhook URL in Pinto Developer Console.

For production, use Cloudflare Named Tunnel + your own domain.

---

# Production: stable Cloudflare domain

Quick Tunnel is for testing.

For stable webhook URL, use named Cloudflare Tunnel.

You need:

```env
CLOUDFLARE_TUNNEL_TOKEN=your_named_tunnel_token
```

Then run compose with:

```bash
docker compose -f docker-compose.docker.yml -f docker-compose.cloudflare.yml up -d
```

Podman:

```bash
podman-compose -f docker-compose.podman.yml -f docker-compose.cloudflare.yml up -d
```

Your webhook becomes stable, for example:

```text
https://your-domain.com/plugins/pinto/webhook
```

---

# Common commands

## Podman

```bash
scripts/podman-start.sh
scripts/podman-status.sh
scripts/podman-stop.sh

scripts/podman-tunnel-start.sh
scripts/podman-tunnel-status.sh
scripts/podman-tunnel-stop.sh
```

Logs:

```bash
podman-compose -f docker-compose.podman.yml logs -f hermes-gateway
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml logs -f cloudflared
```

Rebuild:

```bash
podman-compose -f docker-compose.podman.yml build --no-cache
```

## Docker macOS / Linux

```bash
docker compose -f docker-compose.docker.yml up -d --build
docker compose -f docker-compose.docker.yml ps
docker compose -f docker-compose.docker.yml down
```

Tunnel:

```bash
docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml up -d --build
docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml logs -f cloudflared
docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml down
```

## Windows PowerShell

```powershell
.\scripts\docker-start.ps1
.\scripts\docker-status.ps1
.\scripts\docker-stop.ps1

.\scripts\docker-tunnel-start.ps1
.\scripts\docker-tunnel-status.ps1
.\scripts\docker-tunnel-stop.ps1
```

---

# Troubleshooting

## `PINTO_BOT_ID not set!`

Set this in `.env`:

```env
PINTO_BOT_ID=your_pinto_bot_id_here
```

Restart.

---

## Gateway health fails

Check logs.

Podman:

```bash
podman-compose -f docker-compose.podman.yml logs --tail=100 hermes-gateway
```

Docker:

```bash
docker compose -f docker-compose.docker.yml logs --tail=100 hermes-gateway
```

Expected health URL:

```text
http://127.0.0.1:8642/health
```

---

## Dashboard does not open

Dashboard is not on port `8642`.

Use:

```text
http://127.0.0.1:9119/
```

---

## Webhook returns `500 Internal Server Error`

Check gateway logs.

Podman:

```bash
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml logs --tail=150 hermes-gateway
```

Docker:

```bash
docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml logs --tail=150 hermes-gateway
```

Common causes:

- missing `PINTO_BOT_ID`
- missing AI provider config
- invalid AI API key
- Pinto send API error
- wrong webhook payload

---

## Logs say `No inference provider configured`

Add AI provider config to `.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=http://your-ai-server:port/v1
HERMES_PROVIDER=openai-api
HERMES_MODEL=codex
```

Also ensure `hermes-config/.env` has same provider values after first bootstrap.

Restart.

---

## AI test works but Pinto does not receive reply

If logs show:

```text
Pinto HTTP 500: {"ok":false,"error":"Failed to send message"}
```

Hermes received message and generated reply, but Pinto rejected send-back request.

Check:

- real `chat_id` from Pinto, not fake test payload
- `PINTO_BOT_ID` correct
- `PINTO_API_URL` correct
- `PINTO_WEBHOOK_SECRET` if your Pinto setup requires one
- `PINTO_BEARER_TOKEN` if you want native Pinto chat API, real typing, and binary image upload
- bot permission in Pinto

---

## Cloudflare URL does not resolve / 1033 / 1034

Quick Tunnel sometimes prints a URL before Cloudflare is ready.

Run tunnel script again.

Podman:

```bash
scripts/podman-tunnel-start.sh
```

Windows:

```powershell
.\scripts\docker-tunnel-start.ps1
```

Then update Pinto webhook URL with new URL.

---

## Windows PowerShell blocks script

If PowerShell blocks `.ps1` scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then rerun script.

---

## Windows line ending issue

If Bash scripts show:

```text
/bin/bash^M: bad interpreter
```

Use PowerShell scripts on Windows, or convert line endings to LF.

---

# Security notes

Do not commit `.env`.

`.env` may contain:

```text
API_SERVER_KEY
OPENAI_API_KEY
PINTO_WEBHOOK_SECRET
PINTO_BEARER_TOKEN
CLOUDFLARE_TUNNEL_TOKEN
```

For public bots, avoid `GATEWAY_ALLOW_ALL_USERS=true` unless you intentionally want anyone to chat with your bot.

For testing, this repo defaults to open access because Pinto user IDs can vary during setup.

For production, configure allowlists instead.

---

# License

MIT
