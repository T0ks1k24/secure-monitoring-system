from __future__ import annotations

import asyncio

from schemas import DiscoveredCamera, ScanResult
from service._scanner_utils import scan_network_sync


async def scan_network(
    subnet: str,
    ports: list[int],
    credentials: list[dict],
    timeout: float = 1.0,
    max_workers: int = 64,
) -> ScanResult:
    """
    Asynchronous network scan. Does not block event loop.
    Runs scan_network_sync in thread pool executor,
    converts result to Pydantic ScanResult.
    """
    loop = asyncio.get_running_loop()
    raw = await loop.run_in_executor(
        None,
        scan_network_sync,
        subnet,
        ports,
        credentials,
        timeout,
        max_workers,
    )
    return ScanResult(
        subnet=raw["subnet"],
        ports_scanned=raw["ports_scanned"],
        hosts_scanned=raw["hosts_scanned"],
        found=[DiscoveredCamera(**cam) for cam in raw["found"]],
        scan_duration_sec=raw["scan_duration_sec"],
    )
