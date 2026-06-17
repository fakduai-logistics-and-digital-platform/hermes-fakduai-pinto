#!/usr/bin/env python3
"""Patch Hermes api_server to mount Pinto webhook before aiohttp router freezes."""
from pathlib import Path

p = Path('/usr/local/lib/python3.11/site-packages/gateway/platforms/api_server.py')
s = p.read_text(encoding='utf-8')
marker = '''            # Store the adapter after native routes are registered. Local Hermes-Relay
            # bootstrap shims use this key as a feature-detection hook; registering
            # native routes first lets those shims no-op instead of shadowing the
            # upstream session-control handlers.
            self._app["api_server_adapter"] = self
'''
insert = '''            # Pinto webhook compatibility route. Register before aiohttp router freezes.
            self._app["response_class"] = web.json_response

            async def _pinto_route(request):
                import gc
                if request.method == "GET":
                    return web.json_response({"ok": True, "channel": "pinto"})
                try:
                    body = await request.json()
                except Exception:
                    body = None
                for obj in gc.get_objects():
                    if obj.__class__.__name__ == "PintoAdapter":
                        if body is None:
                            return web.json_response({"ok": False, "error": "invalid json"}, status=400)
                        class _Req:
                            method = "POST"
                            app = {"response_class": web.json_response}
                            headers = request.headers
                            async def json(self):
                                return body
                        # Await the adapter's real response (auth errors, validation
                        # errors, success) and relay it as-is instead of always
                        # answering 200 queued:true before validation runs.
                        result = await obj._handle_webhook(_Req())
                        return result
                return web.json_response({"ok": False, "error": "pinto adapter not ready"}, status=503)
            async def _pinto_media_route(request):
                import gc
                for obj in gc.get_objects():
                    if obj.__class__.__name__ == "PintoAdapter":
                        return await obj._handle_media(request)
                return web.Response(status=503, text="pinto adapter not ready")
            async def _root_route(request):
                html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hermes + Pinto</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; background: #0f172a; color: #e2e8f0; }
    main { max-width: 820px; margin: 48px auto; padding: 0 20px; }
    .card { background: #111827; border: 1px solid #334155; border-radius: 16px; padding: 24px; box-shadow: 0 20px 60px rgba(0,0,0,.3); }
    h1 { margin: 0 0 8px; font-size: 32px; }
    p { color: #94a3b8; line-height: 1.6; }
    .ok { display: inline-block; background: #064e3b; color: #a7f3d0; border: 1px solid #10b981; padding: 6px 10px; border-radius: 999px; font-size: 14px; }
    a { color: #38bdf8; text-decoration: none; }
    a:hover { text-decoration: underline; }
    code { background: #020617; border: 1px solid #334155; border-radius: 8px; padding: 2px 6px; }
    ul { line-height: 2; }
  </style>
</head>
<body>
  <main>
    <div class="card">
      <span class="ok">Hermes running</span>
      <h1>Hermes + Pinto Gateway</h1>
      <p>This container exposes Hermes Agent API and Pinto webhook endpoint.</p>
      <ul>
        <li><a href="/health">Health</a> — <code>/health</code></li>
        <li><a href="/v1/models">Models</a> — <code>/v1/models</code></li>
        <li><a href="/v1/capabilities">Capabilities</a> — <code>/v1/capabilities</code></li>
        <li><a href="/plugins/pinto/webhook">Pinto webhook health</a> — <code>/plugins/pinto/webhook</code></li>
      </ul>
      <p>OpenAI-compatible API base: <code>http://127.0.0.1:8642/v1</code></p>
    </div>
  </main>
</body>
</html>"""
                return web.Response(text=html, content_type="text/html")
            self._app.router.add_get("/", _root_route)
            self._app.router.add_get("/plugins/pinto/webhook", _pinto_route)
            self._app.router.add_post("/plugins/pinto/webhook", _pinto_route)
            self._app.router.add_get("/plugins/pinto/media/{token}", _pinto_media_route)

'''
if insert.strip() in s:
    print('api_server already patched for Pinto webhook')
elif marker not in s:
    raise SystemExit('Expected api_server route marker not found')
else:
    p.write_text(s.replace(marker, insert + marker), encoding='utf-8')
    print('Patched api_server for Pinto webhook route')
