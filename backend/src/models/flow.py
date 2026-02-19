"""
Flow configuration models - Extended with 20+ node types
"""
from enum import Enum
from typing import Optional, Any, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Extended flow node types - 25+ types for complete automation"""

    # ============ BASICOS (existentes) ============
    GREETING = "GREETING"
    QUESTION = "QUESTION"
    CONDITION = "CONDITION"
    MESSAGE = "MESSAGE"
    ACTION = "ACTION"
    HANDOFF = "HANDOFF"
    FOLLOWUP = "FOLLOWUP"

    # ============ COLETA DE DADOS ESPECIFICOS ============
    NOME = "NOME"
    EMAIL = "EMAIL"
    TELEFONE = "TELEFONE"
    CIDADE = "CIDADE"
    ENDERECO = "ENDERECO"
    CPF = "CPF"
    DATA_NASCIMENTO = "DATA_NASCIMENTO"

    # ============ QUALIFICACAO ============
    QUALIFICATION = "QUALIFICATION"
    INTERESSE = "INTERESSE"
    ORCAMENTO = "ORCAMENTO"
    URGENCIA = "URGENCIA"

    # ============ ACOES COMERCIAIS ============
    PROPOSTA = "PROPOSTA"
    NEGOCIACAO = "NEGOCIACAO"
    AGENDAMENTO = "AGENDAMENTO"
    VISITA = "VISITA"

    # ============ NOTIFICACOES ============
    NOTIFICACAO = "NOTIFICACAO"
    ALERTA = "ALERTA"

    # ============ MIDIA ============
    FOTO = "FOTO"
    DOCUMENTO = "DOCUMENTO"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"

    # ============ INTEGRACOES ============
    WEBHOOK_CALL = "WEBHOOK_CALL"
    API_INTEGRATION = "API_INTEGRATION"

    # ============ CONTROLE DE FLUXO ============
    DELAY = "DELAY"
    LOOP = "LOOP"
    SWITCH = "SWITCH"
    PARALLEL = "PARALLEL"  # Execute multiple paths simultaneously
    END = "END"


class FieldType(str, Enum):
    """Field types for data collection nodes"""
    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    DATETIME = "datetime"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    BOOLEAN = "boolean"
    CPF = "cpf"
    CNPJ = "cnpj"
    CEP = "cep"
    CURRENCY = "currency"
    URL = "url"
    FILE = "file"
    IMAGE = "image"


class Operator(str, Enum):
    """Operators for CONDITION nodes"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    EXISTS = "exists"
    MATCHES_REGEX = "matches_regex"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"


class ActionType(str, Enum):
    """Action types for ACTION nodes"""
    WEBHOOK = "webhook"
    API_CALL = "api_call"
    UPDATE_FIELD = "update_field"
    TAG_LEAD = "tag_lead"
    MOVE_STATUS = "move_status"
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    CREATE_TASK = "create_task"
    NOTIFY_TEAM = "notify_team"
    SCHEDULE_FOLLOWUP = "schedule_followup"
    CALCULATE = "calculate"
    SET_VARIABLE = "set_variable"


class UrgencyLevel(str, Enum):
    """Urgency levels for qualification"""
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class QualificationScore(str, Enum):
    """Lead qualification scores"""
    FRIO = "frio"
    MORNO = "morno"
    QUENTE = "quente"
    QUALIFICADO = "qualificado"


class MediaType(str, Enum):
    """Types of media for media nodes"""
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    STICKER = "sticker"


# ============ VALIDATION RULES ============

class ValidationRule(BaseModel):
    """Validation rule for field input"""

    model_config = {"extra": "allow"}

    type: str  # regex, min_length, max_length, min_value, max_value, custom
    value: Any
    error_message: Optional[str] = None


# ============ NODE CONFIGURATIONS ============

class ResponseType(str, Enum):
    """Response type for node output"""
    TEXT = "text"
    AUDIO = "audio"
    BOTH = "both"  # Send both text and audio


class NodeConfig(BaseModel):
    """Extended node configuration for all node types - FLEXIBLE to accept frontend data"""

    model_config = {"extra": "allow"}  # Allow extra fields from frontend

    # ---- RESPONSE TYPE (text or audio via ElevenLabs) ----
    response_type: Optional[str] = "text"  # text, audio, both
    voice_id: Optional[str] = None  # ElevenLabs voice ID (optional, uses default)
    voice_stability: Optional[float] = 0.5
    voice_similarity: Optional[float] = 0.75

    # ---- GREETING / MESSAGE ----
    mensagem: Optional[str] = None
    mensagens_alternativas: Optional[List[str]] = None  # Para variacao
    delay_ms: Optional[int] = None  # Delay antes de enviar

    # ---- QUESTION / DATA COLLECTION ----
    pergunta: Optional[str] = None
    campo_destino: Optional[str] = None
    tipo_campo: Optional[str] = None  # Accept string (text, number, email, etc)
    opcoes: Optional[List[str]] = None  # for SELECT type
    validacao: Optional[str] = None
    validacao_rules: Optional[List[ValidationRule]] = None
    mensagem_erro: Optional[str] = None
    max_retries: Optional[int] = 3
    obrigatorio: Optional[bool] = True
    valor_padrao: Optional[Any] = None
    placeholder: Optional[str] = None

    # ---- CONDITION ----
    campo: Optional[str] = None
    operador: Optional[str] = None  # Accept string (equals, not_equals, etc)
    valor: Optional[Any] = None
    expressao: Optional[str] = None  # Para condicoes complexas

    # ---- ACTION ----
    tipo_acao: Optional[str] = None  # Accept string (webhook, api_call, etc)
    url: Optional[str] = None
    method: Optional[str] = "POST"
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    novo_status_id: Optional[int] = None
    tags: Optional[List[str]] = None
    timeout_seconds: Optional[int] = 30
    retry_on_fail: Optional[bool] = False

    # ---- HANDOFF ----
    motivo: Optional[str] = None
    mensagem_cliente: Optional[str] = None
    notificar_equipe: Optional[bool] = True
    departamento: Optional[str] = None
    prioridade: Optional[str] = "normal"

    # ---- FOLLOWUP ----
    intervalos: Optional[List[int]] = None  # minutes
    mensagens: Optional[List[str]] = None
    max_followups: Optional[int] = 3

    # ---- QUALIFICATION ----
    criterios: Optional[Dict[str, Any]] = None
    score_minimo: Optional[int] = None
    campos_avaliados: Optional[List[str]] = None

    # ---- PROPOSTA / NEGOCIACAO ----
    template_proposta: Optional[str] = None
    valores: Optional[Dict[str, Any]] = None
    condicoes: Optional[List[str]] = None
    prazo_validade_dias: Optional[int] = None

    # ---- AGENDAMENTO / VISITA ----
    tipo_agendamento: Optional[str] = None  # reuniao, visita, ligacao
    duracao_minutos: Optional[int] = 60
    horarios_disponiveis: Optional[List[str]] = None
    local: Optional[str] = None
    responsavel: Optional[str] = None

    # ---- NOTIFICACAO / ALERTA ----
    canal_notificacao: Optional[str] = None  # email, sms, whatsapp, slack
    destinatarios: Optional[List[str]] = None
    nivel_urgencia: Optional[str] = None  # Accept string
    template_notificacao: Optional[str] = None

    # ---- MEDIA ----
    tipo_midia: Optional[str] = None  # Accept string
    url_midia: Optional[str] = None
    caption: Optional[str] = None
    aceitar_tipos: Optional[List[str]] = None  # Para upload
    tamanho_max_mb: Optional[int] = 10

    # ---- DELAY / LOOP ----
    delay_seconds: Optional[int] = None
    max_iterations: Optional[int] = None
    loop_condition: Optional[str] = None

    # ---- SWITCH (multiple conditions) ----
    cases: Optional[Dict[str, str]] = None  # value -> node_id
    default_node_id: Optional[str] = None

    # ---- PARALLEL (execute multiple paths) ----
    parallel_paths: Optional[List[str]] = None  # List of node_ids to execute in parallel
    wait_for_all: Optional[bool] = True  # Wait for all paths to complete before continuing
    merge_node_id: Optional[str] = None  # Node to continue after all paths complete

    # ---- METADATA ----
    descricao: Optional[str] = None
    notas: Optional[str] = None


class FlowNode(BaseModel):
    """Flow node definition - FLEXIBLE to accept frontend data"""

    model_config = {"extra": "allow"}

    id: str
    type: str  # Accept string (GREETING, QUESTION, etc) - flexible
    name: str
    config: Optional[NodeConfig] = None  # Make optional for simpler nodes
    next_node_id: Optional[str] = None
    # For CONDITION nodes
    true_node_id: Optional[str] = None
    false_node_id: Optional[str] = None
    # For SWITCH nodes
    case_node_ids: Optional[Dict[str, str]] = None
    # For PARALLEL nodes (execute multiple paths simultaneously)
    parallel_node_ids: Optional[List[str]] = None
    # Visual position
    position: Optional[Dict[str, Any]] = None  # {x, y} for visual builder - Any to accept int or float
    # Metadata
    group: Optional[str] = None  # Para agrupar nos visualmente
    color: Optional[str] = None
    icon: Optional[str] = None


class FlowEdge(BaseModel):
    """Flow edge definition - FLEXIBLE to accept frontend data"""

    model_config = {"extra": "allow"}

    id: str
    source: str
    target: str
    label: Optional[str] = None
    condition: Optional[str] = None  # Para edges condicionais
    animated: Optional[bool] = False


class GlobalConfig(BaseModel):
    """Global configuration for the entire flow"""

    model_config = {"extra": "allow"}

    # Campos obrigatorios para conversao
    campos_obrigatorios: List[str] = Field(
        default=["nome", "telefone"],
        description="Campos que devem ser coletados antes de encerrar"
    )

    # Campos que nao devem ser exibidos ao usuario
    campos_ocultos: List[str] = Field(
        default=["id", "created_at", "updated_at"],
        description="Campos internos que nao aparecem em mensagens"
    )

    # Mensagens padrao
    saudacao_padrao: str = "Ola! Como posso ajudar?"
    mensagem_timeout: str = "Desculpe, nao entendi. Pode repetir?"
    mensagem_erro_validacao: str = "O valor informado nao e valido. Por favor, tente novamente."
    mensagem_despedida: str = "Obrigado pelo contato! Ate logo."
    mensagem_fora_horario: str = "Estamos fora do horario de atendimento. Retornaremos em breve."

    # Timeouts
    message_timeout_seconds: int = 300  # 5 minutos
    session_timeout_seconds: int = 1800  # 30 minutos
    inactivity_followup_seconds: int = 600  # 10 minutos

    # Retries
    max_retries: int = 3
    retry_delay_seconds: int = 5

    # Comportamento da IA
    comportamento_ia: str = "amigavel"  # formal, amigavel, tecnico, vendedor
    tom_comunicacao: str = "informal"  # formal, informal
    usar_emojis: bool = False
    personalidade: Optional[str] = None

    # Horario de atendimento
    horario_atendimento: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Ex: {'segunda': {'inicio': '08:00', 'fim': '18:00'}, ...}"
    )

    # Fuso horario
    timezone: str = "America/Sao_Paulo"

    # Integracao
    webhook_eventos: List[str] = Field(
        default=["lead_created", "lead_qualified", "handoff"],
        description="Eventos que disparam webhooks"
    )

    # Qualificacao
    score_qualificacao: Dict[str, int] = Field(
        default={
            "nome": 10,
            "telefone": 15,
            "email": 10,
            "interesse": 20,
            "orcamento": 25,
            "urgencia": 20
        },
        description="Pontuacao por campo coletado"
    )
    score_minimo_qualificado: int = 70


class FlowConfig(BaseModel):
    """Complete flow configuration - FLEXIBLE to accept frontend data"""

    model_config = {"extra": "allow"}

    nodes: List[FlowNode]
    edges: List[FlowEdge]
    start_node_id: str
    version: str = "1.0"  # Default to 1.0 to match frontend

    # Configuracoes globais
    global_config: Optional[GlobalConfig] = None

    # Metadata
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None

    # Grupos de nos (para organizacao visual)
    node_groups: Optional[Dict[str, List[str]]] = None

    # Variaveis globais do fluxo
    variables: Optional[Dict[str, Any]] = None


# ============ UTILITY FUNCTIONS ============

