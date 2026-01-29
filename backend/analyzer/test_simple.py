#!/usr/bin/env python3
"""
Simple test for Analyzer agent - Gap Analysis and CV Rewriting
"""

import asyncio
import json
from dotenv import load_dotenv

load_dotenv(override=True)

import sys
import os
# Add database directory to path so 'src' module can be found
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../database")))

from src import Database
from src.schemas import JobCreate
from lambda_handler import lambda_handler


def test_analyzer():
    """Test the analyzer agent with CV vs Job gap analysis"""
    
    # Create a real job in the database
    db = Database()
    job_create = JobCreate(
        clerk_user_id="test_user_001",
        job_type="gap_analysis",
        request_payload={"test": True}
    )
    job_id = db.jobs.create(job_create.model_dump())
    print(f"Created test job: {job_id}")
    
    # Sample CV profile (as if extracted by Extractor agent)
    sample_cv_profile = {
        "name": "John Smith",
        "email": "john.smith@email.com",
        "summary": "Experienced software engineer with 8 years building scalable applications",
        "skills": [
            {"name": "Python", "proficiency": "expert", "years": 6, "evidence": "Led Python-based microservices"},
            {"name": "AWS", "proficiency": "proficient", "years": 4, "evidence": "Deployed to AWS"},
            {"name": "Docker", "proficiency": "proficient", "years": 3, "evidence": "Containerized applications"}
        ],
        "experience": [
            {
                "company": "TechCorp Inc",
                "role": "Senior Software Engineer",
                "start_date": "2020-01",
                "end_date": "Present",
                "highlights": [
                    "Led migration of monolithic application to microservices",
                    "Reduced API latency by 40% through Redis caching"
                ],
                "technologies": ["Python", "AWS", "Docker", "Redis"]
            }
        ],
        "education": ["B.S. Computer Science, State University, 2016"]
    }
    
    # Sample job profile (as if extracted by Extractor agent)
    sample_job_profile = {
        "company": "TechCo",
        "role_title": "Senior Software Engineer",
        "seniority": "senior",
        "location": "San Francisco, CA",
        "remote_policy": "hybrid",
        "must_have": [
            {"text": "5+ years Python experience", "type": "must_have", "category": "technical"},
            {"text": "Experience with Kubernetes", "type": "must_have", "category": "technical"},
            {"text": "Strong distributed systems knowledge", "type": "must_have", "category": "technical"}
        ],
        "nice_to_have": [
            {"text": "Experience with Kafka", "type": "nice_to_have", "category": "technical"},
            {"text": "Machine learning experience", "type": "nice_to_have", "category": "technical"}
        ],
        "responsibilities": [
            "Design and implement scalable microservices",
            "Lead technical design reviews"
        ],
        "ats_keywords": ["Python", "Kubernetes", "AWS", "Microservices", "Docker"]
    }
    
    test_event = {
        "type": "gap_analysis",
        "job_id": job_id,
        "cv_profile": sample_cv_profile,
        "job_profile": sample_job_profile
    }
    
    print("Testing Analyzer Agent - Gap Analysis...")
    print("=" * 60)
    
    result = lambda_handler(test_event, None)
    
    print(f"Status Code: {result['statusCode']}")
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', False)}")
        
        if body.get('gap_analysis'):
            gap = body['gap_analysis']
            print(f"\n📊 Gap Analysis Results:")
            print(f"   Fit Score: {gap.get('fit_score', 'N/A')}%")
            print(f"   ATS Score: {gap.get('ats_score', 'N/A')}%")
            print(f"   Summary: {gap.get('summary', 'N/A')[:100]}...")
            
            if gap.get('strengths'):
                print(f"\n   ✅ Strengths ({len(gap['strengths'])}):")
                for s in gap['strengths'][:3]:
                    print(f"      - {s[:60]}...")
            
            if gap.get('gaps'):
                print(f"\n   ⚠️  Gaps ({len(gap['gaps'])}):")
                for g in gap['gaps'][:3]:
                    if isinstance(g, dict):
                        print(f"      - {g.get('requirement', 'N/A')[:50]} ({g.get('severity', 'N/A')})")
                    else:
                        print(f"      - {g}")
            
            if gap.get('action_items'):
                print(f"\n   📋 Action Items ({len(gap['action_items'])}):")
                for a in gap['action_items'][:3]:
                    print(f"      - {a[:60]}...")
    else:
        print(f"Error: {result['body']}")
    
    # Clean up - delete the test job
    db.jobs.delete(job_id)
    print(f"\nDeleted test job: {job_id}")
    
    print("=" * 60)


def test_analyzer_cv_rewrite():
    """Test the analyzer agent CV rewrite capability"""
    
    db = Database()
    job_create = JobCreate(
        clerk_user_id="test_user_001",
        job_type="cv_rewrite",
        request_payload={"test": True}
    )
    job_id = db.jobs.create(job_create.model_dump())
    
    sample_cv_profile = {
        "name": "John Smith",
        "summary": "Software engineer with experience",
        "skills": [{"name": "Python", "proficiency": "expert", "years": 6}],
        "experience": [{
            "company": "TechCorp",
            "role": "Developer",
            "highlights": ["Built systems", "Worked on projects"]
        }]
    }
    
    sample_job_profile = {
        "company": "TechCo",
        "role_title": "Senior Software Engineer",
        "must_have": [{"text": "Python experience", "type": "must_have", "category": "technical"}],
        "ats_keywords": ["Python", "AWS", "Microservices"]
    }
    
    sample_gap_analysis = {
        "fit_score": 75,
        "ats_score": 60,
        "summary": "Good technical fit with some gaps",
        "strengths": ["Strong Python skills"],
        "gaps": [{"requirement": "AWS experience", "severity": "medium", "recommendation": "Highlight cloud experience"}],
        "action_items": ["Emphasize cloud experience", "Add metrics to achievements"],
        "keywords_present": ["Python"],
        "keywords_missing": ["AWS", "Microservices"]
    }
    
    test_event = {
        "type": "cv_rewrite",
        "job_id": job_id,
        "cv_profile": sample_cv_profile,
        "job_profile": sample_job_profile,
        "gap_analysis": sample_gap_analysis
    }
    
    print("\nTesting Analyzer Agent - CV Rewrite...")
    print("=" * 60)
    
    result = lambda_handler(test_event, None)
    
    print(f"Status Code: {result['statusCode']}")
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', False)}")
        
        if body.get('cv_rewrite'):
            rewrite = body['cv_rewrite']
            print(f"\n📝 CV Rewrite Results:")
            
            if rewrite.get('rewritten_summary'):
                print(f"   New Summary: {rewrite['rewritten_summary'][:100]}...")
            
            if rewrite.get('rewritten_bullets'):
                print(f"\n   Rewritten Bullets ({len(rewrite['rewritten_bullets'])}):")
                for b in rewrite['rewritten_bullets'][:3]:
                    print(f"      - {b[:70]}...")
            
            if rewrite.get('skills_to_highlight'):
                print(f"\n   Skills to Highlight: {', '.join(rewrite['skills_to_highlight'][:5])}")
    else:
        print(f"Error: {result['body']}")
    
    db.jobs.delete(job_id)
    print(f"\nDeleted test job: {job_id}")
    print("=" * 60)


if __name__ == "__main__":
    test_analyzer()
    test_analyzer_cv_rewrite()