import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from server import handle_request
except Exception as e:
    print(f"Import error: {e}")
    # Create a fallback handler
    def handle_request(body):
        return {"status": "error", "message": "Server not initialized"}

def handler(event, context):
    """Vercel serverless function handler"""
    try:
        print(f"Received event: {event['httpMethod']} {event.get('path', '/')}")
        
        # Handle CORS preflight
        if event['httpMethod'] == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
                },
                'body': ''
            }
        
        # Handle GET requests
        if event['httpMethod'] == 'GET':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'AliceBlue Trading API',
                    'status': 'active',
                    'version': '1.0.0',
                    'usage': 'Send POST requests to /api with JSON body containing "action" and "params"'
                })
            }
        
        # Handle POST requests
        if event['httpMethod'] == 'POST':
            # Parse request body
            body = {}
            if event.get('body'):
                try:
                    if event.get('isBase64Encoded'):
                        import base64
                        body_str = base64.b64decode(event['body']).decode('utf-8')
                    else:
                        body_str = event['body']
                    body = json.loads(body_str)
                except Exception as e:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({'error': 'Invalid JSON body'})
                    }
            
            # Process the request
            result = handle_request(body)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result)
            }
        
        # Method not allowed
        return {
            'statusCode': 405,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Method not allowed'})
        }
            
    except Exception as e:
        print(f"Error in handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }