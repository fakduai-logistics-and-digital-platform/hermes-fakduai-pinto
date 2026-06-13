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

media_import_old = 'import uuid\nfrom typing import TYPE_CHECKING, Any, List, Optional\n'
media_import_new = 'import uuid\nfrom pathlib import Path\nfrom typing import TYPE_CHECKING, Any, List, Optional\nfrom urllib.parse import urlparse\n\ntry:\n    from aiohttp import web\nexcept Exception:\n    web = None\n'
if media_import_old in s:
    s = s.replace(media_import_old, media_import_new)
    patched = True
elif 'from urllib.parse import urlparse' in s:
    print('Pinto adapter media imports patch already applied')
else:
    raise SystemExit('Expected Pinto import block not found')

media_init_old = '''        self._webhook_path = extra.get("webhookPath") or os.getenv(
            "PINTO_WEBHOOK_PATH", DEFAULT_WEBHOOK_PATH
        )
        self._client: Optional["_httpx.AsyncClient"] = None
'''
media_init_new = '''        self._webhook_path = extra.get("webhookPath") or os.getenv(
            "PINTO_WEBHOOK_PATH", DEFAULT_WEBHOOK_PATH
        )
        self._media_path = os.getenv("PINTO_MEDIA_PATH", "/plugins/pinto/media")
        self._media_files: dict[str, str] = {}
        self._client: Optional["_httpx.AsyncClient"] = None
'''
if media_init_old in s:
    s = s.replace(media_init_old, media_init_new)
    patched = True
elif 'self._media_files: dict[str, str] = {}' in s:
    print('Pinto adapter media init patch already applied')
else:
    raise SystemExit('Expected Pinto init block not found')

media_route_old = '''                api_app.router.add_post(self._webhook_path, self._handle_webhook)
                api_app.router.add_get(self._webhook_path, self._handle_webhook_ping)
                logger.info(
'''
media_route_new = '''                api_app.router.add_post(self._webhook_path, self._handle_webhook)
                api_app.router.add_get(self._webhook_path, self._handle_webhook_ping)
                api_app.router.add_get(self._media_path + "/{token}", self._handle_media)
                logger.info(
'''
if media_route_old in s:
    s = s.replace(media_route_old, media_route_new)
    patched = True
elif 'self._handle_media' in s:
    print('Pinto adapter media route patch already applied')
else:
    raise SystemExit('Expected Pinto route block not found')

media_methods = '''
    def _public_base_url(self) -> str:
        explicit = os.getenv("PINTO_PUBLIC_BASE_URL", "").rstrip("/")
        if explicit:
            return explicit
        webhook_url = os.getenv("PINTO_WEBHOOK_URL", "")
        env_path = Path(os.getenv("HERMES_HOME", "/root/.hermes")) / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text().splitlines():
                    if line.startswith("PINTO_WEBHOOK_URL="):
                        webhook_url = line.split("=", 1)[1].strip()
                    elif line.startswith("PINTO_PUBLIC_BASE_URL="):
                        explicit = line.split("=", 1)[1].strip().rstrip("/")
                        if explicit:
                            return explicit
            except Exception:
                pass
        if webhook_url:
            parsed = urlparse(webhook_url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        return ""

    def _media_url_for_file(self, file_path: str) -> str:
        if file_path.startswith(("http://", "https://")):
            return file_path
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return file_path
        token = f"{int(time.time())}_{uuid.uuid4().hex}_{path.name}"
        self._media_files[token] = str(path)
        base = self._public_base_url()
        if not base:
            return file_path
        return f"{base}{self._media_path}/{token}"

    async def _handle_media(self, request):
        token = request.match_info.get("token", "")
        file_path = self._media_files.get(token)
        if not file_path or not Path(file_path).exists():
            return web.Response(status=404, text="Not found")
        return web.FileResponse(file_path)
'''
if 'def _public_base_url(self) -> str:' not in s:
    marker = '    # -- send ----------------------------------------------------------------\n'
    if marker not in s:
        raise SystemExit('Expected Pinto send marker not found')
    s = s.replace(marker, media_methods + '\n' + marker)
    patched = True
else:
    print('Pinto adapter media methods patch already applied')

media_send_old = '''        media_files = kwargs.get("media_files")
        if media_files:
            payload["media_url"] = media_files[0]
'''
media_send_new = '''        media_files = kwargs.get("media_files")
        if media_files:
            payload["media_url"] = self._media_url_for_file(str(media_files[0]))
'''
if media_send_old in s:
    s = s.replace(media_send_old, media_send_new)
    patched = True
elif 'self._media_url_for_file(str(media_files[0]))' in s:
    print('Pinto adapter media send patch already applied')
else:
    raise SystemExit('Expected Pinto media send block not found')

p.write_text(s, encoding='utf-8')
print('Patched Pinto adapter for Hermes 0.16 compatibility' if patched else 'Pinto adapter already patched')