def create_default_flow() -> FlowConfig:
    """Create a simple default flow"""
    return FlowConfig(
        name="Fluxo Padrao",
        description="Fluxo basico de atendimento",
        nodes=[
            FlowNode(
                id="greeting",
                type=NodeType.GREETING,
                name="Saudacao",
                config=NodeConfig(
                    mensagem="Ola! Seja bem-vindo. Como posso ajuda-lo hoje?"
                ),
                next_node_id="ask_name"
            ),
            FlowNode(
                id="ask_name",
                type=NodeType.NOME,
                name="Coletar Nome",
                config=NodeConfig(
                    pergunta="Qual e o seu nome?",
                    campo_destino="nome",
                    tipo_campo=FieldType.TEXT,
                    obrigatorio=True,
                    mensagem_erro="Por favor, informe seu nome."
                ),
                next_node_id="ask_phone"
            ),
            FlowNode(
                id="ask_phone",
                type=NodeType.TELEFONE,
                name="Coletar Telefone",
                config=NodeConfig(
                    pergunta="Qual seu telefone para contato?",
                    campo_destino="telefone",
                    tipo_campo=FieldType.PHONE,
                    obrigatorio=True,
                    mensagem_erro="Por favor, informe um telefone valido."
                ),
                next_node_id="ask_interest"
            ),
            FlowNode(
                id="ask_interest",
                type=NodeType.INTERESSE,
                name="Interesse",
                config=NodeConfig(
                    pergunta="No que posso ajuda-lo?",
                    campo_destino="interesse",
                    tipo_campo=FieldType.TEXT
                ),
                next_node_id="qualify"
            ),
            FlowNode(
                id="qualify",
                type=NodeType.QUALIFICATION,
                name="Qualificar Lead",
                config=NodeConfig(
                    criterios={"campos_minimos": ["nome", "telefone", "interesse"]},
                    campos_avaliados=["nome", "telefone", "interesse"]
                ),
                true_node_id="handoff",
                false_node_id="ask_more_info"
            ),
            FlowNode(
                id="ask_more_info",
                type=NodeType.MESSAGE,
                name="Mais Informacoes",
                config=NodeConfig(
                    mensagem="Preciso de mais algumas informacoes para ajuda-lo melhor."
                ),
                next_node_id="ask_interest"
            ),
            FlowNode(
                id="handoff",
                type=NodeType.HANDOFF,
                name="Transferir",
                config=NodeConfig(
                    motivo="Cliente qualificado",
                    mensagem_cliente="Obrigado pelas informacoes, {nome}! Um de nossos atendentes entrara em contato em breve.",
                    notificar_equipe=True
                )
            )
        ],
        edges=[
            FlowEdge(id="e1", source="greeting", target="ask_name"),
            FlowEdge(id="e2", source="ask_name", target="ask_phone"),
            FlowEdge(id="e3", source="ask_phone", target="ask_interest"),
            FlowEdge(id="e4", source="ask_interest", target="qualify"),
            FlowEdge(id="e5", source="qualify", target="handoff", label="qualificado"),
            FlowEdge(id="e6", source="qualify", target="ask_more_info", label="nao qualificado"),
            FlowEdge(id="e7", source="ask_more_info", target="ask_interest")
        ],
        start_node_id="greeting",
        global_config=GlobalConfig(
            campos_obrigatorios=["nome", "telefone"],
            saudacao_padrao="Ola! Como posso ajudar?",
            comportamento_ia="amigavel"
        )
    )


