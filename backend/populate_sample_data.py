
import os
import uuid
import json
import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

# Configuration
AURORA_CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN")
AURORA_SECRET_ARN = os.getenv("AURORA_SECRET_ARN")
DATABASE_NAME = os.getenv("DATABASE_NAME", "career")
AWS_REGION = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

if not AURORA_CLUSTER_ARN or not AURORA_SECRET_ARN:
    print("❌ Database credentials missing in .env")
    exit(1)

rds = boto3.client('rds-data', region_name=AWS_REGION)

def execute_sql(sql, params):
    try:
        response = rds.execute_statement(
            resourceArn=AURORA_CLUSTER_ARN,
            secretArn=AURORA_SECRET_ARN,
            database=DATABASE_NAME,
            sql=sql,
            parameters=params
        )
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def populate_sample_jobs():
    print("Populating sample discovered jobs...")
    
    jobs = [
        {
            "id": str(uuid.uuid4()),
            "source": "indeed",
            "source_job_id": "mock-job-1",
            "company_name": "Tech Corp AI",
            "role_title": "Senior AI Engineer",
            "location": "Remote",
            "remote_policy": "remote",
            "salary_min": 150000,
            "salary_max": 220000,
            "description_text": "We are looking for an experienced AI Engineer to lead our LLM initiatives...",
            "requirements_text": "Python, PyTorch, AWS, 5+ years experience"
        },
        {
            "id": str(uuid.uuid4()),
            "source": "glassdoor",
            "source_job_id": "mock-job-2",
            "company_name": "Data Systems Inc",
            "role_title": "Machine Learning Ops Engineer",
            "location": "New York, NY",
            "remote_policy": "hybrid",
            "salary_min": 140000,
            "salary_max": 190000,
            "description_text": "Join our MLOps team to build scalable inference pipelines...",
            "requirements_text": "Kubernetes, Docker, Python, MLflow"
        }
    ]
    
    for job in jobs:
        sql = """
        INSERT INTO discovered_jobs 
        (id, source, source_job_id, company_name, role_title, location, remote_policy, 
         salary_min, salary_max, description_text, requirements_text, is_active, created_at)
        VALUES 
        (:id::uuid, :source, :source_job_id, :company_name, :role_title, :location, :remote_policy,
         :salary_min, :salary_max, :description_text, :requirements_text, true, NOW())
        ON CONFLICT (source, source_job_id) DO UPDATE SET is_active = true
        """
        
        params = [
            {"name": "id", "value": {"stringValue": job["id"]}},
            {"name": "source", "value": {"stringValue": job["source"]}},
            {"name": "source_job_id", "value": {"stringValue": job["source_job_id"]}},
            {"name": "company_name", "value": {"stringValue": job["company_name"]}},
            {"name": "role_title", "value": {"stringValue": job["role_title"]}},
            {"name": "location", "value": {"stringValue": job["location"]}},
            {"name": "remote_policy", "value": {"stringValue": job["remote_policy"]}},
            {"name": "salary_min", "value": {"longValue": job["salary_min"]}},
            {"name": "salary_max", "value": {"longValue": job["salary_max"]}},
            {"name": "description_text", "value": {"stringValue": job["description_text"]}},
            {"name": "requirements_text", "value": {"stringValue": job["requirements_text"]}}
        ]
        
        if execute_sql(sql, params):
            print(f"✅ Added job: {job['role_title']} at {job['company_name']}")

def populate_sample_research():
    print("\nPopulating sample research findings...")
    
    findings = [
        {
            "id": str(uuid.uuid4()),
            "topic": "AI Trends 2026",
            "category": "role_trend",
            "title": "AI Engineering Demand Soars",
            "summary": "Demand for AI Engineers has increased by 40% in Q1 2026.",
            "content": "Full analysis of the AI job market showing significant growth in specialized roles...",
            "relevance_score": 95,
            "is_featured": True
        }
    ]
    
    for finding in findings:
        sql = """
        INSERT INTO research_findings 
        (id, topic, category, title, summary, content, relevance_score, is_featured, created_at)
        VALUES 
        (:id::uuid, :topic, :category, :title, :summary, :content, :relevance_score, :is_featured, NOW())
        """
        
        params = [
            {"name": "id", "value": {"stringValue": finding["id"]}},
            {"name": "topic", "value": {"stringValue": finding["topic"]}},
            {"name": "category", "value": {"stringValue": finding["category"]}},
            {"name": "title", "value": {"stringValue": finding["title"]}},
            {"name": "summary", "value": {"stringValue": finding["summary"]}},
            {"name": "content", "value": {"stringValue": finding["content"]}},
            {"name": "relevance_score", "value": {"longValue": finding["relevance_score"]}},
            {"name": "is_featured", "value": {"booleanValue": finding["is_featured"]}}
        ]
        
        if execute_sql(sql, params):
            print(f"✅ Added finding: {finding['title']}")

if __name__ == "__main__":
    populate_sample_jobs()
    populate_sample_research()
    print("\n✅ Database population complete!")
