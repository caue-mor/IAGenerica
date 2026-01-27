"""
Database service - CRUD operations
Tabelas com prefixo: iagenericanexma_*
"""
from typing import Optional, Any
from ..core.supabase_client import supabase
from ..models import (
    Company, CompanyCreate, CompanyUpdate,
    Lead, LeadCreate, LeadUpdate, LeadStatus,
    Conversation, Message, MessageCreate,
    FlowConfig
)

# Prefixo das tabelas
TABLE_PREFIX = "iagenericanexma_"

# Nomes das tabelas
COMPANIES_TABLE = f"{TABLE_PREFIX}companies"
LEAD_STATUSES_TABLE = f"{TABLE_PREFIX}lead_statuses"
LEADS_TABLE = f"{TABLE_PREFIX}leads"
CONVERSATIONS_TABLE = f"{TABLE_PREFIX}conversations"
MESSAGES_TABLE = f"{TABLE_PREFIX}messages"


class DatabaseService:
    """Database service for all CRUD operations"""

    # ==================== COMPANIES ====================

    async def get_company(self, company_id: int) -> Optional[Company]:
        """Get company by ID"""
        response = supabase.table(COMPANIES_TABLE).select("*").eq("id", company_id).limit(1).execute()
        if response.data and len(response.data) > 0:
            return Company(**response.data[0])
        return None

    async def get_company_by_whatsapp(self, whatsapp_numero: str) -> Optional[Company]:
        """Get company by WhatsApp number"""
        response = supabase.table(COMPANIES_TABLE).select("*").eq("whatsapp_numero", whatsapp_numero).limit(1).execute()
        if response.data and len(response.data) > 0:
            return Company(**response.data[0])
        return None

    async def get_company_by_token(self, token: str) -> Optional[Company]:
        """Get company by UAZAPI token"""
        response = supabase.table(COMPANIES_TABLE).select("*").eq("uazapi_token", token).limit(1).execute()
        if response.data and len(response.data) > 0:
            return Company(**response.data[0])
        return None

    async def list_companies(self) -> list[Company]:
        """List all companies"""
        response = supabase.table(COMPANIES_TABLE).select("*").order("id").execute()
        return [Company(**c) for c in response.data] if response.data else []

    async def create_company(self, company: CompanyCreate) -> Company:
        """Create new company"""
        response = supabase.table(COMPANIES_TABLE).insert(company.model_dump(exclude_none=True)).execute()
        return Company(**response.data[0])

    async def update_company(self, company_id: int, company: CompanyUpdate | dict[str, Any]) -> Optional[Company]:
        """Update company - accepts CompanyUpdate model or dict"""
        if isinstance(company, dict):
            data = {k: v for k, v in company.items() if v is not None}
        else:
            data = company.model_dump(exclude_none=True)
        if not data:
            return await self.get_company(company_id)
        response = supabase.table(COMPANIES_TABLE).update(data).eq("id", company_id).execute()
        if response.data:
            return Company(**response.data[0])
        return None

    async def update_company_flow(self, company_id: int, flow_config: FlowConfig) -> Optional[Company]:
        """Update company flow configuration"""
        response = supabase.table(COMPANIES_TABLE).update({
            "flow_config": flow_config.model_dump()
        }).eq("id", company_id).execute()
        if response.data:
            return Company(**response.data[0])
        return None

    async def delete_company(self, company_id: int) -> bool:
        """Delete company"""
        response = supabase.table(COMPANIES_TABLE).delete().eq("id", company_id).execute()
        return len(response.data) > 0 if response.data else False

    # ==================== LEAD STATUSES ====================

    async def get_lead_statuses(self, company_id: int) -> list[LeadStatus]:
        """Get all lead statuses for a company"""
        response = supabase.table(LEAD_STATUSES_TABLE).select("*").eq(
            "company_id", company_id
        ).order("ordem").execute()
        return [LeadStatus(**s) for s in response.data] if response.data else []

    async def get_default_status(self, company_id: int) -> Optional[LeadStatus]:
        """Get default status for a company"""
        response = supabase.table(LEAD_STATUSES_TABLE).select("*").eq(
            "company_id", company_id
        ).eq("is_default", True).limit(1).execute()
        if response.data and len(response.data) > 0:
            return LeadStatus(**response.data[0])
        return None

    async def create_lead_status(self, company_id: int, nome: str, cor: str = "#6B7280", ordem: int = 0) -> LeadStatus:
        """Create new lead status"""
        response = supabase.table(LEAD_STATUSES_TABLE).insert({
            "company_id": company_id,
            "nome": nome,
            "cor": cor,
            "ordem": ordem
        }).execute()
        return LeadStatus(**response.data[0])

    # ==================== LEADS ====================

    async def get_lead(self, lead_id: int) -> Optional[Lead]:
        """Get lead by ID"""
        response = supabase.table(LEADS_TABLE).select("*").eq("id", lead_id).limit(1).execute()
        if response.data and len(response.data) > 0:
            return Lead(**response.data[0])
        return None

    async def get_lead_by_phone(self, company_id: int, celular: str) -> Optional[Lead]:
        """Get lead by phone number"""
        response = supabase.table(LEADS_TABLE).select("*").eq(
            "company_id", company_id
        ).eq("celular", celular).limit(1).execute()
        if response.data and len(response.data) > 0:
            return Lead(**response.data[0])
        return None

    async def list_leads(self, company_id: int, status_id: Optional[int] = None) -> list[Lead]:
        """List leads for a company"""
        query = supabase.table(LEADS_TABLE).select("*").eq("company_id", company_id)
        if status_id:
            query = query.eq("status_id", status_id)
        response = query.order("created_at", desc=True).execute()
        return [Lead(**l) for l in response.data] if response.data else []

    async def create_lead(self, lead: LeadCreate) -> Lead:
        """Create new lead"""
        # Get default status if not provided
        if not lead.status_id:
            default_status = await self.get_default_status(lead.company_id)
            if default_status:
                lead.status_id = default_status.id

        response = supabase.table(LEADS_TABLE).insert(lead.model_dump(exclude_none=True)).execute()
        return Lead(**response.data[0])

    async def update_lead(self, lead_id: int, lead: LeadUpdate) -> Optional[Lead]:
        """Update lead"""
        data = lead.model_dump(exclude_none=True)
        if not data:
            return await self.get_lead(lead_id)
        response = supabase.table(LEADS_TABLE).update(data).eq("id", lead_id).execute()
        if response.data:
            return Lead(**response.data[0])
        return None

    async def update_lead_field(self, lead_id: int, field: str, value: Any) -> Optional[Lead]:
        """Update a specific field in dados_coletados"""
        lead = await self.get_lead(lead_id)
        if not lead:
            return None

        dados = lead.dados_coletados or {}
        dados[field] = value

        response = supabase.table(LEADS_TABLE).update({
            "dados_coletados": dados
        }).eq("id", lead_id).execute()

        if response.data:
            return Lead(**response.data[0])
        return None

    async def update_lead_name(self, lead_id: int, nome: str) -> Optional[Lead]:
        """Update lead name"""
        response = supabase.table(LEADS_TABLE).update({
            "nome": nome
        }).eq("id", lead_id).execute()
        if response.data:
            return Lead(**response.data[0])
        return None

    async def update_lead_status(self, lead_id: int, status_id: int) -> Optional[Lead]:
        """Update lead status"""
        response = supabase.table(LEADS_TABLE).update({
            "status_id": status_id
        }).eq("id", lead_id).execute()
        if response.data:
            return Lead(**response.data[0])
        return None

    async def set_lead_ai(self, lead_id: int, enabled: bool) -> Optional[Lead]:
        """Enable/disable AI for lead"""
        response = supabase.table(LEADS_TABLE).update({
            "ai_enabled": enabled
        }).eq("id", lead_id).execute()
        if response.data:
            return Lead(**response.data[0])
        return None

    async def delete_lead(self, lead_id: int) -> bool:
        """Delete lead"""
        response = supabase.table(LEADS_TABLE).delete().eq("id", lead_id).execute()
        return len(response.data) > 0 if response.data else False

    async def get_or_create_lead(self, company_id: int, celular: str, origem: Optional[str] = None) -> Lead:
        """Get existing lead or create new one"""
        lead = await self.get_lead_by_phone(company_id, celular)
        if lead:
            return lead

        return await self.create_lead(LeadCreate(
            company_id=company_id,
            celular=celular,
            origem=origem or "whatsapp"
        ))

    # ==================== CONVERSATIONS ====================

    async def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation by ID"""
        response = supabase.table(CONVERSATIONS_TABLE).select("*").eq("id", conversation_id).limit(1).execute()
        if response.data and len(response.data) > 0:
            return Conversation(**response.data[0])
        return None

    async def get_conversation_by_thread(self, thread_id: str) -> Optional[Conversation]:
        """Get conversation by thread ID"""
        response = supabase.table(CONVERSATIONS_TABLE).select("*").eq("thread_id", thread_id).limit(1).execute()
        if response.data and len(response.data) > 0:
            return Conversation(**response.data[0])
        return None

    async def get_active_conversation(self, lead_id: int) -> Optional[Conversation]:
        """Get active conversation for a lead"""
        response = supabase.table(CONVERSATIONS_TABLE).select("*").eq(
            "lead_id", lead_id
        ).eq("status", "active").order("created_at", desc=True).limit(1).execute()
        if response.data:
            return Conversation(**response.data[0])
        return None

    async def list_conversations(self, company_id: int, lead_id: Optional[int] = None) -> list[Conversation]:
        """List conversations"""
        query = supabase.table(CONVERSATIONS_TABLE).select("*").eq("company_id", company_id)
        if lead_id:
            query = query.eq("lead_id", lead_id)
        response = query.order("updated_at", desc=True).execute()
        return [Conversation(**c) for c in response.data] if response.data else []

    async def create_conversation(
        self,
        company_id: int,
        lead_id: int,
        thread_id: str,
        start_node_id: Optional[str] = None
    ) -> Conversation:
        """Create new conversation"""
        response = supabase.table(CONVERSATIONS_TABLE).insert({
            "company_id": company_id,
            "lead_id": lead_id,
            "thread_id": thread_id,
            "current_node_id": start_node_id
        }).execute()
        return Conversation(**response.data[0])

    async def update_conversation_node(self, conversation_id: int, node_id: Optional[str]) -> Optional[Conversation]:
        """Update current node in conversation"""
        response = supabase.table(CONVERSATIONS_TABLE).update({
            "current_node_id": node_id
        }).eq("id", conversation_id).execute()
        if response.data:
            return Conversation(**response.data[0])
        return None

    async def update_conversation_context(self, conversation_id: int, context: dict[str, Any]) -> Optional[Conversation]:
        """Update conversation context"""
        response = supabase.table(CONVERSATIONS_TABLE).update({
            "context": context
        }).eq("id", conversation_id).execute()
        if response.data:
            return Conversation(**response.data[0])
        return None

    async def set_conversation_ai(self, conversation_id: int, enabled: bool) -> Optional[Conversation]:
        """Enable/disable AI for conversation"""
        response = supabase.table(CONVERSATIONS_TABLE).update({
            "ai_enabled": enabled
        }).eq("id", conversation_id).execute()
        if response.data:
            return Conversation(**response.data[0])
        return None

    async def close_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Close conversation"""
        response = supabase.table(CONVERSATIONS_TABLE).update({
            "status": "closed"
        }).eq("id", conversation_id).execute()
        if response.data:
            return Conversation(**response.data[0])
        return None

    async def get_or_create_conversation(
        self,
        company_id: int,
        lead_id: int,
        thread_id: str,
        start_node_id: Optional[str] = None
    ) -> Conversation:
        """Get existing conversation or create new one"""
        conversation = await self.get_conversation_by_thread(thread_id)
        if conversation:
            return conversation

        return await self.create_conversation(company_id, lead_id, thread_id, start_node_id)

    # ==================== MESSAGES ====================

    async def get_message(self, message_id: int) -> Optional[Message]:
        """Get message by ID"""
        response = supabase.table(MESSAGES_TABLE).select("*").eq("id", message_id).limit(1).execute()
        if response.data and len(response.data) > 0:
            return Message(**response.data[0])
        return None

    async def list_messages(self, conversation_id: int, limit: int = 50) -> list[Message]:
        """List messages in a conversation"""
        response = supabase.table(MESSAGES_TABLE).select("*").eq(
            "conversation_id", conversation_id
        ).order("created_at", desc=True).limit(limit).execute()
        messages = [Message(**m) for m in response.data] if response.data else []
        return list(reversed(messages))  # Return in chronological order

    async def get_recent_messages(self, conversation_id: int, limit: int = 10) -> list[Message]:
        """Get recent messages for context"""
        return await self.list_messages(conversation_id, limit)

    async def create_message(self, message: MessageCreate) -> Message:
        """Create new message"""
        response = supabase.table(MESSAGES_TABLE).insert(message.model_dump(exclude_none=True)).execute()
        return Message(**response.data[0])

    async def save_inbound_message(
        self,
        conversation_id: int,
        lead_id: int,
        content: str,
        message_type: str = "text",
        media_url: Optional[str] = None,
        uazapi_message_id: Optional[str] = None
    ) -> Message:
        """Save inbound message from user"""
        return await self.create_message(MessageCreate(
            conversation_id=conversation_id,
            lead_id=lead_id,
            direction="inbound",
            message_type=message_type,
            content=content,
            media_url=media_url,
            uazapi_message_id=uazapi_message_id
        ))

    async def save_outbound_message(
        self,
        conversation_id: int,
        lead_id: int,
        content: str,
        message_type: str = "text",
        media_url: Optional[str] = None,
        uazapi_message_id: Optional[str] = None
    ) -> Message:
        """Save outbound message to user"""
        return await self.create_message(MessageCreate(
            conversation_id=conversation_id,
            lead_id=lead_id,
            direction="outbound",
            message_type=message_type,
            content=content,
            media_url=media_url,
            uazapi_message_id=uazapi_message_id
        ))


# Singleton instance
db = DatabaseService()
