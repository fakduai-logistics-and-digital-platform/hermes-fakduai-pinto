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

# Resolve per-bot prompts through a local persona registry:
#
#   platforms.pinto.extra.pintoAgents:
#     thai-poet:
#       name: นักแต่งกลอน
#       channelPrompt: ...
#   platforms.pinto.extra.bots:
#     <bot_id>:
#       persona: thai-poet
#
# Backward-compatible fallback keeps bot-level channelPrompt/role/name working.
if 'self._persona_configs = extra.get("pintoAgents")' not in s:
    init_marker = '        self._bot_configs = extra.get("bots") if isinstance(extra.get("bots"), dict) else {}\n'
    if init_marker in s:
        s = s.replace(
            init_marker,
            init_marker + '        self._persona_configs = extra.get("pintoAgents") if isinstance(extra.get("pintoAgents"), dict) else {}\n',
            1,
        )
        patched = True
    else:
        raise SystemExit('Expected Pinto bot configs init marker not found')

old_prompt = '''    def _bot_channel_prompt(self, bot_config: dict) -> Optional[str]:
        prompt = bot_config.get("channelPrompt") or bot_config.get("prompt")
        role = bot_config.get("role") or bot_config.get("name")
        if prompt:
            return str(prompt).strip()
        if role:
            return f"You are {role}. Stay in this role for this chat."
        return None
'''
new_prompt = '''    def _bot_channel_prompt(self, bot_config: dict) -> Optional[str]:
        persona_key = (
            bot_config.get("persona")
            or bot_config.get("personaKey")
            or bot_config.get("agent_id")
            or bot_config.get("agentId")
        )
        persona_config = None
        if persona_key and isinstance(getattr(self, "_persona_configs", None), dict):
            candidate = self._persona_configs.get(str(persona_key))
            if isinstance(candidate, dict):
                persona_config = candidate

        source = persona_config or bot_config
        prompt = source.get("channelPrompt") or source.get("prompt") or source.get("systemPrompt")
        role = source.get("role") or source.get("name") or persona_key
        if prompt:
            return str(prompt).strip()
        if role:
            return f"You are {role}. Stay in this role for this chat."
        return None
'''
if old_prompt in s:
    s = s.replace(old_prompt, new_prompt)
    patched = True
elif 'bot_config.get("persona")' in s and 'self._persona_configs' in s:
    print('Pinto adapter persona registry prompt patch already applied')
else:
    raise SystemExit('Expected Pinto _bot_channel_prompt block not found')

# Optional company workflow mode: when a bot's config has a truthy
# "companyWorkflow" field, run a local sequential persona handoff chain
# (Hermes-only, no OpenClaw) instead of the normal single-turn agent run,
# then send the final handoff output back to the chat directly.
company_marker = '            self._active_bot_by_chat[str(chat_id)] = str(bot_id)\n            channel_prompt = self._bot_channel_prompt(bot_config)\n'
if 'await self._run_company_workflow(' not in s:
    if company_marker not in s:
        raise SystemExit('Expected Pinto webhook bot_config/channel_prompt marker not found')
    company_branch = company_marker + '''
            if bot_config.get("companyWorkflow"):
                asyncio.create_task(self._run_company_workflow(str(chat_id), str(bot_id), bot_config, message_text))
                return request.app["response_class"](
                    status=200,
                    text=json.dumps({"ok": True, "queued": True, "mode": "company_workflow"}),
                    content_type="application/json",
                )
'''
    s = s.replace(company_marker, company_branch, 1)
    patched = True
else:
    print('Pinto adapter company workflow branch already applied')

