"""
Gap Analyzer Agent Lambda Handler
Performs gap analysis and CV rewriting.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

from src import Database
from agent import analyze_gap, rewrite_cv, AnalyzerContext, GapAnalysis, GapItem
from observability import observe, extract_trace_context, log_span

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize database
db = Database()


async def run_gap_analysis(
    job_id: str,
    cv_profile: Dict[str, Any],
    job_profile: Dict[str, Any],
    gap_analysis_id: str = None,
    trace_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """Run gap analysis comparing CV to job."""
    try:
        logger.info(f"🔍 Running gap analysis for job {job_id}")
        gap_analysis = await analyze_gap(cv_profile, job_profile)
        gap_dict = gap_analysis.model_dump()
        
        # Log the analysis result
        log_span(
            trace_context,
            "gap-analysis-result",
            input_data={"cv_name": cv_profile.get("name"), "job_title": job_profile.get("role_title")},
            output_data={"fit_score": gap_dict.get("fit_score"), "gaps_count": len(gap_dict.get("gaps", []))},
            metadata={"fit_score": gap_dict.get("fit_score"), "ats_score": gap_dict.get("ats_score")}
        )
        
        if gap_analysis_id:
            try:
                db.client.update(
                    'gap_analyses',
                    {
                        'fit_score': gap_dict['fit_score'],
                        'gap_report': json.dumps(gap_dict),
                        'action_items': json.dumps(gap_dict.get('action_items', []))
                    },
                    "id = :id",
                    {'id': gap_analysis_id}
                )
                logger.info(f"✅ Updated gap analysis {gap_analysis_id}")
            except Exception as e:
                logger.warning(f"⚠️ Could not update database: {e}")
        
        logger.info(f"✅ Gap analysis complete: fit_score={gap_dict.get('fit_score')}")
        return {'success': True, 'type': 'gap_analysis', 'gap_analysis': gap_dict}
    except Exception as e:
        logger.error(f"❌ Gap analysis error: {e}", exc_info=True)
        log_span(trace_context, "gap-analysis-error", metadata={"error": str(e)}, level="ERROR")
        return {'success': False, 'type': 'gap_analysis', 'error': str(e)}


async def run_cv_rewrite(
    job_id: str,
    cv_profile: Dict[str, Any],
    job_profile: Dict[str, Any],
    gap_analysis_dict: Dict[str, Any],
    cv_rewrite_id: str = None,
    trace_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """Generate CV rewrite based on gap analysis."""
    try:
        logger.info(f"📝 Generating CV rewrite for job {job_id}")
        
        # Validate inputs
        if not cv_profile:
            logger.error("❌ CV profile is empty or None")
            return {'success': False, 'type': 'cv_rewrite', 'error': 'CV profile is required'}
        
        if not job_profile:
            logger.error("❌ Job profile is empty or None")
            return {'success': False, 'type': 'cv_rewrite', 'error': 'Job profile is required'}
        
        if not gap_analysis_dict:
            logger.error("❌ Gap analysis is empty or None")
            return {'success': False, 'type': 'cv_rewrite', 'error': 'Gap analysis is required'}
        
        logger.info(f"📊 Input validation passed: cv_profile={bool(cv_profile)}, job_profile={bool(job_profile)}, gap_analysis={bool(gap_analysis_dict)}")
        
        # Build gap analysis object
        try:
            gaps = [GapItem(**g) for g in gap_analysis_dict.get('gaps', [])]
            gap_analysis = GapAnalysis(
                fit_score=gap_analysis_dict.get('fit_score', 50),
                ats_score=gap_analysis_dict.get('ats_score', 50),
                summary=gap_analysis_dict.get('summary', ''),
                strengths=gap_analysis_dict.get('strengths', []),
                gaps=gaps,
                action_items=gap_analysis_dict.get('action_items', []),
                keywords_present=gap_analysis_dict.get('keywords_present', []),
                keywords_missing=gap_analysis_dict.get('keywords_missing', [])
            )
            logger.info(f"📊 Gap analysis object created: fit_score={gap_analysis.fit_score}, gaps_count={len(gaps)}")
        except Exception as e:
            logger.error(f"❌ Failed to parse gap analysis: {e}", exc_info=True)
            return {'success': False, 'type': 'cv_rewrite', 'error': f'Failed to parse gap analysis: {str(e)}'}
        
        # Call the rewrite agent
        try:
            logger.info(f"🤖 Calling rewrite_cv agent...")
            cv_rewrite = await rewrite_cv(cv_profile, job_profile, gap_analysis)
            logger.info(f"✅ rewrite_cv agent returned successfully")
        except Exception as e:
            logger.error(f"❌ rewrite_cv agent failed: {e}", exc_info=True)
            return {'success': False, 'type': 'cv_rewrite', 'error': f'CV rewrite agent failed: {str(e)}'}
        
        # Convert to dict
        try:
            rewrite_dict = cv_rewrite.model_dump()
            logger.info(f"📦 CV rewrite converted to dict: {list(rewrite_dict.keys())}")
        except Exception as e:
            logger.error(f"❌ Failed to convert cv_rewrite to dict: {e}", exc_info=True)
            return {'success': False, 'type': 'cv_rewrite', 'error': f'Failed to serialize CV rewrite: {str(e)}'}
        
        # Validate the result
        if not rewrite_dict.get('rewritten_summary'):
            logger.warning("⚠️ CV rewrite has empty rewritten_summary")
        
        # Log the rewrite result
        log_span(
            trace_context,
            "cv-rewrite-result",
            output_data={
                "summary_length": len(rewrite_dict.get("rewritten_summary", "")),
                "bullets_count": len(rewrite_dict.get("rewritten_bullets", [])),
                "has_cover_letter": bool(rewrite_dict.get("cover_letter"))
            }
        )
        
        if cv_rewrite_id:
            try:
                db.client.update(
                    'cv_rewrites',
                    {
                        'rewritten_summary': rewrite_dict['rewritten_summary'],
                        'rewritten_bullets': json.dumps(rewrite_dict.get('rewritten_bullets', [])),
                        'cover_letter': rewrite_dict.get('cover_letter')
                    },
                    "id = :id",
                    {'id': cv_rewrite_id}
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not update database: {e}")
        
        logger.info(f"✅ CV rewrite complete: summary_len={len(rewrite_dict.get('rewritten_summary', ''))}, bullets_count={len(rewrite_dict.get('rewritten_bullets', []))}")
        return {'success': True, 'type': 'cv_rewrite', 'cv_rewrite': rewrite_dict}
    except Exception as e:
        logger.error(f"❌ CV rewrite error: {e}", exc_info=True)
        log_span(trace_context, "cv-rewrite-error", metadata={"error": str(e)}, level="ERROR")
        return {'success': False, 'type': 'cv_rewrite', 'error': str(e)}


async def run_full_analysis(
    job_id: str,
    cv_profile: Dict[str, Any],
    job_profile: Dict[str, Any],
    gap_analysis_id: str = None,
    cv_rewrite_id: str = None,
    trace_context: Optional[Dict] = None
) -> Dict[str, Any]:
    """Run complete analysis: gap analysis + CV rewrite."""
    try:
        logger.info(f"🚀 Running full analysis for job {job_id}")
        
        gap_result = await run_gap_analysis(job_id, cv_profile, job_profile, gap_analysis_id, trace_context)
        if not gap_result.get('success'):
            logger.error(f"❌ Gap analysis failed for job {job_id}: {gap_result.get('error')}")
            return gap_result
        
        logger.info(f"✅ Gap analysis complete, starting CV rewrite for job {job_id}")
        
        rewrite_result = await run_cv_rewrite(
            job_id, cv_profile, job_profile, gap_result['gap_analysis'], cv_rewrite_id, trace_context
        )
        
        # Check if cv_rewrite succeeded
        cv_rewrite_data = None
        cv_rewrite_error = None
        
        if rewrite_result.get('success'):
            cv_rewrite_data = rewrite_result.get('cv_rewrite')
            logger.info(f"✅ CV rewrite complete for job {job_id}")
        else:
            cv_rewrite_error = rewrite_result.get('error', 'Unknown CV rewrite error')
            logger.error(f"❌ CV rewrite failed for job {job_id}: {cv_rewrite_error}")
        
        # Return result with partial success info
        result = {
            'success': True,  # Gap analysis succeeded, which is the minimum
            'type': 'full_analysis',
            'gap_analysis': gap_result['gap_analysis'],
            'cv_rewrite': cv_rewrite_data,
            'cv_rewrite_error': cv_rewrite_error
        }
        
        # Log what we're returning
        logger.info(f"📦 Full analysis result: gap_analysis={'present' if result['gap_analysis'] else 'missing'}, cv_rewrite={'present' if result['cv_rewrite'] else 'missing'}")
        
        if cv_rewrite_error:
            logger.warning(f"⚠️ Full analysis partial success: CV rewrite failed - {cv_rewrite_error}")
        else:
            logger.info(f"✅ Full analysis complete for job {job_id}")
        
        return result
    except Exception as e:
        logger.error(f"❌ Full analysis error: {e}", exc_info=True)
        return {'success': False, 'type': 'full_analysis', 'error': str(e)}


def lambda_handler(event, context):
    """
    Lambda handler for gap analysis and CV rewriting.

    Expected event:
    {
        "type": "gap_analysis" | "cv_rewrite" | "full_analysis",
        "job_id": "async job UUID",
        "cv_profile": {...parsed CV data...},
        "job_profile": {...parsed job data...},
        "gap_analysis": {...} (required for cv_rewrite type),
        "_trace_context": {"trace_id": "...", "parent_span_id": "..."} (optional, from orchestrator)
    }
    """
    # Extract trace context from orchestrator (if present)
    trace_ctx = extract_trace_context(event)
    
    analysis_type = event.get('type', 'gap_analysis')
    job_id = event.get('job_id', 'unknown')
    
    logger.info(f"🚀 Analyzer Lambda invoked: type={analysis_type}, job={job_id}")
    
    # Use observability with trace context from orchestrator
    with observe(
        job_id=job_id,
        agent_name="career-analyzer",
        trace_id=trace_ctx.get("trace_id"),
        parent_span_id=trace_ctx.get("parent_span_id"),
        metadata={
            "analysis_type": analysis_type,
            "has_trace_context": bool(trace_ctx.get("trace_id")),
        }
    ) as trace_context:
        try:
            cv_profile = event.get('cv_profile')
            job_profile = event.get('job_profile')
            
            if not cv_profile or not job_profile:
                logger.error("Missing cv_profile or job_profile")
                return {'statusCode': 400, 'body': json.dumps({'error': 'cv_profile and job_profile required'})}
            
            logger.info(f"📊 Input: CV for '{cv_profile.get('name', 'Unknown')}', Job at '{job_profile.get('company', 'Unknown')}'")
            
            if analysis_type == 'gap_analysis':
                result = asyncio.run(run_gap_analysis(job_id, cv_profile, job_profile, trace_context=trace_context))
            elif analysis_type == 'cv_rewrite':
                gap_analysis = event.get('gap_analysis')
                if not gap_analysis:
                    return {'statusCode': 400, 'body': json.dumps({'error': 'gap_analysis required'})}
                result = asyncio.run(run_cv_rewrite(job_id, cv_profile, job_profile, gap_analysis, trace_context=trace_context))
            elif analysis_type == 'full_analysis':
                result = asyncio.run(run_full_analysis(job_id, cv_profile, job_profile, trace_context=trace_context))
            else:
                return {'statusCode': 400, 'body': json.dumps({'error': f'Invalid type: {analysis_type}'})}
            
            status_code = 200 if result.get('success') else 500
            logger.info(f"{'✅' if result.get('success') else '❌'} Analyzer returning status {status_code}")
            
            return {'statusCode': status_code, 'body': json.dumps(result, default=str)}
            
        except Exception as e:
            logger.error(f"❌ Lambda handler error: {e}", exc_info=True)
            return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


if __name__ == "__main__":
    sample_cv = {
        "name": "John Smith",
        "summary": "Experienced software engineer with 8 years building scalable applications",
        "skills": [{"name": "Python", "proficiency": "expert", "years": 6}],
        "experience": [{"company": "Tech Corp", "role": "Senior Software Engineer", 
                       "highlights": ["Led development of microservices"]}]
    }
    sample_job = {
        "company": "TechCo", "role_title": "Senior Software Engineer",
        "must_have": [{"text": "5+ years Python", "type": "must_have", "category": "technical"}],
        "ats_keywords": ["Python", "Kubernetes", "AWS"]
    }
    result = lambda_handler({"type": "gap_analysis", "job_id": "test", "cv_profile": sample_cv, "job_profile": sample_job}, None)
    print(json.dumps(json.loads(result['body']), indent=2))
