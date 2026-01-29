#!/usr/bin/env python3
"""
Simple test for Orchestrator agent - Career workflow coordination
"""

import asyncio
import json
import os
import subprocess
from dotenv import load_dotenv

load_dotenv(override=True)

import sys
import os
# Add database directory to path so 'src' module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../database")))

# Mock lambdas for testing
os.environ['MOCK_LAMBDAS'] = 'true'

from src import Database
from src.schemas import JobCreate


def setup_test_data():
    """Ensure test data exists and create a test job"""
    # Run reset_db with test data to ensure we have a test user
    print("Ensuring test data exists...")
    result = subprocess.run(
        ["uv", "run", "reset_db.py", "--with-test-data", "--skip-drop"],
        cwd="../database",
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Warning: Could not ensure test data: {result.stderr}")
    
    db = Database()
    
    # The reset_db script creates test_user_001
    test_user_id = "test_user_001"
    
    # Check if user exists
    user = db.users.find_by_clerk_id(test_user_id)
    if not user:
        raise ValueError(f"Test user {test_user_id} not found. Please run: cd ../database && uv run reset_db.py --with-test-data")
    
    # Create test job for CV analysis
    job_create = JobCreate(
        clerk_user_id=test_user_id,
        job_type="cv_analysis",
        request_payload={
            "analysis_type": "full",
            "include_gap_analysis": True,
            "include_cv_rewrite": True,
            "include_interview_prep": True,
            "test": True
        }
    )
    job_id = db.jobs.create(job_create.model_dump())
    
    return job_id


def test_orchestrator():
    """Test the orchestrator agent for career workflow coordination"""
    
    # Setup test data
    job_id = setup_test_data()
    
    test_event = {
        "job_id": job_id
    }
    
    print("Testing Orchestrator Agent - Career Workflow...")
    print(f"Job ID: {job_id}")
    print("=" * 60)
    
    from lambda_handler import lambda_handler
    
    result = lambda_handler(test_event, None)
    
    print(f"Status Code: {result['statusCode']}")
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', False)}")
        print(f"Message: {body.get('message', 'N/A')}")
        
        # Check what was produced
        if body.get('results'):
            results = body['results']
            print(f"\n📊 Orchestration Results:")
            
            if 'extraction' in results:
                print(f"   ✅ CV/Job Extraction: Complete")
            if 'gap_analysis' in results:
                gap = results['gap_analysis']
                print(f"   ✅ Gap Analysis: Fit Score {gap.get('fit_score', 'N/A')}%")
            if 'cv_rewrite' in results:
                print(f"   ✅ CV Rewrite: Generated")
            if 'interview_prep' in results:
                interview = results['interview_prep']
                q_count = len(interview.get('questions', []))
                print(f"   ✅ Interview Prep: {q_count} questions generated")
            if 'charts' in results:
                print(f"   ✅ Charts: Generated")
    else:
        print(f"Error: {result['body']}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_orchestrator()