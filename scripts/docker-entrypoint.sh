#!/usr/bin/env sh
set -eu

HERMES_HOME="${HERMES_HOME:-/root/.hermes}"
PLUGIN_SRC="${PLUGIN_SRC:-/opt/hermes-pinto-plugin}"
PLUGIN_DEST="${HERMES_HOME}/plugins/platforms/pinto"
PLUGIN_SITE_DEST="/usr/local/lib/python3.11/site-packages/plugins/platforms/pinto"

# ── Install/update plugin files ──
echo "Installing/updating Pinto plugin at ${PLUGIN_DEST}"
mkdir -p "${PLUGIN_DEST}"
cp "${PLUGIN_SRC}/adapter.py"    "${PLUGIN_DEST}/adapter.py"
cp "${PLUGIN_SRC}/plugin.yaml"   "${PLUGIN_DEST}/plugin.yaml"
cp "${PLUGIN_SRC}/__init__.py"   "${PLUGIN_DEST}/__init__.py"
mkdir -p "${PLUGIN_SITE_DEST}"
cp "${PLUGIN_SRC}/adapter.py"    "${PLUGIN_SITE_DEST}/adapter.py"
cp "${PLUGIN_SRC}/plugin.yaml"   "${PLUGIN_SITE_DEST}/plugin.yaml"
cp "${PLUGIN_SRC}/__init__.py"   "${PLUGIN_SITE_DEST}/__init__.py"

# Hermes 0.16 platform-plugin env injector reads description/prompt/password
# from plugin.yaml but drops the advanced flag. Preserve it so Dashboard can
# hide Pinto power-user fields behind Advanced.
python3 - <<'PY'
from pathlib import Path
p = Path('/usr/local/lib/python3.11/site-packages/hermes_cli/config.py')
if p.exists():
    text = p.read_text(encoding='utf-8')
    old = '                    "category": meta.get("category") or "messaging",\n                }'
    new = '                    "category": meta.get("category") or "messaging",\n                    "advanced": bool(meta.get("advanced", False)),\n                }'
    if old in text and new not in text:
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')

p = Path('/usr/local/lib/python3.11/site-packages/hermes_cli/web_server.py')
if p.exists():
    text = p.read_text(encoding='utf-8')
    old = '                "redacted_value": redact_key(value) if value else None,\n                **_messaging_env_info(key),'
    new = '                "redacted_value": (value if key in ("PINTO_WEBHOOK_URL", "PINTO_WEBHOOK_SECRET") else (redact_key(value) if value else None)),\n                **_messaging_env_info(key),'
    if old in text and new not in text:
        text = text.replace(old, new)
    old = '                "redacted_value": (value if key == "PINTO_WEBHOOK_URL" else (redact_key(value) if value else None)),\n                **_messaging_env_info(key),'
    if old in text and new not in text:
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')

# Dashboard channel modal normally puts configured values in placeholder only.
# For Pinto developer-console copy fields, make current values real input values.
for root in Path('/usr/local/lib/python3.11/site-packages').rglob('assets'):
    if not root.is_dir():
        continue
    for js in root.glob('index-*.js'):
        text = js.read_text(encoding='utf-8')
        old = 'M.env_vars.forEach(P=>{R[P.key]=""})'
        new = 'M.env_vars.forEach(P=>{R[P.key]=M.id==="pinto"&&(P.key==="PINTO_WEBHOOK_URL"||P.key==="PINTO_WEBHOOK_SECRET")&&P.redacted_value?P.redacted_value:""})'
        if old in text and new not in text:
            text = text.replace(old, new)
        old = 'l.jsx(ot,{id:`field-${M.key}`,type:M.is_password?"password":"text",placeholder:M.is_set?M.redacted_value||"•••••• (set — leave blank to keep)":M.key,value:f[M.key]??"",onChange:R=>g(P=>({...P,[M.key]:R.target.value}))})'
        new = 'u.id==="pinto"&&(M.key==="PINTO_WEBHOOK_URL"||M.key==="PINTO_WEBHOOK_SECRET")?l.jsx("div",{className:"select-text break-all border border-border bg-background/40 px-3 py-2 font-mono text-xs text-foreground",children:M.redacted_value||"(not generated yet)"}):l.jsx(ot,{id:`field-${M.key}`,type:M.is_password?"password":"text",placeholder:M.is_set?M.redacted_value||"•••••• (set — leave blank to keep)":M.key,value:f[M.key]??"",onChange:R=>g(P=>({...P,[M.key]:R.target.value}))})'
        if old in text and new not in text:
            text = text.replace(old, new)
        js.write_text(text, encoding='utf-8')
