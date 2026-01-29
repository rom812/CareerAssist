"""
FastAPI backend for CareerAssist - AI-powered Career Advisor
Handles all API routes with Clerk JWT authentication
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Depends, status, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError
import boto3
from mangum import Mangum
from dotenv import load_dotenv
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path

from .pdf_extractor import extract_text_from_pdf, validate_pdf_file, PDFExtractionError

# Load environment variables from project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CareerAssist API",
    description="Backend API for AI-powered career assistance",
    version="1.0.0"
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handlers
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid input data. Please check your request and try again."}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    user_friendly_messages = {
        401: "Your session has expired. Please sign in again.",
        403: "You don't have permission to access this resource.",
        404: "The requested resource was not found.",
        429: "Too many requests. Please slow down and try again later.",
        500: "An internal error occurred. Please try again later.",
        503: "The service is temporarily unavailable. Please try again later."
    }
    message = user_friendly_messages.get(exc.status_code, exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": message})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Our team has been notified."}
    )


# ==============================================================================
# Database Access
# ==============================================================================

class DatabaseClient:
    """Simple Aurora Data API client for CareerAssist"""
    
    def __init__(self):
        self.rds_client = boto3.client('rds-data', region_name=os.getenv('DEFAULT_AWS_REGION', 'us-east-1'))
        self.cluster_arn = os.getenv('AURORA_CLUSTER_ARN', '')
        self.secret_arn = os.getenv('AURORA_SECRET_ARN', '')
        self.database = os.getenv('DATABASE_NAME', 'career')
    
    def execute(self, sql: str, params: Dict[str, Any] = None) -> List[Dict]:
        """Execute SQL and return results as list of dicts."""
        try:
            sql_params = []
            if params:
                for key, value in params.items():
                    param = {"name": key}
                    if value is None:
                        param["value"] = {"isNull": True}
                    elif isinstance(value, bool):
                        param["value"] = {"booleanValue": value}
                    elif isinstance(value, int):
                        param["value"] = {"longValue": value}
                    elif isinstance(value, float):
                        param["value"] = {"doubleValue": value}
                    elif isinstance(value, (dict, list)):
                        param["value"] = {"stringValue": json.dumps(value)}
                    else:
                        param["value"] = {"stringValue": str(value)}
                    sql_params.append(param)
            
            response = self.rds_client.execute_statement(
                resourceArn=self.cluster_arn,
                secretArn=self.secret_arn,
                database=self.database,
                sql=sql,
                parameters=sql_params,
                includeResultMetadata=True
            )
            
            # Parse response into dicts
            results = []
            columns = [col['name'] for col in response.get('columnMetadata', [])]
            for record in response.get('records', []):
                row = {}
                for i, field in enumerate(record):
                    if 'isNull' in field and field['isNull']:
                        row[columns[i]] = None
                    elif 'stringValue' in field:
                        val = field['stringValue']
                        # Try to parse JSON fields
                        if columns[i].endswith('_json') or columns[i].endswith('_payload') or columns[i] in ['target_roles', 'target_locations', 'parsed_json', 'strengths', 'gaps', 'action_items', 'questions', 'answers', 'evaluations', 'focus_areas', 'company_tips', 'input_data', 'request_payload', 'metadata']:
                            try:
                                row[columns[i]] = json.loads(val)
                            except:
                                row[columns[i]] = val
                        else:
                            row[columns[i]] = val
                    elif 'longValue' in field:
                        row[columns[i]] = field['longValue']
                    elif 'doubleValue' in field:
                        row[columns[i]] = field['doubleValue']
                    elif 'booleanValue' in field:
                        row[columns[i]] = field['booleanValue']
                    else:
                        row[columns[i]] = None
                results.append(row)
            
            return results
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise

    def execute_one(self, sql: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Execute and return single result."""
        results = self.execute(sql, params)
        return results[0] if results else None


# Initialize database client (lazy)
_db = None
def get_db() -> DatabaseClient:
    global _db
    if _db is None:
        _db = DatabaseClient()
    return _db


# SQS client for job queueing
sqs_client = boto3.client('sqs', region_name=os.getenv('DEFAULT_AWS_REGION', 'us-east-1'))
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL', '')

# Clerk authentication
clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
clerk_guard = ClerkHTTPBearer(clerk_config)

async def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(clerk_guard)) -> str:
    """Extract user ID from validated Clerk token"""
    user_id = creds.decoded["sub"]
    logger.info(f"Authenticated user: {user_id}")
    return user_id


