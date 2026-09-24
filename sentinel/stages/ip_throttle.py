"""Identity-agnostic IP throttling stage for AgentTrust."""

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


def release_authenticated_request(client_ip: str) -> None:
    """Credit back one request from the IP throttle counter for a verified agent.

    Called by the pipeline after Stage 1 (signature check) passes. The design
    rationale: Stage 0 IP throttle exists to block unauthenticated connection
    floods cheaply, before doing any crypto. Once an agent proves its identity
    cryptographically (Stage 1), it is no longer 'unauthenticated traffic' and
    should be rated by its per-agent quota (Stage 2: rate_limiter) instead of
    the raw IP flood limit.

    Without this, running many personas from localhost (all sharing IP ::1)
    causes the legitimate agent to be falsely blocked by the IP limit after
    attacker requests have filled the window — even though every attacker was
    correctly rejected at Stage 1.
    """
    timestamps = _ip_timestamps.get(client_ip)
    if timestamps:
        # Remove the most recently added timestamp (the one added by this request)
        _ip_timestamps[client_ip] = timestamps[:-1]


def run(request_context: dict) -> StageResult:
    """Run identity-agnostic IP throttling check.

    Runs FIRST in the pipeline (before signature verification) to drop cheap
    network floods without trusting any unverified agent identity claims.

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
            reason=(
                f"IP throttle exceeded: {len(valid_timestamps) + 1} requests "
                f"in {IP_THROTTLE_WINDOW:.0f}s from IP {client_ip} "
                f"(max {IP_THROTTLE_BURST})"
            ),
            stage_name="ip_throttle",
        )

    _ip_timestamps[client_ip].append(now)
    return StageResult(verdict="pass", reason=None, stage_name="ip_throttle")
