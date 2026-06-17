#!/usr/bin/env python3
"""Patch Hermes Dashboard Channels API for Pinto multi-bot cards.

Shows entries in platforms.pinto.extra.bots as editable Pinto cards that use the
same developer-console fields as the primary Pinto card, plus Agent ID.
"""
from pathlib import Path

p = Path('/usr/local/lib/python3.11/site-packages/hermes_cli/web_server.py')
s = p.read_text(encoding='utf-8')

# Extra request model.
model_marker = '''class MessagingPlatformUpdate(BaseModel):
    enabled: Optional[bool] = None
    env: Dict[str, str] = {}
    clear_env: List[str] = []

'''
model_insert = model_marker + '''class PintoBotUpdate(BaseModel):
    bot_id: Optional[str] = None
    agent_id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    channelPrompt: Optional[str] = None
    enabled: Optional[bool] = None

'''
if 'class PintoBotUpdate(BaseModel):' not in s:
    if model_marker not in s:
        raise SystemExit('Expected MessagingPlatformUpdate model block not found')
    s = s.replace(model_marker, model_insert)
else:
    print('Dashboard Pinto bot update model already patched')

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
            "env_vars": ("PINTO_API_URL", "PINTO_BOT_ID", "PINTO_WEBHOOK_SECRET", "PINTO_WEBHOOK_URL", "PINTO_AGENT_ID"),
            "required_env": ("PINTO_API_URL", "PINTO_BOT_ID", "PINTO_WEBHOOK_SECRET", "PINTO_WEBHOOK_URL"),
            "read_only": False,
        }
    return None


def _pinto_extra_bot_entries() -> list[dict[str, Any]]:
    """Return editable pseudo-channel catalog entries for Pinto extra bots."""
    try:
        config = load_config()
        extra = (config.get("platforms", {}).get("pinto", {}).get("extra", {}))
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
        agent_id = str(cfg.get("agent_id") or cfg.get("agentId") or cfg.get("role") or cfg.get("name") or bot_id)
        label = str(cfg.get("name") or agent_id or bot_id)
        description = str(cfg.get("description") or f"Agent ID: {agent_id}")
        entries.append({
            "id": f"pinto:{bot_id}",
            "name": f"Pinto / {label}",
            "description": f"{description} — bot_id: {bot_id}",
            "docs_url": "",
            "env_vars": ("PINTO_API_URL", "PINTO_BOT_ID", "PINTO_WEBHOOK_SECRET", "PINTO_WEBHOOK_URL", "PINTO_AGENT_ID"),
            "required_env": ("PINTO_API_URL", "PINTO_BOT_ID", "PINTO_WEBHOOK_SECRET", "PINTO_WEBHOOK_URL"),
            "read_only": False,
            "parent_platform": "pinto",
            "bot_id": str(bot_id),
            "agent_id": agent_id,
        })
    return entries


