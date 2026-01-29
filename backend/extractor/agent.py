"""
CV/Job Extractor Agent - Parses CVs and job postings into structured data using OpenAI Agents SDK.
"""

import os
import json
import logging
from typing import Optional

from pydantic import BaseModel, Field
from agents import Agent, Runner, trace
from agents.agent_output import AgentOutputSchema
from agents.extensions.models.litellm_model import LitellmModel

# Configure logging
logger = logging.getLogger(__name__)

# Get configuration
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")


# Import schemas from database package (added to extractor's src)
# These are re-exported for convenience
try:
    from src.schemas import (
        CVProfile, JobProfile,
        SkillEntry, ExperienceEntry, EducationEntry,
        JobRequirement, ProficiencyLevel, SkillCategory,
        RequirementType, SeniorityLevel, RemotePolicy
    )
except ImportError:
    # Fallback for local testing - define schemas inline
    from typing import List, Literal, Dict
    
    ProficiencyLevel = Literal["expert", "proficient", "familiar", "learning"]
    SkillCategory = Literal["technical", "soft_skill", "tool", "certification", "language", "domain"]
    RequirementType = Literal["must_have", "nice_to_have", "implicit"]
    SeniorityLevel = Literal["intern", "junior", "mid", "senior", "staff", "principal", "lead", "manager", "director", "vp", "c_level"]
    RemotePolicy = Literal["onsite", "hybrid", "remote", "unknown"]
    
    class SkillEntry(BaseModel):
        name: str = Field(description="Name of the skill")
        proficiency: ProficiencyLevel = Field(description="Proficiency level")
        years: Optional[int] = Field(None, description="Years of experience with this skill", ge=0)
        category: Optional[SkillCategory] = Field(None, description="Type of skill")
        evidence: Optional[str] = Field(None, description="Which CV line/section demonstrates this skill")
    
    class ExperienceEntry(BaseModel):
        company: str = Field(description="Company name")
        role: str = Field(description="Job title")
        start_date: str = Field(description="Start date (YYYY-MM or YYYY)")
        end_date: Optional[str] = Field(None, description="End date (YYYY-MM, YYYY, or 'Present')")
        is_current: bool = Field(default=False, description="Whether this is the current job")
        location: Optional[str] = Field(None, description="Job location")
        highlights: List[str] = Field(default=[], description="Key achievements and responsibilities")
        technologies: List[str] = Field(default=[], description="Technologies used in this role")
    
    class EducationEntry(BaseModel):
        institution: str = Field(description="School or university name")
        degree: str = Field(description="Degree type (BS, MS, PhD, etc.)")
        field: str = Field(description="Field of study")
        graduation_date: Optional[str] = Field(None, description="Graduation date")
        gpa: Optional[float] = Field(None, description="GPA if provided", ge=0, le=4.0)
        honors: Optional[str] = Field(None, description="Honors or distinctions")
    
    class CVProfile(BaseModel):
        name: str = Field(description="Full name from CV")
        email: Optional[str] = Field(None, description="Email address")
        phone: Optional[str] = Field(None, description="Phone number")
        location: Optional[str] = Field(None, description="Location/city")
        linkedin_url: Optional[str] = Field(None, description="LinkedIn URL if found")
        github_url: Optional[str] = Field(None, description="GitHub URL if found")
        portfolio_url: Optional[str] = Field(None, description="Portfolio URL if found")
        summary: Optional[str] = Field(None, description="Professional summary or objective")
        total_years_experience: Optional[int] = Field(None, description="Total years of experience")
        skills: List[SkillEntry] = Field(default=[], description="List of skills with proficiency levels")
        experience: List[ExperienceEntry] = Field(default=[], description="Work experience entries")
        education: List[EducationEntry] = Field(default=[], description="Education entries")
        certifications: List[str] = Field(default=[], description="Professional certifications")
        languages: List[str] = Field(default=[], description="Languages spoken")
        projects: Optional[List[Dict]] = Field(None, description="Notable projects if listed")
    
    class JobRequirement(BaseModel):
        text: str = Field(description="Requirement text from job posting")
        type: RequirementType = Field(description="Whether must-have, nice-to-have, or implied")
        category: SkillCategory = Field(description="Type of requirement")
        years_required: Optional[int] = Field(None, description="Years of experience required if specified")
    
    class JobProfile(BaseModel):
        company: str = Field(description="Company name")
        role_title: str = Field(description="Job title")
        seniority: Optional[SeniorityLevel] = Field(None, description="Inferred seniority level")
        department: Optional[str] = Field(None, description="Department or team")
        location: str = Field(description="Job location")
        remote_policy: RemotePolicy = Field(default="unknown", description="Remote work policy")
        must_have: List[JobRequirement] = Field(default=[], description="Required qualifications")
        nice_to_have: List[JobRequirement] = Field(default=[], description="Preferred qualifications")
        responsibilities: List[str] = Field(default=[], description="Key job responsibilities")
        ats_keywords: List[str] = Field(default=[], description="Key ATS-friendly keywords extracted")
        salary_min: Optional[int] = Field(None, description="Minimum salary if specified")
        salary_max: Optional[int] = Field(None, description="Maximum salary if specified")
        salary_currency: str = Field(default="USD", description="Salary currency")
        benefits: Optional[List[str]] = Field(None, description="Listed benefits")
        company_description: Optional[str] = Field(None, description="Company description if provided")


