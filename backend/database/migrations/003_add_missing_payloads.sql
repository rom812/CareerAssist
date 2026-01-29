-- Add missing payload columns to jobs table
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS report_payload JSONB;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS interview_payload JSONB;
