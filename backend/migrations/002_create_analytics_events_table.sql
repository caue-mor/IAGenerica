-- Migration: Create analytics events table
-- Description: Track all events for funnel analysis and metrics
-- Created: 2024

-- Create analytics events table
CREATE TABLE IF NOT EXISTS iagenericanexma_analytics_events (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    lead_id INTEGER,
    conversation_id INTEGER,

    -- Event identification
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB DEFAULT '{}'::jsonb,

    -- Context
    session_id VARCHAR(100),
    node_id VARCHAR(100),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Foreign key constraints
    CONSTRAINT fk_analytics_company
        FOREIGN KEY (company_id)
        REFERENCES iagenericanexma_companies(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_analytics_lead
        FOREIGN KEY (lead_id)
        REFERENCES iagenericanexma_leads(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_analytics_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES iagenericanexma_conversations(id)
        ON DELETE SET NULL
);

-- Create indexes for analytics queries
CREATE INDEX IF NOT EXISTS idx_analytics_company
    ON iagenericanexma_analytics_events(company_id);

CREATE INDEX IF NOT EXISTS idx_analytics_event_type
    ON iagenericanexma_analytics_events(event_type);

CREATE INDEX IF NOT EXISTS idx_analytics_company_type
    ON iagenericanexma_analytics_events(company_id, event_type);

CREATE INDEX IF NOT EXISTS idx_analytics_created_at
    ON iagenericanexma_analytics_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analytics_lead
    ON iagenericanexma_analytics_events(lead_id)
    WHERE lead_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_analytics_conversation
    ON iagenericanexma_analytics_events(conversation_id)
    WHERE conversation_id IS NOT NULL;

-- Compound index for time-series queries
CREATE INDEX IF NOT EXISTS idx_analytics_company_created
    ON iagenericanexma_analytics_events(company_id, created_at DESC);

-- Index for funnel analysis
CREATE INDEX IF NOT EXISTS idx_analytics_funnel
    ON iagenericanexma_analytics_events(company_id, event_type, created_at);

-- Partial indexes for common event types
CREATE INDEX IF NOT EXISTS idx_analytics_conversation_started
    ON iagenericanexma_analytics_events(company_id, created_at)
    WHERE event_type = 'conversation_started';

CREATE INDEX IF NOT EXISTS idx_analytics_field_collected
    ON iagenericanexma_analytics_events(company_id, created_at)
    WHERE event_type = 'field_collected';

CREATE INDEX IF NOT EXISTS idx_analytics_lead_qualified
    ON iagenericanexma_analytics_events(company_id, created_at)
    WHERE event_type = 'lead_qualified';

CREATE INDEX IF NOT EXISTS idx_analytics_handoff
    ON iagenericanexma_analytics_events(company_id, created_at)
    WHERE event_type = 'handoff_requested';

-- Create enum for event types
DO $$ BEGIN
    CREATE TYPE analytics_event_type AS ENUM (
        -- Conversation events
        'conversation_started',
        'conversation_ended',
        'conversation_abandoned',

        -- Message events
        'message_received',
        'message_sent',
        'message_failed',

        -- Data collection events
        'field_collected',
        'field_validation_failed',
        'field_retry',

        -- Flow events
        'node_entered',
        'node_completed',
        'condition_evaluated',
        'switch_branch_taken',
        'flow_completed',
        'flow_abandoned',

        -- Qualification events
        'lead_scored',
        'lead_qualified',
        'lead_disqualified',
        'temperature_changed',

        -- Notification events
        'notification_triggered',
        'notification_sent',
        'notification_failed',

        -- Handoff events
        'handoff_requested',
        'handoff_completed',

        -- User actions
        'user_intent_detected',
        'sentiment_detected',

        -- System events
        'error_occurred',
        'rate_limited'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add comments for documentation
COMMENT ON TABLE iagenericanexma_analytics_events IS 'Analytics events for funnel and conversion tracking';
COMMENT ON COLUMN iagenericanexma_analytics_events.event_type IS 'Type of event (conversation_started, field_collected, etc.)';
COMMENT ON COLUMN iagenericanexma_analytics_events.event_data IS 'Additional event data (JSON)';
COMMENT ON COLUMN iagenericanexma_analytics_events.session_id IS 'Optional session identifier';
COMMENT ON COLUMN iagenericanexma_analytics_events.node_id IS 'Flow node ID if applicable';

-- Create materialized view for daily aggregates (optional, for performance)
-- This can be refreshed periodically for dashboard queries
CREATE MATERIALIZED VIEW IF NOT EXISTS iagenericanexma_analytics_daily AS
SELECT
    company_id,
    DATE(created_at) as event_date,
    event_type,
    COUNT(*) as event_count
FROM iagenericanexma_analytics_events
GROUP BY company_id, DATE(created_at), event_type
WITH DATA;

-- Create unique index on the materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_analytics_daily_unique
    ON iagenericanexma_analytics_daily(company_id, event_date, event_type);

-- Create function to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_analytics_daily()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY iagenericanexma_analytics_daily;
END;
$$ LANGUAGE plpgsql;

-- Add comment
COMMENT ON MATERIALIZED VIEW iagenericanexma_analytics_daily IS 'Daily aggregated analytics for fast dashboard queries';