from templates import CV_EXTRACTION_PROMPT, JOB_EXTRACTION_PROMPT


async def extract_cv(raw_text: str) -> CVProfile:
    """
    Extract structured data from CV text using LLM.
    
    Args:
        raw_text: Raw CV text content
        
    Returns:
        Structured CVProfile with parsed information
    """
    # Set region for LiteLLM Bedrock calls
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Create agent with structured output
    agent = Agent(
        name="CV Extractor",
        instructions=CV_EXTRACTION_PROMPT,
        model=model,
        output_type=AgentOutputSchema(CVProfile, strict_json_schema=False)
    )
    
    task = f"""Extract all information from this CV/resume text:

---
{raw_text}
---

Parse the CV carefully and extract all relevant information into the structured format."""
    
    with trace("CV Extraction"):
        result = await Runner.run(agent, input=task)
        
    logger.info(f"CV extraction completed for: {result.final_output.name if hasattr(result.final_output, 'name') else 'Unknown'}")
    return result.final_output


async def extract_job_posting(raw_text: str) -> JobProfile:
    """
    Extract structured data from job posting text using LLM.
    
    Args:
        raw_text: Raw job posting text
        
    Returns:
        Structured JobProfile with parsed information
    """
    # Set region for LiteLLM Bedrock calls
    os.environ["AWS_REGION_NAME"] = BEDROCK_REGION
    
    model = LitellmModel(model=f"bedrock/{BEDROCK_MODEL_ID}")
    
    # Create agent with structured output
    agent = Agent(
        name="Job Posting Extractor",
        instructions=JOB_EXTRACTION_PROMPT,
        model=model,
        output_type=AgentOutputSchema(JobProfile, strict_json_schema=False)
    )
    
    task = f"""Extract all information from this job posting:

---
{raw_text}
---

Parse the job posting carefully and extract all relevant requirements and information into the structured format."""
    
    with trace("Job Posting Extraction"):
        result = await Runner.run(agent, input=task)
        
    logger.info(f"Job extraction completed for: {result.final_output.role_title if hasattr(result.final_output, 'role_title') else 'Unknown'} at {result.final_output.company if hasattr(result.final_output, 'company') else 'Unknown'}")
    return result.final_output


def cv_profile_to_dict(profile: CVProfile) -> dict:
    """Convert CVProfile to dictionary for database storage."""
    return profile.model_dump()


def job_profile_to_dict(profile: JobProfile) -> dict:
    """Convert JobProfile to dictionary for database storage."""
    return profile.model_dump()
