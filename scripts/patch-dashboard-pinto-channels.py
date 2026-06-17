#!/usr/bin/env python3
"""Patch Hermes Dashboard Channels API to show Pinto extra bots.

Hermes Dashboard's /channels page renders one card per messaging platform.
Pinto can now route multiple bot IDs via platforms.pinto.extra.bots, but the
Dashboard does not know how to display those sub-bots. This patch appends
read-only pseudo-channel cards for each extra Pinto bot so users can see that
multi-bot routing is configured without storing bot IDs in .env.
"""
from pathlib import Path

p = Path('/usr/local/lib/python3.11/site-packages/hermes_cli/web_server.py')
s = p.read_text(encoding='utf-8')

helper_marker = '''def _catalog_lookup(platform_id: str) -> dict[str, Any] | None:
    for entry in _messaging_platform_catalog():
        if entry["id"] == platform_id:
            return entry
    return None


'''
helper_insert = '''def _catalog_lookup(platform_id: str) -> dict[str, Any] | None:
    for entry in _messaging_platform_catalog():
        if entry["id"] == platform_id:
            return entry
    if platform_id.startswith("pinto:"):
        return {
            "id": platform_id,
            "name": "Pinto bot",
            "description": "Additional Pinto bot from platforms.pinto.extra.bots",
            "docs_url": "",
            "env_vars": (),
            "required_env": (),
            "read_only": True,
        }
    return None


def _pinto_extra_bot_entries() -> list[dict[str, Any]]:
    """Return read-only pseudo-channel catalog entries for Pinto extra bots."""
    try:
        config = load_config()
        extra = (
            config.get("platforms", {})
            .get("pinto", {})
            .get("extra", {})
        )
        bots = extra.get("bots") if isinstance(extra, dict) else None
        if not isinstance(bots, dict):
            return []
    except Exception:
        _log.debug("could not load Pinto extra bots", exc_info=True)
        return []

    entries: list[dict[str, Any]] = []
    for bot_id, bot_cfg in bots.items():
        if not bot_id:
            continue
        cfg = bot_cfg if isinstance(bot_cfg, dict) else {}
        name = str(cfg.get("name") or cfg.get("role") or bot_id)
        description = str(
            cfg.get("description")
            or cfg.get("role")
            or "Additional Pinto bot configured in platforms.pinto.extra.bots"
        )
        entries.append({
            "id": f"pinto:{bot_id}",
            "name": f"Pinto / {name}",
            "description": f"{description} — bot_id: {bot_id}",
            "docs_url": "",
            "env_vars": (),
            "required_env": (),
            "read_only": True,
            "parent_platform": "pinto",
            "bot_id": str(bot_id),
        })
    return entries


'''
if helper_insert.strip() in s:
    print('Dashboard Pinto channel helper already patched')
elif helper_marker in s:
    s = s.replace(helper_marker, helper_insert)
else:
    raise SystemExit('Expected _catalog_lookup block not found')

payload_marker = '''    platform_id = entry["id"]
    gateway_running = get_running_pid() is not None
    runtime_platforms = runtime.get("platforms") if runtime else {}
    runtime_platform = (
        runtime_platforms.get(platform_id, {})
        if isinstance(runtime_platforms, dict)
        else {}
    )
    env_vars = []
'''
payload_insert = '''    platform_id = entry["id"]
    gateway_running = get_running_pid() is not None
    runtime_platforms = runtime.get("platforms") if runtime else {}

    # Read-only pseudo-channel for Pinto extra bots. The actual enabled/configured
    # state follows the parent Pinto platform because all bots share one adapter
    # and webhook endpoint.
    if platform_id.startswith("pinto:"):
        parent_runtime = (
            runtime_platforms.get("pinto", {})
            if isinstance(runtime_platforms, dict)
            else {}
        )
        try:
            gateway_config, platform, platform_config = _gateway_platform_config("pinto")
            enabled = bool(platform_config and platform_config.enabled)
            configured = bool(
                platform_config
                and gateway_config._is_platform_connected(platform, platform_config)
            )
        except Exception:
            enabled = False
            configured = False
        state = parent_runtime.get("state") if isinstance(parent_runtime, dict) else None
        if not enabled:
            state = "disabled"
        elif not configured:
            state = "not_configured"
        elif gateway_running and not state:
            state = "pending_restart"
        elif not gateway_running and not state:
            state = "gateway_stopped"
        if state == "connected":
            gateway_running = True
        return {
            "id": platform_id,
            "name": entry["name"],
            "description": entry["description"],
            "docs_url": entry["docs_url"],
            "enabled": enabled,
            "configured": configured,
            "gateway_running": gateway_running,
            "state": state,
            "error_code": None,
            "error_message": None,
            "updated_at": None,
            "home_channel": None,
            "env_vars": [],
            "read_only": True,
            "parent_platform": "pinto",
            "bot_id": entry.get("bot_id"),
        }

    runtime_platform = (
        runtime_platforms.get(platform_id, {})
        if isinstance(runtime_platforms, dict)
        else {}
    )
    env_vars = []
'''
if payload_insert.strip() in s:
    print('Dashboard Pinto pseudo payload already patched')
elif payload_marker in s:
    s = s.replace(payload_marker, payload_insert)
else:
    raise SystemExit('Expected _messaging_platform_payload header not found')

api_marker = '''@app.get("/api/messaging/platforms")
async def get_messaging_platforms():
    env_on_disk = load_env()
    runtime = read_runtime_status()
    return {
        "platforms": [
            _messaging_platform_payload(entry, env_on_disk, runtime)
            for entry in _messaging_platform_catalog()
        ]
    }


'''
api_insert = '''@app.get("/api/messaging/platforms")
async def get_messaging_platforms():
    env_on_disk = load_env()
    runtime = read_runtime_status()
    entries = list(_messaging_platform_catalog())
    entries.extend(_pinto_extra_bot_entries())
    return {
        "platforms": [
            _messaging_platform_payload(entry, env_on_disk, runtime)
            for entry in entries
        ]
    }


'''
if api_insert.strip() in s:
    print('Dashboard messaging platforms API already patched for Pinto extra bots')
elif api_marker in s:
    s = s.replace(api_marker, api_insert)
else:
    raise SystemExit('Expected /api/messaging/platforms block not found')

update_marker = '''    if not entry:
        raise HTTPException(
            status_code=404, detail=f"Unknown messaging platform: {platform_id}"
        )

    allowed_env = set(entry["env_vars"])
'''
update_insert = '''    if not entry:
        raise HTTPException(
            status_code=404, detail=f"Unknown messaging platform: {platform_id}"
        )
    if entry.get("read_only"):
        raise HTTPException(
            status_code=400,
            detail=f"{entry['name']} is read-only. Edit platforms.pinto.extra.bots in config.yaml.",
        )

    allowed_env = set(entry["env_vars"])
'''
if 'is read-only. Edit platforms.pinto.extra.bots in config.yaml' in s:
    print('Dashboard read-only Pinto pseudo-channel guard already patched')
elif update_marker in s:
    s = s.replace(update_marker, update_insert, 1)
else:
    raise SystemExit('Expected update_messaging_platform guard block not found')

p.write_text(s, encoding='utf-8')
print('Patched Dashboard Channels API for Pinto extra bots')
