-- =============================================
-- IA GENERICA NEXMA - Initial Schema
-- Prefixo: iagenericanexma_*
-- =============================================

-- COMPANIES (Empresas)
CREATE TABLE IF NOT EXISTS iagenericanexma_companies (
    id SERIAL PRIMARY KEY,
    empresa VARCHAR(255) NOT NULL,
    nome_empresa VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    cidade VARCHAR(100),
    site VARCHAR(255),
    horario_funcionamento VARCHAR(255),
    uazapi_instancia VARCHAR(255),
    uazapi_token VARCHAR(255),
    whatsapp_numero VARCHAR(20),
    agent_name VARCHAR(100) DEFAULT 'Assistente',
    agent_tone VARCHAR(50) DEFAULT 'amigavel',
    use_emojis BOOLEAN DEFAULT false,
    informacoes_complementares TEXT,
    flow_config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- LEAD_STATUSES (Kanban Columns)
CREATE TABLE IF NOT EXISTS iagenericanexma_lead_statuses (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES iagenericanexma_companies(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    cor VARCHAR(20) DEFAULT '#6B7280',
    ordem INTEGER DEFAULT 0,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LEADS
CREATE TABLE IF NOT EXISTS iagenericanexma_leads (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES iagenericanexma_companies(id) ON DELETE CASCADE,
    status_id INTEGER REFERENCES iagenericanexma_lead_statuses(id),
    nome VARCHAR(255),
    celular VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    dados_coletados JSONB DEFAULT '{}',
    ai_enabled BOOLEAN DEFAULT true,
    origem VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(company_id, celular)
);

-- CONVERSATIONS
CREATE TABLE IF NOT EXISTS iagenericanexma_conversations (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES iagenericanexma_companies(id) ON DELETE CASCADE,
    lead_id INTEGER REFERENCES iagenericanexma_leads(id) ON DELETE CASCADE,
    thread_id VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(50) DEFAULT 'active',
    ai_enabled BOOLEAN DEFAULT true,
    current_node_id VARCHAR(100),
    context JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- MESSAGES
CREATE TABLE IF NOT EXISTS iagenericanexma_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES iagenericanexma_conversations(id) ON DELETE CASCADE,
    lead_id INTEGER REFERENCES iagenericanexma_leads(id) ON DELETE CASCADE,
    direction VARCHAR(10) NOT NULL,  -- inbound | outbound
    message_type VARCHAR(20) DEFAULT 'text',
    content TEXT,
    media_url TEXT,
    status VARCHAR(20) DEFAULT 'sent',
    uazapi_message_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- INDICES
CREATE INDEX IF NOT EXISTS idx_iagenericanexma_leads_company ON iagenericanexma_leads(company_id);
CREATE INDEX IF NOT EXISTS idx_iagenericanexma_leads_celular ON iagenericanexma_leads(celular);
CREATE INDEX IF NOT EXISTS idx_iagenericanexma_leads_status ON iagenericanexma_leads(status_id);
CREATE INDEX IF NOT EXISTS idx_iagenericanexma_conversations_thread ON iagenericanexma_conversations(thread_id);
CREATE INDEX IF NOT EXISTS idx_iagenericanexma_conversations_lead ON iagenericanexma_conversations(lead_id);
CREATE INDEX IF NOT EXISTS idx_iagenericanexma_messages_conversation ON iagenericanexma_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_iagenericanexma_messages_lead ON iagenericanexma_messages(lead_id);
CREATE INDEX IF NOT EXISTS idx_iagenericanexma_leads_dados_gin ON iagenericanexma_leads USING GIN (dados_coletados);

-- TRIGGER: updated_at para companies
CREATE OR REPLACE FUNCTION iagenericanexma_update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_iagenericanexma_companies_updated_at ON iagenericanexma_companies;
CREATE TRIGGER update_iagenericanexma_companies_updated_at
    BEFORE UPDATE ON iagenericanexma_companies
    FOR EACH ROW
    EXECUTE FUNCTION iagenericanexma_update_updated_at_column();

DROP TRIGGER IF EXISTS update_iagenericanexma_leads_updated_at ON iagenericanexma_leads;
CREATE TRIGGER update_iagenericanexma_leads_updated_at
    BEFORE UPDATE ON iagenericanexma_leads
    FOR EACH ROW
    EXECUTE FUNCTION iagenericanexma_update_updated_at_column();

DROP TRIGGER IF EXISTS update_iagenericanexma_conversations_updated_at ON iagenericanexma_conversations;
CREATE TRIGGER update_iagenericanexma_conversations_updated_at
    BEFORE UPDATE ON iagenericanexma_conversations
    FOR EACH ROW
    EXECUTE FUNCTION iagenericanexma_update_updated_at_column();

-- SEED: Default statuses para novas companies
CREATE OR REPLACE FUNCTION iagenericanexma_create_default_statuses()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO iagenericanexma_lead_statuses (company_id, nome, cor, ordem, is_default) VALUES
        (NEW.id, 'Novo', '#3B82F6', 0, true),
        (NEW.id, 'Em Atendimento', '#F59E0B', 1, false),
        (NEW.id, 'Qualificado', '#10B981', 2, false),
        (NEW.id, 'Convertido', '#8B5CF6', 3, false),
        (NEW.id, 'Perdido', '#EF4444', 4, false);
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS iagenericanexma_create_company_default_statuses ON iagenericanexma_companies;
CREATE TRIGGER iagenericanexma_create_company_default_statuses
    AFTER INSERT ON iagenericanexma_companies
    FOR EACH ROW
    EXECUTE FUNCTION iagenericanexma_create_default_statuses();

-- =============================================
-- RLS (Row Level Security) - Opcional
-- =============================================

-- Habilitar RLS
ALTER TABLE iagenericanexma_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE iagenericanexma_lead_statuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE iagenericanexma_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE iagenericanexma_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE iagenericanexma_messages ENABLE ROW LEVEL SECURITY;

-- Policies para acesso publico via API (webhook)
CREATE POLICY "iagenericanexma_companies_public_read" ON iagenericanexma_companies FOR SELECT USING (true);
CREATE POLICY "iagenericanexma_companies_public_write" ON iagenericanexma_companies FOR ALL USING (true);

CREATE POLICY "iagenericanexma_lead_statuses_public_read" ON iagenericanexma_lead_statuses FOR SELECT USING (true);
CREATE POLICY "iagenericanexma_lead_statuses_public_write" ON iagenericanexma_lead_statuses FOR ALL USING (true);

CREATE POLICY "iagenericanexma_leads_public_read" ON iagenericanexma_leads FOR SELECT USING (true);
CREATE POLICY "iagenericanexma_leads_public_write" ON iagenericanexma_leads FOR ALL USING (true);

CREATE POLICY "iagenericanexma_conversations_public_read" ON iagenericanexma_conversations FOR SELECT USING (true);
CREATE POLICY "iagenericanexma_conversations_public_write" ON iagenericanexma_conversations FOR ALL USING (true);

CREATE POLICY "iagenericanexma_messages_public_read" ON iagenericanexma_messages FOR SELECT USING (true);
CREATE POLICY "iagenericanexma_messages_public_write" ON iagenericanexma_messages FOR ALL USING (true);

-- =============================================
-- COMENTARIOS (Documentacao)
-- =============================================

COMMENT ON TABLE iagenericanexma_companies IS 'Empresas cadastradas no sistema IA Generica Nexma';
COMMENT ON TABLE iagenericanexma_lead_statuses IS 'Status do Kanban para cada empresa';
COMMENT ON TABLE iagenericanexma_leads IS 'Leads/Contatos de cada empresa';
COMMENT ON TABLE iagenericanexma_conversations IS 'Conversas do WhatsApp';
COMMENT ON TABLE iagenericanexma_messages IS 'Mensagens das conversas';

COMMENT ON COLUMN iagenericanexma_leads.dados_coletados IS 'JSONB generico para armazenar dados coletados pelo fluxo';
COMMENT ON COLUMN iagenericanexma_companies.flow_config IS 'Configuracao do fluxo de atendimento em JSON';
