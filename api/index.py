from server import mcp
from fastmcp.server import FastMCP

def handler(request):
    """Vercel serverless function handler"""
    return mcp.handle_request(request)

# For local development
if __name__ == "__main__":
    import os
    app_key = os.getenv("ALICE_APP_KEY")
    api_secret = os.getenv("ALICE_API_SECRET")
    
    if not app_key or not api_secret:
        raise Exception("Missing credentials. Please set ALICE_APP_KEY and ALICE_API_SECRET in .env file")
    
    mcp.run(transport="stdio")