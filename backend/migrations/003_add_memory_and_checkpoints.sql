-- Migration: Add memory and checkpoints for intelligent AI system
-- Description: Adds long-term memory field to leads and creates checkpoints table for LangGraph persistence
-- Date: 2024

-- ==================================================
-- Add memory column to leads table
-- ==================================================
ALTER TABLE iagenericanexma_leads
ADD COLUMN IF NOT EXISTS memory JSONB DEFAULT '{}';

-- Create index for memory queries
CREATE INDEX IF NOT EXISTS idx_leads_memory
    ON iagenericanexma_leads USING GIN (memory);

COMMENT ON COLUMN iagenericanexma_leads.memory IS 'Long-term AI memory for the lead including profile, known facts, and history summary';

-- ==================================================
-- Create checkpoints table for LangGraph persistence
-- ==================================================
CREATE TABLE IF NOT EXISTS iagenericanexma_checkpoints (
    id SERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(thread_id, checkpoint_ns, checkpoint_id)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread
    ON iagenericanexma_checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_ns
    ON iagenericanexma_checkpoints(thread_id, checkpoint_ns);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created
    ON iagenericanexma_checkpoints(created_at DESC);

COMMENT ON TABLE iagenericanexma_checkpoints IS 'LangGraph state checkpoints for conversation persistence';

-- ==================================================
-- Update conversation context structure (documentation)
-- ==================================================
-- The conversation.context JSONB field now supports:
-- {
--     "goal_progress": {
--         "goals": {
--             "nome": {"collected": true, "value": "João"},
--             "email": {"collected": false, "value": null}
--         },
--         "completion": 0.5,
--         "last_updated": "2024-01-01T00:00:00Z"
--     },
--     "conversation_state": {
--         "current_topic": "coleta_email",
--         "last_ai_action": "asked_email",
--         "retry_count": 0,
--         "sentiment": "positive",
--         "user_intent": null,
--         "awaiting_input": "email",
--         "last_question": "Qual seu email?",
--         "recent_context": "",
--         "current_phase": "qualification",
--         "triggered_conditions": [],
--         "pending_actions": []
--     },
--     "flow_position": {
--         "current_phase": "qualification",
--         "triggered_conditions": [],
--         "pending_actions": []
--     },
--     "recent_interactions": [
--         {
--             "timestamp": "2024-01-01T00:00:00Z",
--             "user_message": "Oi",
--             "ai_response": "Olá! Como posso ajudar?",
--             "extracted_data": {},
--             "sentiment": "neutral",
--             "topics": []
--         }
--     ],
--     "updated_at": "2024-01-01T00:00:00Z"
-- }

-- ==================================================
-- Memory field structure (documentation)
-- ==================================================
-- The lead.memory JSONB field stores:
-- {
--     "profile": {
--         "preferences": {},
--         "behavior_patterns": [],
--         "interaction_style": "formal|casual|mixed|unknown",
--         "preferred_contact_time": null,
--         "language_style": "pt-BR"
--     },
--     "facts": {
--         "stated_facts": {"mentioned_budget": "R$ 5000"},
--         "inferred_facts": {},
--         "interests": ["produto X", "serviço Y"],
--         "pain_points": ["preço alto", "demora"],
--         "mentioned_budget": "R$ 5000",
--         "urgency": "alta",
--         "timeline": "urgente"
--     },
--     "history_summary": "Lead interessado em X, mencionou Y...",
--     "last_topics": ["preço", "prazo", "garantia"],
--     "collected_data": {},
--     "updated_at": "2024-01-01T00:00:00Z"
-- }

-- ==================================================
-- Cleanup old checkpoints (optional maintenance)
-- ==================================================
-- Run this periodically to clean up old checkpoints:
-- DELETE FROM iagenericanexma_checkpoints
-- WHERE created_at < NOW() - INTERVAL '30 days';
