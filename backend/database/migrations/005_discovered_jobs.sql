-- ================================================
-- Discovered Jobs Schema
-- Version: 005
-- Description: Store AI-discovered job postings from Indeed/Glassdoor
-- ================================================

-- Discovered Jobs (AI-scraped from job boards)
-- Global table - not user-specific, but users can "save" to their job_postings
CREATE TABLE IF NOT EXISTS discovered_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(50) NOT NULL,              -- 'indeed', 'glassdoor'
    source_url VARCHAR(1000),                 -- Original job URL
    source_job_id VARCHAR(255),               -- ID from source site (for dedup)
    company_name VARCHAR(255),
    role_title VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    remote_policy VARCHAR(50),                -- 'onsite', 'hybrid', 'remote', 'unknown'
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency VARCHAR(10) DEFAULT 'USD',
    description_text TEXT,                    -- Job description
    requirements_text TEXT,                   -- Requirements section
    parsed_json JSONB,                        -- Structured data if parsed
    discovered_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,                     -- When job posting expires
    is_active BOOLEAN DEFAULT true,
    relevance_score INTEGER DEFAULT 50 CHECK (relevance_score >= 0 AND relevance_score <= 100),
    metadata JSONB DEFAULT '{}',              -- Extra data from scraping
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_discovered_jobs_source ON discovered_jobs(source);
CREATE INDEX IF NOT EXISTS idx_discovered_jobs_active ON discovered_jobs(is_active, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_discovered_jobs_company ON discovered_jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_discovered_jobs_role ON discovered_jobs(role_title);
CREATE UNIQUE INDEX IF NOT EXISTS idx_discovered_jobs_source_id ON discovered_jobs(source, source_job_id);

-- Update trigger for updated_at
DROP TRIGGER IF EXISTS update_discovered_jobs_updated_at ON discovered_jobs;
CREATE TRIGGER update_discovered_jobs_updated_at BEFORE UPDATE ON discovered_jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- Source Values Reference:
-- ================================================
-- 'indeed'     - Jobs discovered from Indeed
-- 'glassdoor'  - Jobs discovered from Glassdoor
-- ================================================
