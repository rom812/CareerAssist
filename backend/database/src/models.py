"""
Database models and query builders for CareerAssist
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal
from .client import DataAPIClient
from .schemas import (
    UserProfileCreate, CVVersionCreate, JobPostingCreate,
    GapAnalysisCreate, JobApplicationCreate, JobApplicationUpdate,
    InterviewSessionCreate, JobCreate, JobUpdate
)


class BaseModel:
    """Base class for database models"""
    
    table_name = None
    
    def __init__(self, db: DataAPIClient):
        self.db = db
        if not self.table_name:
            raise ValueError("table_name must be defined")
    
    def find_by_id(self, id: Any) -> Optional[Dict]:
        """Find a record by ID"""
        sql = f"SELECT * FROM {self.table_name} WHERE id = :id::uuid"
        return self.db.query_one(sql, [{'name': 'id', 'value': {'stringValue': str(id)}}])
    
    def find_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Find all records with pagination"""
        sql = f"SELECT * FROM {self.table_name} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        params = [
            {'name': 'limit', 'value': {'longValue': limit}},
            {'name': 'offset', 'value': {'longValue': offset}}
        ]
        return self.db.query(sql, params)
    
    def create(self, data: Dict, returning: str = 'id') -> str:
        """Create a new record"""
        return self.db.insert(self.table_name, data, returning=returning)
    
    def update(self, id: Any, data: Dict) -> int:
        """Update a record by ID"""
        return self.db.update(self.table_name, data, "id = :id::uuid", {'id': str(id)})
    
    def delete(self, id: Any) -> int:
        """Delete a record by ID"""
        return self.db.delete(self.table_name, "id = :id::uuid", {'id': str(id)})


class UserProfiles(BaseModel):
    """User profiles table operations"""
    table_name = 'user_profiles'
    
    def find_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict]:
        """Find user by Clerk ID"""
        sql = f"SELECT * FROM {self.table_name} WHERE clerk_user_id = :clerk_id"
        params = [{'name': 'clerk_id', 'value': {'stringValue': clerk_user_id}}]
        return self.db.query_one(sql, params)
    
    def create_user(self, profile: UserProfileCreate) -> str:
        """Create a new user profile"""
        profile_data = profile.model_dump(exclude_none=True)
        return self.db.insert(self.table_name, profile_data, returning='id')
    
    def update_profile(self, user_id: str, profile_updates: Dict) -> int:
        """Update user profile by ID"""
        return self.db.update(self.table_name, profile_updates, "id = :id::uuid", {'id': str(user_id)})
    
    def get_or_create(self, clerk_user_id: str, full_name: str = None, email: str = None) -> Dict:
        """Get existing user or create new one"""
        user = self.find_by_clerk_id(clerk_user_id)
        if user:
            return user
        
        profile = UserProfileCreate(
            clerk_user_id=clerk_user_id,
            full_name=full_name,
            email=email
        )
        user_id = self.create_user(profile)
        return self.find_by_id(user_id)


class CVVersions(BaseModel):
    """CV versions table operations"""
    table_name = 'cv_versions'
    
    def find_by_user(self, user_id: str) -> List[Dict]:
        """Find all CV versions for a user"""
        sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE user_id = :user_id::uuid 
            ORDER BY is_primary DESC, created_at DESC
        """
        params = [{'name': 'user_id', 'value': {'stringValue': str(user_id)}}]
        return self.db.query(sql, params)
    
    def get_primary(self, user_id: str) -> Optional[Dict]:
        """Get the primary CV version for a user"""
        sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE user_id = :user_id::uuid AND is_primary = true
        """
        params = [{'name': 'user_id', 'value': {'stringValue': str(user_id)}}]
        return self.db.query_one(sql, params)
    
    def create_cv_version(self, user_id: str, cv: CVVersionCreate) -> str:
        """Create a new CV version"""
        cv_data = cv.model_dump(exclude_none=True)
        cv_data['user_id'] = user_id
        
        # If this is set as primary, unset other primaries first
        if cv_data.get('is_primary'):
            self.unset_all_primary(user_id)
        
        return self.db.insert(self.table_name, cv_data, returning='id')
    
    def update_parsed(self, cv_id: str, parsed_json: Dict) -> int:
        """Update CV with parsed data"""
        parsed_data = {'parsed_json': parsed_json}
        return self.db.update(self.table_name, parsed_data, "id = :id::uuid", {'id': str(cv_id)})
    
    def set_primary(self, cv_id: str, user_id: str) -> int:
        """Set a CV version as primary"""
        # First unset all primaries for this user
        self.unset_all_primary(user_id)
        # Then set this one as primary
        primary_update = {'is_primary': True}
        return self.db.update(self.table_name, primary_update, "id = :id::uuid", {'id': str(cv_id)})
    
    def unset_all_primary(self, user_id: str) -> int:
        """Unset primary flag for all user's CVs"""
        primary_update = {'is_primary': False}
        return self.db.update(
            self.table_name, primary_update, 
            "user_id = :user_id::uuid AND is_primary = true", 
            {'user_id': str(user_id)}
        )


