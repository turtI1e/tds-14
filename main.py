import hashlib
from contextvars import ContextVar

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

# --- 1. Configure your exam email ---
NORMALIZED_EMAIL = "24f1000557@ds.study.iitm.ac.in"  # trimmed and lowercased

# --- 2. Create the MCP server instance ---
mcp = FastMCP("iitm-live-mcp-server")

# --- 3. ContextVar to hold the current HTTP request ---
_http_request_var: ContextVar[Request] = ContextVar("http_request")


# --- 4. Define the tool ---
@mcp.tool()
async def solve_challenge() -> str:
    """Compute the required hash from the challenge header."""
    request = _http_request_var.get()
    if request is None:
        raise RuntimeError("No HTTP request context available")

    challenge = request.headers.get("X-Exam-Challenge")
    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    raw_string = f"{challenge}:{NORMALIZED_EMAIL}"
    hash_hex = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()
    return hash_hex[:16]


# --- 5. Pure ASGI middleware to expose the request to tools ---
class RequestContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        token = _http_request_var.set(request)
        try:
            await self.app(scope, receive, send)
        finally:
            _http_request_var.reset(token)


# --- 6. Health check endpoint ---
async def health(request: Request):
    return JSONResponse({"status": "ok"})


# --- 7. Build the final ASGI application ---
mcp_app = mcp.streamable_http_app()

app = Starlette(
    # 🔑 THE FIX: Run the MCP app's lifespan so its session manager
    # (task group) is initialised before any request arrives.
    lifespan=mcp_app.router.lifespan_context,
    middleware=[Middleware(RequestContextMiddleware)],
    routes=[
        Route("/health", health),
        Mount("/", app=mcp_app),
    ],
)
