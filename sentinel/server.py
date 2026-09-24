"""Protected Agent B server — Agent B + AgentTrust middleware.

This is a wrapper that imports Agent B's existing create_app() and
adds the AgentTrust middleware in front of it. Agent B's own code
(agent_b/) is completely unmodified.

Run with:  python -m sentinel.server

This replaces the standalone `python -m agent_b.server` for the
protected demo scenario.
"""

import logging

import uvicorn

from agent_b.card import AGENT_B_HOST, AGENT_B_PORT
from agent_b.server import create_app
from sentinel.middleware import A2ASentinelMiddleware

# Configure logging so we can see sentinel decisions alongside Agent B's logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_protected_app():
    """Create Agent B's FastAPI app with AgentTrust middleware in front."""

    # 1. Create the standard Agent B app (same as agent_b/server.py)
    app = create_app()

    # 2. Add AgentTrust middleware — this runs BEFORE Agent B's routes
    #    see any request. Blocked requests never reach Agent B.
    app.add_middleware(A2ASentinelMiddleware)

    logger.info("AgentTrust middleware enabled — protecting Agent B")
    return app


# Module-level app instance for uvicorn
app = create_protected_app()


if __name__ == "__main__":
    logger.info(
        "Starting PROTECTED Agent B (with AgentTrust) on %s:%d",
        AGENT_B_HOST,
        AGENT_B_PORT,
    )
    uvicorn.run(
        "sentinel.server:app",
        host=AGENT_B_HOST,
        port=AGENT_B_PORT,
        log_level="info",
    )
