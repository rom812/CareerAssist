"""
Tools for the CareerAssist Researcher agent
"""
import os
import json
import uuid
from typing import Dict, Any, Literal
from datetime import datetime, UTC
import httpx
import boto3
from agents import function_tool
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration from environment
CAREER_API_ENDPOINT = os.getenv("CAREER_API_ENDPOINT")
CAREER_API_KEY = os.getenv("CAREER_API_KEY")

# Database configuration for storing research findings
AURORA_CLUSTER_ARN = os.getenv("AURORA_CLUSTER_ARN", "")
AURORA_SECRET_ARN = os.getenv("AURORA_SECRET_ARN", "")
DATABASE_NAME = os.getenv("DATABASE_NAME", "career")
AWS_REGION = os.getenv("DEFAULT_AWS_REGION", "us-east-1")

# Valid research finding categories
VALID_CATEGORIES = ["role_trend", "skill_demand", "salary_insight", "industry_news"]


def _get_rds_client():
    """Get RDS Data API client."""
    return boto3.client('rds-data', region_name=AWS_REGION)


def _execute_sql(sql: str, params: Dict[str, Any] = None) -> Dict:
    """Execute SQL via RDS Data API."""
    if not AURORA_CLUSTER_ARN or not AURORA_SECRET_ARN:
        raise ValueError("Aurora database not configured")
    
    rds = _get_rds_client()
    sql_params = []
    
    if params:
        for key, value in params.items():
            param = {"name": key}
            if value is None:
                param["value"] = {"isNull": True}
            elif isinstance(value, bool):
                param["value"] = {"booleanValue": value}
            elif isinstance(value, int):
                param["value"] = {"longValue": value}
            elif isinstance(value, float):
                param["value"] = {"doubleValue": value}
            elif isinstance(value, (dict, list)):
                param["value"] = {"stringValue": json.dumps(value)}
            else:
                param["value"] = {"stringValue": str(value)}
            sql_params.append(param)
    
    return rds.execute_statement(
        resourceArn=AURORA_CLUSTER_ARN,
        secretArn=AURORA_SECRET_ARN,
        database=DATABASE_NAME,
        sql=sql,
        parameters=sql_params
    )


