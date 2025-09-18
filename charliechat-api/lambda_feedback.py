import json
import boto3
import os
from typing import Dict, Any

# Initialize SES client
ses_client = boto3.client('ses')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing feedback form submissions.
    
    Expected payload:
    {
        "feedback": "string (required)",
        "experience": "positive|neutral|negative (required)", 
        "name": "string (optional)"
    }
    """
    
    # Set CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight'})
        }
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Validate required fields
        feedback = body.get('feedback', '').strip()
        experience = body.get('experience', '').strip()
        name = body.get('name', '').strip()
        
        if not feedback:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Missing required field: feedback'
                })
            }
        
        if experience not in ['positive', 'neutral', 'negative']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Invalid experience value. Must be: positive, neutral, or negative'
                })
            }
        
        # Get environment variables
        sender_email = os.environ.get('FEEDBACK_SENDER_EMAIL')
        recipient_email = os.environ.get('FEEDBACK_RECIPIENT_EMAIL')
        
        if not sender_email or not recipient_email:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Email configuration missing'
                })
            }
        
        # Build email content
        name_display = name if name else 'N/A'
        experience_emoji = {
            'positive': '👍',
            'neutral': '😐', 
            'negative': '👎'
        }.get(experience, '❓')
        
        subject = f"Charlie Chat Feedback - {experience_emoji} {experience.title()}"
        
        email_body = f"""
New feedback received from Charlie Chat:

Feedback: {feedback}

Experience: {experience_emoji} {experience.title()}
Name: {name_display}

---
Sent from Charlie Chat feedback form
        """.strip()
        
        # Send email via SES
        response = ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [recipient_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Text': {'Data': email_body, 'Charset': 'UTF-8'}}
            }
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Feedback submitted successfully',
                'messageId': response['MessageId']
            })
        }
        
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': 'Invalid JSON in request body'
            })
        }
    except Exception as e:
        print(f"Error processing feedback: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error'
            })
        }