company_method_marker = '    def _bot_channel_prompt(self, bot_config: dict) -> Optional[str]:\n'
if 'async def _run_company_workflow(' not in s:
    if company_method_marker not in s:
        raise SystemExit('Expected _bot_channel_prompt def marker not found')
    company_method = '''    async def _run_company_workflow(self, chat_id: str, bot_id: str, bot_config: dict, task_text: str) -> None:
        """Run a local sequential persona handoff chain and send the final output.

        This is a small Hermes-only orchestrator: it does not call OpenClaw or
        any external agent registry. Chain order comes from bot_config["companyWorkflow"]
        (a list of persona keys) or platforms.pinto.extra.companyWorkflows.default.
        Each persona\'s reply becomes the next persona\'s input.
        """
        try:
            await self.send_typing(chat_id)
            chain = bot_config.get("companyWorkflow")
            if not isinstance(chain, list) or not chain:
                extra = getattr(self, "_extra_config", None) or {}
                workflows = extra.get("companyWorkflows") if isinstance(extra, dict) else None
                default_chain = workflows.get("default") if isinstance(workflows, dict) else None
                chain = default_chain if isinstance(default_chain, list) and default_chain else list(getattr(self, "_persona_configs", {}) or {})
            chain = [str(key) for key in chain if key]
            if not chain:
                await self.send(chat_id, "\u26a0\ufe0f \u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e15\u0e35\u0e49\u0e07\u0e04\u0e48\u0e32 company workflow (pintoAgents \u0e27\u0e48\u0e32\u0e07)")
                return

            handoff = task_text
            steps = []
            personas = getattr(self, "_persona_configs", {}) or {}
            for key in chain:
                persona_cfg = personas.get(key) if isinstance(personas, dict) else None
                persona_cfg = persona_cfg if isinstance(persona_cfg, dict) else {}
                prompt = self._company_role_prompt(key, self._bot_channel_prompt({"persona": key}) or f"You are {key}.")
                prior_outputs = "\\n\\n".join(
                    f"[{step['persona']}]\\n{step['output']}" for step in steps[-3:]
                )
                if steps:
                    user_message = (
                        f"Original user request (context only, do not restart from scratch):\\n{task_text}\\n\\n"
                        f"Previous role handoff you must build on:\\n{handoff}\\n\\n"
                        f"Recent prior outputs:\\n{prior_outputs}\\n\\n"
                        f"Your role is '{key}'. Add only your role-specific contribution, decisions, risks, and handoff for the next role. Do not repeat the same plan unless needed."
                    )
                else:
                    user_message = (
                        f"User request for proton company workflow:\\n{task_text}\\n\\n"
                        f"Your role is '{key}'. Produce the first role-specific output and a clear handoff for the next role."
                    )
                reply = await self._run_persona_turn(prompt, user_message)
                steps.append({"persona": key, "output": reply})
                handoff = reply

            await self.send(chat_id, handoff)
        except Exception:
            logger.exception("Pinto company workflow failed chat_id=%s bot_id=%s", chat_id, bot_id)
            try:
                await self.send(chat_id, "\u2716\ufe0f company workflow \u0e25\u0e49\u0e21\u0e40\u0e2b\u0e25\u0e27 \u0e14\u0e39 log \u0e1d\u0e31\u0e48\u0e07 Hermes Gateway")
            except Exception:
                pass

    def _company_role_prompt(self, role_key: str, base_prompt: str) -> str:
        """Inject vendored company AGENTS.md and SKILL.md guidance into one role prompt."""
        try:
            import os
            from pathlib import Path
            root = Path(os.getenv("COMPANY_SKILLS_DIR", "/root/.hermes/company-skills"))
            role = str(role_key or "default").strip().lower() or "default"
            parts = [str(base_prompt or f"You are {role}.")]
            role_agents = root / "templates" / "workspaces" / role / "AGENTS.md"
            default_agents = root / "templates" / "workspaces" / "default" / "AGENTS.md"
            for path in (role_agents, default_agents):
                if path.exists():
                    text = path.read_text(encoding="utf-8", errors="ignore")[:16000]
                    parts.append(f"\n\n--- COMPANY {path.name} ({path}) ---\n{text}")
            skill_map = {
                "pm": [
                    "skills/stop-slop/SKILL.md",
                    "skills/9arm/skills/productivity/management-talk/SKILL.md",
                    "skills/9arm/skills/productivity/qwenchance/SKILL.md",
                    "skills/karpathy-guidelines/SKILL.md",
                ],
                "designer": [
                    "skills/taste-skill/skills/taste-skill/SKILL.md",
                    "skills/karpathy-guidelines/SKILL.md",
                ],
                "frontend": [
                    "skills/taste-skill/skills/taste-skill/SKILL.md",
                    "skills/karpathy-guidelines/SKILL.md",
                ],
                "backend": [
                    "skills/karpathy-guidelines/SKILL.md",
                    "skills/mattpocock/engineering/tdd/SKILL.md",
                    "skills/mattpocock/engineering/diagnosing-bugs/SKILL.md",
                    "skills/mattpocock/engineering/domain-modeling/SKILL.md",
                    "skills/9arm/skills/engineering/debug-mantra/SKILL.md",
                    "skills/9arm/skills/engineering/scrutinize/SKILL.md",
                ],
                "qa": [
                    "skills/karpathy-guidelines/SKILL.md",
                    "skills/mattpocock/deprecated/qa/SKILL.md",
                    "skills/mattpocock/in-progress/review/SKILL.md",
                    "skills/mattpocock/engineering/diagnosing-bugs/SKILL.md",
                    "skills/mattpocock/engineering/tdd/SKILL.md",
                    "skills/mattpocock/engineering/triage/SKILL.md",
                    "skills/9arm/skills/engineering/debug-mantra/SKILL.md",
                    "skills/9arm/skills/engineering/scrutinize/SKILL.md",
                ],
                "techlead": [
                    "skills/karpathy-guidelines/SKILL.md",
                    "skills/stop-slop/SKILL.md",
                    "skills/mattpocock/engineering/codebase-design/SKILL.md",
                    "skills/mattpocock/engineering/diagnosing-bugs/SKILL.md",
                    "skills/9arm/skills/engineering/scrutinize/SKILL.md",
                    "skills/9arm/skills/engineering/post-mortem/SKILL.md",
                    "skills/9arm/skills/productivity/management-talk/SKILL.md",
                ],
            }
            rels = skill_map.get(role, ["skills/karpathy-guidelines/SKILL.md"])
            budget = int(os.getenv("COMPANY_SKILL_PROMPT_BUDGET", "52000"))
            used = sum(len(p) for p in parts)
            for rel in rels:
                path = root / rel
                if not path.exists():
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                remaining = budget - used
                if remaining <= 2000:
                    break
                text = text[: min(len(text), remaining)]
                parts.append(f"\n\n--- SKILL {rel} ---\n{text}")
                used += len(text)
            parts.append("\n\nFollow the injected AGENTS.md and SKILL.md instructions for this role before doing the task. If they conflict with the user's task, keep safety rules and role scope.")
            return "".join(parts)
        except Exception:
            return str(base_prompt or f"You are {role_key}.")

    async def _run_persona_turn(self, system_prompt: str, user_message: str) -> str:
        """Run a single persona turn through the in-process Hermes agent."""
        loop = asyncio.get_running_loop()

        def _run_sync() -> str:
            from gateway.session_context import clear_session_vars, set_session_vars

            session_tokens = []
            try:
                session_tokens = set_session_vars(platform="pinto", session_key=f"company:{uuid.uuid4().hex}")
                agent = self._create_company_agent(system_prompt)
                result = agent.run_conversation(user_message=user_message, conversation_history=[], task_id=uuid.uuid4().hex)
            finally:
                if session_tokens:
                    try:
                        clear_session_vars(session_tokens)
                    except Exception:
                        pass
            if isinstance(result, dict):
                if result.get("failed"):
                    return str(result.get("error") or "agent run failed")
                return str(result.get("final_response") or "")
            return str(result or "")

        return await loop.run_in_executor(None, _run_sync)

    def _create_company_agent(self, system_prompt: str):
        """Best-effort construction of a Hermes agent for one persona turn.

        Looks up the live APIServerAdapter via gc (same compatibility shim used
        for webhook mounting) so persona turns reuse the same agent factory and
        provider/model configuration as the rest of the gateway.
        """
        import gc
        for obj in gc.get_objects():
            if obj.__class__.__name__ == "APIServerAdapter" and hasattr(obj, "_create_agent"):
                return obj._create_agent(ephemeral_system_prompt=system_prompt)
        raise RuntimeError("api_server adapter not found for company workflow agent creation")

'''
    s = s.replace(company_method_marker, company_method + company_method_marker, 1)
    patched = True
else:
    print('Pinto adapter company workflow method already applied')

activity_old = '''            handoff = task_text
            steps = []
            personas = getattr(self, "_persona_configs", {}) or {}
            for key in chain:
                persona_cfg = personas.get(key) if isinstance(personas, dict) else None
                persona_cfg = persona_cfg if isinstance(persona_cfg, dict) else {}
                prompt = self._company_role_prompt(key, self._bot_channel_prompt({"persona": key}) or f"You are {key}.")
                prior_outputs = "\\n\\n".join(
                    f"[{step['persona']}]\\n{step['output']}" for step in steps[-3:]
                )
                if steps:
                    user_message = (
                        f"Original user request (context only, do not restart from scratch):\\n{task_text}\\n\\n"
                        f"Previous role handoff you must build on:\\n{handoff}\\n\\n"
                        f"Recent prior outputs:\\n{prior_outputs}\\n\\n"
                        f"Your role is '{key}'. Add only your role-specific contribution, decisions, risks, and handoff for the next role. Do not repeat the same plan unless needed."
                    )
                else:
                    user_message = (
                        f"User request for proton company workflow:\\n{task_text}\\n\\n"
                        f"Your role is '{key}'. Produce the first role-specific output and a clear handoff for the next role."
                    )
                reply = await self._run_persona_turn(prompt, user_message)
                steps.append({"persona": key, "output": reply})
                handoff = reply

            await self.send(chat_id, handoff)
'''
activity_new = '''            handoff = task_text
            steps = []
            personas = getattr(self, "_persona_configs", {}) or {}
            workflow_id = f"pinto-{chat_id}-{uuid.uuid4().hex[:8]}"

            pm_key = chain[0]
            worker_chain = [key for key in chain[1:] if key]
            pm_prompt = self._company_role_prompt(pm_key, self._bot_channel_prompt({"persona": pm_key}) or f"You are {pm_key}.")
            await self._publish_company_activity({
                "type": "role_started",
                "workflowId": workflow_id,
                "from": "pinto",
                "to": pm_key,
                "agent": pm_key,
                "status": "working",
                "task": task_text,
                "summary": f"{pm_key} started planning and dispatch",
            })
            pm_message = (
                f"User request for proton company workflow:\\n{task_text}\\n\\n"
                f"You are '{pm_key}'. Break this into role-specific tasks for these agents: {', '.join(worker_chain)}.\\n"
                "Return concise Thai planning plus a JSON object at the end in this exact shape:\\n"
                '{"tasks":[{"agent":"designer","task":"..."}],"notes":"..."}\\n'
                "Only include available agents. Each task must be different and fit that role."
            )
            pm_reply = await self._run_persona_turn(pm_prompt, pm_message)
            steps.append({"persona": pm_key, "output": pm_reply})
            await self._publish_company_activity({
                "type": "role_completed",
                "workflowId": workflow_id,
                "from": pm_key,
                "to": "team",
                "agent": pm_key,
                "status": "idle",
                "task": task_text,
                "summary": pm_reply[:240],
            })

            dispatch = self._extract_pm_tasks(pm_reply, worker_chain)
            worker_outputs = []
            for idx, key in enumerate(worker_chain, start=1):
                task_for_role = dispatch.get(key) or f"Build on PM plan for your {key} role."
                prompt = self._company_role_prompt(key, self._bot_channel_prompt({"persona": key}) or f"You are {key}.")
                await self._publish_company_activity({
                    "type": "task_dispatched",
                    "workflowId": workflow_id,
                    "from": pm_key if idx == 1 else worker_chain[idx-2],
                    "to": key,
                    "agent": key,
                    "status": "working",
                    "task": task_for_role,
                    "summary": f"{pm_key} assigned {key}: {task_for_role[:180]}",
                })
                prior_outputs = "\\n\\n".join(
                    f"[{item['persona']}]\\n{item['output']}" for item in worker_outputs[-3:]
                )
                peer_context = prior_outputs or pm_reply
                user_message = (
                    f"Original user request (context only):\\n{task_text}\\n\\n"
                    f"PM plan and dispatch:\\n{pm_reply}\\n\\n"
                    f"Your assigned task from PM:\\n{task_for_role}\\n\\n"
                    f"Recent peer outputs you may coordinate with:\\n{peer_context}\\n\\n"
                    f"Your role is '{key}'. Do only your assigned role-specific work. Complete this todo checklist step by step before handoff:\\n" + "\\n".join(f"- [ ] {todo}" for todo in role_todos) + "\\nTalk to/hand off to the next relevant teammate when useful. Do not redo PM planning."
                )
                reply = await self._run_persona_turn(prompt, user_message)
                worker_outputs.append({"persona": key, "output": reply, "task": task_for_role})
                steps.append({"persona": key, "output": reply, "task": task_for_role})
                next_to = worker_chain[idx] if idx < len(worker_chain) else "techlead"
                await self._publish_company_activity({
                    "type": "peer_handoff",
                    "workflowId": workflow_id,
                    "from": key,
                    "to": next_to,
                    "agent": key,
                    "status": "idle",
                    "task": task_for_role,
                    "summary": reply[:240],
                })

            reviewer_key = "techlead" if "techlead" in worker_chain else worker_chain[-1] if worker_chain else pm_key
            final_prompt = self._company_role_prompt(reviewer_key, self._bot_channel_prompt({"persona": reviewer_key}) or f"You are {reviewer_key}.")
            combined_outputs = "\\n\\n".join(
                f"[{step.get('persona')}] task={step.get('task','')}\\n{step.get('output','')}" for step in steps
            )
            await self._publish_company_activity({
                "type": "review_started",
                "workflowId": workflow_id,
                "from": "team",
                "to": reviewer_key,
                "agent": reviewer_key,
                "status": "working",
                "task": task_text,
                "summary": f"{reviewer_key} started final review",
            })
            final_message = (
                f"Original user request:\\n{task_text}\\n\\n"
                f"Team outputs:\\n{combined_outputs}\\n\\n"
                "Create the final answer to the Pinto user. Be practical, consolidated, and avoid repeating internal chatter."
            )
            await self.send(chat_id, "✅ Tech Lead กำลังสรุป final")
            handoff = await self._run_persona_turn(final_prompt, final_message)
            await self._publish_company_activity({
                "type": "workflow_completed",
                "workflowId": workflow_id,
                "from": reviewer_key,
                "to": "pinto",
                "status": "done",
                "task": task_text,
                "summary": handoff[:240],
            })
            await self.send(chat_id, handoff)
'''

if activity_old in s:
    s = s.replace(activity_old, activity_new, 1)
    patched = True
elif 'role_started' in s and '_publish_company_activity' in s:
    print('Pinto adapter company dashboard activity loop already applied')
else:
    print('Pinto adapter company activity loop patch skipped (shape changed)')

extract_marker = '    async def _run_persona_turn(self, system_prompt: str, user_message: str) -> str:\n'
extract_method = '''    def _extract_pm_tasks(self, text: str, allowed_agents: list) -> dict:
        """Extract PM JSON dispatch tasks from model output."""
        allowed = {str(agent).strip().lower(): str(agent).strip() for agent in (allowed_agents or []) if str(agent).strip()}
        if not text or not allowed:
            return {}
        candidates = []
        raw = str(text)
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                candidates.append(raw[start:end + 1])
            candidates.append(raw)
            for candidate in candidates:
                data = json.loads(candidate)
                tasks = data.get("tasks") if isinstance(data, dict) else None
                if not isinstance(tasks, list):
                    continue
                out = {}
                for item in tasks:
                    if not isinstance(item, dict):
                        continue
                    agent = str(item.get("agent") or item.get("to") or "").strip().lower()
                    task = str(item.get("task") or item.get("summary") or item.get("instruction") or "").strip()
                    if agent in allowed and task:
                        out[allowed[agent]] = task
                if out:
                    return out
        except Exception:
            logger.debug("PM dispatch JSON parse failed", exc_info=True)
        out = {}
        lower = raw.lower()
        for key, original in allowed.items():
            idx = lower.find(key)
            if idx >= 0:
                snippet = raw[idx:idx + 500].strip()
                out[original] = snippet
        return out

'''
if 'def _extract_pm_tasks(' not in s:
    if extract_marker not in s:
        raise SystemExit('Expected _run_persona_turn marker for PM task extractor not found')
    s = s.replace(extract_marker, extract_method + extract_marker, 1)
    patched = True
else:
    print('Pinto adapter PM task extractor already applied')

