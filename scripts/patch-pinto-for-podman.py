#!/usr/bin/env python3
"""Patch Pinto adapter compatibility for Hermes 0.16 + Podman deployment.

Hermes 0.16 does not expose the live api_server adapter on platform_registry.
The Pinto adapter expects it there to mount /plugins/pinto/webhook.
This patch adds a small GC fallback to find the live APIServerAdapter instance.
"""
from pathlib import Path

p = Path('/opt/hermes-pinto-plugin/adapter.py')
s = p.read_text(encoding='utf-8')
old = '''            if api_app is not None:
                api_app.router.add_post(self._webhook_path, self._handle_webhook)
                api_app.router.add_get(self._webhook_path, self._handle_webhook_ping)
                logger.info(
                    "Pinto webhook registered at %s (api_server port %s)",
                    self._webhook_path,
                    api_port,
                )
            else:
                logger.warning(
                    "api_server aiohttp app not found — Pinto webhook not mounted. "
                    "Enable platforms.api_server in config.yaml and ensure it starts before pinto."
                )
'''
new = '''            if api_app is None:
                # Hermes 0.16 does not expose the live api_server adapter on
                # platform_registry. Find it from live objects as a compatibility shim.
                try:
                    import gc
                    for obj in gc.get_objects():
                        if obj.__class__.__name__ == "APIServerAdapter":
                            candidate = getattr(obj, "_app", None)
                            if candidate is not None:
                                api_app = candidate
                                api_port = getattr(obj, "_port", "?")
                                break
                except Exception:
                    pass

            if api_app is not None:
                api_app.router.add_post(self._webhook_path, self._handle_webhook)
                api_app.router.add_get(self._webhook_path, self._handle_webhook_ping)
                logger.info(
                    "Pinto webhook registered at %s (api_server port %s)",
                    self._webhook_path,
                    api_port,
                )
            else:
                logger.warning(
                    "api_server aiohttp app not found — Pinto webhook not mounted. "
                    "Enable platforms.api_server in config.yaml and ensure it starts before pinto."
                )
'''
patched = False
if old not in s:
    if 'Hermes 0.16 does not expose the live api_server adapter' in s:
        print('Pinto adapter route patch already applied')
    else:
        raise SystemExit('Expected Pinto adapter block not found')
else:
    s = s.replace(old, new)
    patched = True

send_old = '''    async def send(self, chat_id: str, text: str, **kwargs: Any) -> SendResult:
        """Post reply back to Pinto via ``POST /v1/bots/webhook/receive``."""
        if not self._client:
'''
send_new = '''    async def send(self, chat_id: str, text: str = "", content: str = "", **kwargs: Any) -> SendResult:
        """Post reply back to Pinto via ``POST /v1/bots/webhook/receive``."""
        if content and not text:
            text = content
        if not self._client:
'''
if send_old in s:
    s = s.replace(send_old, send_new)
    patched = True
elif 'async def send(self, chat_id: str, text: str = "", content: str = "", **kwargs: Any)' in s:
    print('Pinto adapter send signature patch already applied')
else:
    raise SystemExit('Expected Pinto send signature not found')

p.write_text(s, encoding='utf-8')
print('Patched Pinto adapter for Hermes 0.16 compatibility' if patched else 'Pinto adapter already patched')
