"""
Database package for CareerAssist
Provides database models, schemas, and Data API client
"""

from .client import DataAPIClient
from .models import Database
from .schemas import (
    # Types
    ProficiencyLevel,
    SeniorityLevel,
    RemotePolicy,
    SkillCategory,
    RequirementType,
    GapSeverity,
    InterviewType,
    QuestionDifficulty,
    SessionType,
    ApplicationStatus,
    JobType,
    JobStatus,
    
    # User schemas
    UserProfileCreate,
    UserProfileResponse,
    
    # CV schemas
    SkillEntry,
    ExperienceEntry,
    EducationEntry,
    CVProfile,
    CVVersionCreate,
    CVVersionResponse,
    
    # Job posting schemas
    JobRequirement,
    JobProfile,
    JobPostingCreate,
    JobPostingResponse,
    
    # Gap analysis schemas
    GapItem,
    GapAnalysis,
    GapAnalysisCreate,
    GapAnalysisResponse,
    
    # CV rewrite schemas
    CVRewrite,
    CVRewriteResponse,
    
    # Job application schemas
    JobApplicationCreate,
    JobApplicationUpdate,
    JobApplicationResponse,
    
    # Interview schemas
    InterviewQuestion,
    AnswerEvaluation,
    InterviewPack,
    InterviewSessionCreate,
    InterviewSessionResponse,
    
    # Async job schemas
    JobCreate,
    JobUpdate,
    JobResponse,
    
    # Analytics schemas
    ApplicationFunnelData,
    SkillGapFrequency,
    ApplicationAnalytics,
)

# Backwards compatibility aliases
UserCreate = UserProfileCreate

__all__ = [
    # Core
    'Database',
    'DataAPIClient',
    
    # Types
    'ProficiencyLevel',
    'SeniorityLevel',
    'RemotePolicy',
    'SkillCategory',
    'RequirementType',
    'GapSeverity',
    'InterviewType',
    'QuestionDifficulty',
    'SessionType',
    'ApplicationStatus',
    'JobType',
    'JobStatus',
    
    # User
    'UserCreate',
    'UserProfileCreate',
    'UserProfileResponse',
    
    # CV
    'SkillEntry',
    'ExperienceEntry',
    'EducationEntry',
    'CVProfile',
    'CVVersionCreate',
    'CVVersionResponse',
    
    # Job Posting
    'JobRequirement',
    'JobProfile',
    'JobPostingCreate',
    'JobPostingResponse',
    
    # Gap Analysis
    'GapItem',
    'GapAnalysis',
    'GapAnalysisCreate',
    'GapAnalysisResponse',
    
    # CV Rewrite
    'CVRewrite',
    'CVRewriteResponse',
    
    # Job Application
    'JobApplicationCreate',
    'JobApplicationUpdate',
    'JobApplicationResponse',
    
    # Interview
    'InterviewQuestion',
    'AnswerEvaluation',
    'InterviewPack',
    'InterviewSessionCreate',
    'InterviewSessionResponse',
    
    # Async Job
    'JobCreate',
    'JobUpdate',
    'JobResponse',
    
    # Analytics
    'ApplicationFunnelData',
    'SkillGapFrequency',
    'ApplicationAnalytics',
]