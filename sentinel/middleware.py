"""A2ASentinel middleware for FastAPI with 3-tier trust and task polling support."""

import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from sentinel import alert_queue
from sentinel.checks import infer_requested_skill
from sentinel.pipeline import Pipeline

logger = logging.getLogger(__name__)

# ANSI-free log prefix for clear demo output
LOG_PREFIX = "[A2ASentinel]"


class A2ASentinelMiddleware(BaseHTTPMiddleware):
    """FastAPI/Starlette middleware enforcing 3-tier trust verification via Pipeline."""

    def __init__(self, app, pipeline: Pipeline | None = None):
        super().__init__(app)
        self.pipeline = pipeline or Pipeline()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Handle GET /tasks/{task_id}/status polling endpoint
        path = request.url.path
        if request.method == "GET" and path.startswith("/tasks/") and path.endswith("/status"):
            parts = path.strip("/").split("/")
            if len(parts) >= 3:
                task_id_str = parts[1]
                try:
                    alert_id = int(task_id_str)
                    alert = alert_queue.get_alert(alert_id)
                    if alert:
                        return JSONResponse({
                            "task_id": str(alert_id),
                            "status": alert.get("status", "unknown"),
                            "agent_name": alert.get("agent_name"),
                            "requested_task": alert.get("requested_task"),
                        })
                except ValueError:
                    pass
            return JSONResponse({"error": "task not found"}, status_code=404)

        # Only intercept POST to the JSON-RPC endpoint
        if request.method != "POST":
            return await call_next(request)

        # Read and parse the request body
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return await call_next(request)

        # Only check SendMessage requests (the ones Agent A sends)
        method = body.get("method", "")
        if method != "SendMessage":
            return await call_next(request)

        request_id = body.get("id")
        params = body.get("params", {})
        metadata = params.get("metadata", {})
        caller_card = metadata.get("caller_agent_card")
        force_review_result = metadata.get("force_review_result", "")

        # Extract client IP address for identity-agnostic Stage 0 IP throttling
        client_ip = "127.0.0.1"
        if request.client and request.client.host:
            client_ip = request.client.host

        # Extract the message text for skill inference
        message = params.get("message", {})
        message_parts = message.get("parts", [])
        message_text = ""
        for part in message_parts:
            if "text" in part:
                message_text = part["text"]
                break

        # Infer which skill is being requested
        requested_skill = infer_requested_skill(message_text)

        # Get the caller's name for logging
        agent_name = "unknown"
        if caller_card and isinstance(caller_card, dict):
            agent_name = caller_card.get("name", "unknown")

        request_context = {
            "agent_name": agent_name,
            "caller_card": caller_card,
            "message_text": message_text,
            "requested_skill": requested_skill,
            "request_id": request_id,
            "client_ip": client_ip,
            "force_review_result": force_review_result,
        }

        # Run through modular 3-tier pipeline
        decision = self.pipeline.run(request_context)

        if decision.status == "PENDING_REVIEW":
            reason = decision.reason or "requires human review"
            self._log_pending_review(agent_name, requested_skill, reason, decision.alert_id)
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "result": {
                        "status": "PENDING_REVIEW",
                        "task_id": str(decision.alert_id),
                        "message": f"PENDING_REVIEW: {reason} (Enqueued in Alert Queue #{decision.alert_id})",
                    },
                    "id": request_id,
                },
                status_code=202,  # HTTP 202 Accepted for asynchronous task polling
            )

        if decision.status == "BLOCKED":
            reason = decision.reason or "access denied"
            self._log_blocked(agent_name, requested_skill, reason)
            return self._make_blocked_response(request_id, reason)

        # ALLOWED — forward to Agent B
        self._log_allowed(agent_name, requested_skill)
        return await call_next(request)

    def _log_allowed(self, agent_name: str, skill: str) -> None:
        msg = f"{LOG_PREFIX} {agent_name} -> {skill}: ALLOWED"
        logger.info(msg)
        print(msg)

    def _log_pending_review(
        self, agent_name: str, skill: str, reason: str, alert_id: int | None
    ) -> None:
        msg = f"{LOG_PREFIX} {agent_name} -> {skill}: PENDING_REVIEW (reason: {reason} [Alert #{alert_id}])"
        logger.warning(msg)
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
            status_code=200,
        )
