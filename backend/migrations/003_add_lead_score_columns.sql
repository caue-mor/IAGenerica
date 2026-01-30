-- Migration: Add lead scoring columns to leads table
-- Description: Add columns for lead temperature and scoring
-- Created: 2024

-- Add lead scoring columns to existing leads table
ALTER TABLE iagenericanexma_leads
ADD COLUMN IF NOT EXISTS lead_score INTEGER DEFAULT 0;

ALTER TABLE iagenericanexma_leads
ADD COLUMN IF NOT EXISTS lead_temperature VARCHAR(20) DEFAULT 'cold';

ALTER TABLE iagenericanexma_leads
ADD COLUMN IF NOT EXISTS score_breakdown JSONB DEFAULT '{}'::jsonb;

ALTER TABLE iagenericanexma_leads
ADD COLUMN IF NOT EXISTS scored_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE iagenericanexma_leads
ADD COLUMN IF NOT EXISTS qualification_status VARCHAR(50) DEFAULT 'pending';

-- Create index for scoring queries
CREATE INDEX IF NOT EXISTS idx_leads_score
    ON iagenericanexma_leads(lead_score DESC);

CREATE INDEX IF NOT EXISTS idx_leads_temperature
    ON iagenericanexma_leads(lead_temperature);

CREATE INDEX IF NOT EXISTS idx_leads_company_temperature
    ON iagenericanexma_leads(company_id, lead_temperature);

CREATE INDEX IF NOT EXISTS idx_leads_company_score
    ON iagenericanexma_leads(company_id, lead_score DESC);

CREATE INDEX IF NOT EXISTS idx_leads_hot
    ON iagenericanexma_leads(company_id)
    WHERE lead_temperature = 'hot';

-- Add comments
COMMENT ON COLUMN iagenericanexma_leads.lead_score IS 'Calculated lead score (0-100)';
COMMENT ON COLUMN iagenericanexma_leads.lead_temperature IS 'Lead temperature: hot, warm, cold';
COMMENT ON COLUMN iagenericanexma_leads.score_breakdown IS 'Detailed score breakdown by category';
COMMENT ON COLUMN iagenericanexma_leads.scored_at IS 'When the score was last calculated';
COMMENT ON COLUMN iagenericanexma_leads.qualification_status IS 'pending, qualified, disqualified, nurturing';