publish_marker = '    async def _run_persona_turn(self, system_prompt: str, user_message: str) -> str:\n'
publish_method = '''    async def _publish_company_activity(self, event: dict) -> None:
        """Best-effort publish of Hermes company workflow activity to local dashboard."""
        url = os.getenv("HERMES_COMPANY_DASHBOARD_ACTIVITY_URL", "http://host.containers.internal:8090/api/hermes/activity")
        if not url:
            return
        try:
            event = dict(event or {})
            event.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            event.setdefault("sendId", f"hermes-{uuid.uuid4().hex}")
            if HTTPX_AVAILABLE and httpx is not None:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    await client.post(url, json=event)
        except Exception:
            logger.debug("company dashboard activity publish failed", exc_info=True)

    async def _stream_company_message(self, *, workflow_id: str, agent: str, from_agent: str, to_agent: str, task: str, text: str) -> None:
        """Pseudo-stream completed agent output to the dashboard as cumulative chunks."""
        if not text:
            return
        stream_id = f"stream-{uuid.uuid4().hex}"
        await self._publish_company_activity({"type":"message_started","kind":"message_started","workflowId":workflow_id,"from":from_agent,"to":agent,"agent":agent,"status":"working","task":task,"summary":f"{agent} started speaking","streamId":stream_id,"message":""})
        clean = str(text).strip()
        step = int(os.getenv("HERMES_COMPANY_STREAM_CHARS", "90") or "90")
        delay = float(os.getenv("HERMES_COMPANY_STREAM_DELAY", "0.08") or "0.08")
        for end in range(step, min(len(clean), 2000) + step, step):
            chunk = clean[:end]
            await self._publish_company_activity({"type":"message_delta","kind":"message_delta","workflowId":workflow_id,"from":from_agent,"to":agent,"agent":agent,"status":"working","task":task,"summary":chunk[:240],"message":chunk,"streamId":stream_id})
            if delay > 0:
                await asyncio.sleep(delay)
        await self._publish_company_activity({"type":"message_completed","kind":"message_completed","workflowId":workflow_id,"from":from_agent,"to":to_agent,"agent":agent,"status":"idle","task":task,"summary":clean[:240],"message":clean[:2000],"streamId":stream_id})

'''
if 'async def _publish_company_activity(' not in s:
    if publish_marker not in s:
        raise SystemExit('Expected _run_persona_turn marker for activity publisher not found')
    s = s.replace(publish_marker, publish_method + publish_marker, 1)
    patched = True
else:
    print('Pinto adapter company dashboard activity publisher already applied')


stream_marker = '    async def _run_persona_turn(self, system_prompt: str, user_message: str) -> str:\n'
stream_method = '''    async def _stream_company_message(self, *, workflow_id: str, agent: str, from_agent: str, to_agent: str, task: str, text: str) -> None:
        """Pseudo-stream completed agent output to the dashboard as cumulative chunks."""
        if not text:
            return
        stream_id = f"stream-{uuid.uuid4().hex}"
        await self._publish_company_activity({"type":"message_started","kind":"message_started","workflowId":workflow_id,"from":from_agent,"to":agent,"agent":agent,"status":"working","task":task,"summary":f"{agent} started speaking","streamId":stream_id,"message":""})
        clean = str(text).strip()
        step = int(os.getenv("HERMES_COMPANY_STREAM_CHARS", "90") or "90")
        delay = float(os.getenv("HERMES_COMPANY_STREAM_DELAY", "0.08") or "0.08")
        for end in range(step, min(len(clean), 2000) + step, step):
            chunk = clean[:end]
            await self._publish_company_activity({"type":"message_delta","kind":"message_delta","workflowId":workflow_id,"from":from_agent,"to":agent,"agent":agent,"status":"working","task":task,"summary":chunk[:240],"message":chunk,"streamId":stream_id})
            if delay > 0:
                await asyncio.sleep(delay)
        await self._publish_company_activity({"type":"message_completed","kind":"message_completed","workflowId":workflow_id,"from":from_agent,"to":to_agent,"agent":agent,"status":"idle","task":task,"summary":clean[:240],"message":clean[:2000],"streamId":stream_id})

'''
if 'async def _stream_company_message(' not in s:
    if stream_marker not in s:
        raise SystemExit('Expected _run_persona_turn marker for company message streamer not found')
    s = s.replace(stream_marker, stream_method + stream_marker, 1)
    patched = True
else:
    print('Pinto adapter company message streamer already applied')

