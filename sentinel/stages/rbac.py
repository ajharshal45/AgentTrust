"""RBAC / Capability-match pipeline stage supporting 3-tier verdicts (pass, alert, block)."""

from sentinel import alert_queue
from sentinel.checks import check_capability_match
from sentinel.stages.base import StageResult


def _extract_stem(skill_id: str) -> str:
    """Extract keyword stem from skill ID (e.g. 'summarize' from 'summarize_text')."""
    return skill_id.split("_")[0].lower() if skill_id else ""


def run(request_context: dict) -> StageResult:
    """Run capability-match (RBAC) pipeline stage with 3-tier verdict model.

    Outcomes:
        - verdict="pass": Exact match or approved by human reviewer in alert_queue.
        - verdict="alert": Partial / fuzzy match (requires human review).
        - verdict="block": Disjoint capability mismatch or rejected by human reviewer.

    Args:
        request_context: Dictionary containing 'caller_card', 'requested_skill', and 'agent_name'.

    Returns:
        StageResult indicating verdict ('pass', 'alert', or 'block'), reason, and stage_name ('rbac').
    """
    caller_card = request_context.get("caller_card")
    requested_skill = request_context.get("requested_skill", "unknown")
    agent_name = request_context.get("agent_name", "unknown")

    if not caller_card or not isinstance(caller_card, dict):
        return StageResult(
            verdict="block",
            reason="no caller_agent_card in request metadata",
            stage_name="rbac",
        )

    # 1. Check if a human reviewer has already approved or rejected this alert in alert_queue
    reviewer_status = alert_queue.get_alert_status(agent_name, requested_skill)
    if reviewer_status == "approved":
        return StageResult(verdict="pass", reason=None, stage_name="rbac")
    if reviewer_status == "rejected":
        return StageResult(
            verdict="block",
            reason=f"capability mismatch: human reviewer rejected request for '{requested_skill}'",
            stage_name="rbac",
        )

    skills = caller_card.get("skills", [])
    declared_skill_ids = [s.get("id", "") for s in skills if isinstance(s, dict)]

    if not declared_skill_ids:
        return StageResult(
            verdict="block",
            reason="caller's AgentCard declares no skills",
            stage_name="rbac",
        )

    if requested_skill == "unknown":
        return StageResult(verdict="pass", reason=None, stage_name="rbac")

    # 2. Exact match check -> PASS
    if requested_skill in declared_skill_ids:
        return StageResult(verdict="pass", reason=None, stage_name="rbac")

    # 3. Partial / Fuzzy match check -> ALERT
    req_stem = _extract_stem(requested_skill)
    declared_stems = [_extract_stem(sid) for sid in declared_skill_ids]

    if req_stem and req_stem in declared_stems:
        return StageResult(
            verdict="alert",
            reason=(
                f"partial capability match: requested '{requested_skill}' requires human "
                f"review against declared skills {declared_skill_ids}"
            ),
            stage_name="rbac",
        )

    # 4. Disjoint / Unmatched capability -> BLOCK
    return StageResult(
        verdict="block",
        reason=(
            f"capability mismatch: requested skill '{requested_skill}' not in caller's declared "
            f"skills {declared_skill_ids}"
        ),
        stage_name="rbac",
    )
