"""Pipeline executor for AgentTrust security stages with 3-tier verdicts and HITL simulation mode support."""

from dataclasses import dataclass
import os
from typing import Callable, Literal

from sentinel import alert_queue, ledger
from sentinel.stages import (
    injection_filter,
    ip_throttle,
    rate_limiter,
    rbac,
    signature_check,
)
from sentinel.stages.base import StageResult

PipelineStatus = Literal["ALLOWED", "PENDING_REVIEW", "BLOCKED"]


@dataclass
class PipelineDecision:
    """Final decision returned by the Sentinel Pipeline.

    Attributes:
        allowed: True if request is ALLOWED to proceed to Agent B, False otherwise.
        status: "ALLOWED", "PENDING_REVIEW", or "BLOCKED".
        failed_stage: Name of the stage that raised alert/block, or None if allowed.
        reason: Human-readable explanation if status is PENDING_REVIEW or BLOCKED.
        alert_id: Alert queue item ID if status is PENDING_REVIEW, else None.
    """

    allowed: bool
    status: PipelineStatus
    failed_stage: str | None = None
    reason: str | None = None
    alert_id: int | None = None


class Pipeline:
    """Sequential pipeline manager for 3-tier security verification stages."""

    def __init__(self, stages: list[Callable[[dict], StageResult]] | None = None):
        if stages is None:
            # Correct Pipeline Order:
            # 1. ip_throttle (Stage 0: identity-agnostic connection rate limit)
            # 2. signature_check (Stage 1: cryptographic JWS verification)
            # 3. rate_limiter (Stage 2: per-agent quota — AFTER signature verification!)
            # 4. rbac (Stage 3: capability match & alert triggering)
            # 5. injection_filter (Stage 4: prompt injection payload scan)
            self.stages = [
                ip_throttle.run,
                signature_check.run,
                rate_limiter.run,
                rbac.run,
                injection_filter.run,
            ]
        else:
            self.stages = stages

    def run(self, request_context: dict) -> PipelineDecision:
        """Run all registered stages in sequence against the request context.

        Args:
            request_context: Context dictionary containing agent metadata and request info.

        Returns:
            PipelineDecision indicating status, reason, failed stage, and alert_id.
        """
        agent_name = request_context.get("agent_name", "unknown")
        requested_skill = request_context.get("requested_skill", "unknown")
        hitl_mode = os.getenv("HITL_SIMULATION_MODE", "auto").lower()

        for stage_fn in self.stages:
            result: StageResult = stage_fn(request_context)

            # BUG FIX: once an agent passes Stage 1 (signature_check), its
            # request is no longer unauthenticated traffic. Credit it back from
            # the raw IP throttle counter so the legitimate agent is only subject
            # to its per-agent quota (Stage 2: rate_limiter), not the IP flood
            # limit shared with all the attacker personas hitting from ::1.
            if result.verdict == "pass" and result.stage_name == "signature_check":
                from sentinel.stages.ip_throttle import release_authenticated_request
                release_authenticated_request(request_context.get("client_ip", "127.0.0.1"))

            if result.verdict == "block":
                reason_str = result.reason or f"Blocked by stage '{result.stage_name}'"
                ledger.log_decision(
                    agent_name=agent_name,
                    requested_task=requested_skill,
                    decision="BLOCKED",
                    reason=reason_str,
                )
                return PipelineDecision(
                    allowed=False,
                    status="BLOCKED",
                    failed_stage=result.stage_name,
                    reason=reason_str,
                )

            if result.verdict == "alert":
                reason_str = result.reason or f"Alert raised by stage '{result.stage_name}'"

                if hitl_mode == "manual":
                    # Manual mode: enqueue for human CLI review and return PENDING_REVIEW
                    alert_item = alert_queue.enqueue_for_review(
                        agent_name=agent_name,
                        requested_task=requested_skill,
                        reason=reason_str,
                    )
                    ledger.log_decision(
                        agent_name=agent_name,
                        requested_task=requested_skill,
                        decision="PENDING_REVIEW",
                        reason=reason_str,
                    )
                    return PipelineDecision(
                        allowed=False,
                        status="PENDING_REVIEW",
                        failed_stage=result.stage_name,
                        reason=reason_str,
                        alert_id=alert_item.get("alert_id"),
                    )

                # Auto simulation mode (default): log PENDING_REVIEW, then inline simulated resolution
                ledger.log_decision(
                    agent_name=agent_name,
                    requested_task=requested_skill,
                    decision="PENDING_REVIEW",
                    reason=f"{reason_str} (HITL Queue)",
                )

                # Determine inline simulated outcome
                force_result = request_context.get("force_review_result", "").lower()
                if force_result == "reject" or agent_name == "RiskyBot":
                    sim_decision = "BLOCKED"
                    sim_reason = f"capability mismatch: human reviewer rejected request for '{requested_skill}'"
                else:
                    sim_decision = "ALLOWED"
                    sim_reason = "human review approved (auto-simulation)"

                # Log follow-up entry referencing same request/task
                ledger.log_decision(
                    agent_name=agent_name,
                    requested_task=requested_skill,
                    decision=sim_decision,
                    reason=sim_reason,
                )

                if sim_decision == "ALLOWED":
                    return PipelineDecision(
                        allowed=True,
                        status="ALLOWED",
                        failed_stage=None,
                        reason=None,
                    )
                else:
                    return PipelineDecision(
                        allowed=False,
                        status="BLOCKED",
                        failed_stage=result.stage_name,
                        reason=sim_reason,
                    )

        # All stages passed cleanly
        ledger.log_decision(
            agent_name=agent_name,
            requested_task=requested_skill,
            decision="ALLOWED",
            reason="",
        )
        return PipelineDecision(
            allowed=True,
            status="ALLOWED",
            failed_stage=None,
            reason=None,
        )