# ==============================================================================
# Pydantic Models
# ==============================================================================

class UserResponse(BaseModel):
    user: Dict[str, Any]
    created: bool

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    target_roles: Optional[List[str]] = None
    target_locations: Optional[List[str]] = None
    years_of_experience: Optional[int] = None

class CVVersionCreate(BaseModel):
    raw_text: str = Field(min_length=50)
    version_name: str = Field(default="Default", max_length=100)
    is_primary: bool = False
    file_type: str = Field(default="paste")

class JobPostingCreate(BaseModel):
    raw_text: str = Field(min_length=50)
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    url: Optional[str] = None
    location: Optional[str] = None
    remote_policy: Optional[str] = None
    notes: Optional[str] = None

class AnalysisRequest(BaseModel):
    job_type: str = Field(description="Type: cv_parse, job_parse, gap_analysis, cv_rewrite, interview_prep, full_analysis")
    cv_version_id: Optional[str] = None
    job_posting_id: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)

class AnalysisResponse(BaseModel):
    job_id: str
    message: str


# ==============================================================================
# API Routes
# ==============================================================================

@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "CareerAssist", "timestamp": datetime.now().isoformat()}


# ---------------------------
# User Profile Endpoints
# ---------------------------

@app.get("/api/user", response_model=UserResponse)
async def get_or_create_user(
    clerk_user_id: str = Depends(get_current_user_id),
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard)
):
    """Get user profile or create if first time"""
    db = get_db()
    
    try:
        # Check if user exists
        user = db.execute_one(
            "SELECT * FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        
        if user:
            return UserResponse(user=user, created=False)
        
        # Create new user
        token_data = creds.decoded
        full_name = token_data.get('name') or token_data.get('email', '').split('@')[0] or "New User"
        email = token_data.get('email', '')
        
        new_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO user_profiles (id, clerk_user_id, full_name, email, target_roles, target_locations)
               VALUES (:id::uuid, :clerk_user_id, :full_name, :email, :target_roles::jsonb, :target_locations::jsonb)""",
            {
                "id": new_id,
                "clerk_user_id": clerk_user_id,
                "full_name": full_name,
                "email": email,
                "target_roles": json.dumps([]),
                "target_locations": json.dumps([])
            }
        )
        
        # Fetch created user
        created_user = db.execute_one(
            "SELECT * FROM user_profiles WHERE id = :id::uuid",
            {"id": new_id}
        )
        logger.info(f"Created new user profile: {clerk_user_id}")
        return UserResponse(user=created_user, created=True)
        
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        raise HTTPException(status_code=500, detail="Failed to load user profile")


@app.put("/api/user")
async def update_user(user_update: UserUpdate, clerk_user_id: str = Depends(get_current_user_id)):
    """Update user profile"""
    db = get_db()
    
    try:
        # Get user
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build update
        update_data = user_update.model_dump(exclude_unset=True)
        if not update_data:
            return user
        
        set_clauses = []
        params = {"user_id": user["id"]}
        for key, value in update_data.items():
            set_clauses.append(f"{key} = :{key}")
            params[key] = value
        
        sql = f"UPDATE user_profiles SET {', '.join(set_clauses)} WHERE id = :user_id::uuid"
        db.execute(sql, params)
        
        # Return updated user
        return db.execute_one("SELECT * FROM user_profiles WHERE id = :id::uuid", {"id": user["id"]})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# CV Versions Endpoints
# ---------------------------

@app.get("/api/cv-versions")
async def list_cv_versions(clerk_user_id: str = Depends(get_current_user_id)):
    """List user's CV versions"""
    db = get_db()
    
    try:
        # Get user ID
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            return []
        
        cv_versions = db.execute(
            """SELECT id, version_name, is_primary, file_type, created_at, updated_at,
                      LEFT(raw_text, 200) as preview, parsed_json
               FROM cv_versions WHERE user_id = :user_id::uuid ORDER BY is_primary DESC, created_at DESC""",
            {"user_id": user["id"]}
        )
        return cv_versions
        
    except Exception as e:
        logger.error(f"Error listing CV versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cv-versions")
async def create_cv_version(cv_data: CVVersionCreate, clerk_user_id: str = Depends(get_current_user_id)):
    """Create a new CV version"""
    db = get_db()
    
    try:
        # Get user ID
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # If this should be primary, unset any existing primary
        if cv_data.is_primary:
            db.execute(
                "UPDATE cv_versions SET is_primary = false WHERE user_id = :user_id::uuid",
                {"user_id": user["id"]}
            )
        
        # Create CV version
        new_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO cv_versions (id, user_id, raw_text, version_name, is_primary, file_type)
               VALUES (:id::uuid, :user_id::uuid, :raw_text, :version_name, :is_primary, :file_type)""",
            {
                "id": new_id,
                "user_id": user["id"],
                "raw_text": cv_data.raw_text,
                "version_name": cv_data.version_name,
                "is_primary": cv_data.is_primary,
                "file_type": cv_data.file_type
            }
        )
        
        # Return created version
        return db.execute_one("SELECT * FROM cv_versions WHERE id = :id::uuid", {"id": new_id})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating CV version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cv-versions/{cv_id}")
async def get_cv_version(cv_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Get a specific CV version"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        cv = db.execute_one(
            "SELECT * FROM cv_versions WHERE id = :cv_id::uuid AND user_id = :user_id::uuid",
            {"cv_id": cv_id, "user_id": user["id"]}
        )
        if not cv:
            raise HTTPException(status_code=404, detail="CV not found")
        
        return cv
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CV version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cv-versions/{cv_id}")
async def delete_cv_version(cv_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Delete a CV version"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = db.execute(
            "DELETE FROM cv_versions WHERE id = :cv_id::uuid AND user_id = :user_id::uuid RETURNING id",
            {"cv_id": cv_id, "user_id": user["id"]}
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="CV not found")
        
        return {"message": "CV version deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting CV version: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cv-versions/upload")
async def upload_cv_file(
    file: UploadFile = File(...),
    version_name: str = Form("My CV"),
    is_primary: bool = Form(False),
    clerk_user_id: str = Depends(get_current_user_id)
):
    """
    Upload a PDF CV file for parsing.
    
    Accepts a PDF file, extracts text using pdfplumber, creates a cv_version record,
    and automatically triggers the cv_parse job for AI-powered extraction.
    
    Design Log: /design-log/frontend/011-cv-pdf-upload-parser.md
    """
    db = get_db()
    
    try:
        # Get user
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Read file bytes
        file_bytes = await file.read()
        
        # Validate the PDF file
        validation_error = validate_pdf_file(file_bytes)
        if validation_error:
            raise HTTPException(status_code=400, detail=validation_error)
        
        # Extract text from PDF using pdfplumber
        try:
            raw_text = extract_text_from_pdf(file_bytes)
        except PDFExtractionError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Check minimum text length
        if len(raw_text) < 100:
            raise HTTPException(
                status_code=400,
                detail="Could not extract enough text from PDF. Please ensure the PDF contains selectable text, not just images."
            )
        
        # If this should be primary, unset any existing primary
        if is_primary:
            db.execute(
                "UPDATE cv_versions SET is_primary = false WHERE user_id = :user_id::uuid",
                {"user_id": user["id"]}
            )
        
        # Create CV version
        new_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO cv_versions (id, user_id, raw_text, version_name, is_primary, file_type)
               VALUES (:id::uuid, :user_id::uuid, :raw_text, :version_name, :is_primary, 'pdf')""",
            {
                "id": new_id,
                "user_id": user["id"],
                "raw_text": raw_text,
                "version_name": version_name,
                "is_primary": is_primary
            }
        )
        
        # Auto-trigger CV parsing job
        input_data = {
            "cv_text": raw_text,
            "cv_version_id": new_id,
            "options": {}
        }
        
        job_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO jobs (id, user_id, clerk_user_id, job_type, status, input_data)
               VALUES (:id::uuid, :user_id::uuid, :clerk_user_id, 'cv_parse', 'pending', :input_data::jsonb)""",
            {
                "id": job_id,
                "user_id": user["id"],
                "clerk_user_id": clerk_user_id,
                "input_data": json.dumps(input_data)
            }
        )
        
        # Queue for processing via SQS
        if SQS_QUEUE_URL:
            message = {
                "job_id": job_id,
                "clerk_user_id": clerk_user_id,
                "job_type": "cv_parse",
                "input_data": input_data
            }
            sqs_client.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            logger.info(f"CV upload: queued parse job {job_id} for CV {new_id}")
        else:
            logger.warning("SQS_QUEUE_URL not configured, CV created but parsing not queued")
        
        # Get the created CV version
        cv_version = db.execute_one(
            "SELECT * FROM cv_versions WHERE id = :id::uuid",
            {"id": new_id}
        )
        
        logger.info(f"CV uploaded successfully: {new_id}, extracted {len(raw_text)} characters")
        
        return {
            "cv_version": cv_version,
            "job_id": job_id,
            "message": "CV uploaded successfully. AI parsing has started.",
            "extracted_length": len(raw_text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading CV file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process CV upload")


# ---------------------------
# Job Postings Endpoints
# ---------------------------

@app.get("/api/job-postings")
async def list_job_postings(clerk_user_id: str = Depends(get_current_user_id)):
    """List user's saved job postings"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            return []
        
        jobs = db.execute(
            """SELECT id, company_name, role_title, location, remote_policy, url, 
                      is_saved, created_at, updated_at, parsed_json,
                      LEFT(raw_text, 300) as preview
               FROM job_postings WHERE user_id = :user_id::uuid ORDER BY created_at DESC""",
            {"user_id": user["id"]}
        )
        return jobs
        
    except Exception as e:
        logger.error(f"Error listing job postings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/job-postings")
