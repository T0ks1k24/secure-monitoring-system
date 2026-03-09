"""
Тести для AIClient.
Потребують: pip install httpx
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio, unittest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

try:
    import httpx
    from ai_client import AIClient
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


def black_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)

def _mock_response(json_data, status=200):
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status
    resp.raise_for_status = MagicMock()
    return resp

def _mock_client(return_value=None, side_effect=None):
    mc = AsyncMock()
    mc.__aenter__ = AsyncMock(return_value=mc)
    mc.__aexit__ = AsyncMock(return_value=False)
    if side_effect:
        mc.post = AsyncMock(side_effect=side_effect)
    else:
        mc.post = AsyncMock(return_value=return_value)
    return mc


@unittest.skipUnless(DEPS_AVAILABLE, "httpx not installed")
class TestAIClientInit(unittest.TestCase):

    def test_stores_endpoint_and_timeout(self):
        c = AIClient("http://ai/detect", timeout=10)
        self.assertEqual(c.endpoint, "http://ai/detect")
        self.assertEqual(c.timeout, 10)

    def test_default_timeout(self):
        self.assertEqual(AIClient("http://ai/detect").timeout, 5)


@unittest.skipUnless(DEPS_AVAILABLE, "httpx not installed")
class TestSendFrame(unittest.TestCase):

    def test_returns_json_on_success(self):
        async def run():
            expected = {"status": "ok", "events_published": 1}
            mc = _mock_client(_mock_response(expected))
            with patch("ai_client.httpx.AsyncClient", return_value=mc):
                result = await AIClient("http://ai/detect").send_frame(black_frame(), "cam1", 80)
            self.assertEqual(result, expected)
        asyncio.run(run())

    def test_returns_none_on_timeout(self):
        async def run():
            mc = _mock_client(side_effect=httpx.TimeoutException("t"))
            with patch("ai_client.httpx.AsyncClient", return_value=mc):
                result = await AIClient("http://ai/detect").send_frame(black_frame(), "cam1", 80)
            self.assertIsNone(result)
        asyncio.run(run())

    def test_returns_none_on_connection_error(self):
        async def run():
            mc = _mock_client(side_effect=httpx.RequestError("conn"))
            with patch("ai_client.httpx.AsyncClient", return_value=mc):
                result = await AIClient("http://ai/detect").send_frame(black_frame(), "cam1", 80)
            self.assertIsNone(result)
        asyncio.run(run())

    def test_returns_none_on_http_error(self):
        async def run():
            resp = MagicMock()
            resp.status_code = 500
            resp.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=resp)
            )
            resp.json.return_value = {}
            mc = _mock_client(resp)
            with patch("ai_client.httpx.AsyncClient", return_value=mc):
                result = await AIClient("http://ai/detect").send_frame(black_frame(), "cam1", 80)
            self.assertIsNone(result)
        asyncio.run(run())

    def test_returns_none_on_encode_failure(self):
        async def run():
            with patch("ai_client.cv2.imencode", return_value=(False, None)):
                result = await AIClient("http://ai/detect").send_frame(black_frame(), "cam1", 80)
            self.assertIsNone(result)
        asyncio.run(run())

    def test_sends_correct_camera_id(self):
        async def run():
            mc = _mock_client(_mock_response({"status": "ok"}))
            with patch("ai_client.httpx.AsyncClient", return_value=mc):
                await AIClient("http://ai/detect").send_frame(black_frame(), "my_camera", 80)
            kw = mc.post.call_args.kwargs
            self.assertEqual(kw["data"]["camera_id"], "my_camera")
        asyncio.run(run())

    def test_uses_configured_timeout(self):
        async def run():
            mc = _mock_client(_mock_response({"status": "ok"}))
            with patch("ai_client.httpx.AsyncClient", return_value=mc):
                await AIClient("http://ai/detect", timeout=99).send_frame(black_frame(), "cam1", 80)
            self.assertEqual(mc.post.call_args.kwargs["timeout"], 99)
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