'''
if '_pinto_extra_bot_entries()' not in s:
    if helper_marker not in s:
        raise SystemExit('Expected _catalog_lookup block not found')
    s = s.replace(helper_marker, helper_insert)
else:
    print('Dashboard Pinto channel helper already patched')

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

    if platform_id.startswith("pinto:"):
        parent_runtime = runtime_platforms.get("pinto", {}) if isinstance(runtime_platforms, dict) else {}
        try:
            gateway_config, platform, platform_config = _gateway_platform_config("pinto")
            enabled = bool(platform_config and platform_config.enabled)
            configured = bool(platform_config and gateway_config._is_platform_connected(platform, platform_config))
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

        shared = {
            "PINTO_API_URL": env_on_disk.get("PINTO_API_URL") or os.getenv("PINTO_API_URL", ""),
            "PINTO_WEBHOOK_SECRET": env_on_disk.get("PINTO_WEBHOOK_SECRET") or os.getenv("PINTO_WEBHOOK_SECRET", ""),
            "PINTO_WEBHOOK_URL": env_on_disk.get("PINTO_WEBHOOK_URL") or os.getenv("PINTO_WEBHOOK_URL", ""),
            "PINTO_BOT_ID": entry.get("bot_id") or "",
            "PINTO_AGENT_ID": entry.get("agent_id") or "",
        }
        prompts = {
            "PINTO_API_URL": ("Pinto API URL", "Pinto API URL. Dev: https://api-dev.pinto-app.com, Prod: https://api.pinto-app.com"),
            "PINTO_BOT_ID": ("Pinto Bot ID", "Bot ID from Pinto Developer Console"),
            "PINTO_WEBHOOK_SECRET": ("Developer Console Webhook Secret", "Copy this secret into Pinto Developer Console. Shared by all Pinto bots."),
            "PINTO_WEBHOOK_URL": ("Developer Console Webhook URL", "Copy this URL into Pinto Developer Console > Bot Webhook URL. Shared by all Pinto bots."),
            "PINTO_AGENT_ID": ("Agent ID", "Hermes agent/persona routing ID for this Pinto bot"),
        }
        env_vars = []
        for key in ("PINTO_API_URL", "PINTO_BOT_ID", "PINTO_WEBHOOK_SECRET", "PINTO_WEBHOOK_URL", "PINTO_AGENT_ID"):
            value = shared.get(key, "")
            prompt, description = prompts[key]
            env_vars.append({
                "key": key,
                "required": key != "PINTO_AGENT_ID",
                "is_set": bool(value),
                "redacted_value": value or None,
                "description": description,
                "prompt": prompt,
                "url": None,
                "is_password": False,
                "advanced": key == "PINTO_AGENT_ID",
            })
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
            "env_vars": env_vars,
            "read_only": False,
            "parent_platform": "pinto",
            "bot_id": entry.get("bot_id"),
            "agent_id": entry.get("agent_id"),
        }

    runtime_platform = (
        runtime_platforms.get(platform_id, {})
        if isinstance(runtime_platforms, dict)
        else {}
    )
    env_vars = []
'''
if '"PINTO_AGENT_ID": ("Agent ID"' not in s:
    if payload_marker not in s:
        raise SystemExit('Expected _messaging_platform_payload header not found')
    s = s.replace(payload_marker, payload_insert)
else:
    print('Dashboard Pinto pseudo payload already patched')

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
if 'entries.extend(_pinto_extra_bot_entries())' not in s:
    if api_marker not in s:
        raise SystemExit('Expected /api/messaging/platforms block not found')
    s = s.replace(api_marker, api_insert)
else:
    print('Dashboard messaging platforms API already patched')