class JobPostings(BaseModel):
    """Job postings table operations"""
    table_name = 'job_postings'
    
    def find_by_user(self, user_id: str, saved_only: bool = False) -> List[Dict]:
        """Find all job postings for a user"""
        if saved_only:
            sql = f"""
                SELECT * FROM {self.table_name} 
                WHERE user_id = :user_id::uuid AND is_saved = true
                ORDER BY created_at DESC
            """
        else:
            sql = f"""
                SELECT * FROM {self.table_name} 
                WHERE user_id = :user_id::uuid 
                ORDER BY created_at DESC
            """
        params = [{'name': 'user_id', 'value': {'stringValue': str(user_id)}}]
        return self.db.query(sql, params)
    
    def create_job_posting(self, user_id: str, job: JobPostingCreate) -> str:
        """Create a new job posting"""
        job_data = job.model_dump(exclude_none=True)
        job_data['user_id'] = user_id
        return self.db.insert(self.table_name, job_data, returning='id')
    
    def update_parsed(self, job_id: str, parsed_json: Dict) -> int:
        """Update job posting with parsed data"""
        parsed_data = {'parsed_json': parsed_json}
        return self.db.update(self.table_name, parsed_data, "id = :id::uuid", {'id': str(job_id)})
    
    def search_by_company(self, user_id: str, company_name: str) -> List[Dict]:
        """Search job postings by company name"""
        sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE user_id = :user_id::uuid 
              AND LOWER(company_name) LIKE LOWER(:company)
            ORDER BY created_at DESC
        """
        params = [
            {'name': 'user_id', 'value': {'stringValue': str(user_id)}},
            {'name': 'company', 'value': {'stringValue': f'%{company_name}%'}}
        ]
        return self.db.query(sql, params)
    
    def toggle_saved(self, job_id: str, is_saved: bool) -> int:
        """Toggle saved status of a job posting"""
        saved_update = {'is_saved': is_saved}
        return self.db.update(self.table_name, saved_update, "id = :id::uuid", {'id': str(job_id)})


class GapAnalyses(BaseModel):
    """Gap analyses table operations"""
    table_name = 'gap_analyses'
    
    def find_by_job(self, job_id: str) -> List[Dict]:
        """Find all gap analyses for a job posting"""
        sql = f"""
            SELECT ga.*, cv.version_name as cv_name
            FROM {self.table_name} ga
            JOIN cv_versions cv ON ga.cv_version_id = cv.id
            WHERE ga.job_id = :job_id::uuid
            ORDER BY ga.created_at DESC
        """
        params = [{'name': 'job_id', 'value': {'stringValue': str(job_id)}}]
        return self.db.query(sql, params)
    
    def find_by_user(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Find recent gap analyses for a user"""
        sql = f"""
            SELECT ga.*, jp.company_name, jp.role_title, cv.version_name as cv_name
            FROM {self.table_name} ga
            JOIN job_postings jp ON ga.job_id = jp.id
            JOIN cv_versions cv ON ga.cv_version_id = cv.id
            WHERE jp.user_id = :user_id::uuid
            ORDER BY ga.created_at DESC
            LIMIT :limit
        """
        params = [
            {'name': 'user_id', 'value': {'stringValue': str(user_id)}},
            {'name': 'limit', 'value': {'longValue': limit}}
        ]
        return self.db.query(sql, params)
    
    def create_gap_analysis(
        self, job_id: str, cv_version_id: str, 
        fit_score: int, ats_score: int,
        summary: str, strengths: List[str], 
        gaps: List[Dict], action_items: List[str]
    ) -> str:
        """Create a new gap analysis"""
        analysis_data = {
            'job_id': job_id,
            'cv_version_id': cv_version_id,
            'fit_score': fit_score,
            'ats_score': ats_score,
            'summary': summary,
            'strengths': strengths,
            'gaps': gaps,
            'action_items': action_items
        }
        return self.db.insert(self.table_name, analysis_data, returning='id')


