"""
Charter Agent Lambda Handler - Application Analytics.
"""

import os
import json
import asyncio
import logging
import re
from typing import Dict, Any

from agents import Agent, Runner, trace
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from litellm.exceptions import RateLimitError

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from src import Database
from templates import CHARTER_INSTRUCTIONS
from agent import create_agent
from observability import observe, extract_trace_context, log_span

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
)
async def run_charter_agent(job_id: str, applications_data: Dict[str, Any], db=None) -> Dict[str, Any]:
    """Run the charter agent to generate analytics charts."""
    
    model, task = create_agent(job_id, applications_data, db)
    
    with trace("Charter Agent"):
        agent = Agent(
            name="Career Analytics",
            instructions=CHARTER_INSTRUCTIONS,
            model=model
        )
        
        result = await Runner.run(agent, input=task, max_turns=5)
        response = result.final_output
        
        # Parse the JSON response
        try:
            # Clean up the response - remove markdown code blocks if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                cleaned = re.sub(r'\n?```$', '', cleaned)
            
            charts_data = json.loads(cleaned)
            
            if not isinstance(charts_data, dict) or 'charts' not in charts_data:
                charts_data = {'charts': charts_data if isinstance(charts_data, list) else []}
            
            return {
                'success': True,
                'charts': charts_data.get('charts', []),
                'raw_response': response
            }
        except json.JSONDecodeError as e:
            logger.error(f"Charter: JSON parse error: {e}")
            logger.error(f"Charter: Raw response: {response[:500]}")
            return {
                'success': False,
                'error': f"Failed to parse charts JSON: {e}",
                'raw_response': response
            }


def lambda_handler(event, context):
    """
    Lambda handler for application analytics charts.

    Expected event:
    {
        "job_id": "async job UUID",
        "applications_data": {
            "applications": [
                {"status": "applied", "role_title": "...", "fit_score": 75, ...},
                ...
            ]
        },
        "_trace_context": {"trace_id": "...", "parent_span_id": "..."} (optional)
    }
    
    Or with user_id to load from database:
    {
        "job_id": "async job UUID",
        "user_id": "user UUID"
    }
    """
    # Extract trace context from orchestrator (if present)
    trace_ctx = extract_trace_context(event)
    job_id = event.get('job_id', 'unknown')
    
    logger.info(f"🚀 Charter Lambda invoked: job={job_id}")
    
    with observe(
        job_id=job_id,
        agent_name="career-charter",
        trace_id=trace_ctx.get("trace_id"),
        parent_span_id=trace_ctx.get("parent_span_id"),
    ) as trace_context:
        try:
            applications_data = event.get('applications_data')
            
            # If no applications_data, try to load from database
            if not applications_data:
                user_id = event.get('user_id')
                if user_id:
                    try:
                        db = Database()
                        # Load user's applications with job details
                        apps = db.client.query(
                            """SELECT a.*, j.company_name, j.role_title, g.fit_score, g.gap_report
                               FROM job_applications a
                               LEFT JOIN job_postings j ON a.job_id = j.id
                               LEFT JOIN gap_analyses g ON a.job_id = g.job_id
                               WHERE a.user_id = :user_id""",
                            {'user_id': user_id}
                        )
                        applications_data = {
                            'applications': [dict(app) for app in apps] if apps else []
                        }
                    except Exception as e:
                        logger.warning(f"Could not load applications from database: {e}")
                        applications_data = {'applications': []}
                else:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'applications_data or user_id required'})}
            
            # Run the agent
            db = Database()
            result = asyncio.run(run_charter_agent(job_id, applications_data, db))
            
            # Save charts to job if job_id provided
            if result.get('success') and job_id != 'unknown':
                try:
                    db.client.update(
                        'jobs',
                        {'charts': json.dumps(result.get('charts', []))},
                        "id = :id",
                        {'id': job_id}
                    )
                except Exception as e:
                    logger.warning(f"Could not save charts to job: {e}")
            
            return {'statusCode': 200 if result.get('success') else 500, 'body': json.dumps(result, default=str)}
            
        except Exception as e:
            logger.error(f"Charter error: {e}", exc_info=True)
            return {'statusCode': 500, 'body': json.dumps({'success': False, 'error': str(e)})}


if __name__ == "__main__":
    test_data = {
        "applications": [
            {"status": "saved", "role_title": "Senior Software Engineer", "fit_score": 82},
            {"status": "applied", "role_title": "Senior Software Engineer", "fit_score": 75},
            {"status": "applied", "role_title": "Staff Engineer", "fit_score": 88},
            {"status": "interview", "role_title": "Tech Lead", "fit_score": 70},
            {"status": "rejected", "role_title": "Senior Software Engineer", "fit_score": 65},
            {"status": "offer", "role_title": "Staff Engineer", "fit_score": 92},
        ]
    }
    
    result = lambda_handler({"job_id": "test", "applications_data": test_data}, None)
    print(json.dumps(json.loads(result['body']), indent=2))