"""
Gap Analyzer Agent - Compares CVs to job postings and generates rewrites.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from agents import Agent, Runner, function_tool, RunContextWrapper, trace, AgentOutputSchema
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger()

# Get configuration
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")


# Import schemas from database package
try:
    from src.schemas import (
        GapAnalysis, GapItem, CVRewrite,
        CVProfile, JobProfile, GapSeverity
    )
except ImportError:
    # Fallback for local testing
    from pydantic import BaseModel, Field
    from typing import Literal
    
    GapSeverity = Literal["critical", "high", "medium", "low"]
    
    class GapItem(BaseModel):
        requirement: str = Field(description="The job requirement not fully met")
        severity: GapSeverity = Field(description="How critical this gap is")
        current_evidence: Optional[str] = Field(None, description="What the CV shows related to this")
        missing_element: str = Field(description="Specific thing that's missing or weak")
        recommendation: str = Field(description="How to address this gap")
        learnable: bool = Field(default=True, description="Whether this can be learned/acquired")
        estimated_time: Optional[str] = Field(None, description="Estimated time to address if learnable")
    
    class GapAnalysis(BaseModel):
        fit_score: int = Field(description="Overall fit score 0-100", ge=0, le=100)
        ats_score: int = Field(description="ATS keyword match percentage 0-100", ge=0, le=100)
        summary: str = Field(description="Overall analysis summary")
        strengths: List[str] = Field(default=[], description="Key matching strengths")
        gaps: List[GapItem] = Field(default=[], description="Gaps with severity and recommendations")
        action_items: List[str] = Field(default=[], description="Prioritized list of actions to improve candidacy")
        keywords_present: List[str] = Field(default=[], description="ATS keywords found in CV")
        keywords_missing: List[str] = Field(default=[], description="ATS keywords to add")
    
    class CVRewrite(BaseModel):
        rewritten_summary: str = Field(description="Tailored professional summary")
        rewritten_bullets: List[Dict] = Field(description="Improved experience bullets")
        skills_to_highlight: List[str] = Field(description="Skills to emphasize for this specific role")
        keywords_added: List[str] = Field(default=[], description="ATS keywords incorporated")
        cover_letter: Optional[str] = Field(None, description="Generated cover letter")
        linkedin_summary: Optional[str] = Field(None, description="LinkedIn-optimized summary")


from templates import GAP_ANALYSIS_PROMPT, CV_REWRITE_PROMPT


@dataclass
class AnalyzerContext:
    """Context for the Analyzer agent"""
    
    job_id: str
    cv_profile: Dict[str, Any]
    job_profile: Dict[str, Any]
    db: Optional[Any] = None


def format_cv_for_analysis(cv_profile: Dict[str, Any]) -> str:
    """Format CV profile data for LLM analysis."""
    lines = [
        f"## Candidate: {cv_profile.get('name', 'Unknown')}",
        ""
    ]
    
    if cv_profile.get('summary'):
        lines.append(f"**Summary:** {cv_profile['summary']}")
        lines.append("")
    
    if cv_profile.get('total_years_experience'):
        lines.append(f"**Total Experience:** {cv_profile['total_years_experience']} years")
        lines.append("")
    
    # Skills
    if cv_profile.get('skills'):
        lines.append("**Skills:**")
        for skill in cv_profile['skills']:
            name = skill.get('name', '')
            level = skill.get('proficiency', '')
            years = skill.get('years', '')
            skill_line = f"- {name}"
            if level:
                skill_line += f" ({level})"
            if years:
                skill_line += f" - {years} years"
            lines.append(skill_line)
        lines.append("")
    
    # Experience
    if cv_profile.get('experience'):
        lines.append("**Work Experience:**")
        for exp in cv_profile['experience']:
            company = exp.get('company', '')
            role = exp.get('role', '')
            dates = f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}"
            lines.append(f"\n### {role} at {company} ({dates})")
            
            for highlight in exp.get('highlights', []):
                lines.append(f"  - {highlight}")
            
            if exp.get('technologies'):
                lines.append(f"  Technologies: {', '.join(exp['technologies'])}")
        lines.append("")
    
    # Education
    if cv_profile.get('education'):
        lines.append("**Education:**")
        for edu in cv_profile['education']:
            lines.append(f"- {edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('institution', '')}")
        lines.append("")
    
    # Certifications
    if cv_profile.get('certifications'):
        lines.append(f"**Certifications:** {', '.join(cv_profile['certifications'])}")
        lines.append("")
    
    return "\n".join(lines)


def format_job_for_analysis(job_profile: Dict[str, Any]) -> str:
    """Format job profile data for LLM analysis."""
    lines = [
        f"## Job: {job_profile.get('role_title', 'Unknown Role')} at {job_profile.get('company', 'Unknown Company')}",
        ""
    ]
    
    if job_profile.get('location'):
        lines.append(f"**Location:** {job_profile['location']} ({job_profile.get('remote_policy', 'unknown')})")
    
    if job_profile.get('seniority'):
        lines.append(f"**Seniority Level:** {job_profile['seniority']}")
    
    lines.append("")
    
    # Must-have requirements
    if job_profile.get('must_have'):
        lines.append("**Must-Have Requirements:**")
        for req in job_profile['must_have']:
            text = req.get('text', '') if isinstance(req, dict) else str(req)
            category = req.get('category', '') if isinstance(req, dict) else ''
            years = req.get('years_required', '') if isinstance(req, dict) else ''
            
            req_line = f"- {text}"
            if years:
                req_line += f" ({years}+ years)"
            if category:
                req_line += f" [{category}]"
            lines.append(req_line)
        lines.append("")
    
    # Nice-to-have requirements
    if job_profile.get('nice_to_have'):
        lines.append("**Nice-to-Have:**")
        for req in job_profile['nice_to_have']:
            text = req.get('text', '') if isinstance(req, dict) else str(req)
            lines.append(f"- {text}")
        lines.append("")
    
    # Responsibilities
    if job_profile.get('responsibilities'):
        lines.append("**Responsibilities:**")
        for resp in job_profile['responsibilities']:
            lines.append(f"- {resp}")
        lines.append("")
    
    # ATS Keywords
    if job_profile.get('ats_keywords'):
        lines.append(f"**Key ATS Keywords:** {', '.join(job_profile['ats_keywords'])}")
        lines.append("")
    
    return "\n".join(lines)


@function_tool
async def get_bullet_templates(
    wrapper: RunContextWrapper[AnalyzerContext], 
    role_type: str
) -> str:
    """
    Get strong CV bullet templates from vector store.
    
    Args:
        role_type: Type of role (e.g., "software_engineer", "product_manager")
    
    Returns:
        Relevant bullet templates for inspiration
    """
    try:
        import boto3
        
        # Get account ID
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]
        bucket = f"career-vectors-{account_id}"
        
        # Get embeddings
        sagemaker_region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")
        sagemaker = boto3.client("sagemaker-runtime", region_name=sagemaker_region)
        endpoint_name = os.getenv("SAGEMAKER_ENDPOINT", "career-embedding-endpoint")
        query = f"CV bullet templates for {role_type}"
        
        response = sagemaker.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="application/json",
            Body=json.dumps({"inputs": query}),
        )
        
        result = json.loads(response["Body"].read().decode())
        if isinstance(result, list) and result:
            embedding = result[0][0] if isinstance(result[0], list) else result[0]
        else:
            embedding = result
        
        # Search vectors
        s3v = boto3.client("s3vectors", region_name=sagemaker_region)
        response = s3v.query_vectors(
            vectorBucketName=bucket,
            indexName="cv-bullet-templates",
            queryVector={"float32": embedding},
            topK=5,
            returnMetadata=True,
        )
        
        # Format templates
        templates = []
        for vector in response.get("vectors", []):
            metadata = vector.get("metadata", {})
            bullets = metadata.get("bullets", [])
            if bullets:
                templates.extend(bullets[:3])
        
        if templates:
            return "Example strong bullets:\n" + "\n".join(f"• {b}" for b in templates[:10])
        else:
            return "No templates available - generate original bullets based on achievements."
            
    except Exception as e:
        logger.warning(f"Could not retrieve bullet templates: {e}")
        return "Templates unavailable - generate original bullets."


@function_tool
async def get_ats_keywords(
    wrapper: RunContextWrapper[AnalyzerContext],
    industry: str,
    role: str
) -> str:
    """
    Get ATS optimization keywords for a role.
    
    Args:
        industry: Industry (e.g., "tech", "finance")
        role: Role type (e.g., "backend_engineer")
    
    Returns:
        Relevant ATS keywords to include
    """
    try:
        import boto3
        
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]
        bucket = f"career-vectors-{account_id}"
        
        sagemaker_region = os.getenv("DEFAULT_AWS_REGION", "us-east-1")
        sagemaker = boto3.client("sagemaker-runtime", region_name=sagemaker_region)
        endpoint_name = os.getenv("SAGEMAKER_ENDPOINT", "career-embedding-endpoint")
        query = f"ATS keywords for {role} in {industry}"
        
        response = sagemaker.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType="application/json",
            Body=json.dumps({"inputs": query}),
        )
        
        result = json.loads(response["Body"].read().decode())
        if isinstance(result, list) and result:
            embedding = result[0][0] if isinstance(result[0], list) else result[0]
        else:
            embedding = result
        
        s3v = boto3.client("s3vectors", region_name=sagemaker_region)
        response = s3v.query_vectors(
            vectorBucketName=bucket,
            indexName="ats-keywords",
            queryVector={"float32": embedding},
            topK=3,
            returnMetadata=True,
        )
        
        keywords = []
        for vector in response.get("vectors", []):
            metadata = vector.get("metadata", {})
            kw_list = metadata.get("keywords", [])
            keywords.extend(kw_list)
        
        if keywords:
            return f"Important ATS keywords for {role}:\n" + ", ".join(set(keywords[:20]))
        else:
            return "No specific keywords found - use job posting keywords."
            
    except Exception as e:
        logger.warning(f"Could not retrieve ATS keywords: {e}")
        return "Keywords unavailable - extract from job posting."


async def analyze_gap(cv_profile: Dict[str, Any], job_profile: Dict[str, Any]) -> GapAnalysis:
    """
    Perform gap analysis comparing CV to job requirements.
    
    Args:
        cv_profile: Parsed CV profile
        job_profile: Parsed job posting profile
        
    Returns:
        GapAnalysis with fit score, gaps, and recommendations
    """
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Format data for analysis
    cv_text = format_cv_for_analysis(cv_profile)
    job_text = format_job_for_analysis(job_profile)
    
    agent = Agent(
        name="Gap Analyzer",
        instructions=GAP_ANALYSIS_PROMPT,
        model=model,
        output_type=AgentOutputSchema(GapAnalysis, strict_json_schema=False)
    )
    
    task = f"""Analyze the fit between this candidate and job posting.