def _ingest(document: Dict[str, Any]) -> Dict[str, Any]:
    """Internal function to make the actual API call."""
    with httpx.Client() as client:
        response = client.post(
            CAREER_API_ENDPOINT,
            json=document,
            headers={"x-api-key": CAREER_API_KEY},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def ingest_with_retries(document: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest with retry logic for SageMaker cold starts."""
    return _ingest(document)


@function_tool
def ingest_career_document(topic: str, analysis: str) -> Dict[str, Any]:
    """
    Ingest a career document into the CareerAssist knowledge base for RAG retrieval.
    
    Args:
        topic: The topic or subject of the content (e.g., "Interview Tips for Software Engineers", "ATS Optimization Guide")
        analysis: Detailed career advice, interview questions, or CV improvement tips
    
    Returns:
        Dictionary with success status and document ID
    """
    if not CAREER_API_ENDPOINT or not CAREER_API_KEY:
        return {
            "success": False,
            "error": "Career API not configured. Running in local mode."
        }
    
    document = {
        "text": analysis,
        "metadata": {
            "topic": topic,
            "timestamp": datetime.now(UTC).isoformat()
        }
    }
    
    try:
        result = ingest_with_retries(document)
        return {
            "success": True,
            "document_id": result.get("document_id"),  # Changed from documentId
            "message": f"Successfully ingested analysis for {topic}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Valid sources for job discovery
VALID_JOB_SOURCES = ["indeed", "glassdoor"]


@function_tool
def store_discovered_job(
    source: str,
    role_title: str,
    company_name: str,
    location: str = "",
    remote_policy: str = "",
    salary_min: int = 0,
    salary_max: int = 0,
    description_text: str = "",
    requirements_text: str = "",
    source_url: str = "",
    source_job_id: str = ""
) -> Dict[str, Any]:
    """
    Store a discovered job posting from Indeed or Glassdoor.
    Use this to save job listings found during job discovery scraping.
    
    Args:
        source: Job board source ('indeed' or 'glassdoor')
        role_title: Job title (e.g., "Senior Software Engineer")
        company_name: Company name (e.g., "Google")
        location: Job location (e.g., "San Francisco, CA")
        remote_policy: 'onsite', 'hybrid', 'remote', or empty string
        salary_min: Minimum salary if available (0 if not shown)
        salary_max: Maximum salary if available (0 if not shown)
        description_text: Full job description text
        requirements_text: Requirements/qualifications section
        source_url: URL to original job posting
        source_job_id: Unique ID from the source site (for deduplication)
    
    Returns:
        Dictionary with success status and job ID
    """
    # Validate source
    if source.lower() not in VALID_JOB_SOURCES:
        return {
            "success": False,
            "error": f"Invalid source '{source}'. Must be one of: {VALID_JOB_SOURCES}"
        }
    
    # Check database configuration
    if not AURORA_CLUSTER_ARN or not AURORA_SECRET_ARN:
        print(f"[store_discovered_job] Database not configured, skipping DB storage")
        return {
            "success": False,
            "error": "Database not configured. Job not stored.",
            "note": "This is expected in local development mode."
        }
    
    # Generate unique ID
    job_id = str(uuid.uuid4())
    
    # Use generated ID as source_job_id if not provided
    effective_source_job_id = source_job_id or job_id
    
    try:
        # Use UPSERT to avoid duplicates based on source + source_job_id
        _execute_sql(
            """INSERT INTO discovered_jobs 
               (id, source, source_url, source_job_id, company_name, role_title, 
                location, remote_policy, salary_min, salary_max, 
                description_text, requirements_text, is_active)
               VALUES (:id::uuid, :source, :source_url, :source_job_id, :company_name, 
                       :role_title, :location, :remote_policy, :salary_min, :salary_max,
                       :description_text, :requirements_text, true)
               ON CONFLICT (source, source_job_id) 
               DO UPDATE SET 
                   company_name = EXCLUDED.company_name,
                   role_title = EXCLUDED.role_title,
                   location = EXCLUDED.location,
                   salary_min = EXCLUDED.salary_min,
                   salary_max = EXCLUDED.salary_max,
                   description_text = EXCLUDED.description_text,
                   requirements_text = EXCLUDED.requirements_text,
                   is_active = true,
                   updated_at = NOW()""",
            {
                "id": job_id,
                "source": source.lower(),
                "source_url": source_url or None,
                "source_job_id": effective_source_job_id,
                "company_name": company_name,
                "role_title": role_title,
                "location": location or None,
                "remote_policy": remote_policy or None,
                "salary_min": salary_min if salary_min > 0 else None,
                "salary_max": salary_max if salary_max > 0 else None,
                "description_text": description_text or None,
                "requirements_text": requirements_text or None
            }
        )
        
        print(f"[store_discovered_job] Stored job: {job_id} - {role_title} at {company_name}")
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Successfully stored job: {role_title} at {company_name}"
        }
    except Exception as e:
        print(f"[store_discovered_job] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@function_tool
def store_research_finding(
    topic: str,
    category: str,
    title: str,
    summary: str,
    content: str,
    source_url: str = "",
    relevance_score: int = 50,
    is_featured: bool = False,
    metadata: str = "{}"
) -> Dict[str, Any]:
    """
    Store a research finding in the database for frontend display.
    This makes research visible to all users in the Market Insights page.
    
    IMPORTANT: Always call this BEFORE ingest_career_document to ensure
    the finding is stored for user display.
    
    Args:
        topic: The research topic (e.g., "AI Engineering Roles")
        category: One of: 'role_trend', 'skill_demand', 'salary_insight', 'industry_news'
        title: A catchy title for the finding (e.g., "AI Engineers in High Demand")
        summary: A 1-2 sentence summary for card display
        content: The full detailed content/analysis
        source_url: Optional URL to the original source
        relevance_score: 0-100 score indicating importance (default 50)
        is_featured: Whether to feature this prominently (default False)
        metadata: Optional JSON string with additional data
    
    Returns:
        Dictionary with success status and finding ID
    """
    # Validate category
    if category not in VALID_CATEGORIES:
        return {
            "success": False,
            "error": f"Invalid category '{category}'. Must be one of: {VALID_CATEGORIES}"
        }
    
    # Check database configuration
    if not AURORA_CLUSTER_ARN or not AURORA_SECRET_ARN:
        print(f"[store_research_finding] Database not configured, skipping DB storage")
        return {
            "success": False,
            "error": "Database not configured. Finding not stored.",
            "note": "This is expected in local development mode."
        }
    
    # Generate unique ID
    finding_id = str(uuid.uuid4())
    
    try:
        # Parse metadata if it's a string
        if isinstance(metadata, str):
            try:
                metadata_dict = json.loads(metadata) if metadata else {}
            except json.JSONDecodeError:
                metadata_dict = {}
        else:
            metadata_dict = metadata or {}
        
        # Insert into database
        _execute_sql(
            """INSERT INTO research_findings 
               (id, topic, category, title, summary, content, source_url, relevance_score, is_featured, metadata)
               VALUES (:id::uuid, :topic, :category, :title, :summary, :content, :source_url, :relevance_score, :is_featured, :metadata::jsonb)""",
            {
                "id": finding_id,
                "topic": topic,
                "category": category,
                "title": title,
                "summary": summary,
                "content": content,
                "source_url": source_url or None,
                "relevance_score": max(0, min(100, relevance_score)),
                "is_featured": is_featured,
                "metadata": json.dumps(metadata_dict)
            }
        )
        
        print(f"[store_research_finding] Stored finding: {finding_id} - {title}")
        return {
            "success": True,
            "finding_id": finding_id,
            "message": f"Successfully stored research finding: {title}"
        }
    except Exception as e:
        print(f"[store_research_finding] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }