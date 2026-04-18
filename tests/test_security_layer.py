import asyncio
import importlib
import os
import sys
import unittest


def _set_base_env() -> None:
    os.environ["HP_API_KEYS"] = "test-key"
    os.environ["HP_SECURITY_ALLOWED_IPS"] = "127.0.0.1/32,10.0.0.0/8"
    os.environ["HP_HEALTH_ALLOWED_IPS"] = "127.0.0.1/32"
    os.environ["HP_SECURITY_TRUSTED_PROXY_CIDRS"] = "10.10.0.0/16"


def _load_main_module():
    if "main" in sys.modules:
        del sys.modules["main"]
    import main  # noqa: F401
    return importlib.reload(sys.modules["main"])


async def _asgi_call(
    app,
    *,
    method: str,
    path: str,
    query_string: str = "",
    headers: dict[str, str] | None = None,
    body: bytes = b"",
    client: tuple[str, int] = ("127.0.0.1", 50000),
):
    headers = headers or {}
    raw_headers = [(k.lower().encode("ascii"), v.encode("utf-8")) for k, v in headers.items()]
    if not any(k == b"host" for k, _ in raw_headers):
        raw_headers.append((b"host", b"testserver"))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string.encode("utf-8"),
        "headers": raw_headers,
        "client": client,
        "server": ("testserver", 80),
    }
    sent = {"done": False}
    messages: list[dict] = []

    async def receive():
        if not sent["done"]:
            sent["done"] = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.sleep(0)
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)

    start = next(m for m in messages if m["type"] == "http.response.start")
    body_msgs = [m for m in messages if m["type"] == "http.response.body"]
    body_bytes = b"".join(m.get("body", b"") for m in body_msgs)
    headers_out = {
        k.decode("latin1").lower(): v.decode("latin1")
        for k, v in start["headers"]
    }
    return start["status"], headers_out, body_bytes


class SecurityLayerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        _set_base_env()
        self.main = _load_main_module()
        self.app = self.main.app
        self.lifespan_cm = self.app.router.lifespan_context(self.app)
        await self.lifespan_cm.__aenter__()

    async def asyncTearDown(self):
        await self.lifespan_cm.__aexit__(None, None, None)

    async def test_health_allowed_and_minimal_response(self):
        status, headers, body = await _asgi_call(
            self.app,
            method="GET",
            path="/health",
            headers={"X-API-Key": "test-key"},
            client=("127.0.0.1", 50000),
        )
        self.assertEqual(status, 200)
        self.assertIn("x-request-id", headers)
        payload = self.main.json.loads(body.decode("utf-8"))
        self.assertEqual(payload["status"], "ok")
        self.assertIn("timestamp", payload)
        self.assertIn("checks", payload)
        self.assertIn("db", payload["checks"])
        self.assertNotIn("db", payload)
        self.assertNotIn("active_tracks", payload)
        self.assertNotIn("thresholds_loaded", payload)

    async def test_health_denied_ip_returns_403(self):
        status, headers, body = await _asgi_call(
            self.app,
            method="GET",
            path="/health",
            headers={"X-API-Key": "test-key"},
            client=("192.168.1.10", 50000),
        )
        self.assertEqual(status, 403)
        payload = self.main.json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"]["code"], "FORBIDDEN")
        self.assertEqual(payload["error"]["details"]["source"], "header")
        self.assertIn("x-request-id", headers)

    async def test_missing_api_key_returns_401_schema(self):
        status, _, body = await _asgi_call(
            self.app,
            method="GET",
            path="/search",
            client=("127.0.0.1", 50000),
        )
        self.assertEqual(status, 401)
        payload = self.main.json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"]["code"], "UNAUTHORIZED")
        self.assertIn("request_id", payload["error"])

    async def test_invalid_xff_returns_400(self):
        status, _, body = await _asgi_call(
            self.app,
            method="GET",
            path="/search",
            headers={
                "X-API-Key": "test-key",
                "X-Forwarded-For": "invalid-ip-value",
            },
            client=("10.10.1.10", 50000),
        )
        self.assertEqual(status, 400)
        payload = self.main.json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["source"], "header")

    async def test_validation_error_422_schema(self):
        status, _, body = await _asgi_call(
            self.app,
            method="GET",
            path="/concierge",
            query_string="step=abc",
            headers={"X-API-Key": "test-key"},
            client=("127.0.0.1", 50000),
        )
        self.assertEqual(status, 422)
        payload = self.main.json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(payload["error"]["details"]["source"], "query")

    async def test_request_id_passthrough_and_generated(self):
        custom_id = "req_custom_123"
        status1, headers1, _ = await _asgi_call(
            self.app,
            method="GET",
            path="/health",
            headers={"X-API-Key": "test-key", "X-Request-Id": custom_id},
            client=("127.0.0.1", 50000),
        )
        self.assertEqual(status1, 200)
        self.assertEqual(headers1.get("x-request-id"), custom_id)

        status2, headers2, body2 = await _asgi_call(
            self.app,
            method="GET",
            path="/search",
            headers={"X-API-Key": "test-key"},
            client=("127.0.0.1", 50000),
        )
        self.assertEqual(status2, 200)
        self.assertTrue(headers2.get("x-request-id", "").startswith("req_"))
        self.assertTrue(len(body2) > 0)


class FailClosedConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_cidr_fails_startup(self):
        os.environ["HP_API_KEYS"] = "test-key"
        os.environ["HP_SECURITY_ALLOWED_IPS"] = "127.0.0.1/32"
        os.environ["HP_HEALTH_ALLOWED_IPS"] = "127.0.0.1/32"
        os.environ["HP_SECURITY_TRUSTED_PROXY_CIDRS"] = "invalid-cidr"
        main_mod = _load_main_module()
        cm = main_mod.app.router.lifespan_context(main_mod.app)
        with self.assertRaises(RuntimeError):
            await cm.__aenter__()

