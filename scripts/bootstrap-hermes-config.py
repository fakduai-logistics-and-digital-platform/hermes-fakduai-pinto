#!/usr/bin/env python3
"""Bootstrap Hermes config.yaml with Pinto platform for Docker.

Auto-configures:
  - plugins.enabled: platforms/pinto
  - platforms.pinto: enabled
  - platforms.api_server: enabled (webhook receiver)
  - platform_toolsets.pinto: default toolset list
  - .env: API_SERVER_KEY if missing

User can set Pinto botId persistently in config.yaml.
PINTO_BOT_ID from .env is only a first-boot fallback when config.yaml has no botId.
"""

import os
import secrets
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML not installed, skipping config bootstrap")
    sys.exit(0)

HERMES_HOME = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
CONFIG_PATH = Path(HERMES_HOME) / "config.yaml"
ENV_PATH = Path(HERMES_HOME) / ".env"

PINTO_TOOLSETS = [
    "browser",
    "clarify",
    "code_execution",
    "cronjob",
    "delegation",
    "file",
    "image_gen",
    "memory",
    "messaging",
    "session_search",
    "skills",
    "terminal",
    "todo",
    "tts",
    "vision",
    "web",
]


def ensure_api_server_key() -> str:
    key = os.environ.get("API_SERVER_KEY", "").strip()
    if key:
        return key
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("API_SERVER_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return key
    key = secrets.token_urlsafe(32)
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ENV_PATH, "a", encoding="utf-8") as f:
        f.write(f"\nAPI_SERVER_KEY={key}\n")
    print(f"Generated API_SERVER_KEY in {ENV_PATH}")
    return key


def read_env_value(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


def ensure_pinto_bot_id(config: dict) -> None:
    """Warn if Pinto botId is not set in config.yaml or environment fallback."""
    config_bot_id = (
        config.get("platforms", {})
        .get("pinto", {})
        .get("extra", {})
        .get("botId", "")
    )
    bot_id = str(config_bot_id or "").strip() or read_env_value("PINTO_BOT_ID")
    if bot_id:
        return

    print()
    print("=" * 50)
    print("  Pinto botId not set!")
    print("  Preferred persistent setting:")
    print("    hermes-config/config.yaml -> platforms.pinto.extra.botId")
    print("  First-boot fallback:")
    print("    PINTO_BOT_ID=your_bot_id")
    print("=" * 50)
    print()


def main():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if CONFIG_PATH.exists():
        raw = CONFIG_PATH.read_text(encoding="utf-8").strip()
        if raw:
            try:
                config = yaml.safe_load(raw) or {}
            except Exception as e:
                print(f"Cannot parse {CONFIG_PATH}: {e}")
                config = {}

    if not isinstance(config, dict):
        config = {}

    changed = False

    # ── plugins.enabled ──
    plugins = config.get("plugins", {})
    if not isinstance(plugins, dict):
        plugins = {}
    enabled = plugins.get("enabled", [])
    if not isinstance(enabled, list):
        enabled = []
    if "platforms/pinto" not in enabled:
        enabled.append("platforms/pinto")
        plugins["enabled"] = enabled
        config["plugins"] = plugins
        changed = True
        print("Added 'platforms/pinto' to plugins.enabled")

    # ── platforms section ──
    if "platforms" not in config or not isinstance(config["platforms"], dict):
        config["platforms"] = {}
        changed = True

    # Enable api_server
    api_server = config["platforms"].get("api_server", {})
    if not isinstance(api_server, dict):
        api_server = {}
    if not api_server.get("enabled"):
        api_server["enabled"] = True
        changed = True
        print("Enabled platforms.api_server")
    if "extra" not in api_server or not isinstance(api_server.get("extra"), dict):
        api_server["extra"] = {}
    api_host = os.environ.get("API_SERVER_HOST", "0.0.0.0").strip() or "0.0.0.0"
    if api_server["extra"].get("host") != api_host:
        api_server["extra"]["host"] = api_host
        changed = True
        print(f"Set platforms.api_server.extra.host={api_host}")
    config["platforms"]["api_server"] = api_server

    # Enable pinto. Prefer existing config.yaml botId so persistent local
    # config is not overwritten by stale .env/process env values after restart.
    if "pinto" not in config["platforms"]:
        config["platforms"]["pinto"] = {"enabled": True}
        changed = True
        print("Enabled platforms.pinto")
    elif not config["platforms"].get("pinto", {}).get("enabled"):
        config["platforms"]["pinto"] = {"enabled": True}
        changed = True

    # Set botId in platforms.pinto.extra only when config.yaml does not
    # already have one. This makes config.yaml the durable source of truth;
    # PINTO_BOT_ID remains a first-boot fallback for beginner setup.
    pinto_config = config["platforms"]["pinto"]
    if not isinstance(pinto_config, dict):
        pinto_config = {}
        config["platforms"]["pinto"] = pinto_config
    if "extra" not in pinto_config or not isinstance(pinto_config.get("extra"), dict):
        pinto_config["extra"] = {}
    config_bot_id = str(pinto_config["extra"].get("botId") or "").strip()
    fallback_bot_id = read_env_value("PINTO_BOT_ID")
    if not config_bot_id and fallback_bot_id:
        pinto_config["extra"]["botId"] = fallback_bot_id
        changed = True
        print("Set platforms.pinto.extra.botId from PINTO_BOT_ID fallback")

    # ── platform_toolsets.pinto ──
    toolsets = config.get("platform_toolsets", {})
    if not isinstance(toolsets, dict):
        toolsets = {}
    if "pinto" not in toolsets:
        toolsets["pinto"] = PINTO_TOOLSETS
        config["platform_toolsets"] = toolsets
        changed = True
        print(f"Added platform_toolsets.pinto ({len(PINTO_TOOLSETS)} toolsets)")

    if changed:
        CONFIG_PATH.write_text(
            yaml.dump(config, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"Updated Hermes config: {CONFIG_PATH}")

    # ── Generate API_SERVER_KEY ──
    ensure_api_server_key()

    # ── Check PINTO_BOT_ID ──
    ensure_pinto_bot_id(config)

    print("Bootstrap complete!")


if __name__ == "__main__":
    main()
