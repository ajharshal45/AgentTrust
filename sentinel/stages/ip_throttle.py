"""Identity-agnostic IP throttling stage for A2ASentinel."""

import time

from sentinel.stages.base import StageResult

# Configurable IP Throttling Constants
IP_THROTTLE_BURST = 20  # Max requests per IP in sliding window
IP_THROTTLE_WINDOW = 10.0  # Window duration in seconds

# In-memory IP tracking dictionary: client_ip -> list of float timestamps
_ip_timestamps: dict[str, list[float]] = {}


def reset_ip_throttle_state() -> None:
    """Reset in-memory IP throttle state (used in testing)."""
    _ip_timestamps.clear()


def run(request_context: dict) -> StageResult:
    """Run identity-agnostic IP throttling check.

    Runs FIRST in the pipeline (before signature verification) to drop cheap network floods
    without trusting any unverified agent identity claims in the payload.

    Args:
        request_context: Context dictionary containing 'client_ip'.

    Returns:
        StageResult with verdict="pass" or verdict="block".
    """
    client_ip = request_context.get("client_ip", "127.0.0.1")
    now = time.time()

    timestamps = _ip_timestamps.setdefault(client_ip, [])
    cutoff = now - IP_THROTTLE_WINDOW
    valid_timestamps = [t for t in timestamps if t >= cutoff]
    _ip_timestamps[client_ip] = valid_timestamps

    if len(valid_timestamps) >= IP_THROTTLE_BURST:
        return StageResult(
            verdict="block",
            reason=f"IP throttle exceeded: {len(valid_timestamps) + 1} requests in {IP_THROTTLE_WINDOW:.0f}s from IP {client_ip} (max {IP_THROTTLE_BURST})",
            stage_name="ip_throttle",
        )

    _ip_timestamps[client_ip].append(now)
    return StageResult(verdict="pass", reason=None, stage_name="ip_throttle")
