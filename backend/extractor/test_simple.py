#!/usr/bin/env python3
"""
Simple test for Extractor agent - CV and Job Parsing
"""


import asyncio
import json
from dotenv import load_dotenv

load_dotenv(override=True)

import sys
import os
# Add database directory to path so 'src' module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../database")))

from lambda_handler import lambda_handler


def test_extractor_cv():
    """Test the extractor agent with CV parsing"""
    
    sample_cv = """
    John Smith
    Email: john.smith@email.com | Phone: (555) 123-4567
    LinkedIn: linkedin.com/in/johnsmith
    
    SUMMARY
    Experienced software engineer with 8 years building scalable web applications
    and distributed systems. Expert in Python and cloud infrastructure.
    
    EXPERIENCE
    
    Senior Software Engineer | TechCorp Inc | 2020 - Present
    - Led migration of monolithic application to microservices, improving deployment frequency by 300%
    - Reduced API latency by 40% through Redis caching implementation
    - Mentored team of 4 junior developers
    
    Software Engineer | StartupXYZ | 2017 - 2020
    - Built real-time data pipeline processing 1M+ events/day using Kafka and Spark
    - Designed and implemented REST APIs serving 10K requests/second
    
    SKILLS
    Python, JavaScript, AWS, Kubernetes, Docker, PostgreSQL, Redis, Kafka
    
    EDUCATION
    B.S. Computer Science | State University | 2016
    """
    
    test_event = {
        "type": "cv",
        "text": sample_cv
    }
    
    print("Testing Extractor Agent - CV Parsing...")
    print("=" * 60)
    
    result = lambda_handler(test_event, None)
    
    print(f"Status Code: {result['statusCode']}")
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', False)}")
        
        if body.get('cv_profile'):
            profile = body['cv_profile']
            print(f"\nExtracted CV Profile:")
            print(f"  Name: {profile.get('name', 'N/A')}")
            print(f"  Email: {profile.get('email', 'N/A')}")
            print(f"  Skills: {len(profile.get('skills', []))} found")
            print(f"  Experience: {len(profile.get('experience', []))} entries")
            
            if profile.get('skills'):
                print(f"\n  Top Skills:")
                for skill in profile['skills'][:5]:
                    if isinstance(skill, dict):
                        print(f"    - {skill.get('name')}: {skill.get('proficiency', 'N/A')}")
                    else:
                        print(f"    - {skill}")
    else:
        print(f"Error: {result['body']}")
    
    print("=" * 60)


def test_extractor_job():
    """Test the extractor agent with job posting parsing"""
    
    sample_job = """
    Senior Backend Engineer
    TechCo Inc | San Francisco, CA (Hybrid)
    
    About the Role:
    We're looking for a Senior Backend Engineer to join our growing platform team.
    You'll be responsible for designing and implementing scalable microservices.
    
    Requirements:
    - 5+ years of experience in backend development
    - Strong proficiency in Python or Go
    - Experience with Kubernetes and container orchestration
    - Solid understanding of distributed systems
    - Experience with SQL and NoSQL databases
    
    Nice to Have:
    - Experience with Kafka or similar message queues
    - Knowledge of machine learning pipelines
    - Previous startup experience
    
    Salary: $180,000 - $220,000
    """
    
    test_event = {
        "type": "job",
        "text": sample_job
    }
    
    print("\nTesting Extractor Agent - Job Parsing...")
    print("=" * 60)
    
    result = lambda_handler(test_event, None)
    
    print(f"Status Code: {result['statusCode']}")
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', False)}")
        
        if body.get('job_profile'):
            profile = body['job_profile']
            print(f"\nExtracted Job Profile:")
            print(f"  Company: {profile.get('company', 'N/A')}")
            print(f"  Role: {profile.get('role_title', 'N/A')}")
            print(f"  Location: {profile.get('location', 'N/A')}")
            print(f"  Remote Policy: {profile.get('remote_policy', 'N/A')}")
            print(f"  Must Have: {len(profile.get('must_have', []))} requirements")
            print(f"  Nice to Have: {len(profile.get('nice_to_have', []))} requirements")
            print(f"  ATS Keywords: {profile.get('ats_keywords', [])[:5]}")
    else:
        print(f"Error: {result['body']}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_extractor_cv()
    test_extractor_job()