"""
Interviewer Agent Lambda Handler
Generates interview questions and evaluates answers.
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
from agent import generate_interview_pack, evaluate_answer, InterviewQuestion
from observability import observe, extract_trace_context, log_span

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db = Database()


async def run_interview_prep(
    job_id: str,
    job_profile: Dict[str, Any],
    cv_profile: Dict[str, Any] = None,
    gap_analysis: Dict[str, Any] = None,
    session_id: str = None
) -> Dict[str, Any]:
    """Generate interview preparation pack."""
    try:
        logger.info(f"Generating interview prep for job {job_id}")
        
        interview_pack = await generate_interview_pack(
            job_id, job_profile, cv_profile, gap_analysis
        )
        pack_dict = interview_pack.model_dump()
        
        if session_id:
            try:
                db.client.update(
                    'interview_sessions',
                    {
                        'questions': json.dumps(pack_dict.get('questions', [])),
                        'focus_areas': json.dumps(pack_dict.get('focus_areas', []))
                    },
                    "id = :id",
                    {'id': session_id}
                )
            except Exception as e:
                logger.warning(f"Could not update database: {e}")
        
        return {'success': True, 'type': 'interview_prep', 'interview_pack': pack_dict}
    except Exception as e:
        logger.error(f"Interview prep error: {e}", exc_info=True)
        return {'success': False, 'type': 'interview_prep', 'error': str(e)}


async def run_answer_evaluation(
    question_data: Dict[str, Any],
    answer: str,
    session_id: str = None
) -> Dict[str, Any]:
    """Evaluate an interview answer."""
    try:
        logger.info(f"Evaluating answer for question {question_data.get('id')}")
        
        question = InterviewQuestion(**question_data)
        evaluation = await evaluate_answer(question, answer)
        eval_dict = evaluation.model_dump()
        
        if session_id:
            try:
                # Append to answers and evaluations
                session = db.client.query_one(
                    "SELECT answers, evaluations FROM interview_sessions WHERE id = :id",
                    {'id': session_id}
                )
                if session:
                    answers = json.loads(session.get('answers') or '[]')
                    evaluations = json.loads(session.get('evaluations') or '[]')
                    answers.append({'question_id': question_data['id'], 'answer': answer})
                    evaluations.append(eval_dict)
                    db.client.update(
                        'interview_sessions',
                        {'answers': json.dumps(answers), 'evaluations': json.dumps(evaluations)},
                        "id = :id",
                        {'id': session_id}
                    )
            except Exception as e:
                logger.warning(f"Could not update database: {e}")
        
        return {'success': True, 'type': 'answer_evaluation', 'evaluation': eval_dict}
    except Exception as e:
        logger.error(f"Answer evaluation error: {e}", exc_info=True)
        return {'success': False, 'type': 'answer_evaluation', 'error': str(e)}


def lambda_handler(event, context):
    """
    Lambda handler for interview preparation and evaluation.

    Expected event for prep:
    {
        "type": "interview_prep",
        "job_id": "UUID",
        "job_profile": {...},
        "cv_profile": {...optional...},
        "gap_analysis": {...optional...},
        "_trace_context": {"trace_id": "...", "parent_span_id": "..."} (optional)
    }

    Expected event for evaluation:
    {
        "type": "answer_evaluation",
        "question": {...question data...},
        "answer": "candidate's answer text"
    }
    """
    # Extract trace context from orchestrator (if present)
    trace_ctx = extract_trace_context(event)
    action_type = event.get('type', 'interview_prep')
    job_id = event.get('job_id', 'unknown')
    
    logger.info(f"🚀 Interviewer Lambda invoked: type={action_type}, job={job_id}")
    
    with observe(
        job_id=job_id,
        agent_name="career-interviewer",
        trace_id=trace_ctx.get("trace_id"),
        parent_span_id=trace_ctx.get("parent_span_id"),
        metadata={"action_type": action_type}
    ) as trace_context:
        try:
            if action_type == 'interview_prep':
                job_id = event.get('job_id')
                job_profile = event.get('job_profile')
                
                if not job_profile:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'job_profile required'})}
                
                result = asyncio.run(run_interview_prep(
                    job_id or 'unknown',
                    job_profile,
                    event.get('cv_profile'),
                    event.get('gap_analysis'),
                    event.get('session_id')
                ))
                
            elif action_type == 'answer_evaluation':
                question = event.get('question')
                answer = event.get('answer')
                
                if not question or not answer:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'question and answer required'})}
                
                result = asyncio.run(run_answer_evaluation(
                    question, answer, event.get('session_id')
                ))
                
            else:
                return {'statusCode': 400, 'body': json.dumps({'error': f'Invalid type: {action_type}'})}
            
            return {'statusCode': 200 if result.get('success') else 500, 'body': json.dumps(result, default=str)}
        except Exception as e:
            logger.error(f"Lambda handler error: {e}", exc_info=True)
            return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


if __name__ == "__main__":
    sample_job = {
        "company": "TechCo",
        "role_title": "Senior Software Engineer",
        "seniority": "senior",
        "must_have": [
            {"text": "5+ years Python experience", "type": "must_have", "category": "technical"},
            {"text": "Experience with Kubernetes", "type": "must_have", "category": "technical"}
        ],
        "responsibilities": ["Design and implement scalable microservices", "Lead technical design reviews"]
    }
    
    result = lambda_handler({
        "type": "interview_prep",
        "job_id": "test-job-123",
        "job_profile": sample_job
    }, None)
    print(json.dumps(json.loads(result['body']), indent=2, default=str))