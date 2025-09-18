#!/usr/bin/env python3
"""
Test Lambda function to debug the Mangum issue
"""

import json
from mangum import Mangum
from app.main import app

# Create the ASGI handler for Lambda
handler = Mangum(app, lifespan="off")

def test_handler(event, context):
    """Test handler to debug the issue"""
    print(f"Event: {json.dumps(event, indent=2)}")
    print(f"Context: {context}")
    
    try:
        result = handler(event, context)
        print(f"Result: {result}")
        return result
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

if __name__ == "__main__":
    # Test with a sample API Gateway event
    test_event = {
        "version": "2.0",
        "routeKey": "GET /",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.5",
            "host": "charlesob.com",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"
        },
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "domainName": "charlesob.com",
            "http": {
                "method": "GET",
                "path": "/",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0"
            },
            "requestId": "test-request-id",
            "routeKey": "GET /",
            "stage": "$default",
            "time": "16/Sep/2025:21:30:00 +0000",
            "timeEpoch": 1758058200
        },
        "isBase64Encoded": False
    }
    
    test_context = type('Context', (), {
        'function_name': 'test-function',
        'function_version': '$LATEST',
        'invoked_function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:test-function',
        'memory_limit_in_mb': 128,
        'aws_request_id': 'test-request-id',
        'log_group_name': '/aws/lambda/test-function',
        'log_stream_name': '2025/09/16/[$LATEST]test-stream'
    })()
    
    result = test_handler(test_event, test_context)
    print(f"Final result: {json.dumps(result, indent=2)}")

