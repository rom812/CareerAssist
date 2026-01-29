"""
CV/Job Extractor Lambda Handler
Parses CVs and job postings into structured data.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from src import Database
from agent import extract_cv, extract_job_posting, cv_profile_to_dict, job_profile_to_dict
from observability import observe, extract_trace_context, log_span

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize database
db = Database()


async def process_cv_extraction(cv_text: str, user_id: str = None, cv_version_id: str = None) -> Dict[str, Any]:
    """
    Process CV text and extract structured data.
    
    Args:
        cv_text: Raw CV text content
        user_id: Optional user ID for database storage
        cv_version_id: Optional CV version ID to update
        
    Returns:
        Extraction results with parsed CV profile
    """
    try:
        logger.info(f"Processing CV extraction, text length: {len(cv_text)}")
        
        # Extract CV data
        profile = await extract_cv(cv_text)
        profile_dict = cv_profile_to_dict(profile)
        
        # Update database if cv_version_id provided
        if cv_version_id:
            try:
                get_db().client.update(
                    'cv_versions',
                    {'parsed_json': json.dumps(profile_dict)},
                    "id = :id",
                    {'id': cv_version_id}
                )
                logger.info(f"Updated CV version {cv_version_id} with parsed data")
            except Exception as e:
                logger.warning(f"Could not update database: {e}")
        
        return {
            'success': True,
            'type': 'cv',
            'profile': profile_dict,
            'cv_version_id': cv_version_id
        }
        
    except Exception as e:
        logger.error(f"CV extraction error: {e}", exc_info=True)
        return {
            'success': False,
            'type': 'cv',
            'error': str(e)
        }


async def process_job_extraction(job_text: str, user_id: str = None, job_posting_id: str = None) -> Dict[str, Any]:
    """
    Process job posting text and extract structured data.
    
    Args:
        job_text: Raw job posting text
        user_id: Optional user ID for database storage
        job_posting_id: Optional job posting ID to update
        
    Returns:
        Extraction results with parsed job profile
    """
    try:
        logger.info(f"Processing job extraction, text length: {len(job_text)}")
        
        # Extract job data
        profile = await extract_job_posting(job_text)
        profile_dict = job_profile_to_dict(profile)
        
        # Update database if job_posting_id provided
        if job_posting_id:
            try:
                # Prepare update data
                update_data = {
                    'parsed_json': json.dumps(profile_dict),
                    'company_name': profile_dict.get('company'),
                    'role_title': profile_dict.get('role_title'),
                    'location': profile_dict.get('location'),
                    'remote_policy': profile_dict.get('remote_policy')
                }
                # Add salary if present
                if profile_dict.get('salary_min'):
                    update_data['salary_min'] = profile_dict['salary_min']
                if profile_dict.get('salary_max'):
                    update_data['salary_max'] = profile_dict['salary_max']
                
                get_db().client.update(
                    'job_postings',
                    update_data,
                    "id = :id",
                    {'id': job_posting_id}
                )
                logger.info(f"Updated job posting {job_posting_id} with parsed data")
            except Exception as e:
                logger.warning(f"Could not update database: {e}")
        
        return {
            'success': True,
            'type': 'job',
            'profile': profile_dict,
            'job_posting_id': job_posting_id
        }
        
    except Exception as e:
        logger.error(f"Job extraction error: {e}", exc_info=True)
        return {
            'success': False,
            'type': 'job',
            'error': str(e)
        }


def lambda_handler(event, context):
    """
    Lambda handler for CV and job posting extraction.

    Expected event format:
    {
        "type": "cv" | "job",
        "text": "raw text content...",
        "user_id": "optional user UUID",
        "cv_version_id": "optional CV version UUID (for CV type)",
        "job_posting_id": "optional job posting UUID (for job type)",
        "_trace_context": {"trace_id": "...", "parent_span_id": "..."} (optional, from orchestrator)
    }
    
    Or for batch processing:
    {
        "batch": [
            {"type": "cv", "text": "...", ...},
            {"type": "job", "text": "...", ...}
        ]
    }
    """
    # Extract trace context from orchestrator (if present)
    trace_ctx = extract_trace_context(event)
    extraction_type = event.get('type', 'unknown')
    job_id = event.get('job_id', 'unknown')
    
    logger.info(f"🚀 Extractor Lambda invoked: type={extraction_type}, job={job_id}")
    
    with observe(
        job_id=job_id,
        agent_name="career-extractor",
        trace_id=trace_ctx.get("trace_id"),
        parent_span_id=trace_ctx.get("parent_span_id"),
        metadata={"extraction_type": extraction_type}
    ) as trace_context:
        try:
            logger.info(f"Extractor Lambda invoked with event keys: {list(event.keys())}")
            
            # Handle batch processing
            if 'batch' in event:
                results = []
                for item in event['batch']:
                    if item.get('type') == 'cv':
                        result = asyncio.run(process_cv_extraction(
                            item['text'],
                            item.get('user_id'),
                            item.get('cv_version_id')
                        ))
                    elif item.get('type') == 'job':
                        result = asyncio.run(process_job_extraction(
                            item['text'],
                            item.get('user_id'),
                            item.get('job_posting_id')
                        ))
                    else:
                        result = {'success': False, 'error': 'Invalid type, must be "cv" or "job"'}
                    results.append(result)
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({'results': results})
                }
            
            # Handle single extraction
            extraction_type = event.get('type')
            text = event.get('text')
            
            if not text:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'No text provided'})
                }
            
            if extraction_type == 'cv':
                result = asyncio.run(process_cv_extraction(
                    text,
                    event.get('user_id'),
                    event.get('cv_version_id')
                ))
            elif extraction_type == 'job':
                result = asyncio.run(process_job_extraction(
                    text,
                    event.get('user_id'),
                    event.get('job_posting_id')
                ))
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Invalid type, must be "cv" or "job"'})
                }
            
            status_code = 200 if result.get('success') else 500
            return {
                'statusCode': status_code,
                'body': json.dumps(result)
            }
            
        except Exception as e:
            logger.error(f"Lambda handler error: {e}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }


# For local testing
if __name__ == "__main__":
    # Test CV extraction
    sample_cv = """
    John Smith
    Senior Software Engineer
    john.smith@email.com | (555) 123-4567 | San Francisco, CA
    LinkedIn: linkedin.com/in/johnsmith | GitHub: github.com/johnsmith
    
    SUMMARY
    Experienced software engineer with 8+ years building scalable web applications.
    Expert in Python, JavaScript, and cloud technologies.
    
    EXPERIENCE
    
    Tech Corp, Senior Software Engineer
    January 2020 - Present
    - Led development of microservices architecture serving 1M+ daily users
    - Reduced API latency by 40% through Redis caching implementation
    - Mentored team of 5 junior developers
    Technologies: Python, FastAPI, Redis, Kubernetes, AWS
    
    StartupXYZ, Software Engineer
    March 2016 - December 2019
    - Built real-time data pipeline processing 500K events/day
    - Implemented CI/CD pipeline reducing deployment time by 60%
    Technologies: Python, Django, PostgreSQL, Docker
    
    EDUCATION
    BS Computer Science, University of California, Berkeley, 2016
    GPA: 3.8
    
    SKILLS
    Python (Expert), JavaScript (Proficient), TypeScript (Proficient)
    AWS, Docker, Kubernetes, CI/CD, Agile
    
    CERTIFICATIONS
    AWS Solutions Architect - Associate
    """
    
    print("Testing CV extraction...")
    result = asyncio.run(process_cv_extraction(sample_cv))
    print(json.dumps(result, indent=2, default=str))
    
    # Test job extraction
    sample_job = """
    Senior Software Engineer
    TechCo - San Francisco, CA (Hybrid)
    
    About Us
    TechCo is a leading AI company building next-generation products.
    
    About the Role
    We're looking for a Senior Software Engineer to join our platform team.
    
    Requirements
    - 5+ years of experience in software development
    - Strong proficiency in Python and JavaScript
    - Experience with cloud platforms (AWS, GCP, or Azure)
    - Experience with containerization (Docker, Kubernetes)
    
    Nice to Have
    - Experience with machine learning infrastructure
    - Familiarity with Terraform or other IaC tools
    - Open source contributions
    
    Responsibilities
    - Design and implement scalable microservices
    - Lead technical design reviews
    - Mentor junior engineers
    
    Compensation
    $180,000 - $220,000 + equity
    
    Benefits
    - Health, dental, vision
    - 401k matching
    - Unlimited PTO
    """
    
    print("\nTesting Job extraction...")
    result = asyncio.run(process_job_extraction(sample_job))
    print(json.dumps(result, indent=2, default=str))