# Force-upgrade company workflow method to PM dispatch orchestration, even when
# older dashboard-activity workflow code is already present in the adapter.
pm_dispatch_marker = '    def _bot_channel_prompt(self, bot_config: dict) -> Optional[str]:\n'
pm_dispatch_method = '''    async def _run_company_workflow(self, chat_id: str, bot_id: str, bot_config: dict, task_text: str) -> None:
        # Run PM-led company orchestration.
        try:
            await self.send_typing(chat_id)
            chain = bot_config.get("companyWorkflow")
            if not isinstance(chain, list) or not chain:
                extra = getattr(self, "_extra_config", None) or {}
                workflows = extra.get("companyWorkflows") if isinstance(extra, dict) else None
                default_chain = workflows.get("default") if isinstance(workflows, dict) else None
                chain = default_chain if isinstance(default_chain, list) and default_chain else list(getattr(self, "_persona_configs", {}) or {})
            chain = [str(key) for key in chain if key]
            if not chain:
                await self.send(chat_id, "⚠️ ยังไม่ได้ตั้งค่า company workflow (pintoAgents ว่าง)")
                return

            steps = []
            preview_urls_sent = set()
            workflow_id = f"pinto-{chat_id}-{uuid.uuid4().hex[:8]}"
            projects_dir = os.getenv("COMPANY_PROJECTS_DIR", "/company-projects")
            if os.getenv("CLEAR_COMPANY_PROJECTS_ON_WORKFLOW_START", "true").strip().lower() in ("1", "true", "yes", "on"):
                import shutil
                from pathlib import Path
                root = Path(projects_dir)
                root.mkdir(parents=True, exist_ok=True)
                for child in root.iterdir():
                    if child.name in (".gitkeep", ".DS_Store"):
                        continue
                    if child.is_dir() and not child.is_symlink():
                        shutil.rmtree(child)
                    else:
                        child.unlink(missing_ok=True)
            requirement_ledger = self._load_company_requirement_ledger(chat_id)
            self._append_company_requirement(chat_id, task_text)
            requirement_ledger = self._load_company_requirement_ledger(chat_id)
            project_instructions = (
                f"Generated project files must be written under {projects_dir}/<project-name>. "
                "Never write generated project files under /root. Use a clear project slug such as proton-landing."
            )
            pm_key = chain[0]
            worker_chain = [key for key in chain[1:] if key]
            meeting_agents = [pm_key] + worker_chain
            for member in meeting_agents:
                await self._publish_company_activity({"type":"team_meeting_started","workflowId":workflow_id,"from":"pinto","to":member,"agent":member,"status":"working" if member == pm_key else "idle","location":"meeting","task":task_text,"summary":"PM kickoff meeting: requirement intake and task split"})

            pm_prompt = self._company_role_prompt(pm_key, self._bot_channel_prompt({"persona": pm_key}) or f"You are {pm_key}.")
            await self._publish_company_activity({"type":"role_started","workflowId":workflow_id,"from":"pinto","to":pm_key,"agent":pm_key,"status":"working","location":"meeting","task":task_text,"summary":f"{pm_key} started planning and dispatch in kickoff meeting"})
            await self.send(chat_id, f"▶️ {pm_key} เริ่มวางแผนและแบ่งงาน")
            pm_message = (
                f"User request for proton company workflow:\\n{task_text}\\n\\n"
                f"Recent requirement ledger for this chat:\\n{requirement_ledger}\\n\\n"
                f"You are '{pm_key}'. Treat the user as a non-technical client. Convert vague intent into concrete goals, assumptions, acceptance criteria, constraints, and role-specific tasks for these agents: {', '.join(worker_chain)}.\n"
                "If the user asks to run, preview, host, deploy, open, or show the product, route that request directly to frontend and/or backend dev tasks. Do not make the user run it themselves unless credentials or environment are missing. Prefer Cloudflare/Wrangler when authenticated; otherwise use localhost.run via ssh -R 80:localhost:3000 nokey@localhost.run if SSH and a local preview server are available. "
                "Return concise Thai planning plus a JSON object at the end in this exact shape:\\n"
                '{"tasks":[{"agent":"designer","task":"..."}],"notes":"..."}\n'
                "Only include available agents. Each task must be different and fit that role."
            )
            pm_reply = await self._run_persona_turn(pm_prompt, pm_message)
            await self.send(chat_id, "✅ PM แบ่งงานแล้ว กำลังให้ทีมลงมือทำ")
            steps.append({"persona": pm_key, "output": pm_reply, "task": "plan and dispatch"})
            await self._stream_company_message(workflow_id=workflow_id, agent=pm_key, from_agent=pm_key, to_agent="team", task=task_text, text=pm_reply)
            await self._send_preview_urls(chat_id, pm_reply, preview_urls_sent)
            await self._publish_company_activity({"type":"role_completed","workflowId":workflow_id,"from":pm_key,"to":"team","agent":pm_key,"status":"done","task":task_text,"summary":pm_reply[:240],"message":pm_reply[:2000]})
            await self.send(chat_id, f"✅ {pm_key} เสร็จแล้ว ส่งงานต่อให้ทีม")
            asyncio.create_task(self._restore_company_agent_idle(workflow_id, pm_key, task_text, 12))
            for member in meeting_agents:
                await self._publish_company_activity({"type":"team_meeting_ended","workflowId":workflow_id,"from":pm_key,"to":member,"agent":member,"status":"idle" if member == pm_key else "idle","location":"meeting" if member == pm_key else "desk","task":task_text,"summary":"PM stays in meeting room; agents return to desks"})

            dispatch = self._extract_pm_tasks(pm_reply, worker_chain)
            worker_outputs = []
            for idx, key in enumerate(worker_chain, start=1):
                task_for_role = dispatch.get(key) or f"Build on PM plan for your {key} role."
                prompt = self._company_role_prompt(key, self._bot_channel_prompt({"persona": key}) or f"You are {key}.")
                from_agent = pm_key if idx == 1 else worker_chain[idx - 2]
                role_todos = self._build_company_role_todos(key, task_for_role)
                role_location = self._company_role_location(key)
                await self._publish_company_activity({"type":"task_dispatched","workflowId":workflow_id,"from":from_agent,"to":key,"agent":key,"status":"working","location":role_location,"task":task_for_role,"summary":f"{from_agent} -> {key}: {task_for_role[:180]}","todos":role_todos,"todoIndex":1,"todoTotal":len(role_todos)})
                await self._publish_company_activity({"type":"todo_started","workflowId":workflow_id,"from":key,"to":key,"agent":key,"status":"working","location":role_location,"task":task_for_role,"summary":f"{key} todo 1/{len(role_todos)}: {role_todos[0] if role_todos else 'start'}","todos":role_todos,"todoIndex":1,"todoTotal":len(role_todos)})
                await self.send(chat_id, f"▶️ {key} เริ่มทำงาน")
                prior_outputs = "\\n\\n".join(f"[{item['persona']}]\\n{item['output']}" for item in worker_outputs[-3:])
                peer_context = prior_outputs or pm_reply
                user_message = (
                    f"Original user request (context only):\\n{task_text}\\n\\n"
                    f"PM plan and dispatch:\\n{pm_reply}\\n\\n"
                    f"Your assigned task from PM:\\n{task_for_role}\\n\\n"
                    f"Recent peer outputs you may coordinate with:\\n{peer_context}\\n\\n"
                    f"Your role is '{key}'. Do only your assigned role-specific work. Complete this todo checklist step by step before handoff:\\n" + "\\n".join(f"- [ ] {todo}" for todo in role_todos) + "\\nTalk to/hand off to the next relevant teammate when useful. Do not redo PM planning."
                )
                reply = await self._run_persona_turn(prompt, user_message)
                worker_outputs.append({"persona": key, "output": reply, "task": task_for_role})
                steps.append({"persona": key, "output": reply, "task": task_for_role})
                next_to = worker_chain[idx] if idx < len(worker_chain) else "techlead"
                await self._stream_company_message(workflow_id=workflow_id, agent=key, from_agent=key, to_agent=next_to, task=task_for_role, text=reply)
                await self._send_preview_urls(chat_id, reply, preview_urls_sent)
                await self._publish_company_activity({"type":"todo_completed","workflowId":workflow_id,"from":key,"to":key,"agent":key,"status":"done","task":task_for_role,"summary":f"{key} completed {len(role_todos)}/{len(role_todos)} todos","todos":role_todos,"todoIndex":len(role_todos),"todoTotal":len(role_todos),"message":reply[:1200]})
                handoff_location = f"visit:{next_to}" if next_to in worker_chain else "visit:techlead"
                await self._publish_company_activity({"type":"peer_handoff","workflowId":workflow_id,"from":key,"to":next_to,"agent":key,"status":"done","location":handoff_location,"task":task_for_role,"summary":reply[:240],"message":reply[:2000]})
                await self.send(chat_id, f"✅ {key} เสร็จแล้ว ส่งต่อให้ {next_to}")

            await self._publish_company_activity({"type":"pm_waiting","workflowId":workflow_id,"from":pm_key,"to":"team","agent":pm_key,"status":"idle","location":"meeting","task":task_text,"summary":"PM waits in meeting room while team works"})
            await self.send(chat_id, "✅ ทีมทำงานรอบแรกครบแล้ว กำลังให้ PM review")
            team_outputs = "\\n\\n".join(f"[{step.get('persona')}] task={step.get('task','')}\\n{step.get('output','')}" for step in steps)
            await self._publish_company_activity({"type":"pm_review_started","workflowId":workflow_id,"from":"team","to":pm_key,"agent":pm_key,"status":"working","task":task_text,"summary":f"{pm_key} reviewing team outputs for follow-up"})
            await self.send(chat_id, f"▶️ {pm_key} เริ่ม review งานทีม")
            pm_review_message = (
                f"Original user request:\\n{task_text}\\n\\n"
                f"Latest requirement ledger for this chat:\\n{self._load_company_requirement_ledger(chat_id)}\\n\\n"
                f"Team outputs so far:\\n{team_outputs}\\n\\n"
                f"You are '{pm_key}'. Merge teammate outputs with the latest requirement ledger. If new/changed requirements conflict with completed work, preserve useful completed work and assign targeted follow-up tasks to the right available agents: {', '.join(worker_chain)}. If QA or any teammate found bugs, blockers, missing work, or dependencies, assign follow-up tasks too.\\n"
                "Return brief Thai review plus JSON at the end: {\"tasks\":[{\"agent\":\"backend\",\"task\":\"fix/rework ...\"}],\"notes\":\"...\"}. Return empty tasks if no follow-up needed."
            )
            pm_review = await self._run_persona_turn(pm_prompt, pm_review_message)
            steps.append({"persona": pm_key, "output": pm_review, "task": "review and follow-up dispatch"})
            await self._stream_company_message(workflow_id=workflow_id, agent=pm_key, from_agent=pm_key, to_agent="team", task=task_text, text=pm_review)
            await self._send_preview_urls(chat_id, pm_review, preview_urls_sent)
            await self._publish_company_activity({"type":"pm_review_completed","workflowId":workflow_id,"from":pm_key,"to":"team","agent":pm_key,"status":"done","task":task_text,"summary":pm_review[:240],"message":pm_review[:2000]})
            await self.send(chat_id, f"✅ {pm_key} review เสร็จแล้ว")
            asyncio.create_task(self._restore_company_agent_idle(workflow_id, pm_key, task_text, 12))
            for member in worker_chain:
                await self._publish_company_activity({"type":"pm_feedback_completed","workflowId":workflow_id,"from":pm_key,"to":member,"agent":member,"status":"idle","location":"desk","task":task_text,"summary":f"PM feedback complete for {member}; return to desk"})
            followups = self._extract_pm_tasks(pm_review, worker_chain)
            if followups:
                await self.send(chat_id, f"⚠️ PM เจอ follow-up {len(followups)} งาน กำลังส่งกลับทีมที่เกี่ยวข้อง")
            for key, task_for_role in followups.items():
                prompt = self._company_role_prompt(key, self._bot_channel_prompt({"persona": key}) or f"You are {key}.")
                role_todos = self._build_company_role_todos(key, task_for_role)
                role_location = self._company_role_location(key)
                await self._publish_company_activity({"type":"followup_dispatched","workflowId":workflow_id,"from":pm_key,"to":key,"agent":key,"status":"working","location":role_location,"task":task_for_role,"summary":f"{pm_key} follow-up -> {key}: {task_for_role[:180]}","todos":role_todos,"todoIndex":1,"todoTotal":len(role_todos)})
                await self._publish_company_activity({"type":"todo_started","workflowId":workflow_id,"from":key,"to":key,"agent":key,"status":"working","location":role_location,"task":task_for_role,"summary":f"{key} follow-up todo 1/{len(role_todos)}: {role_todos[0] if role_todos else 'start'}","todos":role_todos,"todoIndex":1,"todoTotal":len(role_todos)})
                await self.send(chat_id, f"🔁 {key} กลับไปแก้ follow-up")
                follow_message = (
                    f"Original user request:\\n{task_text}\\n\\n"
                    f"Team outputs and PM review:\\n{team_outputs}\\n\\nPM review:\\n{pm_review}\\n\\n"
                    f"Your follow-up task from PM:\\n{task_for_role}\\n\\n"
                    f"Your role is '{key}'. Address the issue directly. Complete this todo checklist step by step before handoff:\\n" + "\\n".join(f"- [ ] {todo}" for todo in role_todos) + "\\nIf this came from QA, respond with fix/decision and handoff back to QA/PM."
                )
                reply = await self._run_persona_turn(prompt, follow_message)
                steps.append({"persona": key, "output": reply, "task": task_for_role})
                await self._stream_company_message(workflow_id=workflow_id, agent=key, from_agent=key, to_agent=pm_key, task=task_for_role, text=reply)
                await self._send_preview_urls(chat_id, reply, preview_urls_sent)
                await self._publish_company_activity({"type":"todo_completed","workflowId":workflow_id,"from":key,"to":key,"agent":key,"status":"done","task":task_for_role,"summary":f"{key} completed {len(role_todos)}/{len(role_todos)} follow-up todos","todos":role_todos,"todoIndex":len(role_todos),"todoTotal":len(role_todos),"message":reply[:1200]})
                await self._publish_company_activity({"type":"followup_completed","workflowId":workflow_id,"from":key,"to":pm_key,"agent":key,"status":"done","location":"visit:pm","task":task_for_role,"summary":reply[:240],"message":reply[:2000]})
                await self.send(chat_id, f"✅ {key} แก้ follow-up เสร็จแล้ว ส่งกลับ PM")
                asyncio.create_task(self._restore_company_agent_idle(workflow_id, key, task_for_role, 12))

            reviewer_key = "techlead" if "techlead" in worker_chain else worker_chain[-1] if worker_chain else pm_key
            final_prompt = self._company_role_prompt(reviewer_key, self._bot_channel_prompt({"persona": reviewer_key}) or f"You are {reviewer_key}.")
            combined_outputs = "\\n\\n".join(f"[{step.get('persona')}] task={step.get('task','')}\\n{step.get('output','')}" for step in steps)
            await self._publish_company_activity({"type":"review_started","workflowId":workflow_id,"from":"team","to":reviewer_key,"agent":reviewer_key,"status":"working","location":"visit:pm","task":task_text,"summary":f"{reviewer_key} started final review with PM"})
            await self.send(chat_id, f"▶️ {reviewer_key} เริ่ม final review")
            preview_hint = "real preview URL found" if preview_urls_sent else "NO real preview URL found"
            final_message = f"Original user request:\\n{task_text}\\n\\nTeam outputs:\\n{combined_outputs}\\n\\nPreview status: {preview_hint}. Create the final answer to the Pinto user. Be practical, consolidated, and avoid repeating internal chatter. If the user asked to run/show/preview/deploy, do not claim it is running, deployed, hosted, or ready to open unless team outputs contain a real preview URL (workers.dev, pages.dev, trycloudflare.com, localhost.run). If Preview status says NO real preview URL found, explicitly say preview is not available yet and list the exact next step needed to run/host it."
            await self.send(chat_id, "✅ Tech Lead กำลังสรุป final")
            handoff = await self._run_persona_turn(final_prompt, final_message)
            await self._stream_company_message(workflow_id=workflow_id, agent=reviewer_key, from_agent=reviewer_key, to_agent="pinto", task=task_text, text=handoff)
            await self._send_preview_urls(chat_id, handoff, preview_urls_sent)
            await self._publish_company_activity({"type":"workflow_completed","workflowId":workflow_id,"from":reviewer_key,"to":"pinto","agent":reviewer_key,"status":"done","task":task_text,"summary":handoff[:240],"message":handoff[:2000]})
            await self.send(chat_id, handoff)
        except Exception:
            logger.exception("Pinto company workflow failed chat_id=%s bot_id=%s", chat_id, bot_id)
            try:
                await self.send(chat_id, "✖️ company workflow ล้มเหลว ดู log ฝั่ง Hermes Gateway")
            except Exception:
                pass

    def _company_role_location(self, role_key: str) -> str:
        role = str(role_key or "").strip().lower()
        return {
            "frontend": "dev-room",
            "backend": "dev-room",
            "qa": "qa-room",
            "designer": "desk",
            "techlead": "desk",
            "pm": "desk",
        }.get(role, "desk")

    def _build_company_role_todos(self, role_key: str, task_text: str) -> list:
        role = str(role_key or "agent").strip().lower()
        base = str(task_text or "assigned task").strip()[:220]
        presets = {
            "designer": ["Extract UX goals and user journey", "Define layout, visual direction, and responsive states", "Hand off concrete UI guidance to frontend"],
            "frontend": ["Review design/requirements", "Implement UI and interactions", "Run local/hosted preview and report URL if available"],
            "backend": ["Review runtime/hosting requirements", "Implement server/static serving or deploy packaging", "Validate preview command and report URL/path"],
            "qa": ["Derive acceptance checks", "Test happy paths, edge cases, responsive behavior, and preview URL", "Report pass/fail with evidence and follow-up items"],
            "techlead": ["Review outputs against requirements", "Check risks, gaps, and integration", "Produce final user-facing summary with path/link/evidence"],
            "pm": ["Convert client request into requirements", "Split role-specific tasks", "Merge outputs and new requirements into follow-up plan"],
        }
        todos = presets.get(role, ["Understand assigned task", "Produce role-specific output", "Hand off result with evidence"])
        return [f"{item}: {base}" if i == 0 else item for i, item in enumerate(todos)]

    def _company_requirement_path(self, chat_id: str):
        import os
        from pathlib import Path
        root = Path(os.getenv("COMPANY_REQUIREMENTS_DIR", "/root/.hermes/company-requirements"))
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(chat_id or "unknown"))[:120]
        return root / f"{safe}.md"

    def _load_company_requirement_ledger(self, chat_id: str) -> str:
        try:
            path = self._company_requirement_path(chat_id)
            if not path.exists():
                return "(no prior requirements)"
            return path.read_text(encoding="utf-8", errors="ignore")[-12000:]
        except Exception:
            return "(requirement ledger unavailable)"

    def _append_company_requirement(self, chat_id: str, text: str) -> None:
        try:
            import time
            path = self._company_requirement_path(chat_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            entry = f"\\n\\n## {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\\n{text.strip()[:4000]}\\n"
            with path.open("a", encoding="utf-8") as fh:
                fh.write(entry)
        except Exception:
            logger.debug("Failed to append company requirement", exc_info=True)

    async def _send_preview_urls(self, chat_id: str, text: str, sent_urls: set) -> None:
        # Surface hosted preview URLs as soon as any role mentions them, once per workflow.
        try:
            if not text:
                return
            import re
            urls = re.findall(r"https://[^\s<>)\]\\\"']+(?:workers\.dev|pages\.dev|trycloudflare\.com|localhost\.run)[^\s<>)\]\\\"']*", str(text))
            for url in urls:
                clean = url.strip().rstrip(".,;:!?)]}").rstrip("'").rstrip('"')
                if not clean or clean in sent_urls:
                    continue
                sent_urls.add(clean)
                await self.send(chat_id, f"🌐 Preview พร้อมแล้ว: {clean}")
        except Exception:
            logger.debug("Failed to send preview URL", exc_info=True)

    async def _restore_company_agent_idle(self, workflow_id: str, agent: str, task: str, delay_seconds: int = 12) -> None:
        # Keep Done visible briefly, then return the desk/card to Idle unless a newer event made it Working again.
        try:
            await asyncio.sleep(max(1, int(delay_seconds)))
            await self._publish_company_activity({
                "type": "role_idle",
                "workflowId": workflow_id,
                "from": agent,
                "to": agent,
                "agent": agent,
                "status": "idle",
                "task": task,
                "summary": f"{agent} idle after completed handoff",
                "message": "Waiting for next task",
            })
        except Exception:
            logger.debug("Failed to restore company agent idle", exc_info=True)

    def _extract_pm_tasks(self, text: str, allowed_agents: list) -> dict:
        # Extract PM JSON dispatch tasks from model output.
        allowed = {str(agent).strip().lower(): str(agent).strip() for agent in (allowed_agents or []) if str(agent).strip()}
        if not text or not allowed:
            return {}
        raw = str(text)
        try:
            start = raw.find("{")
            end = raw.rfind("}")
            candidates = []
            if start >= 0 and end > start:
                candidates.append(raw[start:end + 1])
            candidates.append(raw)
            for candidate in candidates:
                data = json.loads(candidate)
                tasks = data.get("tasks") if isinstance(data, dict) else None
                if not isinstance(tasks, list):
                    continue
                out = {}
                for item in tasks:
                    if not isinstance(item, dict):
                        continue
                    agent = str(item.get("agent") or item.get("to") or "").strip().lower()
                    task = str(item.get("task") or item.get("summary") or item.get("instruction") or "").strip()
                    if agent in allowed and task:
                        out[allowed[agent]] = task
                if out:
                    return out
        except Exception:
            logger.debug("PM dispatch JSON parse failed", exc_info=True)
        return {}

'''
pattern = r'    async def _run_company_workflow\(self, chat_id: str, bot_id: str, bot_config: dict, task_text: str\) -> None:\n.*?(?=    async def _publish_company_activity\(|    async def _run_persona_turn\(|    def _bot_channel_prompt\()'
new_s, count = re.subn(pattern, lambda _m: pm_dispatch_method, s, count=1, flags=re.S)
if count:
    s = new_s
    patched = True
