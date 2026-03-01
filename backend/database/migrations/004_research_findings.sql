-- ================================================
-- Research Findings Schema
-- Version: 004
-- Description: Store AI-researched market insights for frontend display
-- ================================================

-- Research Findings (AI-generated market insights)
-- Global table - visible to all users in the Market Insights page
CREATE TABLE IF NOT EXISTS research_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic VARCHAR(255) NOT NULL,                -- Research topic (e.g., "AI Engineering Roles")
    category VARCHAR(50) NOT NULL,              -- 'role_trend', 'skill_demand', 'salary_insight', 'industry_news'
    title VARCHAR(500) NOT NULL,                -- Display title for the finding
    summary TEXT,                               -- 1-2 sentence summary for card display
    content TEXT,                               -- Full detailed content/analysis
    source_url VARCHAR(1000),                   -- URL to original source
    relevance_score INTEGER DEFAULT 50 CHECK (relevance_score >= 0 AND relevance_score <= 100),
    is_featured BOOLEAN DEFAULT false,          -- Whether to feature prominently
    metadata JSONB DEFAULT '{}',               -- Additional structured data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_research_findings_category ON research_findings(category);
CREATE INDEX IF NOT EXISTS idx_research_findings_featured ON research_findings(is_featured, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_findings_relevance ON research_findings(relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_research_findings_topic ON research_findings(topic);

-- Update trigger for updated_at
DROP TRIGGER IF EXISTS update_research_findings_updated_at ON research_findings;
CREATE TRIGGER update_research_findings_updated_at BEFORE UPDATE ON research_findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================
-- Category Values Reference:
-- ================================================
-- 'role_trend'      - Trending roles and career paths
-- 'skill_demand'    - In-demand skills and technologies
-- 'salary_insight'  - Salary trends and compensation data
-- 'industry_news'   - General industry news and updates
-- ================================================