endpoints_marker = '''@app.put("/api/messaging/platforms/{platform_id}")
'''
endpoints_insert = '''def _pinto_bots_config(config: dict[str, Any]) -> dict[str, Any]:
    platforms = config.setdefault("platforms", {})
    if not isinstance(platforms, dict):
        platforms = {}; config["platforms"] = platforms
    pinto = platforms.setdefault("pinto", {})
    if not isinstance(pinto, dict):
        pinto = {}; platforms["pinto"] = pinto
    extra = pinto.setdefault("extra", {})
    if not isinstance(extra, dict):
        extra = {}; pinto["extra"] = extra
    bots = extra.setdefault("bots", {})
    if not isinstance(bots, dict):
        bots = {}; extra["bots"] = bots
    return bots


def _pinto_bot_public(bot_id: str, cfg: Any) -> dict[str, Any]:
    data = cfg if isinstance(cfg, dict) else {}
    return {
        "bot_id": bot_id,
        "agent_id": data.get("agent_id") or data.get("agentId"),
        "name": data.get("name"),
        "role": data.get("role"),
        "description": data.get("description"),
        "channelPrompt": data.get("channelPrompt"),
        "enabled": data.get("enabled", True),
    }


@app.get("/api/messaging/pinto/bots")
async def list_pinto_bots():
    config = load_config()
    bots = _pinto_bots_config(config)
    return {"bots": [_pinto_bot_public(str(bot_id), cfg) for bot_id, cfg in bots.items()]}


@app.put("/api/messaging/pinto/bots/{bot_id}")
async def upsert_pinto_bot(bot_id: str, body: PintoBotUpdate):
    bot_id = (body.bot_id or bot_id).strip()
    if not bot_id:
        raise HTTPException(status_code=400, detail="bot_id is required")
    config = load_config()
    bots = _pinto_bots_config(config)
    current = bots.get(bot_id, {})
    data = current if isinstance(current, dict) else {}
    for key in ("agent_id", "name", "role", "description", "channelPrompt", "enabled"):
        value = getattr(body, key, None)
        if value is not None:
            if isinstance(value, str):
                value = value.strip()
            if value == "":
                data.pop(key, None)
            else:
                data[key] = value
    bots[bot_id] = data
    save_config(config)
    return {"ok": True, "bot": _pinto_bot_public(bot_id, data), "needs_restart": True}


@app.delete("/api/messaging/pinto/bots/{bot_id}")
async def delete_pinto_bot(bot_id: str):
    config = load_config()
    bots = _pinto_bots_config(config)
    if bot_id not in bots:
        raise HTTPException(status_code=404, detail=f"Unknown Pinto bot: {bot_id}")
    removed = bots.pop(bot_id)
    save_config(config)
    return {"ok": True, "removed": _pinto_bot_public(bot_id, removed), "needs_restart": True}


@app.put("/api/messaging/platforms/{platform_id}")
'''
if '@app.get("/api/messaging/pinto/bots")' not in s:
    if endpoints_marker not in s:
        raise SystemExit('Expected messaging platform PUT route marker not found')
    s = s.replace(endpoints_marker, endpoints_insert, 1)
else:
    print('Dashboard Pinto bot management API already patched')

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
    if platform_id.startswith("pinto:"):
        old_bot_id = platform_id.split(":", 1)[1]
        new_bot_id = (body.env.get("PINTO_BOT_ID") or old_bot_id).strip()
        if not new_bot_id:
            raise HTTPException(status_code=400, detail="Pinto Bot ID is required")
        config = load_config()
        bots = _pinto_bots_config(config)
        current = bots.pop(old_bot_id, {}) if old_bot_id in bots else {}
        data = current if isinstance(current, dict) else {}
        agent_id = body.env.get("PINTO_AGENT_ID")
        if agent_id is not None:
            agent_id = agent_id.strip()
            if agent_id:
                data["agent_id"] = agent_id
                data.setdefault("name", agent_id)
            else:
                data.pop("agent_id", None)
        if body.enabled is not None:
            data["enabled"] = body.enabled
        bots[new_bot_id] = data
        save_config(config)
        return {"ok": True, "platform": f"pinto:{new_bot_id}", "needs_restart": True}

    allowed_env = set(entry["env_vars"])
'''
if 'Pinto Bot ID is required' not in s:
    if update_marker not in s:
        raise SystemExit('Expected update_messaging_platform guard block not found')
    s = s.replace(update_marker, update_insert, 1)
else:
    print('Dashboard editable Pinto pseudo-channel guard already patched')

# Show primary Pinto bot id/api url as normal values, not redacted secrets.
s = s.replace('("PINTO_WEBHOOK_URL", "PINTO_WEBHOOK_SECRET")', '("PINTO_API_URL", "PINTO_BOT_ID", "PINTO_WEBHOOK_URL", "PINTO_WEBHOOK_SECRET")')
s = s.replace('key == "PINTO_WEBHOOK_URL"', 'key in ("PINTO_API_URL", "PINTO_BOT_ID", "PINTO_WEBHOOK_URL")')

p.write_text(s, encoding='utf-8')
print('Patched Dashboard Channels API for editable Pinto bot cards')
