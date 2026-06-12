#!/usr/bin/env python3
"""Bootstrap Hermes config.yaml with Pinto platform defaults for Docker.

Creates or updates:
  - config.yaml with pinto platform enabled + api_server
  - .env with API_SERVER_KEY if missing
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


def default_pinto_extra() -> dict:
    return {
        "apiUrl": os.environ.get("PINTO_API_URL", "https://api.pinto-app.com"),
        "botId": os.environ.get("PINTO_BOT_ID", ""),
        "webhookSecret": os.environ.get("PINTO_WEBHOOK_SECRET", f"pinto-{secrets.token_hex(12)}"),
        "webhookPath": os.environ.get("PINTO_WEBHOOK_PATH", "/plugins/pinto/webhook"),
    }


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

    # Ensure platforms section
    if "platforms" not in config or not isinstance(config["platforms"], dict):
        config["platforms"] = {}
        changed = True

    # Enable api_server (needed for webhook receiving)
    if "api_server" not in config["platforms"]:
        config["platforms"]["api_server"] = {"enabled": True}
        changed = True
    elif not config["platforms"]["api_server"].get("enabled"):
        config["platforms"]["api_server"]["enabled"] = True
        changed = True

    # Enable pinto platform
    if "pinto" not in config["platforms"]:
        config["platforms"]["pinto"] = {
            "enabled": True,
            "extra": default_pinto_extra(),
        }
        changed = True
        print(f"Initialized platforms.pinto in {CONFIG_PATH}")

    if changed:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True), encoding="utf-8")
        print(f"Updated Hermes config in {CONFIG_PATH}")

    # Generate API_SERVER_KEY if missing
    ensure_api_server_key()


if __name__ == "__main__":
    main()
