import os
import hashlib
from mcp.server.fastmcp import FastMCP, Context
from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn

# Initialize FastMCP
mcp = FastMCP("TDS-Q14-Server")

# Explicitly set the path for streamable HTTP to be just "/mcp"
mcp.settings.streamable_http_path = "/mcp"

@mcp.tool()
def solve_challenge(ctx: Context) -> str:
    """
    Reads the X-Exam-Challenge header, hashes it with the email,
    and returns the first 16 hex characters.
    """
    # Access the underlying Starlette HTTP request from the MCP Context
    request = ctx.request_context.request
    
    # Extract the challenge from the headers
    challenge = request.headers.get("X-Exam-Challenge", "")
    
    # Your normalized email
    email = "24f1000557@ds.study.iitm.ac.in"
    
    if not challenge:
        return "Error: Missing X-Exam-Challenge header"
        
    # Compute SHA-256("${challenge}:${email}")
    text_to_hash = f"{challenge}:{email}"
    hashed = hashlib.sha256(text_to_hash.encode('utf-8')).hexdigest()
    
    # Return the first 16 lowercase hex characters
    return hashed[:16]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    # Create the Starlette app and mount the MCP streamable HTTP app
    # This guarantees the route is available at /mcp
    app = Starlette(routes=[
        Mount("/", app=mcp.streamable_http_app())
    ])
    
    # Run the app with Uvicorn on the port Render assigns
    uvicorn.run(app, host="0.0.0.0", port=port)
