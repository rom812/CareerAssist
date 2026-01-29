"""
Career Orchestrator Lambda Handler
Routes career requests to specialized agents.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional

from agents import Agent, Runner, trace
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from litellm.exceptions import RateLimitError

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from src import Database
from templates import ORCHESTRATOR_INSTRUCTIONS
from agent import create_agent, OrchestratorContext, invoke_lambda_agent, INTERVIEWER_FUNCTION
from observability import observe, log_db_operation

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db = Database()


async def ensure_interviewer_called(
    job_id: str,
    context: OrchestratorContext,
    trace_context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Ensure the interviewer agent was called for a full_analysis job.
    
    The LLM agent may skip the interviewer step, so we check if the 
    interviewer_payload exists in the database and call the interviewer
    directly if it doesn't.
    """
    try:
        # Check if interviewer was already called by querying the database
        job = db.client.query_one(
            "SELECT interviewer_payload FROM jobs WHERE id = :id::uuid",
            [{'name': 'id', 'value': {'stringValue': job_id}}]
        )
        
        if job and job.get('interviewer_payload'):
            logger.info(f"✅ Interviewer already called for job {job_id}")
            return
        
        # Interviewer wasn't called - call it now
        logger.info(f"🔧 Interviewer not called by agent, calling directly for job {job_id}")
        
        result = invoke_lambda_agent(
            "Interviewer",
            INTERVIEWER_FUNCTION,
            {
                "type": "interview_prep",
                "job_id": job_id,
                "job_profile": context.input_data.get("job_profile"),
                "cv_profile": context.input_data.get("cv_profile"),
                "gap_analysis": context.input_data.get("gap_analysis")
            },
            trace_context=trace_context
        )
        
        if result.get("success"):
            # Save results to jobs table
            pack = result.get("interview_pack", {})
            update_data = {'interviewer_payload': result}
            
            rows_updated = db.client.update('jobs', update_data, "id = :id::uuid", {'id': job_id})
            
            if rows_updated > 0:
                logger.info(f"✅ Saved interviewer results for job {job_id} (questions={len(pack.get('questions', []))})")
            else:
                logger.error(f"❌ Failed to save interviewer results - 0 rows updated for job {job_id}")
        else:
            logger.warning(f"⚠️ Interviewer call failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"❌ Error in ensure_interviewer_called: {e}", exc_info=True)


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
)
async def run_orchestrator(
    job_id: str, 
    job_type: str, 
    input_data: Dict[str, Any],
    trace_context: Optional[Dict[str, Any]] = None
) -> None:
    """Run the orchestrator agent to coordinate career analysis."""
    try:
        # Update job status to processing
        db.client.update('jobs', {'status': 'processing'}, "id = :id::uuid", {'id': job_id})
        log_db_operation(trace_context, "update", "jobs", True, affected_rows=1)
        
        # Create agent with trace context for distributed tracing
        model, tools, task, context = create_agent(
            job_id, job_type, input_data, db, 
            trace_context=trace_context
        )
        
        with trace("Career Orchestrator"):
            agent = Agent[OrchestratorContext](
                name="Career Orchestrator",
                instructions=ORCHESTRATOR_INSTRUCTIONS,
                model=model,
                tools=tools
            )
            
            logger.info(f"🤖 Starting orchestrator agent for job {job_id}")
            result = await Runner.run(agent, input=task, context=context, max_turns=15)
            
            # For full_analysis jobs, ensure interviewer is called
            # The LLM agent may skip the interviewer step, so we call it explicitly if needed
            if job_type == "full_analysis":
                await ensure_interviewer_called(job_id, context, trace_context)
            
            # Update job status to completed
            db.client.update('jobs', {'status': 'completed'}, "id = :id::uuid", {'id': job_id})
            log_db_operation(trace_context, "update", "jobs", True, affected_rows=1)
            
            logger.info(f"✅ Orchestrator: Job {job_id} completed successfully")
            logger.info(f"📋 Final output: {str(result.final_output)[:200]}...")
            
    except Exception as e:
        logger.error(f"❌ Orchestrator: Error in orchestration: {e}", exc_info=True)
        try:
            db.client.update('jobs', {'status': 'failed', 'error_message': str(e)}, "id = :id::uuid", {'id': job_id})
            log_db_operation(trace_context, "update", "jobs", True, affected_rows=1)
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
            log_db_operation(trace_context, "update", "jobs", False, error=str(db_error))
        raise


