import os
import hashlib
from mcp.server.fastmcp import FastMCP, Context

# Render assigns a random port, so we must use it
port = int(os.environ.get("PORT", 8000))

# Initialize the MCP server
mcp = FastMCP("TDS-Q14-Server", host="0.0.0.0", port=port)

@mcp.tool()
def solve_challenge(ctx: Context) -> str:
    """
    Reads the X-Exam-Challenge header, hashes it with the email,
    and returns the first 16 hex characters.
    """
    # 1. Access the underlying Starlette HTTP request from the MCP Context
    request = ctx.request_context.request
    
    # 2. Extract the challenge from the headers
    challenge = request.headers.get("X-Exam-Challenge", "")
    
    # Your normalized email
    email = "24f1000557@ds.study.iitm.ac.in"
    
    if not challenge:
        return "Error: Missing X-Exam-Challenge header"
        
    # 3. Compute SHA-256("${challenge}:${email}")
    text_to_hash = f"{challenge}:{email}"
    hashed = hashlib.sha256(text_to_hash.encode('utf-8')).hexdigest()
    
    # 4. Return the first 16 lowercase hex characters
    return hashed[:16]

if __name__ == "__main__":
    # Run the server using the SSE (Server-Sent Events) transport
    mcp.run(transport="sse")
