"""
Pydantic schemas for CareerAssist data validation and LLM tool interfaces
These models serve as both database validation and LLM structured output schemas
"""

from typing import Dict, Literal, Optional, List
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import date, datetime


# ==============================================================================
# Type Definitions
# ==============================================================================

ProficiencyLevel = Literal["expert", "proficient", "familiar", "learning"]

SeniorityLevel = Literal[
    "intern", "junior", "mid", "senior", "staff", "principal", "lead", "manager", "director", "vp", "c_level"
]

RemotePolicy = Literal["onsite", "hybrid", "remote", "unknown"]

SkillCategory = Literal["technical", "soft_skill", "tool", "certification", "language", "domain"]

RequirementType = Literal["must_have", "nice_to_have", "implicit"]

GapSeverity = Literal["critical", "high", "medium", "low"]

InterviewType = Literal["behavioral", "technical", "system_design", "situational", "motivation", "mixed"]

QuestionDifficulty = Literal["easy", "medium", "hard"]

SessionType = Literal["practice", "preparation", "real"]

ApplicationStatus = Literal[
    "saved", "applied", "screening", "phone_screen", "interview", 
    "technical", "onsite", "offer", "rejected", "withdrawn", "accepted"
]

JobType = Literal[
    "cv_parse", "job_parse", "gap_analysis", "cv_rewrite", 
    "interview_prep", "full_analysis", "market_research"
]

JobStatus = Literal["pending", "processing", "completed", "failed"]


# ==============================================================================
# User Profile Schemas
# ==============================================================================

class UserProfileCreate(BaseModel):
    """Schema for creating a user profile"""
    
    clerk_user_id: str = Field(description="Unique identifier from Clerk authentication system")
    full_name: Optional[str] = Field(None, description="User's full name", max_length=255)
    email: Optional[str] = Field(None, description="User's email address", max_length=255)
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL", max_length=500)
    phone: Optional[str] = Field(None, description="Phone number", max_length=50)
    portfolio_url: Optional[str] = Field(None, description="Portfolio website URL", max_length=500)
    github_url: Optional[str] = Field(None, description="GitHub profile URL", max_length=500)
    target_roles: Optional[List[str]] = Field(default=[], description="Target job roles")
    target_locations: Optional[List[str]] = Field(default=[], description="Preferred work locations")
    years_of_experience: Optional[int] = Field(None, description="Total years of professional experience", ge=0, le=60)


class UserProfileResponse(UserProfileCreate):
    """Schema for user profile responses"""
    id: str
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# CV Schemas
# ==============================================================================

class SkillEntry(BaseModel):
    """Individual skill with proficiency and evidence"""
    
    name: str = Field(description="Name of the skill")
    proficiency: ProficiencyLevel = Field(description="Proficiency level")
    years: Optional[int] = Field(None, description="Years of experience with this skill", ge=0)
    category: Optional[SkillCategory] = Field(None, description="Type of skill")
    evidence: Optional[str] = Field(None, description="Which CV line/section demonstrates this skill")


class ExperienceEntry(BaseModel):
    """Work experience entry"""
    
    company: str = Field(description="Company name")
    role: str = Field(description="Job title")
    start_date: str = Field(description="Start date (YYYY-MM or YYYY)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM, YYYY, or 'Present')")
    is_current: bool = Field(default=False, description="Whether this is the current job")
    location: Optional[str] = Field(None, description="Job location")
    highlights: List[str] = Field(default=[], description="Key achievements and responsibilities")
    technologies: List[str] = Field(default=[], description="Technologies used in this role")


class EducationEntry(BaseModel):
    """Education entry"""
    
    institution: str = Field(description="School or university name")
    degree: str = Field(description="Degree type (BS, MS, PhD, etc.)")
    field: str = Field(description="Field of study")
    graduation_date: Optional[str] = Field(None, description="Graduation date")
    gpa: Optional[float] = Field(None, description="GPA if provided", ge=0, le=4.0)
    honors: Optional[str] = Field(None, description="Honors or distinctions")


class CVProfile(BaseModel):
    """Structured CV extraction - output from Extractor agent"""
    
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


