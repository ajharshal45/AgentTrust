# a2a-sdk Reference (verified against installed v1.1.4)

This is real, verified information from directly inspecting the installed
package at `/usr/local/lib/python3.12/dist-packages/a2a` — not assumed from
memory. Still explore further within these areas as needed, but this saves
re-discovering the basics.

## Package layout
```
a2a/
  auth/                 - auth helpers
  client/                - client-side: Client, ClientFactory, interceptors
    transports/
  compat/v0_3/types.py  - core Pydantic models (AgentCard, AgentSkill, etc.)
  server/
    agent_execution/agent_executor.py  - AgentExecutor abstract class
    routes/fastapi_routes.py           - add_a2a_routes_to_fastapi()
    routes/rest_routes.py, jsonrpc_routes.py
    tasks/, events/
  types/                 - protobuf-generated types (a2a_pb2)
```

## AgentCard (in `a2a.compat.v0_3.types` or wherever it's re-exported from
top-level `a2a` — check `a2a/__init__.py` re-exports first)

Key fields (confirmed from source):
```python
class AgentCard(A2ABaseModel):
    name: str
    url: str                              # e.g. "https://api.example.com/a2a/v1"
    version: str                          # e.g. "1.0.0"
    protocol_version: str | None = "0.3.0"
    description: str
    capabilities: AgentCapabilities
    skills: list[AgentSkill]
    default_input_modes: list[str]
    default_output_modes: list[str]
    security: list[dict[str, list[str]]] | None
    security_schemes: dict[str, SecurityScheme] | None
    signatures: list[AgentCardSignature] | None   # <-- the v1.0 signing mechanism
    provider: AgentProvider | None
    additional_interfaces: list[AgentInterface] | None
    preferred_transport: str | None
    supports_authenticated_extended_card: bool | None
```

## AgentCardSignature (JWS per RFC 7515)
```python
class AgentCardSignature(A2ABaseModel):
    header: dict[str, Any] | None
    protected: str      # Base64url-encoded JSON, the protected JWS header
    signature: str      # Base64url-encoded, the actual signature
```
This confirms signatures are real JWS objects — a standard, well-documented
format. Python's `jwcrypto` or `python-jose` can verify JWS if going for a
real (not simplified) implementation.

## AgentSkill
```python
class AgentSkill(A2ABaseModel):
    id: str
    name: str
    description: str
    examples: list[str] | None
    input_modes: list[str] | None
```
This is what a capability-match check should compare requested tasks against.

## AgentExecutor (server side — implement this for Agent B)
```python
from abc import ABC, abstractmethod
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue_v2 import EventQueue

class AgentExecutor(ABC):
    @abstractmethod
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Read from context, publish Task/Message events to event_queue."""
```
Key behavior notes from the source docstring:
- Framework guarantees single execution per request (no concurrency issues
  to worry about for the demo).
- On completion, should publish a `TaskStatusUpdateEvent` with a terminal
  state (e.g. `TASK_STATE_COMPLETED`).
- Simplest valid pattern for a demo: enqueue a single `Message` object for
  an immediate response.

## FastAPI integration (server side)
```python
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
# Signature/usage: explore this function's actual parameters directly —
# confirmed to exist, exact call signature not yet extracted. It attaches
# A2A protocol routes (agent card, jsonrpc/rest dispatch) onto a FastAPI app.
```

## Client (client side — implement this for Agent A)
```python
class Client(ABC):
    async def __aenter__(self) -> Self: ...
    async def send_message(...): ...
    async def get_task(...): ...
    async def list_tasks(...): ...
    async def cancel_task(...): ...
    async def get_extended_agent_card(...): ...
    async def add_interceptor(self, interceptor: ClientCallInterceptor) -> None: ...
```
**Important finding:** the SDK has a native `add_interceptor` hook taking a
`ClientCallInterceptor` (see `a2a/client/interceptors.py`). This is a
built-in extension point for exactly the kind of "inspect/modify a call
before it goes out" behavior A2ASentinel needs. Check `interceptors.py`
for the `ClientCallInterceptor` interface shape before deciding whether
to implement A2ASentinel as a client-side interceptor, FastAPI middleware
on the server side, or both.

## ClientFactory
```python
class ClientFactory:
    def __init__(...): ...
    def register(self, label: str, generator: TransportProducer) -> None: ...
    def create(...): ...

def minimal_agent_card(...) -> AgentCard:
    """Helper to quickly build a minimal AgentCard for testing — useful
    for the demo's legitimate/attacker persona setup."""
```

## What's still unverified — check these before assuming
- Exact call signature/parameters for `add_a2a_routes_to_fastapi(...)`
- Exact shape of `ClientCallInterceptor` in `client/interceptors.py`
- Whether `AgentCapabilities`, `SecurityScheme`, `AgentProvider` have
  required fields that must be filled for a minimal working AgentCard
- Whether there's an example/quickstart script bundled with the package
  (check for a `examples/` dir at the repo level, not just the installed
  package — the GitHub repo for `a2a-python` likely has one)