{cv_text}

---

{job_text}

---

Provide a comprehensive gap analysis with:
1. Overall fit score (0-100)
2. ATS keyword match score (0-100)
3. Key strengths (what matches well)
4. Gaps (what's missing or weak)
5. Action items to improve candidacy
6. Keywords present and missing"""
    
    with trace("Gap Analysis"):
        result = await Runner.run(agent, input=task)
    
    logger.info(f"Gap analysis completed with fit score: {result.final_output.fit_score}")
    return result.final_output


async def rewrite_cv(
    cv_profile: Dict[str, Any], 
    job_profile: Dict[str, Any],
    gap_analysis: GapAnalysis
) -> CVRewrite:
    """
    Generate optimized CV content tailored to the job.
    
    Args:
        cv_profile: Original CV profile
        job_profile: Target job profile
        gap_analysis: Gap analysis results
        
    Returns:
        CVRewrite with optimized content
    """
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Format data
    cv_text = format_cv_for_analysis(cv_profile)
    job_text = format_job_for_analysis(job_profile)
    
    # Format gap analysis
    gap_summary = f"""
Gap Analysis Results:
- Fit Score: {gap_analysis.fit_score}/100
- ATS Score: {gap_analysis.ats_score}/100
- Key Gaps: {', '.join([g.missing_element for g in gap_analysis.gaps[:5]])}
- Missing Keywords: {', '.join(gap_analysis.keywords_missing[:10])}
"""
    
    agent = Agent(
        name="CV Rewriter",
        instructions=CV_REWRITE_PROMPT,
        model=model,
        output_type=AgentOutputSchema(CVRewrite, strict_json_schema=False)
    )
    
    task = f"""Rewrite and optimize this CV for the target job.

## Original CV:
{cv_text}

## Target Job:
{job_text}

## Gap Analysis:
{gap_summary}

Generate an optimized version that:
1. Rewrites the professional summary to target this role
2. Improves experience bullets to highlight relevant achievements
3. Incorporates missing ATS keywords naturally
4. Creates a tailored cover letter
5. Optionally creates a LinkedIn-optimized summary"""
    
    with trace("CV Rewrite"):
        result = await Runner.run(agent, input=task)
    
    logger.info("CV rewrite completed")
    return result.final_output


def create_agent(job_id: str, cv_profile: Dict[str, Any], job_profile: Dict[str, Any], db=None):
    """Create the analyzer agent with tools and context."""
    
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    context = AnalyzerContext(
        job_id=job_id,
        cv_profile=cv_profile,
        job_profile=job_profile,
        db=db
    )
    
    tools = [get_bullet_templates, get_ats_keywords]
    
    cv_text = format_cv_for_analysis(cv_profile)
    job_text = format_job_for_analysis(job_profile)
    
    task = f"""Analyze the gap between this CV and job posting, then provide recommendations.

{cv_text}

---

{job_text}

---

Use the available tools to get bullet templates and ATS keywords if helpful.
Then provide a comprehensive gap analysis."""
    
    return model, tools, task, context
