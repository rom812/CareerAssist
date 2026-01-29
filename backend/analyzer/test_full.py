#!/usr/bin/env python3
"""
Full test for Analyzer agent via Lambda
"""

import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../database")))

from src import Database


def test_analyzer_lambda():
    """Test the Analyzer agent via Lambda invocation"""
    
    db = Database()
    lambda_client = boto3.client('lambda')
    
    # Sample CV and job profiles for gap analysis
    sample_cv_profile = {
        "name": "Jane Doe",
        "summary": "Full-stack developer with 6 years of experience",
        "skills": [
            {"name": "React", "proficiency": "expert", "years": 5},
            {"name": "Node.js", "proficiency": "proficient", "years": 4},
            {"name": "PostgreSQL", "proficiency": "proficient", "years": 3}
        ],
        "experience": [
            {
                "company": "WebAgency",
                "role": "Lead Developer",
                "highlights": ["Built 15+ client websites", "Reduced load times by 60%"]
            }
        ]
    }
    
    sample_job_profile = {
        "company": "BigTech Corp",
        "role_title": "Senior Full-Stack Engineer",
        "must_have": [
            {"text": "5+ years React experience", "type": "must_have", "category": "technical"},
            {"text": "Experience with TypeScript", "type": "must_have", "category": "technical"}
        ],
        "ats_keywords": ["React", "TypeScript", "Node.js", "AWS"]
    }
    
    print("Testing Analyzer Lambda - Gap Analysis")
    print("=" * 60)
    
    try:
        response = lambda_client.invoke(
            FunctionName='career-analyzer',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'type': 'gap_analysis',
                'job_id': 'test-job-lambda',
                'cv_profile': sample_cv_profile,
                'job_profile': sample_job_profile
            })
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Lambda Response Status: {result.get('statusCode')}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            if body.get('gap_analysis'):
                gap = body['gap_analysis']
                print(f"✅ Gap Analysis Completed")
                print(f"   Fit Score: {gap.get('fit_score')}%")
                print(f"   ATS Score: {gap.get('ats_score')}%")
                print(f"   Gaps Found: {len(gap.get('gaps', []))}")
                print(f"   Strengths: {len(gap.get('strengths', []))}")
            else:
                print(f"❌ No gap analysis in response")
        else:
            print(f"❌ Lambda returned error: {result.get('body')}")
                
    except Exception as e:
        print(f"Error invoking Lambda: {e}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_analyzer_lambda()