PY

# ── Runtime defaults ──
# Fill friendly defaults into ~/.hermes/.env so Dashboard shows useful values.
# Secrets are random per install and are never hardcoded in the image/repo.
DEFAULT_EXPORTS="$(python3 - <<'PY'
import os
import secrets
import shlex
from pathlib import Path

home = Path(os.environ.get('HERMES_HOME', '/root/.hermes'))
env_path = home / '.env'
home.mkdir(parents=True, exist_ok=True)

values = {}
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if not line or line.lstrip().startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        values[k.strip()] = v.strip()

def current(key: str) -> str:
    return (os.environ.get(key) or values.get(key) or '').strip()

webhook_secret = current('PINTO_WEBHOOK_SECRET') or secrets.token_urlsafe(32)

def default(key: str, value: str) -> None:
    if not current(key):
        values[key] = value
        os.environ[key] = value

# User-facing Pinto defaults.
default('PINTO_API_URL', 'https://api.pinto-app.com')
default('PINTO_WEBHOOK_PATH', '/plugins/pinto/webhook')
default('PINTO_WEBHOOK_URL', 'http://127.0.0.1:8642/plugins/pinto/webhook')
default('PINTO_GENERATING_PATH', '/v1/bots/webhook/generating')
default('PINTO_GENERATING_TYPE', 'text')
default('PINTO_RECEIVE_MEDIA_PATH', '/v1/bots/webhook/receive-media')
default('PINTO_ALLOW_ALL_USERS', 'true')
default('PINTO_SEND_MEDIA_URL_FIELD', 'false')
default('PINTO_TYPING_STATUS_INTERVAL', '8')
default('PINTO_TYPING_STATUS_MESSAGE', '')

# One shared random secret works for inbound webhook, generating, and media.
default('PINTO_WEBHOOK_SECRET', webhook_secret)
default('PINTO_GENERATING_SECRET', webhook_secret)
default('PINTO_MEDIA_UPLOAD_SECRET', webhook_secret)

# Prefer Pinto bot_generating websocket indicator. Disable old text fallback spam.
if current('PINTO_TYPING_STATUS_MESSAGE'):
    values['PINTO_TYPING_STATUS_MESSAGE'] = ''
    os.environ['PINTO_TYPING_STATUS_MESSAGE'] = ''

existing_lines = []
seen = set()
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if line and not line.lstrip().startswith('#') and '=' in line:
            key = line.split('=', 1)[0].strip()
            if key in values:
                existing_lines.append(f'{key}={values[key]}')
                seen.add(key)
                continue
        existing_lines.append(line)
for key in sorted(values):
    if key not in seen:
        existing_lines.append(f'{key}={values[key]}')

env_path.write_text('\n'.join(existing_lines).rstrip() + '\n', encoding='utf-8')

export_keys = [
    'PINTO_API_URL',
    'PINTO_WEBHOOK_PATH',
    'PINTO_WEBHOOK_URL',
    'PINTO_GENERATING_PATH',
    'PINTO_GENERATING_TYPE',
    'PINTO_RECEIVE_MEDIA_PATH',
    'PINTO_ALLOW_ALL_USERS',
    'PINTO_SEND_MEDIA_URL_FIELD',
    'PINTO_TYPING_STATUS_INTERVAL',
    'PINTO_TYPING_STATUS_MESSAGE',
    'PINTO_WEBHOOK_SECRET',
    'PINTO_GENERATING_SECRET',
    'PINTO_MEDIA_UPLOAD_SECRET',
]
for key in export_keys:
    value = current(key)
    print(f'export {key}={shlex.quote(value)}')
PY
)"

# Export defaults for this process, including generated secrets. Do not source
# full .env because values may contain spaces/Thai text and be intentionally unquoted.
eval "${DEFAULT_EXPORTS}"

# ── Bootstrap config ──
python3 /usr/local/bin/bootstrap-hermes-config.py

exec "$@"
