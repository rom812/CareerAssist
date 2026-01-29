#!/usr/bin/env python3
"""
Full test for Extractor agent via Lambda
"""

import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../database")))

from src import Database


def test_extractor_lambda():
    """Test the Extractor agent via Lambda invocation"""
    
    db = Database()
    lambda_client = boto3.client('lambda')
    
    # Sample CV for extraction
    sample_cv = """
    Jane Doe
    Email: jane.doe@email.com | Phone: (555) 987-6543
    
    SUMMARY
    Full-stack developer with 6 years of experience building web applications.
    Passionate about clean code and user experience.
    
    EXPERIENCE
    
    Lead Developer | WebAgency | 2021 - Present
    - Architected and deployed 15+ client websites using React and Node.js
    - Reduced page load times by 60% through optimization
    
    Frontend Developer | DigitalCo | 2018 - 2021
    - Built responsive UIs for e-commerce platforms
    - Integrated payment systems handling $2M+ monthly transactions
    
    SKILLS
    React, Node.js, TypeScript, PostgreSQL, AWS, Docker
    
    EDUCATION
    B.S. Computer Science | Tech University | 2018
    """
    
    print("Testing Extractor Lambda")
    print("=" * 60)
    print("Extracting CV profile...")
    
    # Invoke Lambda for CV extraction
    try:
        response = lambda_client.invoke(
            FunctionName='career-extractor',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'type': 'cv',
                'text': sample_cv
            })
        )
        
        result = json.loads(response['Payload'].read())
        print(f"\nLambda Response Status: {result.get('statusCode')}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            if body.get('cv_profile'):
                profile = body['cv_profile']
                print(f"✅ CV Extracted Successfully")
                print(f"   Name: {profile.get('name', 'N/A')}")
                print(f"   Skills: {len(profile.get('skills', []))} found")
                print(f"   Experience: {len(profile.get('experience', []))} entries")
            else:
                print(f"❌ No CV profile in response")
        else:
            print(f"❌ Lambda returned error: {result.get('body')}")
                
    except Exception as e:
        print(f"Error invoking Lambda: {e}")
    
    # Test job posting extraction
    sample_job = """
    Product Manager
    FinTech Startup | Remote
    
    We need a Product Manager to lead our mobile app team.
    
    Requirements:
    - 4+ years product management experience
    - Experience with agile methodologies
    - Strong analytical skills
    
    Salary: $150,000 - $180,000
    """
    
    print("\n" + "-" * 60)
    print("Extracting Job posting...")
    
    try:
        response = lambda_client.invoke(
            FunctionName='career-extractor',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'type': 'job',
                'text': sample_job
            })
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            if body.get('job_profile'):
                profile = body['job_profile']
                print(f"✅ Job Extracted Successfully")
                print(f"   Company: {profile.get('company', 'N/A')}")
                print(f"   Role: {profile.get('role_title', 'N/A')}")
                print(f"   Requirements: {len(profile.get('must_have', []))} found")
            else:
                print(f"❌ No job profile in response")
        else:
            print(f"❌ Lambda returned error")
            
    except Exception as e:
        print(f"Error invoking Lambda: {e}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_extractor_lambda()