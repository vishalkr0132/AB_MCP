import os
import sys
import json

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from server import mcp
except ImportError as e:
    print(f"Import error: {e}")
    # Create a simple fallback
    mcp = None

def handler(request):
    """Vercel serverless function handler"""
    try:
        # Handle different HTTP methods
        if request.method == 'POST':
            try:
                body = request.get_json()
            except:
                body = None
                
            if body and 'method' in body and mcp:
                # Process MCP request
                result = mcp.handle_request(body)
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps(result)
                }
        
        # Return simple response for all requests
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'AliceBlue MCP Server is running',
                'status': 'active',
                'endpoints': {
                    'POST': 'Send MCP requests with JSON body'
                }
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }