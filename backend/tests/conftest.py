"""
Pytest configuration and shared fixtures for IAGenerica tests.
"""
import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_collected_data() -> Dict[str, Any]:
    """Sample collected data for testing."""
    return {
        "nome": "João Silva",
        "email": "joao@email.com",
        "telefone": "11999998888",
        "cidade": "São Paulo",
        "interesse": "Quero comprar um apartamento na zona sul",
        "orcamento": "R$ 800.000",
        "urgencia": "imediata"
    }


@pytest.fixture
def partial_collected_data() -> Dict[str, Any]:
    """Partial collected data (some fields missing)."""
    return {
        "nome": "Maria",
        "telefone": "11988887777"
    }


@pytest.fixture
def sample_flow_config() -> Dict[str, Any]:
    """Sample flow configuration for testing."""
    return {
        "nodes": [
            {
                "id": "greeting",
                "type": "GREETING",
                "name": "Saudação",
                "config": {"mensagem": "Olá! Como posso ajudar?"},
                "next_node_id": "ask_name"
            },
            {
                "id": "ask_name",
                "type": "NOME",
                "name": "Coletar Nome",
                "config": {
                    "pergunta": "Qual seu nome?",
                    "campo_destino": "nome"
                },
                "next_node_id": "ask_phone"
            },
            {
                "id": "ask_phone",
                "type": "TELEFONE",
                "name": "Coletar Telefone",
                "config": {
                    "pergunta": "Qual seu telefone?",
                    "campo_destino": "telefone"
                },
                "next_node_id": "ask_interest"
            },
            {
                "id": "ask_interest",
                "type": "INTERESSE",
                "name": "Interesse",
                "config": {
                    "pergunta": "No que podemos ajudar?",
                    "campo_destino": "interesse"
                },
                "next_node_id": "check_budget"
            },
            {
                "id": "check_budget",
                "type": "SWITCH",
                "name": "Verificar Orçamento",
                "config": {
                    "campo": "orcamento",
                    "cases": {
                        "alto": "high_value_path",
                        "medio": "medium_value_path",
                        "baixo": "low_value_path"
                    },
                    "default_node_id": "default_path"
                }
            },
            {
                "id": "high_value_path",
                "type": "HANDOFF",
                "name": "Cliente Premium",
                "config": {
                    "motivo": "Cliente com alto orçamento",
                    "mensagem_cliente": "Vou transferir para nosso consultor VIP!"
                }
            },
            {
                "id": "medium_value_path",
                "type": "MESSAGE",
                "name": "Caminho Médio",
                "config": {"mensagem": "Temos ótimas opções para você!"},
                "next_node_id": "end"
            },
            {
                "id": "low_value_path",
                "type": "MESSAGE",
                "name": "Caminho Baixo",
                "config": {"mensagem": "Temos opções acessíveis!"},
                "next_node_id": "end"
            },
            {
                "id": "default_path",
                "type": "MESSAGE",
                "name": "Caminho Padrão",
                "config": {"mensagem": "Entendi!"},
                "next_node_id": "end"
            },
            {
                "id": "end",
                "type": "END",
                "name": "Fim",
                "config": {"mensagem": "Obrigado pelo contato!"}
            }
        ],
        "edges": [
            {"id": "e1", "source": "greeting", "target": "ask_name"},
            {"id": "e2", "source": "ask_name", "target": "ask_phone"},
            {"id": "e3", "source": "ask_phone", "target": "ask_interest"},
            {"id": "e4", "source": "ask_interest", "target": "check_budget"}
        ],
        "start_node_id": "greeting",
        "global_config": {
            "campos_obrigatorios": ["nome", "telefone"],
            "comportamento_ia": "amigavel",
            "score_qualificacao": {
                "nome": 10,
                "telefone": 15,
                "email": 10,
                "interesse": 20,
                "orcamento": 25,
                "urgencia": 20
            },
            "score_minimo_qualificado": 70
        }
    }


@pytest.fixture
def sample_condition_flow_config() -> Dict[str, Any]:
    """Flow config with CONDITION node for testing."""
    return {
        "nodes": [
            {
                "id": "start",
                "type": "GREETING",
                "name": "Início",
                "config": {"mensagem": "Olá!"},
                "next_node_id": "check_urgency"
            },
            {
                "id": "check_urgency",
                "type": "CONDITION",
                "name": "Verificar Urgência",
                "config": {
                    "campo": "urgencia",
                    "operador": "equals",
                    "valor": "imediata"
                },
                "true_node_id": "urgent_path",
                "false_node_id": "normal_path"
            },
            {
                "id": "urgent_path",
                "type": "HANDOFF",
                "name": "Urgente",
                "config": {"motivo": "Cliente com urgência imediata"}
            },
            {
                "id": "normal_path",
                "type": "MESSAGE",
                "name": "Normal",
                "config": {"mensagem": "Vamos prosseguir normalmente."},
                "next_node_id": "end"
            },
            {
                "id": "end",
                "type": "END",
                "name": "Fim"
            }
        ],
        "edges": [],
        "start_node_id": "start"
    }


@pytest.fixture
def conversation_history():
    """Sample conversation history."""
    return [
        {"role": "user", "content": "Oi"},
        {"role": "assistant", "content": "Olá! Como posso ajudar?"},
        {"role": "user", "content": "Quero comprar um apartamento"},
        {"role": "assistant", "content": "Ótimo! Qual seu nome?"},
        {"role": "user", "content": "João Silva"},
    ]
