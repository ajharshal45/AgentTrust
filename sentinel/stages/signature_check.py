"""Signature verification pipeline stage."""

from sentinel.checks import check_signature
from sentinel.stages.base import StageResult


def run(request_context: dict) -> StageResult:
    """Run cryptographic JWS signature verification stage.

    Args:
        request_context: Dictionary containing 'caller_card' and request details.

    Returns:
        StageResult indicating verdict ('pass' or 'block'), reason, and stage_name ('signature_check').
    """
    caller_card = request_context.get("caller_card")
    if not caller_card or not isinstance(caller_card, dict):
        return StageResult(
            verdict="block",
            reason="no caller_agent_card in request metadata",
            stage_name="signature_check",
        )

    sig_ok, sig_reason = check_signature(caller_card)
    if not sig_ok:
        return StageResult(
            verdict="block",
            reason=f"invalid signature: {sig_reason}",
            stage_name="signature_check",
        )

    return StageResult(verdict="pass", reason=None, stage_name="signature_check")