elif pm_dispatch_marker in s:
    s = s.replace(pm_dispatch_marker, pm_dispatch_method + pm_dispatch_marker, 1)
    patched = True
else:
    raise SystemExit('Expected company workflow insertion marker not found')

company_role_prompt_method = '''    def _company_role_prompt(self, role_key: str, base_prompt: str) -> str:
        """Inject vendored company AGENTS.md and SKILL.md guidance into one role prompt."""
        try:
            import os
            from pathlib import Path
            root = Path(os.getenv("COMPANY_SKILLS_DIR", "/root/.hermes/company-skills"))
            role = str(role_key or "default").strip().lower() or "default"
            parts = [str(base_prompt or f"You are {role}.")]
            for path in (root / "templates" / "workspaces" / role / "AGENTS.md", root / "templates" / "workspaces" / "default" / "AGENTS.md"):
                if path.exists():
                    parts.append(f"\\n\\n--- COMPANY AGENTS ({path}) ---\\n{path.read_text(encoding='utf-8', errors='ignore')[:16000]}")
            skill_map = {
                "pm": ["skills/stop-slop/SKILL.md", "skills/9arm/skills/productivity/management-talk/SKILL.md", "skills/9arm/skills/productivity/qwenchance/SKILL.md", "skills/karpathy-guidelines/SKILL.md"],
                "designer": ["skills/taste-skill/skills/taste-skill/SKILL.md", "skills/karpathy-guidelines/SKILL.md"],
                "frontend": ["skills/taste-skill/skills/taste-skill/SKILL.md", "skills/karpathy-guidelines/SKILL.md", "skills/cloudflare/skills/cloudflare/SKILL.md", "skills/cloudflare/skills/wrangler/SKILL.md", "skills/cloudflare/skills/workers-best-practices/SKILL.md"],
                "backend": ["skills/karpathy-guidelines/SKILL.md", "skills/mattpocock/engineering/tdd/SKILL.md", "skills/mattpocock/engineering/diagnosing-bugs/SKILL.md", "skills/mattpocock/engineering/domain-modeling/SKILL.md", "skills/9arm/skills/engineering/debug-mantra/SKILL.md", "skills/9arm/skills/engineering/scrutinize/SKILL.md", "skills/cloudflare/skills/cloudflare/SKILL.md", "skills/cloudflare/skills/wrangler/SKILL.md", "skills/cloudflare/skills/workers-best-practices/SKILL.md"],
                "qa": ["skills/karpathy-guidelines/SKILL.md", "skills/mattpocock/deprecated/qa/SKILL.md", "skills/mattpocock/in-progress/review/SKILL.md", "skills/mattpocock/engineering/diagnosing-bugs/SKILL.md", "skills/mattpocock/engineering/tdd/SKILL.md", "skills/mattpocock/engineering/triage/SKILL.md", "skills/9arm/skills/engineering/debug-mantra/SKILL.md", "skills/9arm/skills/engineering/scrutinize/SKILL.md"],
                "techlead": ["skills/karpathy-guidelines/SKILL.md", "skills/stop-slop/SKILL.md", "skills/mattpocock/engineering/codebase-design/SKILL.md", "skills/mattpocock/engineering/diagnosing-bugs/SKILL.md", "skills/9arm/skills/engineering/scrutinize/SKILL.md", "skills/9arm/skills/engineering/post-mortem/SKILL.md", "skills/9arm/skills/productivity/management-talk/SKILL.md"],
            }
            budget = int(os.getenv("COMPANY_SKILL_PROMPT_BUDGET", "52000"))
            used = sum(len(x) for x in parts)
            for rel in skill_map.get(role, ["skills/karpathy-guidelines/SKILL.md"]):
                path = root / rel
                if not path.exists():
                    continue
                remaining = budget - used
                if remaining <= 2000:
                    break
                text = path.read_text(encoding="utf-8", errors="ignore")[:remaining]
                parts.append(f"\\n\\n--- SKILL {rel} ---\\n{text}")
                used += len(text)
            parts.append("\\n\\nFollow the injected AGENTS.md and SKILL.md instructions for this role before doing the task. If they conflict with the user's task, keep safety rules and role scope.")
            return "".join(parts)
        except Exception:
            return str(base_prompt or f"You are {role_key}.")

'''
if 'def _company_role_prompt(self, role_key: str, base_prompt: str)' not in s:
    marker = '    async def _run_persona_turn(self, system_prompt: str, user_message: str) -> str:\n'
    if marker not in s:
        raise SystemExit('Expected _run_persona_turn marker for company role prompt helper')
    s = s.replace(marker, company_role_prompt_method + marker, 1)
    patched = True
