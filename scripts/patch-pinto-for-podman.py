#!/usr/bin/env python3
"""Patch Pinto adapter compatibility for Hermes 0.16 + Podman deployment.

Hermes 0.16 does not expose the live api_server adapter on platform_registry.
The Pinto adapter expects it there to mount /plugins/pinto/webhook.
This patch adds a small GC fallback to find the live APIServerAdapter instance.
"""
from pathlib import Path
import re

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
    print('Pinto adapter route patch not needed or already changed upstream')
else:
    s = s.replace(old, new)
    patched = True

auth_old = '''            if self._webhook_secret:
                inbound_secret = request.headers.get(PINTO_SECRET_HEADER, "")
                if inbound_secret != self._webhook_secret:
                    return request.app["response_class"](
                        status=401,
                        text=json.dumps({"error": "Invalid webhook secret"}),
                        content_type="application/json",
                    )
'''
auth_new = '''            if self._webhook_secret:
                inbound_secret = request.headers.get(PINTO_SECRET_HEADER, "")
                if inbound_secret != self._webhook_secret:
                    return request.app["response_class"](
                        status=401,
                        text=json.dumps({
                            "ok": False,
                            "error": "invalid_webhook_secret",
                            "message": (
                                "\u2716\ufe0f Access Denied \u2014 Webhook Secret \u0e44\u0e21\u0e48\u0e16\u0e39\u0e01\u0e15\u0e49\u0e2d\u0e07 "
                                "\u0e2b\u0e23\u0e37\u0e2d\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e23\u0e31\u0e1a\u0e01\u0e32\u0e23\u0e22\u0e37\u0e19\u0e22\u0e31\u0e19\u0e08\u0e32\u0e01\u0e1f\u0e32\u0e01\u0e08\u0e32\u0e21 Hermes Gateway "
                                "\u0e42\u0e1b\u0e23\u0e14\u0e15\u0e23\u0e27\u0e08\u0e2a\u0e2d\u0e1a Webhook Secret \u0e43\u0e2b\u0e49\u0e15\u0e23\u0e07\u0e01\u0e31\u0e1a\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e1a\u0e19 Hermes Dashboard "
                                "\u0e41\u0e25\u0e49\u0e27\u0e25\u0e2d\u0e07\u0e2d\u0e35\u0e01\u0e04\u0e23\u0e31\u0e49\u0e07\u0e04\u0e23\u0e31\u0e1a/\u0e04\u0e48\u0e30"
                            ),
                        }),
                        content_type="application/json",
                    )
'''
if auth_old in s:
    s = s.replace(auth_old, auth_new)
    patched = True
elif 'invalid_webhook_secret' in s:
    print('Pinto adapter webhook secret error message patch already applied')
else:
    raise SystemExit('Expected Pinto webhook secret check block not found')

mismatch_old = '''            if bot_id != self._bot_id:
                return request.app["response_class"](
                    status=403,
                    text=json.dumps({"error": "bot_id mismatch"}),
                    content_type="application/json",
                )
'''
mismatch_new = '''            if bot_id != self._bot_id:
                return request.app["response_class"](
                    status=403,
                    text=json.dumps({
                        "ok": False,
                        "error": "bot_id_mismatch",
                        "message": (
                            "\u2716\ufe0f Access Denied \u2014 Bot ID \u0e44\u0e21\u0e48\u0e16\u0e39\u0e01\u0e15\u0e49\u0e2d\u0e07 "
                            "\u0e23\u0e49\u0e2d\u0e07\u0e02\u0e2d\u0e19\u0e35\u0e49\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e16\u0e39\u0e01\u0e25\u0e07\u0e17\u0e30\u0e40\u0e1a\u0e35\u0e22\u0e19\u0e44\u0e27\u0e49\u0e01\u0e31\u0e1a Gateway \u0e19\u0e35\u0e49 "
                            "\u0e42\u0e1b\u0e23\u0e14\u0e15\u0e23\u0e27\u0e08\u0e2a\u0e2d\u0e1a PINTO_BOT_ID \u0e43\u0e2b\u0e49\u0e15\u0e23\u0e07\u0e01\u0e31\u0e1a\u0e1a\u0e2d\u0e15\u0e17\u0e35\u0e48\u0e25\u0e07\u0e17\u0e30\u0e40\u0e1a\u0e35\u0e22\u0e19\u0e44\u0e27\u0e49 "
                            "\u0e41\u0e25\u0e49\u0e27\u0e25\u0e2d\u0e07\u0e2d\u0e35\u0e01\u0e04\u0e23\u0e31\u0e49\u0e07\u0e04\u0e23\u0e31\u0e1a/\u0e04\u0e48\u0e30"
                        ),
                    }),
                    content_type="application/json",
                )
'''
if mismatch_old in s:
    s = s.replace(mismatch_old, mismatch_new)
    patched = True