class CVRewrites(BaseModel):
    """CV rewrites table operations"""
    table_name = 'cv_rewrites'
    
    def find_by_gap_analysis(self, gap_analysis_id: str) -> Optional[Dict]:
        """Find CV rewrite for a gap analysis"""
        sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE gap_analysis_id = :gap_id::uuid
        """
        params = [{'name': 'gap_id', 'value': {'stringValue': str(gap_analysis_id)}}]
        return self.db.query_one(sql, params)
    
    def create_rewrite(
        self, gap_analysis_id: str, 
        rewritten_summary: str, rewritten_bullets: List[Dict],
        skills_to_highlight: List[str], 
        cover_letter: str = None, linkedin_summary: str = None
    ) -> str:
        """Create a CV rewrite"""
        rewrite_data = {
            'gap_analysis_id': gap_analysis_id,
            'rewritten_summary': rewritten_summary,
            'rewritten_bullets': rewritten_bullets,
            'skills_to_highlight': skills_to_highlight,
            'cover_letter': cover_letter,
            'linkedin_summary': linkedin_summary
        }
        return self.db.insert(self.table_name, rewrite_data, returning='id')


class JobApplications(BaseModel):
    """Job applications table operations"""
    table_name = 'job_applications'
    
    def find_by_user(self, user_id: str, status: str = None) -> List[Dict]:
        """Find all job applications for a user"""
        if status:
            sql = f"""
                SELECT ja.*, jp.company_name, jp.role_title, jp.location
                FROM {self.table_name} ja
                JOIN job_postings jp ON ja.job_id = jp.id
                WHERE ja.user_id = :user_id::uuid AND ja.status = :status
                ORDER BY ja.last_status_change DESC
            """
            params = [
                {'name': 'user_id', 'value': {'stringValue': str(user_id)}},
                {'name': 'status', 'value': {'stringValue': status}}
            ]
        else:
            sql = f"""
                SELECT ja.*, jp.company_name, jp.role_title, jp.location
                FROM {self.table_name} ja
                JOIN job_postings jp ON ja.job_id = jp.id
                WHERE ja.user_id = :user_id::uuid
                ORDER BY ja.last_status_change DESC
            """
            params = [{'name': 'user_id', 'value': {'stringValue': str(user_id)}}]
        
        return self.db.query(sql, params)
    
    def get_pipeline(self, user_id: str) -> Dict[str, int]:
        """Get application pipeline counts by status"""
        sql = """
            SELECT status, COUNT(*) as count
            FROM job_applications
            WHERE user_id = :user_id::uuid
            GROUP BY status
        """
        params = [{'name': 'user_id', 'value': {'stringValue': str(user_id)}}]
        results = self.db.query(sql, params)
        return {r['status']: r['count'] for r in results}
    
    def create_application(self, user_id: str, app: JobApplicationCreate) -> str:
        """Create a new job application"""
        application_data = app.model_dump(exclude_none=True)
        application_data['user_id'] = user_id
        return self.db.insert(self.table_name, application_data, returning='id')
    
    def update_status(self, app_id: str, status: str, notes: str = None) -> int:
        """Update application status"""
        status_update = {
            'status': status,
            'last_status_change': datetime.utcnow()
        }
        if notes:
            status_update['notes'] = notes
        if status == 'applied':
            status_update['applied_at'] = datetime.utcnow()
        return self.db.update(self.table_name, status_update, "id = :id::uuid", {'id': str(app_id)})
    
    def update_application(self, app_id: str, update: JobApplicationUpdate) -> int:
        """Update job application with new data"""
        application_updates = update.model_dump(exclude_none=True)
        if application_updates.get('status'):
            application_updates['last_status_change'] = datetime.utcnow()
        return self.db.update(self.table_name, application_updates, "id = :id::uuid", {'id': str(app_id)})


class InterviewSessions(BaseModel):
    """Interview sessions table operations"""
    table_name = 'interview_sessions'
    
    def find_by_user(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Find all interview sessions for a user"""
        sql = f"""
            SELECT iss.*, jp.company_name, jp.role_title
            FROM {self.table_name} iss
            LEFT JOIN job_postings jp ON iss.job_id = jp.id
            WHERE iss.user_id = :user_id::uuid
            ORDER BY iss.created_at DESC
            LIMIT :limit
        """
        params = [
            {'name': 'user_id', 'value': {'stringValue': str(user_id)}},
            {'name': 'limit', 'value': {'longValue': limit}}
        ]
        return self.db.query(sql, params)
    
    def find_by_application(self, app_id: str) -> List[Dict]:
        """Find interview sessions for a job application"""
        sql = f"""
            SELECT * FROM {self.table_name} 
            WHERE job_application_id = :app_id::uuid
            ORDER BY created_at DESC
        """
        params = [{'name': 'app_id', 'value': {'stringValue': str(app_id)}}]
        return self.db.query(sql, params)
    
    def create_session(self, user_id: str, session: InterviewSessionCreate) -> str:
        """Create a new interview session"""
        session_data = session.model_dump(exclude_none=True)
        session_data['user_id'] = user_id
        return self.db.insert(self.table_name, session_data, returning='id')
    
    def update_questions(self, session_id: str, questions: List[Dict]) -> int:
        """Update session with questions"""
        questions_update = {'questions': questions}
        return self.db.update(self.table_name, questions_update, "id = :id::uuid", {'id': str(session_id)})
    
    def save_answer(self, session_id: str, question_id: str, answer: str) -> int:
        """Save an answer to a question"""
        # First get current answers
        session = self.find_by_id(session_id)
        answers = session.get('answers', []) if session else []
        
        # Add or update the answer
        answer_found = False
        for ans in answers:
            if ans.get('question_id') == question_id:
                ans['answer'] = answer
                ans['answered_at'] = datetime.utcnow().isoformat()
                answer_found = True
                break
        
        if not answer_found:
            answers.append({
                'question_id': question_id,
                'answer': answer,
                'answered_at': datetime.utcnow().isoformat()
            })
        
        answers_update = {'answers': answers}
        return self.db.update(self.table_name, answers_update, "id = :id::uuid", {'id': str(session_id)})
    
    def save_evaluation(self, session_id: str, question_id: str, evaluation: Dict) -> int:
        """Save an evaluation for a question"""
        session = self.find_by_id(session_id)
        evaluations = session.get('evaluations', []) if session else []
        
        evaluation['question_id'] = question_id
        evaluations.append(evaluation)
        
        evaluations_update = {'evaluations': evaluations}
        return self.db.update(self.table_name, evaluations_update, "id = :id::uuid", {'id': str(session_id)})
    
    def complete_session(self, session_id: str, overall_score: int, duration_minutes: int) -> int:
        """Mark session as complete"""
        completion_data = {
            'overall_score': overall_score,
            'duration_minutes': duration_minutes,
            'completed_at': datetime.utcnow()
        }
        return self.db.update(self.table_name, completion_data, "id = :id::uuid", {'id': str(session_id)})