else:
    print('Pinto adapter company role prompt helper already applied')

extra_config_marker = '        self._persona_configs = extra.get("pintoAgents") if isinstance(extra.get("pintoAgents"), dict) else {}\n'
if 'self._extra_config = extra\n' not in s:
    if extra_config_marker not in s:
        raise SystemExit('Expected persona configs init marker not found for extra_config save')
    s = s.replace(extra_config_marker, extra_config_marker + '        self._extra_config = extra if isinstance(extra, dict) else {}\n', 1)
    patched = True
else:
    print('Pinto adapter extra_config reference already saved')

primary_old = '''    def _bot_config(self, bot_id: str) -> Optional[dict]:
        if self._bot_id and bot_id == self._bot_id:
            return {}
        cfg = self._bot_configs.get(bot_id)
        if isinstance(cfg, dict):
            return cfg
        return None
'''
primary_new = '''    def _bot_config(self, bot_id: str) -> Optional[dict]:
        if self._bot_id and bot_id == self._bot_id:
            extra = getattr(self, "_extra_config", {}) or {}
            cfg = {}
            if isinstance(extra, dict):
                primary_cfg = extra.get("primaryBot")
                if isinstance(primary_cfg, dict):
                    cfg.update(primary_cfg)
                for key in ("persona", "personaKey", "companyWorkflow", "channelPrompt", "prompt", "role", "name", "enabled"):
                    if key in extra and key not in cfg:
                        cfg[key] = extra[key]
            return cfg
        cfg = self._bot_configs.get(bot_id)
        if isinstance(cfg, dict):
            return cfg
        return None
'''