elif 'bot_id_mismatch' in s:
    print('Pinto adapter bot_id mismatch error message patch already applied')
else:
    raise SystemExit('Expected Pinto bot_id mismatch block not found')

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

if 'import re\n' not in s:
    s = s.replace('import os\n', 'import os\nimport re\n', 1)
    patched = True

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
        self._typing_last_sent: dict[str, float] = {}
        self._typing_status_message = os.getenv("PINTO_TYPING_STATUS_MESSAGE", "")
        self._typing_status_interval = float(os.getenv("PINTO_TYPING_STATUS_INTERVAL", "20"))
        self._generating_path = os.getenv("PINTO_GENERATING_PATH", "/v1/bots/webhook/generating")
        self._generating_secret = os.getenv("PINTO_GENERATING_SECRET", "") or os.getenv("PINTO_WEBHOOK_SECRET", "")
        self._generating_type_default = os.getenv("PINTO_GENERATING_TYPE", "text")
        self._generating_state: dict[str, tuple[bool, str]] = {}
        self._receive_media_path = os.getenv("PINTO_RECEIVE_MEDIA_PATH", "/v1/bots/webhook/receive-media")
        self._media_upload_secret = os.getenv("PINTO_MEDIA_UPLOAD_SECRET", "") or os.getenv("PINTO_WEBHOOK_SECRET", "")
        self._client: Optional["_httpx.AsyncClient"] = None
'''
if media_init_old in s:
    s = s.replace(media_init_old, media_init_new)
    patched = True
elif 'self._media_files: dict[str, str] = {}' in s:
    if 'self._generating_path =' not in s:
        s = s.replace('''        self._typing_status_interval = float(os.getenv("PINTO_TYPING_STATUS_INTERVAL", "20"))
        self._client: Optional["_httpx.AsyncClient"] = None
''', '''        self._typing_status_interval = float(os.getenv("PINTO_TYPING_STATUS_INTERVAL", "20"))
        self._generating_path = os.getenv("PINTO_GENERATING_PATH", "/v1/bots/webhook/generating")
        self._generating_secret = os.getenv("PINTO_GENERATING_SECRET", "") or os.getenv("PINTO_WEBHOOK_SECRET", "")
        self._generating_type_default = os.getenv("PINTO_GENERATING_TYPE", "text")
        self._generating_state: dict[str, tuple[bool, str]] = {}
        self._receive_media_path = os.getenv("PINTO_RECEIVE_MEDIA_PATH", "/v1/bots/webhook/receive-media")
        self._media_upload_secret = os.getenv("PINTO_MEDIA_UPLOAD_SECRET", "") or os.getenv("PINTO_WEBHOOK_SECRET", "")
        self._client: Optional["_httpx.AsyncClient"] = None
