"""
Career Orchestrator Agent - Routes career requests to specialized agents.
"""

import os
import json
import boto3
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from agents import Agent, Runner, function_tool, RunContextWrapper, trace
from agents.extensions.models.litellm_model import LitellmModel

from observability import (
    log_agent_invocation, 
    log_db_operation,
    get_trace_context_for_propagation,
    truncate_for_trace
)

logger = logging.getLogger(__name__)

# Lambda function names
EXTRACTOR_FUNCTION = os.getenv("EXTRACTOR_FUNCTION", "career-extractor")
ANALYZER_FUNCTION = os.getenv("ANALYZER_FUNCTION", "career-analyzer")
CHARTER_FUNCTION = os.getenv("CHARTER_FUNCTION", "career-charter")
INTERVIEWER_FUNCTION = os.getenv("INTERVIEWER_FUNCTION", "career-interviewer")
MOCK_LAMBDAS = os.getenv("MOCK_LAMBDAS", "false").lower() == "true"

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")


@dataclass
class OrchestratorContext:
    """Context for orchestrator agent tools."""
    job_id: str
    job_type: str
    input_data: Dict[str, Any]
    db: Optional[Any] = None
    trace_context: Optional[Dict[str, Any]] = field(default=None)  # For Langfuse tracing


def invoke_lambda_agent(
    agent_name: str, 
    function_name: str, 
    payload: Dict[str, Any],
    trace_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Invoke a Lambda function for an agent with trace context propagation."""
    
    # Add trace context to payload for distributed tracing
    if trace_context:
        propagation_context = get_trace_context_for_propagation(trace_context)
        if propagation_context:
            payload["_trace_context"] = propagation_context
            logger.info(f"📊 Propagating trace context to {agent_name}: {propagation_context.get('trace_id', 'N/A')[:16]}...")
    
    if MOCK_LAMBDAS:
        logger.info(f"MOCK: Would invoke {agent_name} ({function_name}) with payload keys: {list(payload.keys())}")
        # Log mock invocation
        log_agent_invocation(
            trace_context=trace_context,
            agent_name=agent_name,
            input_payload={"mock": True, "keys": list(payload.keys())},
            output_payload={"success": True, "mock": True}
        )
        return {"success": True, "mock": True, "agent": agent_name}
    
    start_time = time.time()
    error_msg = None
    result = None
    
    try:
        lambda_client = boto3.client('lambda')
        
        logger.info(f"🚀 Invoking {agent_name} Lambda: {function_name}")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        response_payload = json.loads(response['Payload'].read().decode())
        
        if 'body' in response_payload:
            body = response_payload['body']
            if isinstance(body, str):
                result = json.loads(body)
            else:
                result = body
        else:
            result = response_payload
        
        # Check for errors in response
        if not result.get("success", True):
            error_msg = result.get("error", "Unknown error in response")
            logger.warning(f"⚠️ {agent_name} returned error: {error_msg}")
        else:
            logger.info(f"✅ {agent_name} completed successfully")
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error invoking {agent_name}: {e}")
        result = {"success": False, "error": error_msg}
        return result
        
    finally:
        # Log the invocation to Langfuse
        duration_ms = (time.time() - start_time) * 1000
        log_agent_invocation(
            trace_context=trace_context,
            agent_name=agent_name,
            input_payload=truncate_for_trace(payload),
            output_payload=truncate_for_trace(result) if result else None,
            error=error_msg,
            duration_ms=duration_ms
        )


def load_job_data(job_id: str, db) -> Dict[str, Any]:
    """Load job data and related information from database."""
    try:
        job = db.client.query_one(
            "SELECT * FROM jobs WHERE id = :id",
            {'id': job_id}
        )
        if not job:
            return {}
        
        input_data = json.loads(job.get('input_data') or '{}')
        return {
            'job': dict(job),
            'input_data': input_data,
            'user_id': job.get('user_id')
        }
    except Exception as e:
        logger.warning(f"Could not load job data: {e}")
        return {}


@function_tool
async def invoke_extractor(
    wrapper: RunContextWrapper[OrchestratorContext],
    extraction_type: str,
    text: str
) -> str:
    """
    Invoke the Extractor agent to parse CV or job posting text.
    
    Args:
        extraction_type: "cv" or "job"
        text: Raw text to parse
    
    Returns:
        Confirmation and extracted profile summary
    """
    context = wrapper.context
    logger.info(f"Orchestrator: Invoking Extractor for {extraction_type}")
    
    result = invoke_lambda_agent(
        "Extractor", 
        EXTRACTOR_FUNCTION, 
        {
            "type": extraction_type,
            "text": text,
            "job_id": context.job_id
        },
        trace_context=context.trace_context
    )
    
    if result.get("success"):
        profile = result.get("profile", {})
        
        # Store extracted profile in context for subsequent agent calls
        if extraction_type == "cv":
            context.input_data["cv_profile"] = profile
            logger.info(f"Orchestrator: Stored cv_profile in context")
            
            # Save to jobs table
            if context.db:
                try:
                    context.db.client.update('jobs', {'extractor_payload': {'cv_profile': profile}}, "id = :id::uuid", {'id': context.job_id})
                except Exception as e:
                    logger.warning(f"Could not save extractor results: {e}")
            
            return f"CV extracted: {profile.get('name', 'Unknown')} with {len(profile.get('skills', []))} skills"
        else:
            context.input_data["job_profile"] = profile
            logger.info(f"Orchestrator: Stored job_profile in context")
            
            # Save to jobs table
            if context.db:
                try:
                    existing = context.db.client.query_one("SELECT extractor_payload FROM jobs WHERE id = :id::uuid", [{'name': 'id', 'value': {'stringValue': context.job_id}}])
                    extractor_payload = existing.get('extractor_payload', {}) if existing else {}
                    if isinstance(extractor_payload, str):
                        import json
                        extractor_payload = json.loads(extractor_payload)
                    extractor_payload['job_profile'] = profile
                    context.db.client.update('jobs', {'extractor_payload': extractor_payload}, "id = :id::uuid", {'id': context.job_id})
                except Exception as e:
                    logger.warning(f"Could not save extractor results: {e}")
            
            return f"Job extracted: {profile.get('role_title', 'Unknown')} at {profile.get('company', 'Unknown')}"
    return f"Extraction failed: {result.get('error', 'Unknown error')}"


@function_tool
async def invoke_analyzer(
    wrapper: RunContextWrapper[OrchestratorContext],
    analysis_type: str
) -> str:
    """
    Invoke the Analyzer agent for gap analysis or CV rewriting.
    
    Args:
        analysis_type: "gap_analysis", "cv_rewrite", or "full_analysis"
    
    Returns:
        Confirmation and analysis summary
    """
    context = wrapper.context
    logger.info(f"Orchestrator: Invoking Analyzer for {analysis_type}")
    
    result = invoke_lambda_agent(
        "Analyzer", 
        ANALYZER_FUNCTION, 
        {
            "type": analysis_type,
            "job_id": context.job_id,
            "cv_profile": context.input_data.get("cv_profile"),
            "job_profile": context.input_data.get("job_profile"),
            "gap_analysis": context.input_data.get("gap_analysis")
        },
        trace_context=context.trace_context
    )
    
    if result.get("success"):
        # Store gap_analysis in context for subsequent agent calls (e.g., Interviewer)
        gap = result.get("gap_analysis", {})
        if gap:
            context.input_data["gap_analysis"] = gap
            logger.info(f"Orchestrator: Stored gap_analysis in context (fit_score={gap.get('fit_score')})")
        
        # Check cv_rewrite status
        cv_rewrite = result.get("cv_rewrite")
        cv_rewrite_error = result.get("cv_rewrite_error")
        
        if cv_rewrite:
            logger.info(f"Orchestrator: CV rewrite present with {len(cv_rewrite.get('rewritten_bullets', []))} bullets")
        elif cv_rewrite_error:
            logger.warning(f"Orchestrator: CV rewrite failed - {cv_rewrite_error}")
        else:
            logger.warning(f"Orchestrator: CV rewrite is missing (no data and no error)")
        
        # Save results to jobs table
        if context.db:
            try:
                update_data = {'analyzer_payload': result}
                if cv_rewrite:
                    update_data['summary_payload'] = cv_rewrite
                
                logger.info(f"Orchestrator: Attempting to save analyzer results: {list(update_data.keys())}")
                logger.info(f"Orchestrator: analyzer_payload keys: {list(result.keys()) if result else 'None'}")
                
                rows_updated = context.db.client.update('jobs', update_data, "id = :id::uuid", {'id': context.job_id})
                
                if rows_updated > 0:
                    logger.info(f"Orchestrator: Saved analyzer results to job {context.job_id} (rows={rows_updated}, cv_rewrite={'present' if cv_rewrite else 'missing'})")
                else:
                    logger.error(f"Orchestrator: Failed to save analyzer results - 0 rows updated for job {context.job_id}")
            except Exception as e:
                logger.error(f"Orchestrator: Error saving analyzer results: {e}", exc_info=True)
        
        if analysis_type == "gap_analysis":
            return f"Gap analysis complete: Fit score {gap.get('fit_score', 'N/A')}/100"
        elif analysis_type == "cv_rewrite":
            if cv_rewrite:
                return "CV rewrite generated successfully"
            else:
                return f"CV rewrite failed: {cv_rewrite_error or 'Unknown error'}"
        else:
            # Full analysis
            cv_status = "generated" if cv_rewrite else f"failed ({cv_rewrite_error or 'unknown'})"
            return f"Full analysis complete: Fit score {gap.get('fit_score', 'N/A')}/100, CV rewrite {cv_status}"
    return f"Analysis failed: {result.get('error', 'Unknown error')}"


@function_tool
async def invoke_interviewer(wrapper: RunContextWrapper[OrchestratorContext]) -> str:
    """
    Invoke the Interviewer agent for interview preparation.
    
    Returns:
        Confirmation and interview prep summary
    """
    context = wrapper.context
    logger.info("Orchestrator: Invoking Interviewer")
    
    result = invoke_lambda_agent(
        "Interviewer", 
        INTERVIEWER_FUNCTION, 
        {
            "type": "interview_prep",
            "job_id": context.job_id,
            "job_profile": context.input_data.get("job_profile"),
            "cv_profile": context.input_data.get("cv_profile"),
            "gap_analysis": context.input_data.get("gap_analysis")
        },
        trace_context=context.trace_context
    )
    
    if result.get("success"):
        # Save results to jobs table
        if context.db:
            try:
                pack = result.get("interview_pack", {})
                # Only save to interviewer_payload - interview_payload column doesn't exist
                update_data = {
                    'interviewer_payload': result
                }
                
                logger.info(f"Orchestrator: Attempting to save interviewer results")
                logger.info(f"Orchestrator: interviewer_payload keys: {list(result.keys()) if result else 'None'}")
                
                rows_updated = context.db.client.update('jobs', update_data, "id = :id::uuid", {'id': context.job_id})
                
                if rows_updated > 0:
                    logger.info(f"Orchestrator: Saved interviewer results to job {context.job_id} (rows={rows_updated}, questions={len(pack.get('questions', []))})")
                else:
                    logger.error(f"Orchestrator: Failed to save interviewer results - 0 rows updated for job {context.job_id}")
            except Exception as e:
                logger.error(f"Orchestrator: Error saving interviewer results: {e}", exc_info=True)
        
        pack = result.get("interview_pack", {})
        return f"Interview prep complete: {len(pack.get('questions', []))} questions generated"
    return f"Interview prep failed: {result.get('error', 'Unknown error')}"


@function_tool
async def invoke_charter(wrapper: RunContextWrapper[OrchestratorContext]) -> str:
    """
    Invoke the Charter agent for application analytics.
    
    Returns:
        Confirmation and analytics summary
    """
    context = wrapper.context
    logger.info("Orchestrator: Invoking Charter")
    
    result = invoke_lambda_agent(
        "Charter", 
        CHARTER_FUNCTION, 
        {
            "job_id": context.job_id,
            "applications_data": context.input_data.get("applications_data"),
            "user_id": context.input_data.get("user_id")
        },
        trace_context=context.trace_context
    )
    
    if result.get("success"):
        charts = result.get("charts", [])
        return f"Analytics generated: {len(charts)} charts created"
    return f"Analytics failed: {result.get('error', 'Unknown error')}"


def create_agent(
    job_id: str, 
    job_type: str, 
    input_data: Dict[str, Any], 
    db=None,
    trace_context: Optional[Dict[str, Any]] = None
):
    """Create the orchestrator agent with tools and context."""
    
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    context = OrchestratorContext(
        job_id=job_id,
        job_type=job_type,
        input_data=input_data,
        db=db,
        trace_context=trace_context
    )
    
    tools = [invoke_extractor, invoke_analyzer, invoke_interviewer, invoke_charter]
    
    # Determine task based on job type
    if job_type == "cv_parse":
        task = f"Parse the provided CV text using invoke_extractor with type='cv'. Job ID: {job_id}"
    elif job_type == "job_parse":
        task = f"Parse the provided job posting using invoke_extractor with type='job'. Job ID: {job_id}"
    elif job_type == "gap_analysis":
        task = f"Run gap analysis comparing CV to job using invoke_analyzer. Job ID: {job_id}"
    elif job_type == "cv_rewrite":
        task = f"Generate CV rewrite using invoke_analyzer with type='cv_rewrite'. Job ID: {job_id}"
    elif job_type == "interview_prep":
        task = f"Generate interview preparation using invoke_interviewer. Job ID: {job_id}"
    elif job_type == "get_analytics":
        task = f"Generate application analytics using invoke_charter. Job ID: {job_id}"
    elif job_type == "full_analysis":
        # Build extraction steps based on what's missing
        extraction_steps = []
        cv_text = input_data.get("cv_text", "")
        job_text = input_data.get("job_text", "")
        cv_profile = input_data.get("cv_profile")
        job_profile = input_data.get("job_profile")
        
        step_num = 1
        
        if cv_text and not cv_profile:
            extraction_steps.append(f"{step_num}. Call invoke_extractor(extraction_type=\"cv\", text=<the CV text>) to parse the CV. WAIT for result.")
            step_num += 1
        
        if job_text and not job_profile:
            extraction_steps.append(f"{step_num}. Call invoke_extractor(extraction_type=\"job\", text=<the job text>) to parse the job posting. WAIT for result.")
            step_num += 1
        
        extraction_instructions = "\n".join(extraction_steps) if extraction_steps else ""
        
        task = f"""Complete full career analysis workflow for job {job_id}:

INPUT DATA:
- CV Text available: {"Yes" if cv_text else "No"}
- CV Profile parsed: {"Yes" if cv_profile else "No"}
- Job Text available: {"Yes" if job_text else "No"}  
- Job Profile parsed: {"Yes" if job_profile else "No"}

{f"EXTRACTION PHASE (required before analysis):{chr(10)}{extraction_instructions}{chr(10)}" if extraction_instructions else ""}
ANALYSIS PHASE:
{step_num}. Call invoke_analyzer(analysis_type="full_analysis") and WAIT for the result.
{step_num + 1}. Call invoke_interviewer() and WAIT for the result.
{step_num + 2}. Only AFTER all tools have succeeded, respond with 'Done'.

{"CV TEXT:" + chr(10) + cv_text[:2000] + ("..." if len(cv_text) > 2000 else "") if cv_text and not cv_profile else ""}

{"JOB TEXT:" + chr(10) + job_text[:2000] + ("..." if len(job_text) > 2000 else "") if job_text and not job_profile else ""}"""
    else:
        task = f"Unknown job type: {job_type}. Respond with error."
    
    return model, tools, task, context
