-- Migration: Add Proposals and Followups tables
-- Date: 2026-01-30
-- Description: Creates tables for managing proposals and enhanced followups

-- ==========================================
-- 1. PROPOSALS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS iagenericanexma_proposals (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    lead_id INTEGER NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,

    -- Values and conditions (JSONB for flexibility)
    valores JSONB DEFAULT '{}',
    condicoes TEXT[] DEFAULT '{}',

    -- Status: draft, sent, viewed, accepted, rejected, expired, negotiating
    status VARCHAR(50) DEFAULT 'draft',

    -- Document attachment
    documento_url VARCHAR(500),
    documento_tipo VARCHAR(50),  -- pdf, link, image

    -- Timestamps
    enviada_em TIMESTAMP,
    visualizada_em TIMESTAMP,
    respondida_em TIMESTAMP,

    -- Expiration
    validade_dias INTEGER DEFAULT 7,
    expira_em TIMESTAMP,

    -- Additional metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for proposals
CREATE INDEX IF NOT EXISTS idx_proposals_company_id ON iagenericanexma_proposals(company_id);
CREATE INDEX IF NOT EXISTS idx_proposals_lead_id ON iagenericanexma_proposals(lead_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON iagenericanexma_proposals(status);
CREATE INDEX IF NOT EXISTS idx_proposals_expira_em ON iagenericanexma_proposals(expira_em) WHERE status = 'sent';

-- ==========================================
-- 2. FOLLOWUPS TABLE
-- ==========================================
CREATE TABLE IF NOT EXISTS iagenericanexma_followups (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    lead_id INTEGER NOT NULL,

    -- Scheduling
    scheduled_for TIMESTAMP NOT NULL,
    stage VARCHAR(50) DEFAULT 'first',  -- first, second, third, fourth, custom
    reason VARCHAR(50) DEFAULT 'inactivity',  -- inactivity, proposal_sent, document_pending, field_pending, scheduled, custom

    -- Message content
    message TEXT,
    template_id VARCHAR(100),

    -- Context preservation (JSONB for flexibility)
    context JSONB DEFAULT '{}',
    -- Context can include:
    -- - last_question: str
    -- - pending_field: str
    -- - conversation_summary: str
    -- - last_topic: str
    -- - lead_name: str
    -- - proposal_id: int

    -- Status: pending, sent, cancelled, failed, expired
    status VARCHAR(50) DEFAULT 'pending',
    sent_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancelled_reason TEXT,

    -- Additional metadata
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for followups
CREATE INDEX IF NOT EXISTS idx_followups_company_id ON iagenericanexma_followups(company_id);
CREATE INDEX IF NOT EXISTS idx_followups_lead_id ON iagenericanexma_followups(lead_id);
CREATE INDEX IF NOT EXISTS idx_followups_status ON iagenericanexma_followups(status);
CREATE INDEX IF NOT EXISTS idx_followups_scheduled_for ON iagenericanexma_followups(scheduled_for) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_followups_lead_pending ON iagenericanexma_followups(lead_id, status) WHERE status = 'pending';

-- ==========================================
-- 3. ADD proposta_ativa_id TO LEADS TABLE
-- ==========================================
ALTER TABLE iagenericanexma_leads
ADD COLUMN IF NOT EXISTS proposta_ativa_id INTEGER;

-- Index for proposal lookup
CREATE INDEX IF NOT EXISTS idx_leads_proposta_ativa ON iagenericanexma_leads(proposta_ativa_id) WHERE proposta_ativa_id IS NOT NULL;

-- ==========================================
-- 4. TRIGGERS FOR UPDATED_AT
-- ==========================================
-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for proposals
DROP TRIGGER IF EXISTS update_proposals_updated_at ON iagenericanexma_proposals;
CREATE TRIGGER update_proposals_updated_at
    BEFORE UPDATE ON iagenericanexma_proposals
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- 5. HELPFUL VIEWS
-- ==========================================

-- View for active proposals (not expired, rejected, or accepted)
CREATE OR REPLACE VIEW iagenericanexma_active_proposals AS
SELECT p.*, l.nome as lead_nome, l.celular as lead_celular
FROM iagenericanexma_proposals p
JOIN iagenericanexma_leads l ON p.lead_id = l.id
WHERE p.status NOT IN ('accepted', 'rejected', 'expired')
  AND (p.expira_em IS NULL OR p.expira_em > NOW());

-- View for pending followups that are due
CREATE OR REPLACE VIEW iagenericanexma_due_followups AS
SELECT f.*, l.nome as lead_nome, l.celular as lead_celular
FROM iagenericanexma_followups f
JOIN iagenericanexma_leads l ON f.lead_id = l.id
WHERE f.status = 'pending'
  AND f.scheduled_for <= NOW();

-- ==========================================
-- 6. COMMENTS FOR DOCUMENTATION
-- ==========================================
COMMENT ON TABLE iagenericanexma_proposals IS 'Proposals sent to leads with status tracking';
COMMENT ON TABLE iagenericanexma_followups IS 'Scheduled follow-up messages with context preservation';
COMMENT ON COLUMN iagenericanexma_proposals.valores IS 'JSON object with proposal values (e.g., {"total": 1000, "parcelas": 12})';
COMMENT ON COLUMN iagenericanexma_proposals.condicoes IS 'Array of text conditions for the proposal';
COMMENT ON COLUMN iagenericanexma_followups.context IS 'JSON object preserving conversation context for the followup';
COMMENT ON COLUMN iagenericanexma_leads.proposta_ativa_id IS 'ID of the currently active proposal for this lead';
