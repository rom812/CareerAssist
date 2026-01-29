-- ================================================
-- Research Findings Schema
-- Version: 004
-- Description: Store researcher agent findings for frontend display
-- ================================================

-- Research findings from the Researcher agent
-- Stores market insights, trending roles, salary data for user display
CREATE TABLE IF NOT EXISTS research_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'role_trend', 'skill_demand', 'salary_insight', 'industry_news'
    title VARCHAR(255) NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',    -- Flexible storage for category-specific data
    source_url VARCHAR(500),        -- Original source URL if available
    relevance_score INTEGER DEFAULT 50 CHECK (relevance_score >= 0 AND relevance_score <= 100),
    is_featured BOOLEAN DEFAULT false,
    expires_at TIMESTAMP,           -- Optional expiry for time-sensitive data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_research_findings_category ON research_findings(category);
CREATE INDEX IF NOT EXISTS idx_research_findings_created ON research_findings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_findings_featured ON research_findings(is_featured, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_findings_topic ON research_findings(topic);

-- Update trigger for updated_at
DROP TRIGGER IF EXISTS update_research_findings_updated_at ON research_findings;
CREATE TRIGGER update_research_findings_updated_at BEFORE UPDATE ON research_findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- Sample Categories Reference:
-- ================================================
-- 'role_trend'     - Trending job roles, new positions emerging
-- 'skill_demand'   - In-demand skills, technology trends
-- 'salary_insight' - Salary ranges, compensation trends
-- 'industry_news'  - General industry news and updates
-- ================================================
