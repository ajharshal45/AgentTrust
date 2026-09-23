"""Base dataclass for Sentinel pipeline stages."""

from dataclasses import dataclass
from typing import Literal

VerdictType = Literal["pass", "alert", "block"]


@dataclass
class StageResult:
    """Result returned by an individual pipeline stage.

    Attributes:
        verdict: "pass" (clean pass), "alert" (requires human review), or "block" (hard failure).
        reason: Human-readable failure/alert reason, or None if verdict is "pass".
        stage_name: Unique identifier of the stage that performed the check.
    """

    verdict: VerdictType
    reason: str | None = None
    stage_name: str = ""
