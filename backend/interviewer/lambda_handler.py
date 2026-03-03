"""
Interviewer Agent Lambda Handler - Interview Prep and Answer Evaluation.
"""

import asyncio
import json
import logging
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(override=True)
except ImportError:
    pass

from agent import evaluate_answer, generate_interview_pack
from observability import extract_trace_context, log_span, observe
from src import Database

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db = Database()


async def run_interview_prep(
    job_id: str,
    job_profile: dict[str, Any],
    cv_profile: dict[str, Any] | None = None,
    gap_analysis: dict[str, Any] | None = None,
    trace_context: dict | None = None,
) -> dict[str, Any]:
    """Generate interview preparation pack."""
    try:
        logger.info(f"🎤 Generating interview prep for job {job_id}")

        pack = await generate_interview_pack(job_id, job_profile, cv_profile, gap_analysis)
        pack_dict = pack.model_dump()

        log_span(
            trace_context,
            "interview-prep-result",
            input_data={"job_title": job_profile.get("role_title"), "company": job_profile.get("company")},
            output_data={"questions_count": len(pack_dict.get("questions", []))},
        )

        # Save to jobs table
        try:
            db.jobs.update_interviewer(job_id, {"interview_pack": pack_dict})
            logger.info(f"✅ Saved interview prep to job {job_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not save to database: {e}")

        logger.info(f"✅ Interview prep complete: {len(pack_dict.get('questions', []))} questions generated")
        return {"success": True, "type": "interview_prep", "interview_pack": pack_dict}

    except Exception as e:
        logger.error(f"❌ Interview prep error: {e}", exc_info=True)
        log_span(trace_context, "interview-prep-error", metadata={"error": str(e)}, level="ERROR")
        return {"success": False, "type": "interview_prep", "error": str(e)}


async def run_answer_evaluation(
    question: dict[str, Any],
    answer: str,
    trace_context: dict | None = None,
) -> dict[str, Any]:
    """Evaluate an interview answer."""
    try:
        logger.info(f"📝 Evaluating answer for question {question.get('id', 'unknown')}")

        from src.schemas import InterviewQuestion

        question_obj = InterviewQuestion(**question)
        evaluation = await evaluate_answer(question_obj, answer)
        eval_dict = evaluation.model_dump()

        log_span(
            trace_context,
            "answer-evaluation-result",
            output_data={"score": eval_dict.get("score"), "question_id": eval_dict.get("question_id")},
        )

        logger.info(f"✅ Answer evaluation complete: score={eval_dict.get('score')}")
        return {"success": True, "type": "answer_evaluation", "evaluation": eval_dict}

    except Exception as e:
        logger.error(f"❌ Answer evaluation error: {e}", exc_info=True)
        log_span(trace_context, "answer-evaluation-error", metadata={"error": str(e)}, level="ERROR")
        return {"success": False, "type": "answer_evaluation", "error": str(e)}


def lambda_handler(event, context):
    """
    Lambda handler for interview preparation and answer evaluation.

    Expected event for interview_prep:
    {
        "type": "interview_prep",
        "job_id": "async job UUID",
        "job_profile": {...parsed job data...},
        "cv_profile": {...parsed CV data...} (optional),
        "gap_analysis": {...} (optional),
        "_trace_context": {"trace_id": "...", "parent_span_id": "..."} (optional)
    }

    Expected event for answer_evaluation:
    {
        "type": "answer_evaluation",
        "question": {...interview question...},
        "answer": "candidate's answer text",
        "_trace_context": {"trace_id": "...", "parent_span_id": "..."} (optional)
    }
    """
    trace_ctx = extract_trace_context(event)

    event_type = event.get("type", "interview_prep")
    job_id = event.get("job_id", "unknown")

    logger.info(f"🚀 Interviewer Lambda invoked: type={event_type}, job={job_id}")

    with observe(
        job_id=job_id,
        agent_name="career-interviewer",
        trace_id=trace_ctx.get("trace_id"),
        parent_span_id=trace_ctx.get("parent_span_id"),
        metadata={"event_type": event_type},
    ) as trace_context:
        try:
            if event_type == "interview_prep":
                job_profile = event.get("job_profile")
                if not job_profile:
                    return {"statusCode": 400, "body": json.dumps({"error": "job_profile required"})}

                cv_profile = event.get("cv_profile")
                gap_analysis = event.get("gap_analysis")

                result = asyncio.run(run_interview_prep(job_id, job_profile, cv_profile, gap_analysis, trace_context))

            elif event_type == "answer_evaluation":
                question = event.get("question")
                answer = event.get("answer")

                if not question or not answer:
                    return {"statusCode": 400, "body": json.dumps({"error": "question and answer required"})}

                result = asyncio.run(run_answer_evaluation(question, answer, trace_context))

            else:
                return {"statusCode": 400, "body": json.dumps({"error": f"Invalid type: {event_type}"})}

            status_code = 200 if result.get("success") else 500
            logger.info(f"{'✅' if result.get('success') else '❌'} Interviewer returning status {status_code}")

            return {"statusCode": status_code, "body": json.dumps(result, default=str)}

        except Exception as e:
            logger.error(f"❌ Lambda handler error: {e}", exc_info=True)
            return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    sample_job = {
        "company": "TechCo",
        "role_title": "Senior Software Engineer",
        "seniority": "senior",
        "must_have": [{"text": "5+ years Python", "type": "must_have", "category": "technical"}],
        "responsibilities": ["Design and implement scalable microservices"],
    }

    result = lambda_handler({"type": "interview_prep", "job_id": "test", "job_profile": sample_job}, None)
    print(json.dumps(json.loads(result["body"]), indent=2))
