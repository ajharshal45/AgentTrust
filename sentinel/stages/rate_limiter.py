"""Per-Agent Rate Limiter & Cycle Overflow Mitigation stage.

Runs AFTER signature_check in the pipeline, ensuring per-agent quota and cycle overflow tracking
is only enforced once the caller's identity has been cryptographically verified.
"""

import time

from sentinel.stages.base import StageResult

# Configurable Rate Limiting Constants (Post-Signature Verification)
RATE_LIMIT_BURST = 5  # Max requests per window per verified agent
RATE_LIMIT_WINDOW = 10.0  # Sliding window duration in seconds

# Configurable Cycle Overflow / Loop Detection Constants
CYCLE_REPEAT_THRESHOLD = 3  # Max repeat requests for exact same task in window
CYCLE_REPEAT_WINDOW = 5.0  # Sliding window duration for repeat task detection in seconds

# In-memory sliding window tracking structures
_agent_timestamps: dict[str, list[float]] = {}
_agent_task_history: dict[tuple[str, str], list[float]] = {}


def reset_rate_limiter_state() -> None:
    """Reset in-memory rate limiter tracking state (used in testing)."""
    _agent_timestamps.clear()
    _agent_task_history.clear()


def run(request_context: dict) -> StageResult:
    """Run per-agent rate limiting and cycle overflow detection stage.

    Keyed by verified agent_name (guaranteed verified because signature_check ran before this).

    Args:
        request_context: Context dictionary containing agent metadata and request info.

    Returns:
        StageResult with verdict="pass" or verdict="block".
    """
    agent_name = request_context.get("agent_name", "unknown")
    requested_task = request_context.get("requested_skill", "unknown")
    now = time.time()

    # 1. Overall Per-Agent Rate Limiting
    timestamps = _agent_timestamps.setdefault(agent_name, [])
    cutoff = now - RATE_LIMIT_WINDOW
    valid_timestamps = [t for t in timestamps if t >= cutoff]
    _agent_timestamps[agent_name] = valid_timestamps

    if len(valid_timestamps) >= RATE_LIMIT_BURST:
        return StageResult(
            verdict="block",
            reason=f"rate limit exceeded: {len(valid_timestamps) + 1} requests in {RATE_LIMIT_WINDOW:.0f}s for agent '{agent_name}' (max {RATE_LIMIT_BURST})",
            stage_name="rate_limiter",
        )

    # 2. Cycle Overflow / Task Loop Detection
    task_key = (agent_name, requested_task)
    task_timestamps = _agent_task_history.setdefault(task_key, [])
    task_cutoff = now - CYCLE_REPEAT_WINDOW
    valid_task_timestamps = [t for t in task_timestamps if t >= task_cutoff]
    _agent_task_history[task_key] = valid_task_timestamps

    if len(valid_task_timestamps) >= CYCLE_REPEAT_THRESHOLD:
        return StageResult(
            verdict="block",
            reason=(
                f"cycle overflow detected: agent '{agent_name}' repeated task "
                f"'{requested_task}' {len(valid_task_timestamps) + 1} times in {CYCLE_REPEAT_WINDOW:.0f}s"
            ),
            stage_name="rate_limiter",
        )

    _agent_timestamps[agent_name].append(now)
    _agent_task_history[task_key].append(now)

    return StageResult(verdict="pass", reason=None, stage_name="rate_limiter")