def create_sales_flow() -> FlowConfig:
    """Create a complete sales flow with qualification"""
    return FlowConfig(
        name="Fluxo de Vendas",
        description="Fluxo completo para qualificacao e venda",
        nodes=[
            FlowNode(
                id="greeting",
                type=NodeType.GREETING,
                name="Saudacao",
                config=NodeConfig(
                    mensagem="Ola! Bem-vindo! Sou o assistente virtual. Como posso ajudar voce hoje?"
                ),
                next_node_id="ask_name"
            ),
            FlowNode(
                id="ask_name",
                type=NodeType.NOME,
                name="Nome",
                config=NodeConfig(
                    pergunta="Para comecar, qual e o seu nome?",
                    campo_destino="nome",
                    tipo_campo=FieldType.TEXT,
                    obrigatorio=True
                ),
                next_node_id="ask_email"
            ),
            FlowNode(
                id="ask_email",
                type=NodeType.EMAIL,
                name="Email",
                config=NodeConfig(
                    pergunta="Qual seu melhor email?",
                    campo_destino="email",
                    tipo_campo=FieldType.EMAIL,
                    obrigatorio=True,
                    mensagem_erro="Por favor, informe um email valido (exemplo@dominio.com)"
                ),
                next_node_id="ask_phone"
            ),
            FlowNode(
                id="ask_phone",
                type=NodeType.TELEFONE,
                name="Telefone",
                config=NodeConfig(
                    pergunta="E um telefone para contato?",
                    campo_destino="telefone",
                    tipo_campo=FieldType.PHONE,
                    obrigatorio=True
                ),
                next_node_id="ask_city"
            ),
            FlowNode(
                id="ask_city",
                type=NodeType.CIDADE,
                name="Cidade",
                config=NodeConfig(
                    pergunta="Em qual cidade voce esta?",
                    campo_destino="cidade",
                    tipo_campo=FieldType.TEXT
                ),
                next_node_id="ask_interest"
            ),
            FlowNode(
                id="ask_interest",
                type=NodeType.INTERESSE,
                name="Interesse",
                config=NodeConfig(
                    pergunta="O que voce esta procurando?",
                    campo_destino="interesse",
                    tipo_campo=FieldType.TEXT
                ),
                next_node_id="ask_budget"
            ),
            FlowNode(
                id="ask_budget",
                type=NodeType.ORCAMENTO,
                name="Orcamento",
                config=NodeConfig(
                    pergunta="Qual o orcamento disponivel?",
                    campo_destino="orcamento",
                    tipo_campo=FieldType.CURRENCY,
                    opcoes=["Ate R$ 1.000", "R$ 1.000 - R$ 5.000", "R$ 5.000 - R$ 10.000", "Acima de R$ 10.000"]
                ),
                next_node_id="ask_urgency"
            ),
            FlowNode(
                id="ask_urgency",
                type=NodeType.URGENCIA,
                name="Urgencia",
                config=NodeConfig(
                    pergunta="Qual a urgencia para resolver isso?",
                    campo_destino="urgencia",
                    tipo_campo=FieldType.SELECT,
                    opcoes=["Imediata", "Esta semana", "Este mes", "Apenas pesquisando"]
                ),
                next_node_id="qualify"
            ),
            FlowNode(
                id="qualify",
                type=NodeType.QUALIFICATION,
                name="Qualificacao",
                config=NodeConfig(
                    campos_avaliados=["nome", "email", "telefone", "interesse", "orcamento", "urgencia"],
                    score_minimo=70
                ),
                true_node_id="schedule",
                false_node_id="nurture"
            ),
            FlowNode(
                id="schedule",
                type=NodeType.AGENDAMENTO,
                name="Agendar Reuniao",
                config=NodeConfig(
                    mensagem="Otimo, {nome}! Vou agendar uma conversa com nosso especialista.",
                    tipo_agendamento="reuniao",
                    duracao_minutos=30
                ),
                next_node_id="notify_team"
            ),
            FlowNode(
                id="notify_team",
                type=NodeType.NOTIFICACAO,
                name="Notificar Equipe",
                config=NodeConfig(
                    canal_notificacao="email",
                    template_notificacao="Novo lead qualificado: {nome} - {interesse}",
                    nivel_urgencia=UrgencyLevel.ALTA
                ),
                next_node_id="handoff"
            ),
            FlowNode(
                id="nurture",
                type=NodeType.FOLLOWUP,
                name="Nutricao",
                config=NodeConfig(
                    mensagem="Entendi, {nome}. Vou enviar mais informacoes por email.",
                    intervalos=[1440, 4320, 10080],  # 1 dia, 3 dias, 7 dias
                    mensagens=[
                        "Ola {nome}, separei algumas informacoes que podem te interessar...",
                        "Oi {nome}, como esta? Conseguiu avaliar as informacoes?",
                        "{nome}, ainda posso ajudar com algo?"
                    ]
                ),
                next_node_id="end"
            ),
            FlowNode(
                id="handoff",
                type=NodeType.HANDOFF,
                name="Transferir",
                config=NodeConfig(
                    motivo="Lead qualificado para venda",
                    mensagem_cliente="Perfeito! Nosso especialista entrara em contato em breve. Obrigado!",
                    notificar_equipe=True,
                    prioridade="alta"
                )
            ),
            FlowNode(
                id="end",
                type=NodeType.END,
                name="Fim",
                config=NodeConfig(
                    mensagem="Obrigado pelo contato! Qualquer duvida, estamos a disposicao."
                )
            )
        ],
        edges=[
            FlowEdge(id="e1", source="greeting", target="ask_name"),
            FlowEdge(id="e2", source="ask_name", target="ask_email"),
            FlowEdge(id="e3", source="ask_email", target="ask_phone"),
            FlowEdge(id="e4", source="ask_phone", target="ask_city"),
            FlowEdge(id="e5", source="ask_city", target="ask_interest"),
            FlowEdge(id="e6", source="ask_interest", target="ask_budget"),
            FlowEdge(id="e7", source="ask_budget", target="ask_urgency"),
            FlowEdge(id="e8", source="ask_urgency", target="qualify"),
            FlowEdge(id="e9", source="qualify", target="schedule", label="qualificado"),
            FlowEdge(id="e10", source="qualify", target="nurture", label="nurture"),
            FlowEdge(id="e11", source="schedule", target="notify_team"),
            FlowEdge(id="e12", source="notify_team", target="handoff"),
            FlowEdge(id="e13", source="nurture", target="end")
        ],
        start_node_id="greeting",
        global_config=GlobalConfig(
            campos_obrigatorios=["nome", "telefone", "email"],
            comportamento_ia="vendedor",
            score_qualificacao={
                "nome": 10,
                "telefone": 15,
                "email": 15,
                "cidade": 5,
                "interesse": 20,
                "orcamento": 20,
                "urgencia": 15
            },
            score_minimo_qualificado=70
        )
    )
