"""A2ASentinel middleware for FastAPI.

Sits in front of Agent B's existing routes and intercepts incoming
JSON-RPC requests. Extracts the caller's AgentCard from the request
metadata, runs signature and capability-match checks, and either
forwards the request to Agent B or returns a JSON-RPC error.

This is a clearly separate, pluggable component — it lives in the
sentinel/ module and is added to Agent B's app via app.add_middleware()
without modifying any agent_b/ code.
"""

import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from sentinel.checks import (
    check_capability_match,
    check_signature,
    infer_requested_skill,
)

logger = logging.getLogger(__name__)

# ANSI-free log prefix for clear demo output
LOG_PREFIX = "[A2ASentinel]"


class A2ASentinelMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware that enforces trust verification.

    Intercepts POST requests to the JSON-RPC endpoint ("/") and runs
    two checks on the caller's AgentCard (from request metadata):
      1. Signature check — is the card's JWS signature valid?
      2. Capability-match check — does the requested skill match a
         declared skill in the caller's card?

    Non-POST requests (e.g., GET /.well-known/agent-card.json) pass
    through unmodified.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only intercept POST to the JSON-RPC endpoint
        if request.method != "POST":
            return await call_next(request)

        # Read and parse the request body
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Not valid JSON — let the downstream handler deal with it
            return await call_next(request)

        # Only check SendMessage requests (the ones Agent A sends)
        method = body.get("method", "")
        if method != "SendMessage":
            return await call_next(request)

        request_id = body.get("id")
        params = body.get("params", {})
        metadata = params.get("metadata", {})
        caller_card = metadata.get("caller_agent_card")

        # Extract the message text for skill inference
        message = params.get("message", {})
        parts = message.get("parts", [])
        message_text = ""
        for part in parts:
            if "text" in part:
                message_text = part["text"]
                break

        # Infer which skill is being requested
        requested_skill = infer_requested_skill(message_text)

        # Get the caller's name for logging
        agent_name = "unknown"
        if caller_card and isinstance(caller_card, dict):
            agent_name = caller_card.get("name", "unknown")

        # --- CHECK 1: No caller card at all ---
        if not caller_card or not isinstance(caller_card, dict):
            reason = "no caller_agent_card in request metadata"
            self._log_blocked(agent_name, requested_skill, reason)
            return self._make_blocked_response(request_id, reason)

        # --- CHECK 2: Signature verification ---
        sig_ok, sig_reason = check_signature(caller_card)
        if not sig_ok:
            reason = f"invalid signature: {sig_reason}"
            self._log_blocked(agent_name, requested_skill, reason)
            return self._make_blocked_response(request_id, reason)

        # --- CHECK 3: Capability-match ---
        cap_ok, cap_reason = check_capability_match(caller_card, requested_skill)
        if not cap_ok:
            reason = f"capability mismatch: {cap_reason}"
            self._log_blocked(agent_name, requested_skill, reason)
            return self._make_blocked_response(request_id, reason)

        # All checks passed — forward to Agent B
        self._log_allowed(agent_name, requested_skill)
        return await call_next(request)

    def _log_allowed(self, agent_name: str, skill: str) -> None:
        msg = f"{LOG_PREFIX} {agent_name} -> {skill}: ALLOWED"
        logger.info(msg)
        print(msg)

    def _log_blocked(self, agent_name: str, skill: str, reason: str) -> None:
        msg = f"{LOG_PREFIX} {agent_name} -> {skill}: BLOCKED (reason: {reason})"
        logger.warning(msg)
        print(msg)

    def _make_blocked_response(
        self, request_id: str | int | None, reason: str
    ) -> JSONResponse:
        """Return a JSON-RPC error response for blocked requests.

        Uses error code -32403 (custom, analogous to HTTP 403 Forbidden).
        """
        return JSONResponse(
            {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32403,
                    "message": f"BLOCKED by A2ASentinel: {reason}",
                },
                "id": request_id,
            },
            status_code=200,  # JSON-RPC errors are still 200 OK at HTTP level
        )
