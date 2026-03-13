"""Tests for scanner utilities — build_rtsp_url, check_tcp_port, scan_network_sync."""
import socket
import unittest
from unittest.mock import patch, MagicMock

from service._scanner_utils import (
    build_rtsp_url,
    check_tcp_port,
    probe_host,
    scan_network_sync,
)


class TestBuildRtspUrl(unittest.TestCase):

    def test_no_auth_no_path(self):
        url = build_rtsp_url("192.168.1.1", 554)
        self.assertEqual(url, "rtsp://192.168.1.1:554/")

    def test_with_user_and_password(self):
        url = build_rtsp_url("192.168.1.1", 554, user="admin", password="pass")
        self.assertEqual(url, "rtsp://admin:pass@192.168.1.1:554/")

    def test_with_user_no_password(self):
        url = build_rtsp_url("10.0.0.1", 8554, user="admin", password="")
        self.assertIn("admin@", url)
        self.assertNotIn(":@", url)

    def test_with_path(self):
        url = build_rtsp_url("1.2.3.4", 554, path="/stream")
        self.assertEqual(url, "rtsp://1.2.3.4:554/stream")

    def test_with_all_params(self):
        url = build_rtsp_url("10.0.0.1", 8554, user="admin", password="12345", path="live")
        self.assertEqual(url, "rtsp://admin:12345@10.0.0.1:8554/live")

    def test_strips_leading_slash_from_path(self):
        url = build_rtsp_url("1.2.3.4", 554, path="/stream/main")
        self.assertEqual(url, "rtsp://1.2.3.4:554/stream/main")


class TestCheckTcpPort(unittest.TestCase):

    @patch("service._scanner_utils.socket.create_connection")
    def test_open_port_returns_true(self, mock_conn):
        mock_conn.return_value.__enter__ = MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        self.assertTrue(check_tcp_port("1.2.3.4", 554, timeout=1.0))

    @patch("service._scanner_utils.socket.create_connection")
    def test_refused_port_returns_false(self, mock_conn):
        mock_conn.side_effect = ConnectionRefusedError()
        self.assertFalse(check_tcp_port("1.2.3.4", 554, timeout=1.0))

    @patch("service._scanner_utils.socket.create_connection")
    def test_timeout_returns_false(self, mock_conn):
        mock_conn.side_effect = socket.timeout()
        self.assertFalse(check_tcp_port("1.2.3.4", 554, timeout=1.0))

    @patch("service._scanner_utils.socket.create_connection")
    def test_os_error_returns_false(self, mock_conn):
        mock_conn.side_effect = OSError("network unreachable")
        self.assertFalse(check_tcp_port("1.2.3.4", 554, timeout=1.0))


class TestProbeHost(unittest.TestCase):

    @patch("service._scanner_utils.check_tcp_port", return_value=False)
    def test_port_closed_returns_none(self, mock_check):
        result = probe_host("1.2.3.4", 554, [], timeout=1.0)
        self.assertIsNone(result)

    @patch("service._scanner_utils.try_rtsp_connect", return_value=True)
    @patch("service._scanner_utils.check_tcp_port", return_value=True)
    def test_connectable_without_creds(self, mock_check, mock_rtsp):
        result = probe_host("1.2.3.4", 554, [], timeout=1.0)
        self.assertIsNotNone(result)
        self.assertTrue(result["connectable"])

    @patch("service._scanner_utils.try_rtsp_connect")
    @patch("service._scanner_utils.check_tcp_port", return_value=True)
    def test_connectable_with_creds(self, mock_check, mock_rtsp):
        # First call without creds fails, then with creds succeeds
        mock_rtsp.side_effect = lambda url, _: "admin" in url
        result = probe_host(
            "1.2.3.4", 554,
            [{"user": "admin", "password": "pass"}],
            timeout=1.0,
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["connectable"])

    @patch("service._scanner_utils.try_rtsp_connect", return_value=False)
    @patch("service._scanner_utils.check_tcp_port", return_value=True)
    def test_reachable_but_not_connectable(self, mock_check, mock_rtsp):
        result = probe_host("1.2.3.4", 554, [], timeout=1.0)
        self.assertIsNotNone(result)
        self.assertTrue(result["reachable"])
        self.assertFalse(result["connectable"])


class TestScanNetworkSync(unittest.TestCase):

    def test_invalid_subnet_raises_value_error(self):
        with self.assertRaises(ValueError):
            scan_network_sync("not_a_subnet", [554], [], timeout=0.1, max_workers=1)

    @patch("service._scanner_utils.probe_host", return_value=None)
    def test_correct_result_structure(self, mock_probe):
        result = scan_network_sync("192.0.2.0/30", [554], [], timeout=0.1, max_workers=2)
        for key in ("subnet", "ports_scanned", "hosts_scanned", "found", "scan_duration_sec"):
            self.assertIn(key, result, f"Missing key: {key}")
        self.assertEqual(result["subnet"], "192.0.2.0/30")
        self.assertEqual(result["ports_scanned"], [554])

    @patch("service._scanner_utils.probe_host")
    def test_results_sorted_by_ip_and_port(self, mock_probe):
        mock_probe.side_effect = lambda ip, port, *a, **kw: {
            "ip": ip, "port": port, "connectable": True,
            "reachable": True, "rtsp_url": f"rtsp://{ip}:{port}",
            "credentials_used": None, "suggested_id": f"cam_{ip}",
        }
        result = scan_network_sync("192.0.2.0/30", [554, 8554], [], timeout=0.1, max_workers=2)
        ips = [(c["ip"], c["port"]) for c in result["found"]]
        self.assertEqual(ips, sorted(ips))

    @patch("service._scanner_utils.probe_host", return_value=None)
    def test_all_ports_scanned(self, mock_probe):
        result = scan_network_sync("192.0.2.0/30", [554, 8554], [], timeout=0.1, max_workers=2)
        self.assertEqual(result["ports_scanned"], [554, 8554])


if __name__ == "__main__":
    unittest.main(verbosity=2)
