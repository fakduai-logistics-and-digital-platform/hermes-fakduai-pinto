# CLAUDE.md

Instructions for Claude / coding agents in this repo.

## Cloudflare Quick Tunnel rule

This project uses Cloudflare Quick Tunnel through the `cloudflared` compose service.

**Do not restart, remove, recreate, or bring down `cloudflared` unless the user explicitly asks.**

Quick Tunnel URLs are temporary. Recreating the `cloudflared` container changes the public webhook URL and requires manually updating Pinto Developer Console.

### Safe when changing Hermes code/config

Prefer restarting/recreating only the service being changed, for example:

```bash
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml build hermes-gateway
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml up -d --no-deps --force-recreate hermes-gateway
```

For config-only changes:

```bash
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml restart hermes-gateway
```

Dashboard-only changes:

```bash
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml build hermes-dashboard
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml up -d --no-deps --force-recreate hermes-dashboard
```

### Avoid unless user approves URL change

Do not run these casually:

```bash
podman rm -f hermes-fakduai-pinto_cloudflared_1
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml down
podman-compose -f docker-compose.podman.yml -f docker-compose.trycloudflare.yml up -d --force-recreate
```

If `cloudflared` must be recreated, tell user first that the public Pinto webhook URL will change.

## Repo split

Keep Hermes repo and local company dashboard repo separate.

- Hermes repo: `/Users/watchakorn.b/FILE_CODE/hermes-fakduai-pinto`
- Company dashboard repo: `/Users/watchakorn.b/FILE_CODE/fakduai-agent-company`

For `fakduai-agent-company`, commit local changes if needed, but **do not push** unless user explicitly asks. Future work may split/use it as a separate repo.
