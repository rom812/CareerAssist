"""
CV/Job Extractor Agent - Parses CVs and job postings into structured data using OpenAI Agents SDK.
"""

import logging
import os

from agents import Agent, Runner, trace
from agents.agent_output import AgentOutputSchema
from agents.extensions.models.litellm_model import LitellmModel
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)

# Get configuration
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-west-2")


# Import schemas from database package (added to extractor's src)
# These are re-exported for convenience
try:
    from src.schemas import (
        CVProfile,
        EducationEntry,
        ExperienceEntry,
        JobProfile,
        JobRequirement,
        ProficiencyLevel,
        RemotePolicy,
        RequirementType,
        SeniorityLevel,
        SkillCategory,
        SkillEntry,
    )
except ImportError:
    # Fallback for local testing - define schemas inline
    from typing import Literal

    ProficiencyLevel = Literal["expert", "proficient", "familiar", "learning"]
    SkillCategory = Literal["technical", "soft_skill", "tool", "certification", "language", "domain"]
    RequirementType = Literal["must_have", "nice_to_have", "implicit"]
    SeniorityLevel = Literal[
        "intern", "junior", "mid", "senior", "staff", "principal", "lead", "manager", "director", "vp", "c_level"
    ]
    RemotePolicy = Literal["onsite", "hybrid", "remote", "unknown"]

    class SkillEntry(BaseModel):
        name: str = Field(description="Name of the skill")
        proficiency: ProficiencyLevel = Field(description="Proficiency level")
        years: int | None = Field(None, description="Years of experience with this skill", ge=0)
        category: SkillCategory | None = Field(None, description="Type of skill")
        evidence: str | None = Field(None, description="Which CV line/section demonstrates this skill")

    class ExperienceEntry(BaseModel):
        company: str = Field(description="Company name")
        role: str = Field(description="Job title")
        start_date: str = Field(description="Start date (YYYY-MM or YYYY)")
        end_date: str | None = Field(None, description="End date (YYYY-MM, YYYY, or 'Present')")
        is_current: bool = Field(default=False, description="Whether this is the current job")
        location: str | None = Field(None, description="Job location")
        highlights: list[str] = Field(default=[], description="Key achievements and responsibilities")
        technologies: list[str] = Field(default=[], description="Technologies used in this role")

    class EducationEntry(BaseModel):
        institution: str = Field(description="School or university name")
        degree: str = Field(description="Degree type (BS, MS, PhD, etc.)")
        field: str = Field(description="Field of study")
        graduation_date: str | None = Field(None, description="Graduation date")
        gpa: float | None = Field(None, description="GPA if provided", ge=0, le=4.0)
        honors: str | None = Field(None, description="Honors or distinctions")

    class CVProfile(BaseModel):
        name: str = Field(description="Full name from CV")
        email: str | None = Field(None, description="Email address")
        phone: str | None = Field(None, description="Phone number")
        location: str | None = Field(None, description="Location/city")
        linkedin_url: str | None = Field(None, description="LinkedIn URL if found")
        github_url: str | None = Field(None, description="GitHub URL if found")
        portfolio_url: str | None = Field(None, description="Portfolio URL if found")
        summary: str | None = Field(None, description="Professional summary or objective")
        total_years_experience: int | None = Field(None, description="Total years of experience")
        skills: list[SkillEntry] = Field(default=[], description="List of skills with proficiency levels")
        experience: list[ExperienceEntry] = Field(default=[], description="Work experience entries")
        education: list[EducationEntry] = Field(default=[], description="Education entries")
        certifications: list[str] = Field(default=[], description="Professional certifications")
        languages: list[str] = Field(default=[], description="Languages spoken")
        projects: list[dict] | None = Field(None, description="Notable projects if listed")

    class JobRequirement(BaseModel):
        text: str = Field(description="Requirement text from job posting")
        type: RequirementType = Field(description="Whether must-have, nice-to-have, or implied")
        category: SkillCategory = Field(description="Type of requirement")
        years_required: int | None = Field(None, description="Years of experience required if specified")

    class JobProfile(BaseModel):
        company: str = Field(description="Company name")
        role_title: str = Field(description="Job title")
        seniority: SeniorityLevel | None = Field(None, description="Inferred seniority level")
        department: str | None = Field(None, description="Department or team")
        location: str = Field(description="Job location")
        remote_policy: RemotePolicy = Field(default="unknown", description="Remote work policy")
        must_have: list[JobRequirement] = Field(default=[], description="Required qualifications")
        nice_to_have: list[JobRequirement] = Field(default=[], description="Preferred qualifications")
        responsibilities: list[str] = Field(default=[], description="Key job responsibilities")
        ats_keywords: list[str] = Field(default=[], description="Key ATS-friendly keywords extracted")
        salary_min: int | None = Field(None, description="Minimum salary if specified")
        salary_max: int | None = Field(None, description="Maximum salary if specified")
        salary_currency: str = Field(default="USD", description="Salary currency")
        benefits: list[str] | None = Field(None, description="Listed benefits")
        company_description: str | None = Field(None, description="Company description if provided")


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
        output_type=AgentOutputSchema(CVProfile, strict_json_schema=False),
    )

    task = f"""Extract all information from this CV/resume text:

---
{raw_text}
---

Parse the CV carefully and extract all relevant information into the structured format."""

    with trace("CV Extraction"):
        result = await Runner.run(agent, input=task)

    logger.info(
        f"CV extraction completed for: {result.final_output.name if hasattr(result.final_output, 'name') else 'Unknown'}"
    )
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
        output_type=AgentOutputSchema(JobProfile, strict_json_schema=False),
    )

    task = f"""Extract all information from this job posting:

---
{raw_text}
---

Parse the job posting carefully and extract all relevant requirements and information into the structured format."""

    with trace("Job Posting Extraction"):
        result = await Runner.run(agent, input=task)

    logger.info(
        f"Job extraction completed for: {result.final_output.role_title if hasattr(result.final_output, 'role_title') else 'Unknown'} at {result.final_output.company if hasattr(result.final_output, 'company') else 'Unknown'}"
    )
    return result.final_output


def cv_profile_to_dict(profile: CVProfile) -> dict:
    """Convert CVProfile to dictionary for database storage."""
    return profile.model_dump()


def job_profile_to_dict(profile: JobProfile) -> dict:
    """Convert JobProfile to dictionary for database storage."""
    return profile.model_dump()