async def create_job_posting(job_data: JobPostingCreate, clerk_user_id: str = Depends(get_current_user_id)):
    """Create a new job posting"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        new_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO job_postings (id, user_id, raw_text, company_name, role_title, url, location, remote_policy, notes)
               VALUES (:id::uuid, :user_id::uuid, :raw_text, :company_name, :role_title, :url, :location, :remote_policy, :notes)""",
            {
                "id": new_id,
                "user_id": user["id"],
                "raw_text": job_data.raw_text,
                "company_name": job_data.company_name,
                "role_title": job_data.role_title,
                "url": job_data.url,
                "location": job_data.location,
                "remote_policy": job_data.remote_policy,
                "notes": job_data.notes
            }
        )
        
        return db.execute_one("SELECT * FROM job_postings WHERE id = :id::uuid", {"id": new_id})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job posting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/job-postings/{job_id}")
async def get_job_posting(job_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Get a specific job posting"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        job = db.execute_one(
            "SELECT * FROM job_postings WHERE id = :job_id::uuid AND user_id = :user_id::uuid",
            {"job_id": job_id, "user_id": user["id"]}
        )
        if not job:
            raise HTTPException(status_code=404, detail="Job posting not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job posting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/job-postings/{job_id}")
async def delete_job_posting(job_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Delete a job posting"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        result = db.execute(
            "DELETE FROM job_postings WHERE id = :job_id::uuid AND user_id = :user_id::uuid RETURNING id",
            {"job_id": job_id, "user_id": user["id"]}
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Job posting not found")
        
        return {"message": "Job posting deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job posting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Gap Analysis Endpoints
# ---------------------------

@app.get("/api/gap-analyses")
async def list_gap_analyses(clerk_user_id: str = Depends(get_current_user_id)):
    """List user's gap analyses"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            return []
        
        analyses = db.execute(
            """SELECT ga.id, ga.fit_score, ga.ats_score, ga.summary, ga.created_at,
                      jp.company_name, jp.role_title, cv.version_name as cv_version
               FROM gap_analyses ga
               JOIN job_postings jp ON ga.job_id = jp.id
               JOIN cv_versions cv ON ga.cv_version_id = cv.id
               WHERE jp.user_id = :user_id::uuid
               ORDER BY ga.created_at DESC""",
            {"user_id": user["id"]}
        )
        return analyses
        
    except Exception as e:
        logger.error(f"Error listing gap analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gap-analyses/{analysis_id}")
async def get_gap_analysis(analysis_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Get a specific gap analysis"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        analysis = db.execute_one(
            """SELECT ga.*, jp.company_name, jp.role_title, cv.version_name as cv_version
               FROM gap_analyses ga
               JOIN job_postings jp ON ga.job_id = jp.id
               JOIN cv_versions cv ON ga.cv_version_id = cv.id
               WHERE ga.id = :analysis_id::uuid AND jp.user_id = :user_id::uuid""",
            {"analysis_id": analysis_id, "user_id": user["id"]}
        )
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Gap analysis not found")
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting gap analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Analysis Jobs Endpoints (Trigger Agents)
# ---------------------------

@app.post("/api/analyze", response_model=AnalysisResponse)
async def trigger_analysis(request: AnalysisRequest, clerk_user_id: str = Depends(get_current_user_id)):
    """Trigger a career analysis job"""
    db = get_db()
    
    try:
        # Get user
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build input data based on job type
        input_data = {"options": request.options}
        
        if request.cv_version_id:
            cv = db.execute_one(
                "SELECT raw_text, parsed_json FROM cv_versions WHERE id = :cv_id::uuid AND user_id = :user_id::uuid",
                {"cv_id": request.cv_version_id, "user_id": user["id"]}
            )
            if cv:
                input_data["cv_text"] = cv["raw_text"]
                input_data["cv_profile"] = cv.get("parsed_json")
                input_data["cv_version_id"] = request.cv_version_id
        
        if request.job_posting_id:
            job_posting = db.execute_one(
                "SELECT raw_text, parsed_json FROM job_postings WHERE id = :job_id::uuid AND user_id = :user_id::uuid",
                {"job_id": request.job_posting_id, "user_id": user["id"]}
            )
            if job_posting:
                input_data["job_text"] = job_posting["raw_text"]
                input_data["job_profile"] = job_posting.get("parsed_json")
                input_data["job_posting_id"] = request.job_posting_id
        
        # Create job record
        job_id = str(uuid.uuid4())
        db.execute(
            """INSERT INTO jobs (id, user_id, clerk_user_id, job_type, status, input_data, request_payload)
               VALUES (:id::uuid, :user_id::uuid, :clerk_user_id, :job_type, 'pending', :input_data::jsonb, :request_payload::jsonb)""",
            {
                "id": job_id,
                "user_id": user["id"],
                "clerk_user_id": clerk_user_id,
                "job_type": request.job_type,
                "input_data": json.dumps(input_data),
                "request_payload": json.dumps(request.model_dump())
            }
        )
        
        # Send to SQS for processing
        if SQS_QUEUE_URL:
            message = {
                "job_id": job_id,
                "clerk_user_id": clerk_user_id,
                "job_type": request.job_type,
                "input_data": input_data
            }
            sqs_client.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            logger.info(f"Sent analysis job to SQS: {job_id}")
        else:
            logger.warning("SQS_QUEUE_URL not configured, job created but not queued")
        
        job_type_messages = {
            "cv_parse": "CV parsing started. Your CV is being analyzed.",
            "job_parse": "Job parsing started. The job posting is being analyzed.",
            "gap_analysis": "Gap analysis started. Comparing your CV to the job requirements.",
            "cv_rewrite": "CV rewrite started. Optimizing your CV for this role.",
            "interview_prep": "Interview prep started. Generating tailored questions.",
            "full_analysis": "Full analysis started. This may take a minute."
        }
        
        return AnalysisResponse(
            job_id=job_id,
            message=job_type_messages.get(request.job_type, "Analysis started.")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs")
async def list_jobs(clerk_user_id: str = Depends(get_current_user_id)):
    """List user's analysis jobs"""
    db = get_db()
    
    try:
        jobs = db.execute(
            """SELECT id, job_type, status, progress_percentage, error_message, 
                      created_at, started_at, completed_at
               FROM jobs WHERE clerk_user_id = :clerk_user_id 
               ORDER BY created_at DESC LIMIT 50""",
            {"clerk_user_id": clerk_user_id}
        )
        return {"jobs": jobs}
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Get job status and results"""
    db = get_db()
    
    try:
        job = db.execute_one(
            """SELECT * FROM jobs WHERE id = :job_id::uuid AND clerk_user_id = :clerk_user_id""",
            {"job_id": job_id, "clerk_user_id": clerk_user_id}
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Interview Sessions Endpoints
# ---------------------------

@app.get("/api/interview-sessions")
async def list_interview_sessions(clerk_user_id: str = Depends(get_current_user_id)):
    """List user's interview sessions"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            return []
        
        sessions = db.execute(
            """SELECT id, session_type, interview_type, overall_score, 
                      duration_minutes, completed_at, created_at
               FROM interview_sessions WHERE user_id = :user_id::uuid 
               ORDER BY created_at DESC""",
            {"user_id": user["id"]}
        )
        return sessions
        
    except Exception as e:
        logger.error(f"Error listing interview sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/interview-sessions/{session_id}")
async def get_interview_session(session_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """Get a specific interview session"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        session = db.execute_one(
            "SELECT * FROM interview_sessions WHERE id = :session_id::uuid AND user_id = :user_id::uuid",
            {"session_id": session_id, "user_id": user["id"]}
        )
        
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting interview session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Dashboard Analytics
# ---------------------------

@app.get("/api/dashboard-stats")
async def get_dashboard_stats(clerk_user_id: str = Depends(get_current_user_id)):
    """Get dashboard statistics for the user"""
    db = get_db()
    
    try:
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            return {
                "cv_count": 0,
                "job_count": 0,
                "analysis_count": 0,
                "avg_fit_score": None,
                "recent_analyses": []
            }
        
        # CV count
        cv_result = db.execute_one(
            "SELECT COUNT(*) as count FROM cv_versions WHERE user_id = :user_id::uuid",
            {"user_id": user["id"]}
        )
        
        # Job count
        job_result = db.execute_one(
            "SELECT COUNT(*) as count FROM job_postings WHERE user_id = :user_id::uuid",
            {"user_id": user["id"]}
        )
        
        # Analysis stats
        analysis_stats = db.execute_one(
            """SELECT COUNT(*) as count, AVG(fit_score) as avg_fit
               FROM gap_analyses ga
               JOIN job_postings jp ON ga.job_id = jp.id
               WHERE jp.user_id = :user_id::uuid""",
            {"user_id": user["id"]}
        )
        
        # Recent analyses
        recent = db.execute(
            """SELECT ga.id, ga.fit_score, ga.ats_score, ga.created_at,
                      jp.company_name, jp.role_title
               FROM gap_analyses ga
               JOIN job_postings jp ON ga.job_id = jp.id
               WHERE jp.user_id = :user_id::uuid
               ORDER BY ga.created_at DESC LIMIT 5""",
            {"user_id": user["id"]}
        )
        
        return {
            "cv_count": cv_result["count"] if cv_result else 0,
            "job_count": job_result["count"] if job_result else 0,
            "analysis_count": analysis_stats["count"] if analysis_stats else 0,
            "avg_fit_score": round(analysis_stats["avg_fit"], 1) if analysis_stats and analysis_stats.get("avg_fit") else None,
            "recent_analyses": recent
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Research Findings Endpoints (Public - no auth required)
# ---------------------------

class ResearchFindingResponse(BaseModel):
    id: str
    topic: str
    category: str
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_url: Optional[str] = None
    relevance_score: int
    is_featured: bool
    created_at: str
    updated_at: str


@app.get("/api/research-findings")
async def list_research_findings(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    featured_only: bool = False
):
    """
    List research findings from the Researcher agent.
    Public endpoint - no authentication required.
    
    Query params:
    - category: Filter by category (role_trend, skill_demand, salary_insight, industry_news)
    - limit: Max results (default 20, max 50)
    - offset: Pagination offset
    - featured_only: Only return featured items
    """
    db = get_db()
    
    # Validate and cap limit
    limit = min(limit, 50)
    
    try:
        # Build query based on filters
        where_clauses = []
        params = {"limit": limit, "offset": offset}
        
        if category:
            where_clauses.append("category = :category")
            params["category"] = category
        
        if featured_only:
            where_clauses.append("is_featured = true")
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        findings = db.execute(
            f"""SELECT id, topic, category, title, summary, content, metadata,
                       source_url, relevance_score, is_featured, 
                       created_at::text, updated_at::text
                FROM research_findings
                {where_sql}
                ORDER BY is_featured DESC, relevance_score DESC, created_at DESC
                LIMIT :limit OFFSET :offset""",
            params
        )
        
        # Get total count for pagination
        count_result = db.execute_one(
            f"SELECT COUNT(*) as total FROM research_findings {where_sql}",
            {k: v for k, v in params.items() if k not in ['limit', 'offset']}
        )
        
        return {
            "findings": findings,
            "total": count_result["total"] if count_result else 0,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            logger.warning("research_findings table does not exist - run migration 004")
            return {"findings": [], "total": 0, "limit": limit, "offset": offset}
        logger.error(f"Error listing research findings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trending-roles")
async def get_trending_roles(limit: int = 10):
    """
    Get trending roles from research findings.
    Public endpoint - no authentication required.
    """
    db = get_db()
    limit = min(limit, 20)
    
    try:
        findings = db.execute(
            """SELECT id, topic, category, title, summary, content, metadata,
                      source_url, relevance_score, is_featured,
                      created_at::text, updated_at::text
               FROM research_findings
               WHERE category = 'role_trend'
               ORDER BY is_featured DESC, relevance_score DESC, created_at DESC
               LIMIT :limit""",
            {"limit": limit}
        )
        
        return {"roles": findings, "count": len(findings)}
        
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            logger.warning("research_findings table does not exist - run migration 004")
            return {"roles": [], "count": 0}
        logger.error(f"Error getting trending roles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/research-findings/{finding_id}")
async def get_research_finding(finding_id: str):
    """
    Get a specific research finding by ID.
    Public endpoint - no authentication required.
    """
    db = get_db()
    
    try:
        finding = db.execute_one(
            """SELECT id, topic, category, title, summary, content, metadata,
                      source_url, relevance_score, is_featured,
                      created_at::text, updated_at::text
               FROM research_findings
               WHERE id = :finding_id::uuid""",
            {"finding_id": finding_id}
        )
        
        if not finding:
            raise HTTPException(status_code=404, detail="Research finding not found")
        
        return finding
        
    except HTTPException:
        raise
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            logger.warning("research_findings table does not exist - run migration 004")
            raise HTTPException(status_code=404, detail="Research findings not available")
        logger.error(f"Error getting research finding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market-insights-summary")
async def get_market_insights_summary():
    """
    Get a summary of market insights by category.
    Public endpoint - no authentication required.
    """
    db = get_db()
    
    try:
        # Get counts by category
        category_counts = db.execute(
            """SELECT category, COUNT(*) as count
               FROM research_findings
               GROUP BY category
               ORDER BY count DESC"""
        )
        
        # Get featured items
        featured = db.execute(
            """SELECT id, topic, category, title, summary, relevance_score, created_at::text
               FROM research_findings
               WHERE is_featured = true
               ORDER BY relevance_score DESC, created_at DESC
               LIMIT 5"""
        )
        
        # Get latest items
        latest = db.execute(
            """SELECT id, topic, category, title, summary, relevance_score, created_at::text
               FROM research_findings
               ORDER BY created_at DESC
               LIMIT 5"""
        )
        
        # Total count
        total = db.execute_one("SELECT COUNT(*) as total FROM research_findings")
        
        return {
            "total_findings": total["total"] if total else 0,
            "by_category": {item["category"]: item["count"] for item in category_counts},
            "featured": featured,
            "latest": latest
        }
        
    except Exception as e:
        if "relation" in str(e).lower() and "does not exist" in str(e).lower():
            logger.warning("research_findings table does not exist - run migration 004")
            return {"total_findings": 0, "by_category": {}, "featured": [], "latest": []}
        logger.error(f"Error getting market insights summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# Discovered Jobs Endpoints (Public - no auth for listing)
# ---------------------------

class DiscoveredJobResponse(BaseModel):
    id: str
    source: str
    source_url: Optional[str] = None
    company_name: Optional[str] = None
    role_title: str
    location: Optional[str] = None
    remote_policy: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description_text: Optional[str] = None
    requirements_text: Optional[str] = None
    discovered_at: str
    is_active: bool


@app.get("/api/discovered-jobs")
async def list_discovered_jobs(
    source: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    List AI-discovered job postings from Indeed/Glassdoor.
    Public endpoint - no authentication required.
    
    Query params:
    - source: Filter by source ('indeed' or 'glassdoor')
    - location: Filter by location (partial match)
    - limit: Max results (default 20, max 50)
    - offset: Pagination offset
    """
    db = get_db()
    
    # Validate and cap limit
    limit = min(limit, 50)
    
    try:
        # Build query based on filters
        where_clauses = ["is_active = true"]
        params = {"limit": limit, "offset": offset}
        
        if source:
            where_clauses.append("source = :source")
            params["source"] = source.lower()
        
        if location:
            where_clauses.append("location ILIKE :location")
            params["location"] = f"%{location}%"
        
        where_sql = " AND ".join(where_clauses)
        
        jobs = db.execute(
            f"""SELECT id, source, source_url, company_name, role_title,
                       location, remote_policy, salary_min, salary_max,
                       LEFT(description_text, 500) as description_text,
                       discovered_at::text, is_active
                FROM discovered_jobs
                WHERE {where_sql}
                ORDER BY discovered_at DESC
                LIMIT :limit OFFSET :offset""",
            params
        )
        
        # Get total count for pagination
        count_result = db.execute_one(
            f"SELECT COUNT(*) as total FROM discovered_jobs WHERE {where_sql}",
            {k: v for k, v in params.items() if k not in ['limit', 'offset']}
        )
        
        return {
            "jobs": jobs,
            "total": count_result["total"] if count_result else 0,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing discovered jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/discovered-jobs/{job_id}")
async def get_discovered_job(job_id: str):
    """
    Get a specific discovered job by ID.
    Public endpoint - no authentication required.
    """
    db = get_db()
    
    try:
        job = db.execute_one(
            """SELECT id, source, source_url, source_job_id, company_name, role_title,
                      location, remote_policy, salary_min, salary_max, salary_currency,
                      description_text, requirements_text, parsed_json, metadata,
                      discovered_at::text, is_active, created_at::text, updated_at::text
               FROM discovered_jobs
               WHERE id = :job_id::uuid""",
            {"job_id": job_id}
        )
        
        if not job:
            raise HTTPException(status_code=404, detail="Discovered job not found")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting discovered job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/discovered-jobs/{job_id}/save")
async def save_discovered_job(job_id: str, clerk_user_id: str = Depends(get_current_user_id)):
    """
    Save a discovered job to user's personal job postings.
    This copies the job to job_postings table for analysis.
    Requires authentication.
    """
    db = get_db()
    
    try:
        # Get user
        user = db.execute_one(
            "SELECT id FROM user_profiles WHERE clerk_user_id = :clerk_user_id",
            {"clerk_user_id": clerk_user_id}
        )
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get discovered job
        discovered = db.execute_one(
            """SELECT id, source, source_url, company_name, role_title,
                      location, remote_policy, salary_min, salary_max,
                      description_text, requirements_text
               FROM discovered_jobs WHERE id = :job_id::uuid""",
            {"job_id": job_id}
        )
        if not discovered:
            raise HTTPException(status_code=404, detail="Discovered job not found")
        
        # Check if already saved
        existing = db.execute_one(
            """SELECT id FROM job_postings 
               WHERE user_id = :user_id::uuid AND url = :url AND role_title = :role_title""",
            {
                "user_id": user["id"],
                "url": discovered.get("source_url") or "",
                "role_title": discovered.get("role_title")
            }
        )
        if existing:
            return {
                "success": False,
                "message": "You've already saved this job",
                "job_posting_id": existing["id"]
            }
        
        # Create job posting from discovered job
        new_id = str(uuid.uuid4())
        raw_text = discovered.get("description_text") or ""
        if discovered.get("requirements_text"):
            raw_text += f"\n\nRequirements:\n{discovered.get('requirements_text')}"
        
        # Ensure we have enough text for the job posting
        if not raw_text or len(raw_text) < 50:
            raw_text = f"Job: {discovered.get('role_title')} at {discovered.get('company_name')}\n\nLocation: {discovered.get('location') or 'Not specified'}"
        
        db.execute(
            """INSERT INTO job_postings 
               (id, user_id, raw_text, company_name, role_title, url, 
                location, remote_policy, notes, is_saved)
               VALUES (:id::uuid, :user_id::uuid, :raw_text, :company_name, :role_title, 
                       :url, :location, :remote_policy, :notes, true)""",
            {
                "id": new_id,
                "user_id": user["id"],
                "raw_text": raw_text,
                "company_name": discovered.get("company_name"),
                "role_title": discovered.get("role_title"),
                "url": discovered.get("source_url"),
                "location": discovered.get("location"),
                "remote_policy": discovered.get("remote_policy"),
                "notes": f"Discovered from {discovered.get('source', 'job board')}"
            }
        )
        
        # Return the new job posting
        new_job = db.execute_one(
            "SELECT * FROM job_postings WHERE id = :id::uuid",
            {"id": new_id}
        )
        
        logger.info(f"Saved discovered job {job_id} to user job posting {new_id}")
        
        return {
            "success": True,
            "job_posting": new_job,
            "message": "Job saved to your job board!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving discovered job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/discovered-jobs-summary")
async def get_discovered_jobs_summary():
    """
    Get a summary of discovered jobs by source and location.
    Public endpoint - no authentication required.
    """
    db = get_db()
    
    try:
        # Get counts by source
        source_counts = db.execute(
            """SELECT source, COUNT(*) as count
               FROM discovered_jobs
               WHERE is_active = true
               GROUP BY source
               ORDER BY count DESC"""
        )
        
        # Get total count
        total = db.execute_one(
            "SELECT COUNT(*) as total FROM discovered_jobs WHERE is_active = true"
        )
        
        # Get latest discoveries
        latest = db.execute(
            """SELECT id, source, company_name, role_title, location, 
                      discovered_at::text, salary_min, salary_max
               FROM discovered_jobs
               WHERE is_active = true
               ORDER BY discovered_at DESC
               LIMIT 5"""
        )
        
        # Get most recent discovery time
        last_discovery = db.execute_one(
            """SELECT MAX(discovered_at)::text as last_discovered
               FROM discovered_jobs
               WHERE is_active = true"""
        )
        
        return {
            "total_jobs": total["total"] if total else 0,
            "by_source": {item["source"]: item["count"] for item in source_counts},
            "latest": latest,
            "last_discovered": last_discovery.get("last_discovered") if last_discovery else None
        }
        
    except Exception as e:
        logger.error(f"Error getting discovered jobs summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Lambda handler
handler = Mangum(app, lifespan="off")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
