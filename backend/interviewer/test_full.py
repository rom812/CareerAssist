#!/usr/bin/env python3
"""
Full test for Interviewer agent via Lambda
"""

import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../database")))

from src import Database


def test_interviewer_lambda():
    """Test the Interviewer agent via Lambda invocation"""
    
    db = Database()
    lambda_client = boto3.client('lambda')
    
    sample_job_profile = {
        "company": "TechCo",
        "role_title": "Senior Software Engineer",
        "seniority": "senior",
        "must_have": [
            {"text": "5+ years Python experience", "type": "must_have", "category": "technical"},
            {"text": "Experience with Kubernetes", "type": "must_have", "category": "technical"}
        ],
        "responsibilities": [
            "Design and implement scalable microservices",
            "Lead technical design reviews"
        ]
    }
    
    print("Testing Interviewer Lambda - Interview Prep")
    print("=" * 60)
    
    try:
        response = lambda_client.invoke(
            FunctionName='career-interviewer',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'type': 'interview_prep',
                'job_id': 'test-job-lambda',
                'job_profile': sample_job_profile
            })
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Lambda Response Status: {result.get('statusCode')}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            if body.get('interview_pack'):
                pack = body['interview_pack']
                print(f"✅ Interview Pack Generated")
                print(f"   Questions: {len(pack.get('questions', []))}")
                print(f"   Focus Areas: {len(pack.get('focus_areas', []))}")
                
                if pack.get('questions'):
                    print(f"\n   Sample Questions:")
                    for q in pack['questions'][:3]:
                        if isinstance(q, dict):
                            print(f"      - [{q.get('type')}] {q.get('question', '')[:50]}...")
            else:
                print(f"❌ No interview pack in response")
        else:
            print(f"❌ Lambda returned error: {result.get('body')}")
                
    except Exception as e:
        print(f"Error invoking Lambda: {e}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_interviewer_lambda()