class Jobs(BaseModel):
    """Async jobs table operations (for agent processing)"""
    table_name = 'jobs'
    
    def create_job(self, user_id: str, job_type: str, input_data: Dict = None) -> str:
        """Create a new async job"""
        job_data = {
            'user_id': user_id,
            'job_type': job_type,
            'status': 'pending',
            'input_data': input_data,
            'progress_percentage': 0
        }
        return self.db.insert(self.table_name, job_data, returning='id')
    
    def update_status(self, job_id: str, status: str, error_message: str = None, progress: int = None) -> int:
        """Update job status"""
        status_update = {'status': status}
        
        if status == 'processing':
            status_update['started_at'] = datetime.utcnow()
        elif status in ['completed', 'failed']:
            status_update['completed_at'] = datetime.utcnow()
        
        if error_message:
            status_update['error_message'] = error_message
        
        if progress is not None:
            status_update['progress_percentage'] = progress
        
        return self.db.update(self.table_name, status_update, "id = :id::uuid", {'id': str(job_id)})
    
    def update_extractor(self, job_id: str, extractor_payload: Dict) -> int:
        """Update job with Extractor agent's parsed data"""
        extractor_update = {'extractor_payload': extractor_payload}
        return self.db.update(self.table_name, extractor_update, "id = :id::uuid", {'id': str(job_id)})
    
    def update_analyzer(self, job_id: str, analyzer_payload: Dict) -> int:
        """Update job with Analyzer agent's gap analysis"""
        analyzer_update = {'analyzer_payload': analyzer_payload}
        return self.db.update(self.table_name, analyzer_update, "id = :id::uuid", {'id': str(job_id)})
    
    def update_interviewer(self, job_id: str, interviewer_payload: Dict) -> int:
        """Update job with Interviewer agent's interview prep"""
        interviewer_update = {'interviewer_payload': interviewer_payload}
        return self.db.update(self.table_name, interviewer_update, "id = :id::uuid", {'id': str(job_id)})
    
    def update_charter(self, job_id: str, charter_payload: Dict) -> int:
        """Update job with Charter agent's analytics"""
        charter_update = {'charter_payload': charter_payload}
        return self.db.update(self.table_name, charter_update, "id = :id::uuid", {'id': str(job_id)})
    
    def update_summary(self, job_id: str, summary_payload: Dict) -> int:
        """Update job with Orchestrator's final summary"""
        summary_update = {'summary_payload': summary_payload}
        return self.db.update(self.table_name, summary_update, "id = :id::uuid", {'id': str(job_id)})
    
    def find_by_user(self, user_id: str, status: str = None, job_type: str = None, limit: int = 20) -> List[Dict]:
        """Find jobs for a user"""
        conditions = ["user_id = :user_id::uuid"]
        params = [{'name': 'user_id', 'value': {'stringValue': str(user_id)}}]
        
        if status:
            conditions.append("status = :status")
            params.append({'name': 'status', 'value': {'stringValue': status}})
        
        if job_type:
            conditions.append("job_type = :job_type")
            params.append({'name': 'job_type', 'value': {'stringValue': job_type}})
        
        params.append({'name': 'limit', 'value': {'longValue': limit}})
        
        sql = f"""
            SELECT * FROM {self.table_name}
            WHERE {' AND '.join(conditions)}
            ORDER BY created_at DESC
            LIMIT :limit
        """
        
        return self.db.query(sql, params)
    
    def get_pending(self, limit: int = 10) -> List[Dict]:
        """Get pending jobs for processing"""
        sql = f"""
            SELECT * FROM {self.table_name}
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT :limit
        """
        params = [{'name': 'limit', 'value': {'longValue': limit}}]
        return self.db.query(sql, params)


class Database:
    """Main database interface providing access to all models"""
    
    def __init__(self, cluster_arn: str = None, secret_arn: str = None,
                 database: str = None, region: str = None):
        """Initialize database with all model classes"""
        self.client = DataAPIClient(cluster_arn, secret_arn, database, region)
        
        # Initialize all models
        self.user_profiles = UserProfiles(self.client)
        self.cv_versions = CVVersions(self.client)
        self.job_postings = JobPostings(self.client)
        self.gap_analyses = GapAnalyses(self.client)
        self.cv_rewrites = CVRewrites(self.client)
        self.job_applications = JobApplications(self.client)
        self.interview_sessions = InterviewSessions(self.client)
        self.jobs = Jobs(self.client)
    
    def execute_raw(self, sql: str, parameters: List[Dict] = None) -> Dict:
        """Execute raw SQL for complex queries"""
        return self.client.execute(sql, parameters)
    
    def query_raw(self, sql: str, parameters: List[Dict] = None) -> List[Dict]:
        """Execute raw SELECT query"""
        return self.client.query(sql, parameters)