''')
        patched = True
    else:
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
    async def _set_generating(self, chat_id: str, is_generating: bool, generating_type: str = "text") -> None:
        if not self._client or not self._bot_id:
            return
        generating_type = (generating_type or self._generating_type_default or "text") if is_generating else ""
        state = (is_generating, generating_type)
        if self._generating_state.get(chat_id) == state:
            return
        self._generating_state[chat_id] = state
        url = f"{self._api_url}{self._generating_path}"
        headers = {"Content-Type": "application/json"}
        if self._generating_secret:
            headers[PINTO_SECRET_HEADER] = self._generating_secret
        payload = {
            "bot_id": self._bot_id,
            "chat_id": chat_id,
            "is_generating": is_generating,
            "generating_type": generating_type,
        }
        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            if resp.status_code >= 300:
                logger.warning("Pinto generating status failed: HTTP %s %s", resp.status_code, resp.text)
        except Exception as e:
            logger.warning("Pinto generating status failed: %s", e)

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

    async def _send_media_file(self, chat_id: str, caption: str, file_path: str) -> SendResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return SendResult(success=False, error=f"Media file not found: {file_path}")
        url = f"{self._api_url}{self._receive_media_path}"
        headers = {}
        if self._media_upload_secret:
            headers["X-Pinto-Media-Secret"] = self._media_upload_secret
        data = {
            "bot_id": self._bot_id,
            "chat_id": chat_id,
        }
        if caption:
            data["reply_message"] = caption
        content_type = "image/png"
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif suffix == ".webp":
            content_type = "image/webp"
        elif suffix == ".gif":
            content_type = "image/gif"
        try:
            await self._set_generating(chat_id, False, "image")
            with path.open("rb") as f:
                files = {"file": (path.name, f, content_type)}
                resp = await self._client.post(url, data=data, files=files, headers=headers)
            if resp.status_code >= 300:
                return SendResult(success=False, error=f"Pinto media HTTP {resp.status_code}: {resp.text}")
            return SendResult(success=True, message_id=str(time.time()))
        except Exception as e:
            return SendResult(success=False, error=str(e))

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
elif 'async def _set_generating(' not in s:
    s = s.replace('    def _public_base_url(self) -> str:\n', media_methods.split('    def _public_base_url(self) -> str:\n', 1)[0] + '    def _public_base_url(self) -> str:\n')
    patched = True
elif 'async def _send_media_file(' not in s:
    s = s.replace('    async def _handle_media(self, request):\n', media_methods.split('    async def _handle_media(self, request):\n', 1)[0].split('    def _public_base_url(self) -> str:\n', 1)[1].split('    async def _send_media_file', 1)[1].join(['    async def _send_media_file', '']) + '    async def _handle_media(self, request):\n')
    patched = True
else:
    print('Pinto adapter media/generating methods patch already applied')

media_send_old = '''        media_files = kwargs.get("media_files")
        if media_files:
            payload["media_url"] = media_files[0]
'''
media_send_new = '''        media_files = kwargs.get("media_files")
        generating_type = self._generating_type_default
        if media_files:
            generating_type = "image"
            media_file = str(media_files[0])
            if Path(media_file).exists() and Path(media_file).is_file():
                return await self._send_media_file(chat_id, text, media_file)
            payload["media_url"] = self._media_url_for_file(media_file)
        elif text:
            match = re.search(r"(/[^\\s]+\\.(?:png|jpg|jpeg|gif|webp))", text, re.IGNORECASE)
            if match:
                generating_type = "image"
                media_url = self._media_url_for_file(match.group(1))
                if media_url != match.group(1):
                    payload["media_url"] = media_url
        await self._set_generating(chat_id, False, generating_type)
'''
if media_send_old in s:
    s = s.replace(media_send_old, media_send_new)
    patched = True
elif 're.search(r"(/[^\\s]+\\.(?:png|jpg|jpeg|gif|webp))"' in s:
    if 'return await self._send_media_file(chat_id, text, media_file)' not in s:
        s = s.replace('''        media_files = kwargs.get("media_files")
        generating_type = self._generating_type_default
        if media_files:
            generating_type = "image"
            payload["media_url"] = self._media_url_for_file(str(media_files[0]))
