"""
Knowledge tools for the agent.

Tools for searching knowledge base and retrieving lead/company information.
"""
import logging
from typing import Any, Optional
from datetime import datetime
from langchain_core.tools import tool
from ...services.database import db

logger = logging.getLogger(__name__)


@tool
async def search_knowledge(
    company_id: int,
    query: str,
    category: Optional[str] = None
) -> dict[str, Any]:
    """
    Search the company's knowledge base for relevant information.
    Use this to find answers about products, services, pricing, FAQs, etc.

    Args:
        company_id: The company ID
        query: Search query or question
        category: Optional category filter - "produtos", "servicos", "precos", "faq", "politicas"

    Returns:
        Dictionary with search results and relevant information

    Example:
        search_knowledge(
            company_id=1,
            query="qual o preco do plano basico?",
            category="precos"
        )
    """
    try:
        logger.info(f"[TOOL] search_knowledge - company={company_id}, query={query}, category={category}")

        # Get company info
        company = await db.get_company(company_id)

        if not company:
            return {
                "success": False,
                "error": f"Empresa {company_id} nao encontrada.",
                "company_id": company_id
            }

        # Get company's informacoes_complementares as knowledge base
        company_info = company.informacoes_complementares or ""

        # In a production system, this would use vector search or semantic search
        # For now, we return the company info for the LLM to process

        # Simple keyword-based relevance (placeholder for semantic search)
        query_lower = query.lower()
        keywords = query_lower.split()

        # Check if query is about specific topics
        topic_hints = []
        if any(word in query_lower for word in ["preco", "valor", "custo", "quanto"]):
            topic_hints.append("precos")
        if any(word in query_lower for word in ["produto", "servico", "oferecer", "vender"]):
            topic_hints.append("produtos_servicos")
        if any(word in query_lower for word in ["horario", "funciona", "atendimento", "aberto"]):
            topic_hints.append("horarios")
        if any(word in query_lower for word in ["endereco", "localiza", "onde", "local"]):
            topic_hints.append("localizacao")
        if any(word in query_lower for word in ["prazo", "entrega", "demora", "tempo"]):
            topic_hints.append("prazos")
        if any(word in query_lower for word in ["garantia", "troca", "devolu"]):
            topic_hints.append("garantias")

        logger.info(f"[TOOL] search_knowledge - SUCCESS - topics: {topic_hints}")

        return {
            "success": True,
            "company_id": company_id,
            "company_name": company.nome_empresa or company.empresa,
            "query": query,
            "category": category,
            "topic_hints": topic_hints,
            "company_info": company_info,
            "note": "Use as informacoes da empresa para responder a pergunta do cliente.",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] search_knowledge - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao buscar conhecimento: {str(e)}",
            "company_id": company_id
        }


@tool
async def get_lead_history(
    lead_id: int,
    include_messages: bool = True,
    message_limit: int = 20
) -> dict[str, Any]:
    """
    Get the complete history of a lead including all interactions.
    Use this to understand the lead's journey and previous conversations.

    Args:
        lead_id: The lead ID in the database
        include_messages: Whether to include message history (default: True)
        message_limit: Maximum number of messages to retrieve (default: 20)

    Returns:
        Dictionary with lead history, collected data, and optionally messages

    Example:
        history = get_lead_history(lead_id=123, include_messages=True)
    """
    try:
        logger.info(f"[TOOL] get_lead_history - lead_id={lead_id}, include_messages={include_messages}")

        # Get lead info
        lead = await db.get_lead(lead_id)

        if not lead:
            return {
                "success": False,
                "error": f"Lead {lead_id} nao encontrado.",
                "lead_id": lead_id
            }

        # Build history object
        history = {
            "success": True,
            "lead_id": lead_id,
            "lead_info": {
                "nome": lead.nome,
                "celular": lead.celular,
                "email": lead.email,
                "origem": lead.origem,
                "ai_enabled": lead.ai_enabled,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
                "updated_at": lead.updated_at.isoformat() if lead.updated_at else None
            },
            "dados_coletados": lead.dados_coletados or {},
            "timeline": []
        }

        # Extract timeline events from dados_coletados
        dados = lead.dados_coletados or {}

        # Add follow-ups to timeline
        for followup in dados.get("followups", []):
            history["timeline"].append({
                "type": "followup",
                "status": followup.get("status"),
                "scheduled_for": followup.get("scheduled_for"),
                "message": followup.get("message")
            })

        # Add visits to timeline
        for visit in dados.get("visits", []):
            history["timeline"].append({
                "type": "visit",
                "status": visit.get("status"),
                "scheduled_for": visit.get("scheduled_for"),
                "visit_type": visit.get("type")
            })

        # Get messages if requested
        if include_messages:
            # Get active conversation
            conversation = await db.get_active_conversation(lead_id)

            if conversation:
                messages = await db.get_recent_messages(conversation.id, message_limit)

                history["conversation"] = {
                    "id": conversation.id,
                    "status": conversation.status,
                    "ai_enabled": conversation.ai_enabled,
                    "current_node_id": conversation.current_node_id
                }

                history["messages"] = [
                    {
                        "direction": msg.direction,
                        "content": msg.content,
                        "message_type": msg.message_type,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None
                    }
                    for msg in messages
                ]

        logger.info(f"[TOOL] get_lead_history - SUCCESS - retrieved history")

        return history
    except Exception as e:
        logger.error(f"[TOOL] get_lead_history - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao obter historico: {str(e)}",
            "lead_id": lead_id
        }


