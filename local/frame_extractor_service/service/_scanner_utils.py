from __future__ import annotations

import ipaddress
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

logger = logging.getLogger(__name__)

# Typical RTSP paths by manufacturer
RTSP_PATHS = [
    "",
    "/stream", "/live", "/h264", "/video1",
    "/Streaming/Channels/101",
    "/cam/realmonitor?channel=1&subtype=0",
    "/axis-media/media.amp",
    "/h264Preview_01_main",
    "/videoMain", "/ch0_0.264", "/media/video1",
]


def build_rtsp_url(
    ip: str,
    port: int,
    user: str = "",
    password: str = "",
    path: str = "",
) -> str:
    """Forms an RTSP URL with or without authorization."""
    if user:
        auth = f"{user}:{password}@" if password else f"{user}@"
    else:
        auth = ""
    return f"rtsp://{auth}{ip}:{port}/{path.lstrip('/')}"


def check_tcp_port(ip: str, port: int, timeout: float) -> bool:
    """Checks if a TCP port is open."""
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def try_rtsp_connect(rtsp_url: str, timeout: float) -> bool:
    """Trying to connect to RTSP stream via OpenCV."""
    try:
        import cv2
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        ok = cap.isOpened()
        cap.release()
        return ok
    except Exception:
        return False


def probe_host(
    ip: str,
    port: int,
    credentials: list[dict],
    timeout: float,
) -> Optional[dict]:
    """
    Tests a single IP:PORT.

    Returns a dict with the result or None if the port is unavailable.
    """
    if not check_tcp_port(ip, port, timeout):
        return None

    suggested_id = f"cam_{ip.replace('.', '_')}_{port}"

    # Let's try without authorization
    for path in RTSP_PATHS:
        url = build_rtsp_url(ip, port, path=path)
        if try_rtsp_connect(url, timeout):
            return dict(
                ip=ip, port=port, rtsp_url=url,
                reachable=True, connectable=True,
                credentials_used=None, suggested_id=suggested_id,
            )

    # Let's try with each set of credentials
    for cred in credentials:
        user = cred.get("user", "admin")
        pwd  = cred.get("password", "")
        for path in RTSP_PATHS:
            url = build_rtsp_url(ip, port, user=user, password=pwd, path=path)
            if try_rtsp_connect(url, timeout):
                return dict(
                    ip=ip, port=port, rtsp_url=url,
                    reachable=True, connectable=True,
                    credentials_used={"user": user, "password": pwd},
                    suggested_id=suggested_id,
                )

    # Port is open, but connection failed
    return dict(
        ip=ip, port=port,
        rtsp_url=build_rtsp_url(ip, port),
        reachable=True, connectable=False,
        credentials_used=None, suggested_id=suggested_id,
    )


def scan_network_sync(
    subnet: str,
    ports: list[int],
    credentials: list[dict],
    timeout: float = 1.0,
    max_workers: int = 64,
) -> dict:
    """
    Synchronous subnet scan. Returns a plain dict.
    """
    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError as exc:
        raise ValueError(f"Невірний формат підмережі '{subnet}': {exc}") from exc

    hosts = list(network.hosts())
    logger.info("Scanning %d hosts in %s, ports=%s", len(hosts), subnet, ports)
    start = time.monotonic()

    found: list[dict] = []
    tasks = [(str(ip), port) for ip in hosts for port in ports]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(probe_host, ip, port, credentials, timeout): (ip, port)
            for ip, port in tasks
        }
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                found.append(result)
                logger.info(
                    "Found camera: %s:%d connectable=%s",
                    result["ip"], result["port"], result["connectable"],
                )

    duration = time.monotonic() - start
    found.sort(key=lambda c: (c["ip"], c["port"]))

    logger.info("Scan complete: %d cameras in %.1fs", len(found), duration)
    return dict(
        subnet=subnet,
        ports_scanned=ports,
        hosts_scanned=len(hosts),
        found=found,
        scan_duration_sec=round(duration, 2),
    )