class CVVersionCreate(BaseModel):
    """Schema for creating a CV version"""
    
    raw_text: str = Field(description="Raw CV text content", min_length=100)
    version_name: str = Field(default="Default", description="Name for this CV version", max_length=100)
    is_primary: bool = Field(default=False, description="Whether this is the primary CV")
    file_url: Optional[str] = Field(None, description="S3 URL if uploaded as file")
    file_type: Optional[str] = Field(None, description="File type: pdf, docx, txt, paste")


class CVVersionResponse(CVVersionCreate):
    """Schema for CV version responses"""
    id: str
    user_id: str
    parsed_json: Optional[CVProfile] = None
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# Job Posting Schemas
# ==============================================================================

class JobRequirement(BaseModel):
    """Individual job requirement"""
    
    text: str = Field(description="Requirement text from job posting")
    type: RequirementType = Field(description="Whether must-have, nice-to-have, or implied")
    category: SkillCategory = Field(description="Type of requirement")
    years_required: Optional[int] = Field(None, description="Years of experience required if specified")


class JobProfile(BaseModel):
    """Structured job posting extraction - output from Extractor agent"""
    
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


class JobPostingCreate(BaseModel):
    """Schema for creating a job posting"""
    
    raw_text: str = Field(description="Raw job posting text", min_length=50)
    company_name: Optional[str] = Field(None, description="Company name", max_length=255)
    role_title: Optional[str] = Field(None, description="Job title", max_length=255)
    url: Optional[str] = Field(None, description="Original job posting URL", max_length=500)
    salary_min: Optional[int] = Field(None, description="Minimum salary")
    salary_max: Optional[int] = Field(None, description="Maximum salary")
    salary_currency: str = Field(default="USD", description="Salary currency")
    location: Optional[str] = Field(None, description="Job location")
    remote_policy: Optional[RemotePolicy] = Field(None, description="Remote work policy")
    deadline: Optional[date] = Field(None, description="Application deadline")
    notes: Optional[str] = Field(None, description="Personal notes about this job")


class JobPostingResponse(JobPostingCreate):
    """Schema for job posting responses"""
    id: str
    user_id: str
    parsed_json: Optional[JobProfile] = None
    is_saved: bool
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# Gap Analysis Schemas
# ==============================================================================

class GapItem(BaseModel):
    """Individual gap between CV and job requirement"""
    
    requirement: str = Field(description="The job requirement not fully met")
    severity: GapSeverity = Field(description="How critical this gap is")
    current_evidence: Optional[str] = Field(None, description="What the CV shows related to this")
    missing_element: str = Field(description="Specific thing that's missing or weak")
    recommendation: str = Field(description="How to address this gap")
    learnable: bool = Field(default=True, description="Whether this can be learned/acquired")
    estimated_time: Optional[str] = Field(None, description="Estimated time to address if learnable")


class GapAnalysis(BaseModel):
    """Full gap analysis result - output from Analyzer agent"""
    
    fit_score: int = Field(description="Overall fit score 0-100", ge=0, le=100)
    ats_score: int = Field(description="ATS keyword match percentage 0-100", ge=0, le=100)
    
    summary: str = Field(description="Overall analysis summary")
    
    strengths: List[str] = Field(default=[], description="Key matching strengths")
    gaps: List[GapItem] = Field(default=[], description="Gaps with severity and recommendations")
    
    action_items: List[str] = Field(
        default=[], 
        description="Prioritized list of actions to improve candidacy"
    )
    
    keywords_present: List[str] = Field(default=[], description="ATS keywords found in CV")
    keywords_missing: List[str] = Field(default=[], description="ATS keywords to add")


class GapAnalysisCreate(BaseModel):
    """Schema for creating a gap analysis"""
    
    job_id: str = Field(description="UUID of the job posting")
    cv_version_id: str = Field(description="UUID of the CV version")


class GapAnalysisResponse(BaseModel):
    """Schema for gap analysis responses"""
    id: str
    job_id: str
    cv_version_id: str
    fit_score: Optional[int]
    ats_score: Optional[int]
    summary: Optional[str]
    strengths: Optional[List[str]]
    gaps: Optional[List[GapItem]]
    action_items: Optional[List[str]]
    created_at: datetime


# ==============================================================================
# CV Rewrite Schemas
# ==============================================================================

