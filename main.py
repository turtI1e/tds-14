import os
import hashlib
from mcp.server.fastmcp import FastMCP, Context

# Initialize FastMCP. 
# The default streamable_http_path is already "/mcp", so we don't need to specify it.
mcp = FastMCP("TDS-Q14-Server")

@mcp.tool()
def solve_challenge(ctx: Context) -> str:
    """
    Reads the X-Exam-Challenge header, hashes it with the email,
    and returns the first 16 hex characters.
    """
    request = ctx.request_context.request
    challenge = request.headers.get("X-Exam-Challenge", "")
    
    email = "24f1000557@ds.study.iitm.ac.in"
    
    if not challenge:
        return "Error: Missing X-Exam-Challenge header"
        
    text_to_hash = f"{challenge}:{email}"
    hashed = hashlib.sha256(text_to_hash.encode('utf-8')).hexdigest()
    
    return hashed[:16]

if __name__ == "__main__":
    # Use the built-in runner. 
    # It automatically binds to 0.0.0.0, uses the PORT env var, and serves at /mcp.
    mcp.run(transport="streamable-http")