''', '''        media_files = kwargs.get("media_files")
        generating_type = self._generating_type_default
        if media_files:
            generating_type = "image"
            media_file = str(media_files[0])
            if Path(media_file).exists() and Path(media_file).is_file():
                return await self._send_media_file(chat_id, text, media_file)
            payload["media_url"] = self._media_url_for_file(media_file)
''')
        patched = True
    else:
        print('Pinto adapter text path media patch already applied')
elif 'self._media_url_for_file(str(media_files[0]))' in s:
    s = s.replace('''        media_files = kwargs.get("media_files")
        if media_files:
            payload["media_url"] = self._media_url_for_file(str(media_files[0]))
''', media_send_new)
    patched = True
else:
    raise SystemExit('Expected Pinto media send block not found')

typing_old = '''    async def send_typing(self, chat_id: str) -> None:\n        pass  # Pinto has no typing indicator API\n'''
typing_new = '''    async def send_typing(self, chat_id: str, metadata=None) -> None:\n        """Tell Pinto clients this bot is generating a response.\n\n        Pinto exposes ``POST /v1/bots/webhook/generating`` and broadcasts a\n        ``bot_generating`` websocket event. Hermes calls this while processing;\n        ``send()`` clears the indicator before delivering the final message.\n        """\n        generating_type = self._generating_type_default\n        if isinstance(metadata, dict):\n            generating_type = metadata.get("generating_type") or metadata.get("type") or generating_type\n        await self._set_generating(chat_id, True, generating_type)\n        if not self._typing_status_message:\n            return\n        now = time.time()\n        last = self._typing_last_sent.get(chat_id, 0)\n        if now - last < self._typing_status_interval:\n            return\n        self._typing_last_sent[chat_id] = now\n        await self.send(chat_id, self._typing_status_message)\n'''
receive_media_method = '''
    async def _send_receive_media_file(self, chat_id: str, caption: str, file_path: str) -> SendResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return SendResult(success=False, error=f"Media file not found: {file_path}")
        url = f"{self._api_url}{self._receive_media_path}"
        headers = {}
        if self._media_upload_secret:
            headers["X-Pinto-Media-Secret"] = self._media_upload_secret
        data = {"bot_id": self._bot_id, "chat_id": chat_id}
        if caption:
            data["reply_message"] = caption
        content_type = "image/png"
        suffix = path.suffix.lower()
        if suffix in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif suffix == ".webp":
            content_type = "image/webp"
        elif suffix == ".gif":
            content_type = "image/gif"
        await self._set_generating(chat_id, False, "image")
        with path.open("rb") as file_handle:
            files = {"file": (path.name, file_handle, content_type)}
            resp = await self._client.post(url, data=data, files=files, headers=headers)
        if resp.status_code >= 300:
            return SendResult(success=False, error=f"Pinto media HTTP {resp.status_code}: {resp.text}")
        return SendResult(success=True, message_id=str(time.time()))
'''
extract_new = '''    def _extract_media_file(self, text: str, media_files: Any = None) -> Optional[str]:
        if media_files:
            return str(media_files[0])
        if text:
            match = re.search(r"(/[^\\s]+\\.(?:png|jpg|jpeg|gif|webp))", text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
'''
if 'newest = max(candidates, key=lambda p: p.stat().st_mtime)' not in s and 'def _extract_media_file(' in s:
    s2 = re.sub(
        r'    def _extract_media_file\(self, text: str, media_files: Any = None\) -> Optional\[str\]:.*?(?=\n    async def _send_native_chat_message\()',
        lambda _m: extract_new + '\n',
        s,
        count=1,
        flags=re.S,
    )
    if s2 != s:
        s = s2
        patched = True