class CVRewrite(BaseModel):
    """CV rewrite tailored to a specific job - output from Analyzer agent"""
    
    rewritten_summary: str = Field(description="Tailored professional summary")
    
    rewritten_bullets: List[Dict] = Field(
        description="Improved experience bullets with original and improved versions",
        example=[{"original": "...", "improved": "...", "experience_index": 0}]
    )
    
    skills_to_highlight: List[str] = Field(
        description="Skills to emphasize for this specific role"
    )
    
    keywords_added: List[str] = Field(
        default=[], 
        description="ATS keywords incorporated into the rewrite"
    )
    
    cover_letter: Optional[str] = Field(None, description="Generated cover letter")
    linkedin_summary: Optional[str] = Field(None, description="LinkedIn-optimized summary")


class CVRewriteResponse(CVRewrite):
    """Schema for CV rewrite responses"""
    id: str
    gap_analysis_id: str
    created_at: datetime


# ==============================================================================
# Job Application Schemas
# ==============================================================================

class JobApplicationCreate(BaseModel):
    """Schema for creating a job application"""
    
    job_id: str = Field(description="UUID of the job posting")
    cv_version_id: Optional[str] = Field(None, description="UUID of the CV version used")
    gap_analysis_id: Optional[str] = Field(None, description="UUID of the gap analysis")
    status: ApplicationStatus = Field(default="saved", description="Application status")
    notes: Optional[str] = Field(None, description="Personal notes")


class JobApplicationUpdate(BaseModel):
    """Schema for updating a job application"""
    
    status: Optional[ApplicationStatus] = Field(None, description="New status")
    cv_version_id: Optional[str] = Field(None, description="UUID of CV version used")
    applied_at: Optional[datetime] = Field(None, description="When application was submitted")
    response_date: Optional[datetime] = Field(None, description="When company responded")
    next_step: Optional[str] = Field(None, description="Next step in process")
    next_step_date: Optional[datetime] = Field(None, description="Date of next step")
    contact_name: Optional[str] = Field(None, description="Recruiter/hiring manager name")
    contact_email: Optional[str] = Field(None, description="Recruiter/hiring manager email")
    notes: Optional[str] = Field(None, description="Personal notes")


class JobApplicationResponse(JobApplicationCreate):
    """Schema for job application responses"""
    id: str
    user_id: str
    applied_at: Optional[datetime]
    last_status_change: datetime
    response_date: Optional[datetime]
    next_step: Optional[str]
    next_step_date: Optional[datetime]
    contact_name: Optional[str]
    contact_email: Optional[str]
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# Interview Schemas
# ==============================================================================

class InterviewQuestion(BaseModel):
    """Individual interview question"""
    
    id: str = Field(description="Unique question ID")
    question: str = Field(description="The interview question")
    type: InterviewType = Field(description="Type of question")
    topic: str = Field(description="Topic area being tested")
    difficulty: QuestionDifficulty = Field(description="Difficulty level")
    
    what_theyre_testing: str = Field(description="What this question assesses")
    sample_answer_outline: str = Field(description="Outline of a good answer structure")
    follow_up_questions: List[str] = Field(default=[], description="Potential follow-up questions")
    
    company_specific: bool = Field(default=False, description="Whether specific to this company")
    gap_related: bool = Field(default=False, description="Whether addresses a gap from analysis")


class AnswerEvaluation(BaseModel):
    """Evaluation of an interview answer"""
    
    question_id: str = Field(description="ID of the question being evaluated")
    
    score: int = Field(description="Score 1-5", ge=1, le=5)
    star_method_used: Optional[bool] = Field(None, description="For behavioral: was STAR used?")
    
    clarity: int = Field(description="Clarity of communication 1-5", ge=1, le=5)
    relevance: int = Field(description="Relevance to the question 1-5", ge=1, le=5)
    depth: int = Field(description="Depth of answer 1-5", ge=1, le=5)
    
    strengths: List[str] = Field(default=[], description="What was done well")
    improvements: List[str] = Field(default=[], description="Areas for improvement")
    
    better_answer_example: str = Field(description="Example of an improved answer")


