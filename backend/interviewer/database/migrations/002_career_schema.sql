-- ================================================
-- CareerAssist Database Schema
-- Version: 002
-- Description: Career assistant platform schema - replaces financial planner
-- ================================================

-- Enable UUID extension for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop old tables (if converting from Alex financial planner)
-- Comment these out if you want to keep old data during migration
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS instruments CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ================================================
-- User Profiles (extends Clerk users)
-- ================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clerk_user_id VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    email VARCHAR(255),
    linkedin_url VARCHAR(500),
    phone VARCHAR(50),
    portfolio_url VARCHAR(500),
    github_url VARCHAR(500),
    target_roles JSONB DEFAULT '[]',        -- ["software engineer", "data scientist"]
    target_locations JSONB DEFAULT '[]',    -- ["San Francisco", "Remote"]
    years_of_experience INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- CV Versions (versioned resume storage)
-- ================================================
CREATE TABLE IF NOT EXISTS cv_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    raw_text TEXT NOT NULL,                 -- Original CV text
    parsed_json JSONB,                      -- Structured CV data (skills, experience, etc.)
    version_name VARCHAR(100) DEFAULT 'Default',
    is_primary BOOLEAN DEFAULT false,
    file_url VARCHAR(500),                  -- S3 URL if uploaded as file
    file_type VARCHAR(50),                  -- 'pdf', 'docx', 'txt', 'paste'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- Job Postings (stored job descriptions)
-- ================================================
CREATE TABLE IF NOT EXISTS job_postings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    company_name VARCHAR(255),
    role_title VARCHAR(255),
    raw_text TEXT NOT NULL,                 -- Original job posting text
    parsed_json JSONB,                      -- Structured job data (requirements, etc.)
    url VARCHAR(500),                       -- Original job posting URL
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'USD',
    location VARCHAR(255),
    remote_policy VARCHAR(50),              -- 'onsite', 'hybrid', 'remote', 'unknown'
    deadline DATE,
    notes TEXT,
    is_saved BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- Gap Analyses (CV vs Job comparison)
-- ================================================
CREATE TABLE IF NOT EXISTS gap_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES job_postings(id) ON DELETE CASCADE,
    cv_version_id UUID REFERENCES cv_versions(id) ON DELETE CASCADE,
    fit_score INTEGER CHECK (fit_score >= 0 AND fit_score <= 100),
    ats_score INTEGER CHECK (ats_score >= 0 AND ats_score <= 100),
    summary TEXT,                           -- Overall summary of the analysis
    strengths JSONB,                        -- List of matching strengths
    gaps JSONB,                             -- List of gaps with severity and recommendations
    action_items JSONB,                     -- Prioritized improvement actions
    created_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- CV Rewrites (job-tailored CV versions)
-- ================================================
CREATE TABLE IF NOT EXISTS cv_rewrites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gap_analysis_id UUID REFERENCES gap_analyses(id) ON DELETE CASCADE,
    rewritten_summary TEXT,                 -- Tailored professional summary
    rewritten_bullets JSONB,                -- Improved experience bullets
    skills_to_highlight JSONB,              -- Skills emphasized for this role
    cover_letter TEXT,                      -- Generated cover letter
    linkedin_summary TEXT,                  -- LinkedIn-optimized summary
    created_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- Job Applications (tracking pipeline)
-- ================================================
CREATE TABLE IF NOT EXISTS job_applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    job_id UUID REFERENCES job_postings(id) ON DELETE CASCADE,
    cv_version_id UUID REFERENCES cv_versions(id),
    gap_analysis_id UUID REFERENCES gap_analyses(id),
    status VARCHAR(50) DEFAULT 'saved',
    -- Status values: saved, applied, screening, phone_screen, interview, 
    --                technical, onsite, offer, rejected, withdrawn, accepted
    applied_at TIMESTAMP,
    last_status_change TIMESTAMP DEFAULT NOW(),
    response_date TIMESTAMP,
    next_step VARCHAR(255),
    next_step_date TIMESTAMP,
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- Interview Sessions (practice and real)
-- ================================================
CREATE TABLE IF NOT EXISTS interview_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    job_application_id UUID REFERENCES job_applications(id) ON DELETE SET NULL,
    job_id UUID REFERENCES job_postings(id) ON DELETE SET NULL,
    session_type VARCHAR(50) NOT NULL,      -- 'practice', 'preparation', 'real'
    interview_type VARCHAR(50),             -- 'behavioral', 'technical', 'system_design', 'mixed'
    questions JSONB,                        -- List of questions with metadata
    answers JSONB,                          -- User answers
    evaluations JSONB,                      -- AI evaluations of answers
    overall_score INTEGER CHECK (overall_score >= 0 AND overall_score <= 100),
    focus_areas JSONB,                      -- Key areas to focus on based on gaps
    company_tips JSONB,                     -- Company-specific interview tips
    duration_minutes INTEGER,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- Analysis Jobs (async processing queue)
