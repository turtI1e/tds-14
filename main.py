import os
import hashlib
from mcp.server.fastmcp import FastMCP, Context

# Initialize FastMCP
mcp = FastMCP("TDS-Q14-Server")

# --- CRITICAL FIXES ---
# 1. Explicitly set the path to "/mcp" (this is the default, but we force it)
mcp.settings.streamable_http_path = "/mcp"
# 2. Enable stateless mode to handle Render's multiple workers
mcp.settings.stateless_http = True

@mcp.tool()
def solve_challenge(ctx: Context) -> str:
    request = ctx.request_context.request
    challenge = request.headers.get("X-Exam-Challenge", "")
    email = "24f1000557@ds.study.iitm.ac.in"
    if not challenge:
        return "Error: Missing X-Exam-Challenge header"
    text_to_hash = f"{challenge}:{email}"
    hashed = hashlib.sha256(text_to_hash.encode('utf-8')).hexdigest()
    return hashed[:16]

if __name__ == "__main__":
    # Run the server using the streamable-http transport
    mcp.run(transport="streamable-http")
