"""
Lambda function to trigger App Runner research endpoint.
Called by EventBridge on a schedule (every 5 hours).

Alternates between job discovery and market research modes.
"""
import os
import urllib.request
import json
from datetime import datetime


def handler(event, context):
    """
    Trigger the research endpoint on App Runner.
    Alternates between job discovery and market research based on the hour.
    """
    
    app_runner_url = os.environ.get('APP_RUNNER_URL')
    if not app_runner_url:
        raise ValueError("APP_RUNNER_URL environment variable not set")
    
    # Remove any protocol if included
    if app_runner_url.startswith('https://'):
        app_runner_url = app_runner_url.replace('https://', '')
    elif app_runner_url.startswith('http://'):
        app_runner_url = app_runner_url.replace('http://', '')
    
    url = f"https://{app_runner_url}/research"
    
    # Determine which mode to run based on hour of day
    # Even hours (0, 2, 4, ...) = job discovery
    # Odd hours (1, 3, 5, ...) = market research
    current_hour = datetime.utcnow().hour
    
    if current_hour % 2 == 0:
        # Job discovery mode
        topic = "Discover new software engineering and data science job listings from Indeed. Navigate to Indeed.com, search for 'software engineer' jobs, and extract 5-10 job listings with store_discovered_job()."
        mode = "job_discovery"
    else:
        # Market research mode (default)
        topic = ""  # Let agent pick a topic
        mode = "market_research"
    
    print(f"Running in {mode} mode at hour {current_hour} UTC")
    
    try:
        # Create POST request with topic
        payload = {"topic": topic} if topic else {}
        request_body = json.dumps(payload).encode('utf-8')
        http_request = urllib.request.Request(
            url, 
            data=request_body,
            method='POST',
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(http_request, timeout=270) as response:
            result = response.read().decode('utf-8')
            print(f"Research triggered successfully ({mode}): {result}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Research triggered successfully ({mode})',
                    'mode': mode,
                    'result': result
                })
            }
    except Exception as e:
        print(f"Error triggering research: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'mode': mode
            })
        }