class InterviewPack(BaseModel):
    """Full interview preparation pack - output from Interviewer agent"""
    
    job_id: str = Field(description="UUID of the job posting")
    company: Optional[str] = Field(None, description="Company name")
    role: Optional[str] = Field(None, description="Role title")
    
    questions: List[InterviewQuestion] = Field(description="Prepared interview questions")
    
    focus_areas: List[str] = Field(
        description="Key areas to focus on based on job and any gaps"
    )
    
    company_specific_tips: List[str] = Field(
        default=[], 
        description="Tips specific to this company's interview process"
    )
    
    general_tips: List[str] = Field(
        default=[],
        description="General interview tips for this role type"
    )


class InterviewSessionCreate(BaseModel):
    """Schema for creating an interview session"""
    
    job_application_id: Optional[str] = Field(None, description="UUID of job application")
    job_id: Optional[str] = Field(None, description="UUID of job posting for practice")
    session_type: SessionType = Field(description="Type of session")
    interview_type: Optional[InterviewType] = Field(None, description="Type of interview")


class InterviewSessionResponse(InterviewSessionCreate):
    """Schema for interview session responses"""
    id: str
    user_id: str
    questions: Optional[List[InterviewQuestion]] = None
    answers: Optional[List[Dict]] = None
    evaluations: Optional[List[AnswerEvaluation]] = None
    overall_score: Optional[int] = None
    focus_areas: Optional[List[str]] = None
    company_tips: Optional[List[str]] = None
    duration_minutes: Optional[int] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# ==============================================================================
# Job (Async Processing) Schemas
# ==============================================================================

class JobCreate(BaseModel):
    """Schema for creating an async job"""
    
    clerk_user_id: str = Field(description="Clerk user ID for the job owner")
    job_type: JobType = Field(description="Type of job to run")
    request_payload: Optional[Dict] = Field(None, description="Request parameters for the job")
    input_data: Optional[Dict] = Field(None, description="Input parameters for the job")


class JobUpdate(BaseModel):
    """Schema for updating job status"""
    
    status: JobStatus = Field(description="New status")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    progress_percentage: Optional[int] = Field(None, description="Progress 0-100", ge=0, le=100)


class JobResponse(BaseModel):
    """Schema for job responses"""
    id: str
    user_id: str
    job_type: JobType
    status: JobStatus
    input_data: Optional[Dict] = None
    extractor_payload: Optional[Dict] = None
    analyzer_payload: Optional[Dict] = None
    interviewer_payload: Optional[Dict] = None
    charter_payload: Optional[Dict] = None
    summary_payload: Optional[Dict] = None
    error_message: Optional[str] = None
    progress_percentage: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ==============================================================================
# Analytics Schemas (for Charter agent)
# ==============================================================================

class ApplicationFunnelData(BaseModel):
    """Application funnel analytics"""
    
    total_saved: int = Field(description="Total jobs saved")
    total_applied: int = Field(description="Total applications submitted")
    total_responses: int = Field(description="Total responses received")
    total_interviews: int = Field(description="Total interview invites")
    total_offers: int = Field(description="Total offers received")
    
    response_rate: float = Field(description="Percentage of applications with responses")
    interview_rate: float = Field(description="Percentage of applications with interviews")
    offer_rate: float = Field(description="Percentage of interviews resulting in offers")


class SkillGapFrequency(BaseModel):
    """Frequency of skill gaps across job analyses"""
    
    skill: str = Field(description="The skill gap")
    frequency: int = Field(description="Number of jobs requiring this skill")
    average_severity: str = Field(description="Average severity across gaps")
    recommendations: List[str] = Field(description="Common recommendations")


class ApplicationAnalytics(BaseModel):
    """Full application analytics - output from Charter agent"""
    
    funnel: ApplicationFunnelData = Field(description="Application funnel metrics")
    
    skill_gaps: List[SkillGapFrequency] = Field(
        description="Most common missing skills"
    )
    
    response_rate_by_role: Dict[str, float] = Field(
        description="Response rates by role type"
    )
    
    average_fit_score: float = Field(description="Average fit score across jobs")
    
    best_performing_cv: Optional[str] = Field(
        None, description="CV version with best response rate"
    )
    
    top_companies_by_response: List[str] = Field(
        default=[], description="Companies with highest response rates"
    )
    
    average_days_to_response: Optional[float] = Field(
        None, description="Average days between application and response"
    )