# Repair any accidental literal newlines inside generated adapter f-strings.
s = s.replace('f"User request for proton company workflow:\n{task_text}\n\n"', 'f"User request for proton company workflow:\\n{task_text}\\n\\n"')
s = s.replace('f"You are \'{pm_key}\'. Break this into role-specific tasks for these agents: {\', \'.join(worker_chain)}.\n"', 'f"You are \'{pm_key}\'. Break this into role-specific tasks for these agents: {\', \'.join(worker_chain)}.\\n"')
s = s.replace('"Return concise Thai planning plus a JSON object at the end in this exact shape:\n"', '"Return concise Thai planning plus a JSON object at the end in this exact shape:\\n"')
s = s.replace('\'{"tasks":[{"agent":"designer","task":"..."}],"notes":"..."}\n\'', '\'{"tasks":[{"agent":"designer","task":"..."}],"notes":"..."}\\n\'')
s = s.replace('prior_outputs = "\n\n".join(f"[{item[\'persona\']}]\n{item[\'output\']}"', 'prior_outputs = "\\n\\n".join(f"[{item[\'persona\']}]\\n{item[\'output\']}"')
s = s.replace('f"Original user request (context only):\n{task_text}\n\n"', 'f"Original user request (context only):\\n{task_text}\\n\\n"')
s = s.replace('f"PM plan and dispatch:\n{pm_reply}\n\n"', 'f"PM plan and dispatch:\\n{pm_reply}\\n\\n"')
s = s.replace('f"Your assigned task from PM:\n{task_for_role}\n\n"', 'f"Your assigned task from PM:\\n{task_for_role}\\n\\n"')
s = s.replace('f"Recent peer outputs you may coordinate with:\n{peer_context}\n\n"', 'f"Recent peer outputs you may coordinate with:\\n{peer_context}\\n\\n"')
s = s.replace('combined_outputs = "\n\n".join(f"[{step.get(\'persona\')}] task={step.get(\'task\',\'\')}\n{step.get(\'output\',\'\')}"', 'combined_outputs = "\\n\\n".join(f"[{step.get(\'persona\')}] task={step.get(\'task\',\'\')}\\n{step.get(\'output\',\'\')}"')
s = s.replace('final_message = f"Original user request:\n{task_text}\n\nTeam outputs:\n{combined_outputs}\n\nCreate', 'final_message = f"Original user request:\\n{task_text}\\n\\nTeam outputs:\\n{combined_outputs}\\n\\nCreate')

s = s.replace('team_outputs = "\n\n".join(f"[{step.get(\'persona\')}] task={step.get(\'task\',\'\')}\n{step.get(\'output\',\'\')}"', 'team_outputs = "\\n\\n".join(f"[{step.get(\'persona\')}] task={step.get(\'task\',\'\')}\\n{step.get(\'output\',\'\')}"')
s = s.replace('f"Original user request:\n{task_text}\n\n"', 'f"Original user request:\\n{task_text}\\n\\n"')
s = s.replace('f"Team outputs so far:\n{team_outputs}\n\n"', 'f"Team outputs so far:\\n{team_outputs}\\n\\n"')
s = s.replace('}.\n"', '}.\\n"')
s = s.replace('f"Team outputs and PM review:\n{team_outputs}\n\nPM review:\n{pm_review}\n\n"', 'f"Team outputs and PM review:\\n{team_outputs}\\n\\nPM review:\\n{pm_review}\\n\\n"')
s = s.replace('f"Your follow-up task from PM:\n{task_for_role}\n\n"', 'f"Your follow-up task from PM:\\n{task_for_role}\\n\\n"')


s = s.replace('"Return brief Thai review plus JSON at the end: {"tasks":[{"agent":"backend","task":"fix/rework ..."}],"notes":"..."}. Return empty tasks if no follow-up needed."', '"Return brief Thai review plus JSON at the end: {\\"tasks\\":[{\\"agent\\":\\"backend\\",\\"task\\":\\"fix/rework ...\\"}],\\"notes\\":\\"...\\"}. Return empty tasks if no follow-up needed."')
if primary_old in s:
    s = s.replace(primary_old, primary_new)
    patched = True
elif 'primary_cfg = extra.get("primaryBot")' in s:
    print('Pinto adapter primary bot config patch already applied')
else:
    raise SystemExit('Expected Pinto _bot_config primary block not found')

p.write_text(s, encoding='utf-8')
print('Patched Pinto adapter for Hermes 0.16 compatibility' if patched else 'Pinto adapter already patched')