-- ================================================
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    clerk_user_id VARCHAR(255),                 -- Direct clerk user ID for simplified access
    job_type VARCHAR(50) NOT NULL,
    -- Types: cv_parse, job_parse, gap_analysis, cv_rewrite, 
    --        interview_prep, full_analysis, market_research
    status VARCHAR(50) DEFAULT 'pending',
    -- Status: pending, processing, completed, failed
    input_data JSONB,                       -- Input parameters for the job
    request_payload JSONB,                  -- Request payload for the job
    
    -- Separate fields for each agent's results (no merging needed)
    extractor_payload JSONB,                -- Extractor agent's parsed data
    analyzer_payload JSONB,                 -- Analyzer agent's gap analysis
    interviewer_payload JSONB,              -- Interviewer agent's interview prep
    charter_payload JSONB,                  -- Charter agent's analytics
    summary_payload JSONB,                  -- Orchestrator's final summary
    
    error_message TEXT,
    progress_percentage INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- Skill Categories (reference data)
-- ================================================
CREATE TABLE IF NOT EXISTS skill_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    category_type VARCHAR(50),              -- 'technical', 'soft', 'tool', 'certification'
    parent_category VARCHAR(100),           -- For hierarchical organization
    aliases JSONB DEFAULT '[]',             -- Alternative names for the skill
    created_at TIMESTAMP DEFAULT NOW()
);

-- ================================================
-- Create Indexes for Performance
-- ================================================
CREATE INDEX IF NOT EXISTS idx_user_profiles_clerk ON user_profiles(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_cv_versions_user ON cv_versions(user_id);
CREATE INDEX IF NOT EXISTS idx_cv_versions_primary ON cv_versions(user_id, is_primary);
CREATE INDEX IF NOT EXISTS idx_job_postings_user ON job_postings(user_id);
CREATE INDEX IF NOT EXISTS idx_job_postings_company ON job_postings(company_name);
CREATE INDEX IF NOT EXISTS idx_gap_analyses_job ON gap_analyses(job_id);
CREATE INDEX IF NOT EXISTS idx_gap_analyses_cv ON gap_analyses(cv_version_id);
CREATE INDEX IF NOT EXISTS idx_cv_rewrites_analysis ON cv_rewrites(gap_analysis_id);
CREATE INDEX IF NOT EXISTS idx_job_applications_user ON job_applications(user_id);
CREATE INDEX IF NOT EXISTS idx_job_applications_status ON job_applications(status);
CREATE INDEX IF NOT EXISTS idx_job_applications_job ON job_applications(job_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_user ON interview_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_interview_sessions_app ON interview_sessions(job_application_id);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type);

-- ================================================
-- Create Update Timestamp Trigger Function
-- ================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ================================================
-- Add Update Triggers to Tables with updated_at
-- ================================================
DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_cv_versions_updated_at ON cv_versions;
CREATE TRIGGER update_cv_versions_updated_at BEFORE UPDATE ON cv_versions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_job_postings_updated_at ON job_postings;
CREATE TRIGGER update_job_postings_updated_at BEFORE UPDATE ON job_postings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_job_applications_updated_at ON job_applications;
CREATE TRIGGER update_job_applications_updated_at BEFORE UPDATE ON job_applications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- Helper Views
-- ================================================

-- View: User's application pipeline stats
CREATE OR REPLACE VIEW application_pipeline_stats AS
SELECT 
    user_id,
    status,
    COUNT(*) as count,
    MIN(created_at) as earliest,
    MAX(created_at) as latest
FROM job_applications
GROUP BY user_id, status;

-- View: Recent gap analyses with scores
CREATE OR REPLACE VIEW recent_gap_analyses AS
SELECT 
    ga.id,
    ga.fit_score,
    ga.ats_score,
    ga.created_at,
    jp.company_name,
    jp.role_title,
    cv.version_name as cv_version
FROM gap_analyses ga
JOIN job_postings jp ON ga.job_id = jp.id
JOIN cv_versions cv ON ga.cv_version_id = cv.id
ORDER BY ga.created_at DESC;
