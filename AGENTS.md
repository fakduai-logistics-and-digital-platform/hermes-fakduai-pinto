# AGENTS.md

Instructions for AI coding agents working in this repo.

## Project

This repo runs **Hermes Agent** as a **Pinto chatbot**.

Main flow:

```text
Pinto Chatbot -> Cloudflare Tunnel -> Hermes Gateway -> AI Provider
```

Before editing, read:

1. `README.md` — user-facing setup guide.
2. `llm.txt` — project context for AI agents.
3. `.env.example` — supported configuration.
4. Relevant compose/script files for the target runtime.

## Safety rules

- Do not commit `.env`.
- Do not print or expose real API keys, webhook secrets, or tunnel tokens.
- Do not hardcode user secrets into docs, compose files, scripts, or images.
- Keep public docs using placeholder values.
- If a command may destroy containers, volumes, or tunnel URLs, explain the effect clearly.

## Runtime split

Keep Podman and Docker support separate.

### Podman path

Use for macOS/Linux Podman users:

```text
Dockerfile.podman
docker-compose.podman.yml
scripts/podman-start.sh
scripts/podman-status.sh
scripts/podman-stop.sh
scripts/podman-tunnel-start.sh
scripts/podman-tunnel-status.sh
scripts/podman-tunnel-stop.sh
```

### Docker path

Use for Docker Desktop / Docker Engine users:

```text
Dockerfile
docker-compose.docker.yml
scripts/docker-start.ps1
scripts/docker-status.ps1
scripts/docker-stop.ps1
scripts/docker-tunnel-start.ps1
scripts/docker-tunnel-status.ps1
scripts/docker-tunnel-stop.ps1
```

### Shared files

```text
docker-compose.trycloudflare.yml
docker-compose.cloudflare.yml
scripts/bootstrap-hermes-config.py
scripts/patch-api-server-for-pinto-podman.py
scripts/patch-pinto-for-podman.py
```

## Documentation rules

If setup behavior changes, update:

```text
README.md
llm.txt
AGENTS.md if agent workflow changes
```

Keep `README.md` beginner-friendly and step-by-step.

Use exact commands that new users can copy.

## Required service behavior

Hermes Gateway:

```text
http://127.0.0.1:8642/health
```

Expected:

```json
{"status":"ok","platform":"hermes-agent"}
```

Pinto webhook:

```text
http://127.0.0.1:8642/plugins/pinto/webhook
```

Expected:

```json
{"ok":true,"channel":"pinto"}
```

Dashboard:

```text
http://127.0.0.1:9119/
```

Public Pinto webhook:

```text
https://<cloudflare-host>/plugins/pinto/webhook
```

## Important implementation notes

- Hermes Gateway must bind `API_SERVER_HOST=0.0.0.0` inside containers.
- Dashboard is separate from Gateway and runs on port `9119`.
- Gateway root `/` may return 404. Use `/health`.
- Pinto webhook route is `/plugins/pinto/webhook`.
- Cloudflare Quick Tunnel URLs are temporary and may change after restart.
- For production, use Cloudflare Named Tunnel with `CLOUDFLARE_TUNNEL_TOKEN`.
- Podman on macOS can fail with `host.docker.internal:host-gateway`; avoid that in Podman compose.
- Compatibility patches are required for Hermes 0.16 + Pinto adapter route mounting and sending.

## Environment config

Required `.env` values:

```env
PINTO_BOT_ID=your_pinto_bot_id
API_SERVER_KEY=generated_hex_key
API_SERVER_HOST=0.0.0.0
PINTO_ALLOW_ALL_USERS=true
GATEWAY_ALLOW_ALL_USERS=true
HERMES_DASHBOARD=1
HERMES_DASHBOARD_PORT=9119
```

AI provider config uses OpenAI-compatible APIs:

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=http://your-ai-server:port/v1
HERMES_PROVIDER=openai-api
HERMES_MODEL=your_model
```

Never reveal the real `OPENAI_API_KEY`.

## Verification commands

### Podman

```bash
scripts/podman-status.sh
curl http://127.0.0.1:8642/health
curl http://127.0.0.1:8642/plugins/pinto/webhook
```

Tunnel:

```bash
scripts/podman-tunnel-start.sh
scripts/podman-tunnel-status.sh
```

Logs:

```bash
podman-compose -f docker-compose.podman.yml logs --tail=100 hermes-gateway
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml logs --tail=100 cloudflared
```

### Docker macOS/Linux

```bash
docker compose -f docker-compose.docker.yml up -d --build
docker compose -f docker-compose.docker.yml ps
curl http://127.0.0.1:8642/health
curl http://127.0.0.1:8642/plugins/pinto/webhook
```

Tunnel:

```bash
docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml up -d --build
docker compose -f docker-compose.docker.yml -f docker-compose.trycloudflare.yml logs cloudflared
```

### Windows PowerShell

```powershell
.\scripts\docker-start.ps1
.\scripts\docker-status.ps1
.\scripts\docker-tunnel-start.ps1
.\scripts\docker-tunnel-status.ps1
```

## AI provider test

Inside gateway container:

```bash
hermes -z "reply only: ok" --provider openai-api --model codex
```

Expected:

```text
ok
```

## Common failure handling

### `No inference provider configured`

Check `.env` and `hermes-config/.env` for:

```env
OPENAI_API_KEY=...
OPENAI_BASE_URL=...
HERMES_PROVIDER=openai-api
HERMES_MODEL=...
```

Restart gateway after changes.

### `Pinto HTTP 500: {"ok":false,"error":"Failed to send message"}`

Hermes likely received webhook and generated a reply, but Pinto rejected send-back.

Check:

- real Pinto `chat_id`
- `PINTO_BOT_ID`
- `PINTO_API_URL`
- `PINTO_WEBHOOK_SECRET`
- bot permissions in Pinto

### Cloudflare 1033 / 1034 / DNS failure

Quick Tunnel URL may not be ready or may be bad.

Run tunnel start script again and update Pinto Developer Console with the new webhook URL.

## Editing style

- Prefer small, targeted changes.
- Keep Podman scripts Bash.
- Keep Windows Docker scripts PowerShell.
- Keep compose files readable and explicit.
- Update docs in the same change when behavior changes.
