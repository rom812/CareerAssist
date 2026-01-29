#!/usr/bin/env python3
"""Full end-to-end test via SQS for the CareerAssist platform"""

import os
import json
import boto3
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(override=True)

from database.src import Database, UserCreate

def setup_test_data(db):
    """Ensure test user and CV exist"""
    print("Setting up test data...")
    
    # Check/create test user
    test_user_id = 'test_user_001'
    user = db.user_profiles.find_by_clerk_id(test_user_id)
    if not user:
        user_data = UserCreate(
            clerk_user_id=test_user_id,
            display_name="Test User",
            email="testuser@example.com"
        )
        db.user_profiles.create_user(user_data)
        print(f"  ✓ Created test user: {test_user_id}")
    else:
        print(f"  ✓ Test user exists: {test_user_id}")
    
    return test_user_id

def main():
    print("=" * 70)
    print("🎯 Full End-to-End Test via SQS")
    print("=" * 70)
    
    db = Database()
    sqs = boto3.client('sqs')
    
    # Setup test data
    test_user_id = setup_test_data(db)
    
    # Create test job with sample data
    print("\nCreating analysis job...")
    
    # Sample CV data
    sample_cv = {
        "name": "John Smith",
        "email": "john.smith@example.com",
        "phone": "+1-555-0123",
        "summary": "Experienced software engineer with 8 years building scalable applications",
        "skills": [
            {"name": "Python", "proficiency": "expert", "years": 6},
            {"name": "JavaScript", "proficiency": "advanced", "years": 5},
            {"name": "AWS", "proficiency": "intermediate", "years": 3}
        ],
        "experience": [
            {
                "company": "Tech Corp",
                "role": "Senior Software Engineer",
                "start_date": "2020-01-01",
                "end_date": "2024-01-01",
                "highlights": ["Led development of microservices platform", "Reduced deployment time by 50%"]
            }
        ]
    }
    
    # Sample job posting data
    sample_job = {
        "company": "TechCo",
        "role_title": "Senior Full Stack Engineer",
        "location": "Remote",
        "must_have": [
            {"text": "5+ years Python experience", "type": "must_have", "category": "technical"},
            {"text": "Experience with cloud platforms", "type": "must_have", "category": "technical"}
        ],
        "nice_to_have": [
            {"text": "Kubernetes knowledge", "type": "nice_to_have", "category": "technical"}
        ],
        "ats_keywords": ["Python", "Kubernetes", "AWS", "Docker", "Microservices"]
    }
    
    job_data = {
        'clerk_user_id': test_user_id,
        'job_type': 'full_analysis',
        'status': 'pending',
        'input_data': {
            'cv_profile': sample_cv,
            'job_profile': sample_job
        },
        'request_payload': {
            'analysis_type': 'full',
            'requested_at': datetime.now(timezone.utc).isoformat(),
            'test_run': True,
            'include_interview_prep': True,
            'include_charts': True,
            'include_report': True
        }
    }
    
    job_id = db.jobs.create(job_data)
    print(f"  ✓ Created job: {job_id}")
    
    # Get queue URL
    QUEUE_NAME = 'career-analysis-jobs'
    response = sqs.list_queues(QueueNamePrefix=QUEUE_NAME)
    queue_url = None
    for url in response.get('QueueUrls', []):
        if QUEUE_NAME in url:
            queue_url = url
            break
    
    if not queue_url:
        print(f"  ❌ Queue {QUEUE_NAME} not found")
        return 1
    
    print(f"  ✓ Found queue: {QUEUE_NAME}")
    
    # Send message to SQS
    print("\nTriggering analysis via SQS...")
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps({'job_id': job_id})
    )
    print(f"  ✓ Message sent: {response['MessageId']}")
    
    # Monitor job progress
    print("\n⏳ Monitoring job progress...")
    print("-" * 50)
    
    start_time = time.time()
    timeout = 180  # 3 minutes
    last_status = None
    
    while time.time() - start_time < timeout:
        job = db.jobs.find_by_id(job_id)
        status = job['status']
        
        if status != last_status:
            elapsed = int(time.time() - start_time)
            print(f"[{elapsed:3d}s] Status: {status}")
            last_status = status
            
            if status == 'failed' and job.get('error_message'):
                print(f"       Error: {job.get('error_message')}")
        
        if status == 'completed':
            print("-" * 50)
            print("\n✅ Job completed successfully!")
            print("\n📊 Analysis Results:")
            
            # Report
            if job.get('report_payload'):
                report_content = job['report_payload'].get('content', '')
                print(f"\n📝 Report Generated:")
                print(f"   - Length: {len(report_content)} characters")
                print(f"   - Preview: {report_content[:200]}...")
            else:
                print("\n❌ No report found")
            
            # Charts
            if job.get('charts_payload'):
                charts = job['charts_payload']
                print(f"\n📊 Charts Created: {len(charts)} visualizations")
                for chart_key, chart_data in charts.items():
                    if isinstance(chart_data, dict):
                        title = chart_data.get('title', 'Untitled')
                        chart_type = chart_data.get('type', 'unknown')
                        data_points = len(chart_data.get('data', []))
                        print(f"   - {chart_key}: {title} ({chart_type}, {data_points} data points)")
            else:
                print("\n❌ No charts found")
            
            # Interview Prep
            if job.get('interview_payload'):
                interview = job['interview_payload']
                print(f"\n🎯 Interview Prep:")
                if isinstance(interview, dict):
                    if 'questions_count' in interview:
                        print(f"   - Questions Generated: {interview['questions_count']}")
                    if 'focus_areas' in interview:
                        print(f"   - Focus Areas: {', '.join(interview['focus_areas'])}")
                    if 'analysis' in interview:
                        print(f"   - Analysis Length: {len(interview['analysis'])} characters")
            else:
                print("\n❌ No interview prep found")
            
            # Summary
            if job.get('summary_payload'):
                summary = job['summary_payload']
                print(f"\n📋 Summary:")
                if isinstance(summary, dict):
                    for key, value in summary.items():
                        if key != 'timestamp':
                            print(f"   - {key}: {value}")
            
            break
        elif status == 'failed':
            print("-" * 50)
            print(f"\n❌ Job failed")
            if job.get('error_message'):
                print(f"Error details: {job['error_message']}")
            break
        
        time.sleep(2)
    else:
        print("-" * 50)
        print("\n❌ Job timed out after 3 minutes")
        print(f"Final status: {job['status']}")
        return 1
    
    print(f"\n📋 Job Details:")
    print(f"   - Job ID: {job_id}")
    print(f"   - User ID: {test_user_id}")
    print(f"   - Total Time: {int(time.time() - start_time)} seconds")
    
    return 0

if __name__ == "__main__":
    exit(main())