def lambda_handler(event, context):
    """
    Lambda handler for SQS-triggered orchestration.

    Expected event from SQS:
    {
        "Records": [{"body": "job_id"}]
    }
    
    Or direct invocation:
    {
        "job_id": "uuid",
        "job_type": "full_analysis",
        "input_data": {...}
    }
    """
    job_id = None
    user_id = None
    
    try:
        logger.info(f"🚀 Orchestrator Lambda invoked")
        
        # Extract job_id from SQS or direct invocation
        if 'Records' in event and len(event['Records']) > 0:
            body = event['Records'][0]['body']
            if isinstance(body, str) and body.startswith('{'):
                try:
                    data = json.loads(body)
                    job_id = data.get('job_id', body)
                    user_id = data.get('clerk_user_id')  # Get user_id if available
                except json.JSONDecodeError:
                    job_id = body
            else:
                job_id = body
                
            # Load job details from database
            job = db.client.query_one(
                "SELECT * FROM jobs WHERE id = :id::uuid", 
                [{'name': 'id', 'value': {'stringValue': job_id}}]
            )
            if not job:
                logger.error(f"Job {job_id} not found in database")
                return {'statusCode': 404, 'body': json.dumps({'error': f'Job {job_id} not found'})}
            
            job_type = job.get('job_type', 'full_analysis')
            user_id = user_id or job.get('clerk_user_id')
            input_data_raw = job.get('input_data') or {}
            # Handle both dict (from JSONB) and string (from JSON)
            input_data = input_data_raw if isinstance(input_data_raw, dict) else json.loads(input_data_raw or '{}')
            
        elif 'job_id' in event:
            job_id = event['job_id']
            job_type = event.get('job_type', 'full_analysis')
            input_data = event.get('input_data', {})
            user_id = event.get('clerk_user_id')
        else:
            return {'statusCode': 400, 'body': json.dumps({'error': 'No job_id provided'})}
        
        logger.info(f"📊 Starting {job_type} for job {job_id} (user: {user_id or 'unknown'})")
        
        # Use new observability with job_id as trace seed
        with observe(
            job_id=job_id,
            agent_name="career-orchestrator",
            user_id=user_id,
            metadata={
                "job_type": job_type,
                "has_cv_text": bool(input_data.get("cv_text")),
                "has_job_text": bool(input_data.get("job_text")),
                "has_cv_profile": bool(input_data.get("cv_profile")),
                "has_job_profile": bool(input_data.get("job_profile")),
            }
        ) as trace_context:
            asyncio.run(run_orchestrator(job_id, job_type, input_data, trace_context))
        
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'message': f'{job_type} completed for job {job_id}'})
        }
        
    except Exception as e:
        logger.error(f"❌ Orchestrator error: {e}", exc_info=True)
        return {'statusCode': 500, 'body': json.dumps({'success': False, 'error': str(e)})}




if __name__ == "__main__":
    # Test direct invocation
    test_event = {
        'job_id': 'test-orchestrator-123',
        'job_type': 'gap_analysis',
        'input_data': {
            'cv_profile': {'name': 'John Smith', 'skills': [{'name': 'Python'}]},
            'job_profile': {'company': 'TechCo', 'role_title': 'Senior Engineer'}
        }
    }
    
    # Set mock mode for testing
    os.environ['MOCK_LAMBDAS'] = 'true'
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))
