import hashlib
import json

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

# --- 1. Exam email ---
NORMALIZED_EMAIL = "24f1000557@ds.study.iitm.ac.in"

# --- 2. MCP server ---
# transport_security is passed HERE, not to streamable_http_app().
mcp = FastMCP(
    "iitm-live-mcp-server",
    transport_security=TransportSecuritySettings(
        allowed_hosts=[
            "tds-14.onrender.com",
            "tds-14.onrender.com:*",
            "localhost",
            "localhost:*",
            "127.0.0.1",
            "127.0.0.1:*",
        ],
    ),
)

# --- 3. Shared store: MCP request id -> lowercase header dict ---
_request_headers: dict = {}


def _headers_from_scope(scope) -> dict:
    out = {}
    for k, v in scope.get("headers", []):
        try:
            out[k.decode("latin-1").lower()] = v.decode("latin-1")
        except Exception:
            pass
    return out


# --- 4. Middleware: capture headers + JSON-RPC id, replay body unchanged ---
class HeaderCaptureMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Only intercept POST /mcp. Leave GET (SSE stream) and /health alone.
        if scope["type"] != "http" or scope.get("path") != "/mcp" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        headers = _headers_from_scope(scope)

        # Drain body so we can parse the JSON-RPC id.
        body = b""
        more_body = True
        while more_body:
            msg = await receive()
            body += msg.get("body", b"")
            more_body = msg.get("more_body", False)

        req_id = None
        try:
            payload = json.loads(body) if body else None
            if isinstance(payload, dict):
                req_id = payload.get("id")
        except Exception:
            pass

        if req_id is not None:
            _request_headers[str(req_id)] = headers

        # Replay the body once, then pass through to the real receive.
        replayed = False

        async def replay_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)


# --- 5. Tool ---
@mcp.tool()
async def solve_challenge(ctx: Context) -> str:
    """Compute the required hash from the challenge header."""
    # Look up the id defensively — different mcp versions expose it differently.
    req_id = getattr(ctx, "request_id", None)
    if req_id is None:
        rc = getattr(ctx, "request_context", None)
        if rc is not None:
            req_id = getattr(rc, "request_id", None)

    headers = _request_headers.get(str(req_id), {}) if req_id is not None else {}
    challenge = headers.get("x-exam-challenge", "")
    if not challenge:
        raise ValueError(
            f"Missing X-Exam-Challenge header (req_id={req_id}, "
            f"captured={sorted(headers.keys())})"
        )

    raw_string = f"{challenge}:{NORMALIZED_EMAIL}"
    return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()[:16]


# --- 6. Health check ---
async def health(request: Request):
    return JSONResponse({"status": "ok"})


# --- 7. App ---
mcp_app = mcp.streamable_http_app()

app = Starlette(
    lifespan=mcp_app.router.lifespan_context,
    middleware=[Middleware(HeaderCaptureMiddleware)],
    routes=[
        Route("/health", health),
        Mount("/", app=mcp_app),
    ],
)
