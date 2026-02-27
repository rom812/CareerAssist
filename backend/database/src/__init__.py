"""
Database package for CareerAssist
Provides database models, schemas, and Data API client
"""

from .client import DataAPIClient
from .models import Database
from .schemas import (
    AnswerEvaluation,
    ApplicationAnalytics,
    # Analytics schemas
    ApplicationFunnelData,
    ApplicationStatus,
    CVProfile,
    # CV rewrite schemas
    CVRewrite,
    CVRewriteResponse,
    CVVersionCreate,
    CVVersionResponse,
    EducationEntry,
    ExperienceEntry,
    GapAnalysis,
    GapAnalysisCreate,
    GapAnalysisResponse,
    # Gap analysis schemas
    GapItem,
    GapSeverity,
    InterviewPack,
    # Interview schemas
    InterviewQuestion,
    InterviewSessionCreate,
    InterviewSessionResponse,
    InterviewType,
    # Job application schemas
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
    # Async job schemas
    JobCreate,
    JobPostingCreate,
    JobPostingResponse,
    JobProfile,
    # Job posting schemas
    JobRequirement,
    JobResponse,
    JobStatus,
    JobType,
    JobUpdate,
    # Types
    ProficiencyLevel,
    QuestionDifficulty,
    RemotePolicy,
    RequirementType,
    SeniorityLevel,
    SessionType,
    SkillCategory,
    # CV schemas
    SkillEntry,
    SkillGapFrequency,
    # User schemas
    UserProfileCreate,
    UserProfileResponse,
)

# Backwards compatibility aliases
UserCreate = UserProfileCreate

__all__ = [
    # Core
    "Database",
    "DataAPIClient",
    # Types
    "ProficiencyLevel",
    "SeniorityLevel",
    "RemotePolicy",
    "SkillCategory",
    "RequirementType",
    "GapSeverity",
    "InterviewType",
    "QuestionDifficulty",
    "SessionType",
    "ApplicationStatus",
    "JobType",
    "JobStatus",
    # User
    "UserCreate",
    "UserProfileCreate",
    "UserProfileResponse",
    # CV
    "SkillEntry",
    "ExperienceEntry",
    "EducationEntry",
    "CVProfile",
    "CVVersionCreate",
    "CVVersionResponse",
    # Job Posting
    "JobRequirement",
    "JobProfile",
    "JobPostingCreate",
    "JobPostingResponse",
    # Gap Analysis
    "GapItem",
    "GapAnalysis",
    "GapAnalysisCreate",
    "GapAnalysisResponse",
    # CV Rewrite
    "CVRewrite",
    "CVRewriteResponse",
    # Job Application
    "JobApplicationCreate",
    "JobApplicationUpdate",
    "JobApplicationResponse",
    # Interview
    "InterviewQuestion",
    "AnswerEvaluation",
    "InterviewPack",
    "InterviewSessionCreate",
    "InterviewSessionResponse",
    # Async Job
    "JobCreate",
    "JobUpdate",
    "JobResponse",
    # Analytics
    "ApplicationFunnelData",
    "SkillGapFrequency",
    "ApplicationAnalytics",
]
