"""FastAPI server for Agent B.

Wiring summary (confirmed from SDK source):
  - DefaultRequestHandler (= DefaultRequestHandlerV2) constructor:
      Positional required: agent_executor, task_store, agent_card
      Optional (deprecated in v2): queue_manager (defaults to None, ignored)
  - create_agent_card_routes(agent_card) -> list[Route]  (GET /.well-known/agent-card.json)
  - create_jsonrpc_routes(request_handler, rpc_url) -> list[Route]  (POST at rpc_url)
  - add_a2a_routes_to_fastapi(app, agent_card_routes=..., jsonrpc_routes=...) mounts them

Run with:  python -m agent_b.server
"""

import logging
import uvicorn
from fastapi import FastAPI

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes

from agent_b.card import create_agent_b_card, AGENT_B_HOST, AGENT_B_PORT
from agent_b.executor import AgentBExecutor

# Configure logging so we can see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and return the fully-wired FastAPI application for Agent B."""

    app = FastAPI(
        title="Agent B — A2ASentinel Demo",
        description="Task-executing A2A agent with summarize_text and translate_text skills.",
        version="1.0.0",
    )

    # 1. Create the AgentCard (protobuf, used by both the card endpoint
    #    and the request handler)
    agent_card = create_agent_b_card()

    # 2. Create the executor (our canned-response implementation)
    executor = AgentBExecutor()

    # 3. Create an in-memory task store (no persistence needed for demo)
    task_store = InMemoryTaskStore()

    # 4. Create the DefaultRequestHandler (= DefaultRequestHandlerV2)
    #    Constructor signature: (agent_executor, task_store, agent_card)
    #    queue_manager is optional and deprecated in v2 — omitted.
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=task_store,
        agent_card=agent_card,
    )

    # 5. Create route collections
    #    - Agent card routes: serves GET /.well-known/agent-card.json
    #    - JSON-RPC routes: handles POST / for message/send, tasks/get, etc.
    card_routes = create_agent_card_routes(agent_card=agent_card)
    jsonrpc_routes = create_jsonrpc_routes(
        request_handler=request_handler,
        rpc_url="/",
    )

    # 6. Mount all A2A routes onto the FastAPI app
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=card_routes,
        jsonrpc_routes=jsonrpc_routes,
    )

    logger.info(
        "Agent B configured with skills: summarize_text, translate_text"
    )
    return app


# Module-level app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    logger.info("Starting Agent B on %s:%d", AGENT_B_HOST, AGENT_B_PORT)
    uvicorn.run(
        "agent_b.server:app",
        host=AGENT_B_HOST,
        port=AGENT_B_PORT,
        log_level="info",
    )
