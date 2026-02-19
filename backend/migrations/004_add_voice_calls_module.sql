-- ============================================================
-- MIGRAÇÃO: Módulo de Chamadas de Voz (Voice Calls)
-- Data: 2026-02-01
-- Descrição: Adiciona suporte para chamadas de voz via ElevenLabs
--            Módulo isolado e opcional - pode ser ativado/desativado
-- ============================================================

-- Adicionar colunas na tabela companies para o toggle e config
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS voice_calls_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS voice_calls_config JSONB DEFAULT NULL;

-- Comentários nas colunas
COMMENT ON COLUMN companies.voice_calls_enabled IS 'Toggle para ativar/desativar chamadas de voz IA';
COMMENT ON COLUMN companies.voice_calls_config IS 'Configuração do módulo: api_key, agent_id, etc';

-- ============================================================
-- Tabela de logs de chamadas (histórico)
-- ============================================================
CREATE TABLE IF NOT EXISTS voice_call_logs (
    id BIGSERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,

    -- Identificação da chamada
    call_id VARCHAR(255),                    -- ID da chamada no ElevenLabs
    conversation_id VARCHAR(255),            -- ID da conversa

    -- Dados da chamada
    phone VARCHAR(50) NOT NULL,              -- Número chamado
    channel VARCHAR(20) DEFAULT 'whatsapp',  -- whatsapp, twilio
    status VARCHAR(50) DEFAULT 'pending',    -- pending, initiated, completed, failed, etc

    -- Resultado
    duration_seconds INTEGER,                -- Duração em segundos
    transcript JSONB,                        -- Transcrição da conversa
    analysis JSONB,                          -- Análise do ElevenLabs (success_evaluation, etc)

    -- Contexto
    context JSONB,                           -- Variáveis dinâmicas enviadas
    first_message TEXT,                      -- Mensagem inicial customizada

    -- Metadados
    error_message TEXT,                      -- Mensagem de erro se falhou
    webhook_received_at TIMESTAMPTZ,         -- Quando recebeu webhook de conclusão

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_voice_call_logs_company_id ON voice_call_logs(company_id);
CREATE INDEX IF NOT EXISTS idx_voice_call_logs_lead_id ON voice_call_logs(lead_id);
CREATE INDEX IF NOT EXISTS idx_voice_call_logs_call_id ON voice_call_logs(call_id);
CREATE INDEX IF NOT EXISTS idx_voice_call_logs_status ON voice_call_logs(status);
CREATE INDEX IF NOT EXISTS idx_voice_call_logs_created_at ON voice_call_logs(created_at DESC);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_voice_call_logs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_voice_call_logs_updated_at ON voice_call_logs;
CREATE TRIGGER trigger_voice_call_logs_updated_at
    BEFORE UPDATE ON voice_call_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_voice_call_logs_updated_at();

-- ============================================================
-- RLS (Row Level Security) - Opcional
-- ============================================================
-- ALTER TABLE voice_call_logs ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Exemplo de configuração JSON para voice_calls_config:
-- {
--     "api_key": "xi_...",
--     "agent_id": "agent_...",
--     "whatsapp_number_id": "...",
--     "twilio_from_number": "+55...",
--     "settings": {
--         "max_daily_calls": 100,
--         "call_hours_start": "09:00",
--         "call_hours_end": "18:00"
--     }
-- }
-- ============================================================
