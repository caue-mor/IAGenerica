-- Migration: Create notifications table
-- Description: Persistent notifications with retry support
-- Created: 2024

-- Create notifications table
CREATE TABLE IF NOT EXISTS iagenericanexma_notifications (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    lead_id INTEGER,
    conversation_id INTEGER,

    -- Notification content
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,

    -- Delivery configuration
    channels JSONB DEFAULT '["in_app"]'::jsonb,
    priority VARCHAR(20) DEFAULT 'normal',

    -- Additional data
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending',
    delivery_attempts INTEGER DEFAULT 0,
    max_delivery_attempts INTEGER DEFAULT 3,
    last_error TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    scheduled_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,

    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Foreign key constraints
    CONSTRAINT fk_notification_company
        FOREIGN KEY (company_id)
        REFERENCES iagenericanexma_companies(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_notification_lead
        FOREIGN KEY (lead_id)
        REFERENCES iagenericanexma_leads(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_notification_conversation
        FOREIGN KEY (conversation_id)
        REFERENCES iagenericanexma_conversations(id)
        ON DELETE SET NULL
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_notifications_company
    ON iagenericanexma_notifications(company_id);

CREATE INDEX IF NOT EXISTS idx_notifications_status
    ON iagenericanexma_notifications(status);

CREATE INDEX IF NOT EXISTS idx_notifications_company_status
    ON iagenericanexma_notifications(company_id, status);

CREATE INDEX IF NOT EXISTS idx_notifications_lead
    ON iagenericanexma_notifications(lead_id)
    WHERE lead_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_notifications_created_at
    ON iagenericanexma_notifications(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_notifications_pending
    ON iagenericanexma_notifications(company_id, status)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_notifications_failed
    ON iagenericanexma_notifications(company_id, status, delivery_attempts)
    WHERE status = 'failed' AND delivery_attempts < 3;

-- Create enum types (if not exists - PostgreSQL doesn't have IF NOT EXISTS for types)
DO $$ BEGIN
    CREATE TYPE notification_status AS ENUM ('pending', 'processing', 'sent', 'delivered', 'read', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE notification_priority AS ENUM ('low', 'normal', 'high', 'urgent');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE notification_type AS ENUM (
        'new_lead',
        'lead_qualified',
        'handoff_request',
        'follow_up_needed',
        'proposal_requested',
        'document_received',
        'appointment_scheduled',
        'urgent',
        'error',
        'info'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add comments for documentation
COMMENT ON TABLE iagenericanexma_notifications IS 'Persistent notifications with retry support';
COMMENT ON COLUMN iagenericanexma_notifications.channels IS 'Array of delivery channels: in_app, email, whatsapp, slack';
COMMENT ON COLUMN iagenericanexma_notifications.status IS 'pending, processing, sent, delivered, read, failed';
COMMENT ON COLUMN iagenericanexma_notifications.priority IS 'low, normal, high, urgent';
COMMENT ON COLUMN iagenericanexma_notifications.metadata IS 'Additional notification data (JSON)';
