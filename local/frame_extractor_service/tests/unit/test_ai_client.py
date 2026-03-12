"""Tests for AIClient — send_frame, update_endpoint, aclose, _get_client."""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import httpx

from core.ai_client import AIClient


class TestAIClientSendFrame(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.client = AIClient(endpoint="http://ai-test:5000/detect", timeout=2)

    @patch("cv2.imencode")
    async def test_send_frame_success_returns_json(self, mock_imencode):
        mock_buf = MagicMock()
        mock_buf.tobytes.return_value = b"fake-jpeg"
        mock_imencode.return_value = (True, mock_buf)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"detections": []}
        mock_resp.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_resp
        self.client._client = mock_httpx

        result = await self.client.send_frame(
            frame=MagicMock(), camera_id="cam1", jpeg_quality=90
        )
        self.assertEqual(result, {"detections": []})
        mock_resp.raise_for_status.assert_called_once()

    @patch("cv2.imencode")
    async def test_send_frame_timeout_returns_none(self, mock_imencode):
        mock_buf = MagicMock()
        mock_buf.tobytes.return_value = b"fake"
        mock_imencode.return_value = (True, mock_buf)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.post.side_effect = httpx.TimeoutException("timeout")
        self.client._client = mock_httpx

        result = await self.client.send_frame(MagicMock(), "cam1")
        self.assertIsNone(result)

    @patch("cv2.imencode")
    async def test_send_frame_http_status_error_returns_none(self, mock_imencode):
        mock_buf = MagicMock()
        mock_buf.tobytes.return_value = b"fake"
        mock_imencode.return_value = (True, mock_buf)

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_resp,
        )
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.post.return_value = mock_resp
        self.client._client = mock_httpx

        result = await self.client.send_frame(MagicMock(), "cam1")
        self.assertIsNone(result)

    @patch("cv2.imencode")
    async def test_send_frame_request_error_returns_none(self, mock_imencode):
        mock_buf = MagicMock()
        mock_buf.tobytes.return_value = b"fake"
        mock_imencode.return_value = (True, mock_buf)

        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        mock_httpx.post.side_effect = httpx.RequestError("connection failed")
        self.client._client = mock_httpx

        result = await self.client.send_frame(MagicMock(), "cam1")
        self.assertIsNone(result)

    @patch("cv2.imencode")
    async def test_send_frame_invalid_frame_encode_fails_returns_none(self, mock_imencode):
        mock_imencode.return_value = (False, None)

        result = await self.client.send_frame(MagicMock(), "cam1")
        self.assertIsNone(result)


class TestAIClientUpdateEndpoint(unittest.TestCase):

    def test_update_endpoint_changes_url(self):
        client = AIClient(endpoint="http://old:5000", timeout=1)
        client.update_endpoint("http://new:6000/v2/detect")
        self.assertEqual(client.endpoint, "http://new:6000/v2/detect")


class TestAIClientAclose(unittest.IsolatedAsyncioTestCase):

    async def test_aclose_open_client_closes_and_clears(self):
        client = AIClient(endpoint="http://test", timeout=1)
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = False
        client._client = mock_httpx

        await client.aclose()

        mock_httpx.aclose.assert_awaited_once()
        self.assertIsNone(client._client)

    async def test_aclose_already_closed_client_does_nothing(self):
        client = AIClient(endpoint="http://test", timeout=1)
        mock_httpx = AsyncMock()
        mock_httpx.is_closed = True
        client._client = mock_httpx

        await client.aclose()
        mock_httpx.aclose.assert_not_awaited()

    async def test_aclose_none_client_does_nothing(self):
        client = AIClient(endpoint="http://test", timeout=1)
        client._client = None
        await client.aclose()  # should not raise


class TestAIClientGetClient(unittest.TestCase):

    @patch("core.ai_client.httpx.AsyncClient")
    def test_get_client_lazy_initializes(self, mock_cls):
        client = AIClient(endpoint="http://test", timeout=3)
        self.assertIsNone(client._client)
        c = client._get_client()
        mock_cls.assert_called_once_with(timeout=3)

    @patch("core.ai_client.httpx.AsyncClient")
    def test_get_client_reuses_existing_open_client(self, mock_cls):
        client = AIClient(endpoint="http://test", timeout=1)
        mock_instance = MagicMock()
        mock_instance.is_closed = False
        client._client = mock_instance

        c = client._get_client()
        self.assertIs(c, mock_instance)
        mock_cls.assert_not_called()

    @patch("core.ai_client.httpx.AsyncClient")
    def test_get_client_recreates_after_close(self, mock_cls):
        client = AIClient(endpoint="http://test", timeout=1)
        mock_closed = MagicMock()
        mock_closed.is_closed = True
        client._client = mock_closed

        client._get_client()
        mock_cls.assert_called_once_with(timeout=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
