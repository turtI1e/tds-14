import hashlib
import os
from contextvars import ContextVar
from typing import Any

from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request

# --- 1. Configure your exam email ---
# This MUST be your registered exam email, exactly as given in the assignment.
NORMALIZED_EMAIL = "24f1000557@ds.study.iitm.ac.in"  # trimmed and lowercased

# --- 2. Create the MCP server instance ---
# FastMCP is a high-level wrapper that makes building MCP servers easy.
mcp = FastMCP("iitm-live-mcp-server")

# --- 3. Create a place to store the current request's headers ---
# MCP tools are called per-request. We need a way to access the HTTP headers
# of the *current* request from inside the tool function.
# A ContextVar is the correct, thread-safe way to do this.
_http_request_var: ContextVar[Request] = ContextVar("http_request")


# --- 4. Define the tool ---
@mcp.tool()
async def solve_challenge() -> str:
    """
    Compute the required hash from the challenge header.
    This tool takes NO arguments (input schema has no required properties).
    """
    # 4a. Retrieve the current HTTP request from the ContextVar.
    request = _http_request_var.get()
    if request is None:
        raise RuntimeError("No HTTP request context available")

    # 4b. Read the challenge header. This is the core requirement:
    #     read the challenge from the HTTP header, NOT the JSON body.
    challenge = request.headers.get("X-Exam-Challenge")
    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    # (Optional) You could also read the timestamp and signature here
    # for verification, but the assignment says signature verification is optional.
    # timestamp = request.headers.get("X-Exam-Timestamp")
    # signature = request.headers.get("X-Exam-Signature")

    # 4c. Compute SHA-256 of the string: "<challenge>:<normalizedEmail>"
    raw_string = f"{challenge}:{NORMALIZED_EMAIL}"
    hash_hex = hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

    # 4d. Return the first 16 lowercase hex characters.
    return hash_hex[:16]


# --- 5. Wire up the HTTP request context ---
# When FastMCP runs over Streamable HTTP, it does not automatically expose
# the raw Starlette Request object to tools. We use a small piece of
# middleware to capture the request and store it in our ContextVar
# *before* the tool is called.
async def http_middleware(request: Request, call_next):
    """Middleware to make the current HTTP request available to tools."""
    token = _http_request_var.set(request)
    try:
        response = await call_next(request)
    finally:
        _http_request_var.reset(token)
    return response


# --- 6. Create the final ASGI application ---
# FastMCP can produce a Starlette app that serves the MCP endpoint.
# We add our middleware to capture headers.
app = mcp.streamable_http_app(middleware=[http_middleware])


# --- 7. Health check endpoint (optional but useful for deployment) ---
@app.get("/health")
async def health():
    return {"status": "ok"}