send_new_logged = '''    async def send(self, chat_id: str, text: str = "", content: str = "", **kwargs: Any) -> SendResult:
        """Post reply back to Pinto."""
        if content and not text:
            text = content
        if not self._client:
            return SendResult(success=False, error="Adapter not connected")

        media_file = self._extract_media_file(text, kwargs.get("media_files"))
        try:
            if media_file:
                await self._set_generating(chat_id, True, "image")
            await self._set_generating(chat_id, False, "")
            image_completion_text = bool(
                text
                and not media_file
                and (
                    "ภาพสร้างแล้ว" in text
                    or "รูปสร้างแล้ว" in text
                    or "image generated" in text.lower()
                    or "generated image" in text.lower()
                )
            )
            if image_completion_text:
                logger.warning("Pinto outbound suppress image completion text chat_id=%s text_len=%s", chat_id, len(text or ""))
                return SendResult(success=True, message_id=str(time.time()))
            if self._bearer_token:
                result = await self._send_native_chat_message(chat_id, text, media_file)
            else:
                result = await self._send_webhook_receive(chat_id, text, media_file)
            if result.success:
                logger.warning("Pinto outbound send OK chat_id=%s media=%s text_len=%s", chat_id, bool(media_file), len(text or ""))
            else:
                logger.error("Pinto outbound send FAILED chat_id=%s media=%s error=%s", chat_id, bool(media_file), result.error)
            return result
        except Exception as e:
            logger.exception("Pinto outbound send exception chat_id=%s media=%s", chat_id, bool(media_file))
            return SendResult(success=False, error=str(e))
        finally:
            self._generating_state.pop(chat_id, None)
            await self._set_generating(chat_id, False, "")
'''
if 'Pinto outbound send OK chat_id=' not in s and 'async def send(self, chat_id:' in s:
    s2 = re.sub(
        r'    async def send\(self, chat_id: str.*?(?=\n    async def send_typing\()',
        lambda _m: send_new_logged + '\n',
        s,
        count=1,
        flags=re.S,
    )
    if s2 != s:
        s = s2
        patched = True

if 'async def _send_webhook_receive(' in s and 'async def _send_receive_media_file(' not in s:
    s = s.replace('    async def _send_webhook_receive(', receive_media_method + '\n    async def _send_webhook_receive(', 1)
    patched = True
if 'async def _send_webhook_receive(' in s and 'return await self._send_receive_media_file(chat_id, text, media_file)' not in s:
    s = s.replace('''        if media_file:
            media_url = await self._public_url_for_media(media_file)
''', '''        if media_file:
            if Path(str(media_file)).exists() and Path(str(media_file)).is_file():
                return await self._send_receive_media_file(chat_id, "", str(media_file))
            media_url = await self._public_url_for_media(media_file)
''')
    patched = True

active_chat_patch = '''                os.environ["PINTO_ACTIVE_CHAT_ID"] = str(chat_id or "")
                os.environ["PINTO_ACTIVE_BOT_ID"] = str(bot_id or self._bot_id or "")
'''
if 'PINTO_ACTIVE_CHAT_ID' not in s:
    markers = [
        '                username = body.get("username") or str(user_id)\n',
        '                username = (raw_msg.get("sender") or {}).get("username") or str(user_id)\n',
    ]
    for marker in markers:
        if marker in s:
            s = s.replace(marker, marker + active_chat_patch, 1)
            patched = True
    if 'PINTO_ACTIVE_CHAT_ID' not in s:
        raise SystemExit('Expected Pinto webhook parse username markers not found')

if typing_old in s:
    s = s.replace(typing_old, typing_new)
    patched = True
elif 'Pinto exposes ``POST /v1/bots/webhook/generating``' in s:
    print('Pinto adapter typing status patch already applied')
elif 'async def send_typing(self, chat_id:' in s:
    s2 = re.sub(
        r'    async def send_typing\(self, chat_id: str[^\n]*\).*?(?=\n    async def send_image\()',
        typing_new.rstrip() + '\n',
        s,
        count=1,
        flags=re.S,
    )
    if s2 == s:
        raise SystemExit('Expected Pinto send_typing block not replaced')
    s = s2
    patched = True
else:
    raise SystemExit('Expected Pinto send_typing block not found')

p.write_text(s, encoding='utf-8')
print('Patched Pinto adapter for Hermes 0.16 compatibility' if patched else 'Pinto adapter already patched')
