#!/usr/bin/env python3
"""
Simple test for Interviewer agent - Interview Question Generation and Answer Evaluation
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


def test_interviewer():
    """Test the interviewer agent with interview prep generation"""
    
    # Create a real job in the database
    db = Database()
    job_create = JobCreate(
        clerk_user_id="test_user_001",
        job_type="interview_prep",
        request_payload={"test": True}
    )
    job_id = db.jobs.create(job_create.model_dump())
    print(f"Created test job: {job_id}")
    
    # Sample job profile for interview question generation
    sample_job_profile = {
        "company": "TechCo",
        "role_title": "Senior Software Engineer",
        "seniority": "senior",
        "must_have": [
            {"text": "5+ years Python experience", "type": "must_have", "category": "technical"},
            {"text": "Experience with Kubernetes", "type": "must_have", "category": "technical"},
            {"text": "Team leadership experience", "type": "must_have", "category": "soft_skill"}
        ],
        "responsibilities": [
            "Design and implement scalable microservices",
            "Lead technical design reviews",
            "Mentor junior developers"
        ]
    }
    
    # Optional CV profile for personalized questions
    sample_cv_profile = {
        "name": "John Smith",
        "summary": "Experienced software engineer with 8 years building scalable applications",
        "skills": [
            {"name": "Python", "proficiency": "expert", "years": 6},
            {"name": "AWS", "proficiency": "proficient", "years": 4}
        ],
        "experience": [
            {
                "company": "TechCorp Inc",
                "role": "Senior Software Engineer",
                "highlights": ["Led migration to microservices", "Mentored team of 4"]
            }
        ]
    }
    
    test_event = {
        "type": "interview_prep",
        "job_id": job_id,
        "job_profile": sample_job_profile,
        "cv_profile": sample_cv_profile
    }
    
    print("Testing Interviewer Agent - Interview Prep...")
    print("=" * 60)
    
    result = lambda_handler(test_event, None)
    
    print(f"Status Code: {result['statusCode']}")
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', False)}")
        
        if body.get('interview_pack'):
            pack = body['interview_pack']
            print(f"\n🎯 Interview Prep Pack:")
            print(f"   Job ID: {pack.get('job_id', 'N/A')}")
            
            if pack.get('questions'):
                print(f"\n   📋 Questions Generated ({len(pack['questions'])}):")
                for i, q in enumerate(pack['questions'][:5], 1):
                    if isinstance(q, dict):
                        print(f"\n   {i}. [{q.get('type', 'N/A')}] {q.get('question', 'N/A')[:70]}...")
                        print(f"      Topic: {q.get('topic', 'N/A')}")
                        print(f"      Difficulty: {q.get('difficulty', 'N/A')}")
                        if q.get('what_theyre_testing'):
                            print(f"      Testing: {q.get('what_theyre_testing')[:60]}...")
                    else:
                        print(f"   {i}. {q}")
            
            if pack.get('focus_areas'):
                print(f"\n   🎯 Focus Areas: {', '.join(pack['focus_areas'][:5])}")
            
            if pack.get('company_specific_tips'):
                print(f"\n   💡 Company Tips ({len(pack['company_specific_tips'])}):")
                for tip in pack['company_specific_tips'][:3]:
                    print(f"      - {tip[:70]}...")
    else:
        print(f"Error: {result['body']}")
    
    # Clean up - delete the test job
    db.jobs.delete(job_id)
    print(f"\nDeleted test job: {job_id}")
    
    print("=" * 60)


def test_answer_evaluation():
    """Test the interviewer agent answer evaluation"""
    
    sample_question = {
        "id": "q1",
        "question": "Tell me about a time you had to lead a difficult technical migration",
        "type": "behavioral",
        "topic": "leadership",
        "difficulty": "medium",
        "what_theyre_testing": "Leadership skills, technical decision making, communication",
        "sample_answer_outline": "Use STAR method: describe the situation and challenge, your specific role and responsibilities, the actions you took to lead the migration, and the measurable results achieved.",
        "follow_up_questions": ["What would you do differently?", "How did you handle resistance from the team?"]
    }
    
    sample_answer = """
    At TechCorp, I led the migration of our monolithic application to microservices.
    
    Situation: We had a 5-year-old monolith that was becoming increasingly difficult to deploy and scale.
    
    Task: I was asked to lead a team of 4 engineers to break it into microservices without disrupting our 
    100K daily active users.
    
    Action: I started by mapping all dependencies and identifying the bounded contexts. We used the strangler 
    pattern to gradually extract services. I held weekly architecture reviews and created detailed runbooks 
    for each migration step.
    
    Result: Over 6 months, we successfully migrated to 12 microservices. Deployment frequency increased by 
    300% and we reduced incident response time by 50%.
    """
    
    test_event = {
        "type": "answer_evaluation",
        "question": sample_question,
        "answer": sample_answer
    }
    
    print("\nTesting Interviewer Agent - Answer Evaluation...")
    print("=" * 60)
    
    result = lambda_handler(test_event, None)
    
    print(f"Status Code: {result['statusCode']}")
    
    if result['statusCode'] == 200:
        body = json.loads(result['body'])
        print(f"Success: {body.get('success', False)}")
        
        if body.get('evaluation'):
            eval_result = body['evaluation']
            print(f"\n📊 Answer Evaluation:")
            print(f"   Overall Score: {eval_result.get('score', 'N/A')}/5")
            print(f"   STAR Method Used: {'✅ Yes' if eval_result.get('star_method_used') else '❌ No'}")
            print(f"   Clarity: {eval_result.get('clarity', 'N/A')}/5")
            print(f"   Relevance: {eval_result.get('relevance', 'N/A')}/5")
            print(f"   Depth: {eval_result.get('depth', 'N/A')}/5")
            
            if eval_result.get('strengths'):
                print(f"\n   ✅ Strengths:")
                for s in eval_result['strengths'][:3]:
                    print(f"      - {s[:70]}...")
            
            if eval_result.get('improvements'):
                print(f"\n   📈 Areas for Improvement:")
                for i in eval_result['improvements'][:3]:
                    print(f"      - {i[:70]}...")
    else:
        print(f"Error: {result['body']}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_interviewer()
    test_answer_evaluation()