@tool
async def get_company_info(company_id: int) -> dict[str, Any]:
    """
    Get detailed information about a company.
    Use this to understand company context, settings, and preferences.

    Args:
        company_id: The company ID

    Returns:
        Dictionary with company information and settings

    Example:
        info = get_company_info(company_id=1)
    """
    try:
        logger.info(f"[TOOL] get_company_info - company_id={company_id}")

        company = await db.get_company(company_id)

        if not company:
            return {
                "success": False,
                "error": f"Empresa {company_id} nao encontrada.",
                "company_id": company_id
            }

        # Get lead statuses for the company
        statuses = await db.get_lead_statuses(company_id)

        info = {
            "success": True,
            "company_id": company_id,
            "company_name": company.nome_empresa or company.empresa,
            "agent_name": company.agent_name,
            "agent_tone": company.agent_tone,
            "use_emojis": company.use_emojis,
            "informacoes_complementares": company.informacoes_complementares,
            "whatsapp_numero": company.whatsapp_numero,
            "lead_statuses": [
                {
                    "id": status.id,
                    "nome": status.nome,
                    "cor": status.cor,
                    "is_default": status.is_default
                }
                for status in statuses
            ],
            "has_flow": company.flow_config is not None,
            "timestamp": datetime.utcnow().isoformat()
        }

        logger.info(f"[TOOL] get_company_info - SUCCESS")

        return info
    except Exception as e:
        logger.error(f"[TOOL] get_company_info - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao obter informacoes: {str(e)}",
            "company_id": company_id
        }


@tool
async def get_available_statuses(company_id: int) -> dict[str, Any]:
    """
    Get all available lead statuses for a company's kanban.
    Use this to know which statuses a lead can be moved to.

    Args:
        company_id: The company ID

    Returns:
        Dictionary with list of available statuses

    Example:
        statuses = get_available_statuses(company_id=1)
    """
    try:
        logger.info(f"[TOOL] get_available_statuses - company_id={company_id}")

        statuses = await db.get_lead_statuses(company_id)

        if not statuses:
            return {
                "success": False,
                "error": f"Nenhum status encontrado para empresa {company_id}.",
                "company_id": company_id
            }

        logger.info(f"[TOOL] get_available_statuses - SUCCESS - {len(statuses)} statuses")

        return {
            "success": True,
            "company_id": company_id,
            "statuses": [
                {
                    "id": status.id,
                    "nome": status.nome,
                    "cor": status.cor,
                    "ordem": status.ordem,
                    "is_default": status.is_default
                }
                for status in statuses
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[TOOL] get_available_statuses - ERROR - {str(e)}")
        return {
            "success": False,
            "error": f"Erro ao obter statuses: {str(e)}",
            "company_id": company_id
        }


# Export tools list
knowledge_tools = [
    search_knowledge,
    get_lead_history,
    get_company_info,
    get_available_statuses
]

__all__ = [
    "knowledge_tools",
    "search_knowledge",
    "get_lead_history",
    "get_company_info",
    "get_available_statuses"
]
