"""
Document Extractor Service
Generic document data extraction using Vision API and LLM.

Supports:
- PDFs and images (invoices, contracts, proposals, forms)
- Confidence scoring per field
- Automatic document type classification
- Field validation
- Integration with lead data collection

This service works for any business segment.
"""
import logging
import json
import re
import base64
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import httpx

from openai import OpenAI
from ..core.config import settings
from .vision import vision, VisionService

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """Types of documents that can be extracted"""
    # Identification
    RG = "rg"
    CPF = "cpf"
    CNH = "cnh"

    # Address
    COMPROVANTE_RESIDENCIA = "comprovante_residencia"

    # Financial
    CONTA_LUZ = "conta_luz"
    CONTA_AGUA = "conta_agua"
    FATURA = "fatura"
    NOTA_FISCAL = "nota_fiscal"
    EXTRATO_BANCARIO = "extrato_bancario"

    # Business
    CONTRATO = "contrato"
    PROPOSTA = "proposta"
    ORCAMENTO = "orcamento"

    # Forms
    FORMULARIO = "formulario"
    FICHA_CADASTRAL = "ficha_cadastral"

    # Generic
    DOCUMENTO = "documento"
    DESCONHECIDO = "desconhecido"


@dataclass
class ExtractedField:
    """A single extracted field from a document"""
    field_name: str
    value: Any
    confidence: float  # 0.0 to 1.0
    source_text: Optional[str] = None  # Original text from document
    validated: bool = False
    validation_error: Optional[str] = None


@dataclass
class ExtractionResult:
    """Result of document extraction"""
    success: bool
    document_type: DocumentType
    document_type_confidence: float
    fields: Dict[str, ExtractedField] = field(default_factory=dict)
    raw_text: Optional[str] = None
    summary: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    extracted_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "document_type": self.document_type.value,
            "document_type_confidence": self.document_type_confidence,
            "fields": {
                name: {
                    "value": f.value,
                    "confidence": f.confidence,
                    "validated": f.validated,
                    "validation_error": f.validation_error
                }
                for name, f in self.fields.items()
            },
            "summary": self.summary,
            "errors": self.errors,
            "extracted_at": self.extracted_at.isoformat()
        }

    def get_validated_data(self) -> Dict[str, Any]:
        """Get only validated fields with their values"""
        return {
            name: f.value
            for name, f in self.fields.items()
            if f.validated or f.confidence >= 0.7
        }

    @property
    def average_confidence(self) -> float:
        """Average confidence across all fields"""
        if not self.fields:
            return 0.0
        return sum(f.confidence for f in self.fields.values()) / len(self.fields)


class DocumentExtractor:
    """
    Generic document data extractor using Vision API and LLM.

    Workflow:
    1. Receive document (URL or base64)
    2. Classify document type
    3. Extract fields based on document type
    4. Validate extracted fields
    5. Return structured data with confidence scores
    """

    # Generic extraction templates for different document types
    EXTRACTION_TEMPLATES = {
        DocumentType.CONTA_LUZ: {
            "prompt": """Extraia os dados desta conta de energia elétrica:
- nome_titular: Nome do titular
- endereco: Endereço completo
- cep: CEP
- consumo_kwh: Consumo em kWh
- valor_total: Valor total
- vencimento: Data de vencimento
- numero_instalacao: Número da instalação/UC
- distribuidora: Nome da distribuidora""",
            "fields": ["nome_titular", "endereco", "cep", "consumo_kwh", "valor_total", "vencimento", "numero_instalacao", "distribuidora"]
        },
        DocumentType.FATURA: {
            "prompt": """Extraia os dados desta fatura/boleto:
- nome: Nome do cliente
- valor: Valor total
- vencimento: Data de vencimento
- codigo_barras: Código de barras (se visível)
- empresa: Nome da empresa emissora
- descricao: Descrição do serviço/produto""",
            "fields": ["nome", "valor", "vencimento", "codigo_barras", "empresa", "descricao"]
        },
        DocumentType.ORCAMENTO: {
            "prompt": """Extraia os dados deste orçamento/cotação:
- empresa: Nome da empresa
- cliente: Nome do cliente
- itens: Lista de itens/serviços com valores
- valor_total: Valor total
- validade: Validade do orçamento
- condicoes: Condições de pagamento
- observacoes: Observações relevantes""",
            "fields": ["empresa", "cliente", "itens", "valor_total", "validade", "condicoes", "observacoes"]
        },
        DocumentType.PROPOSTA: {
            "prompt": """Extraia os dados desta proposta comercial:
- empresa: Nome da empresa que fez a proposta
- cliente: Nome do cliente
- descricao: Descrição do produto/serviço
- valores: Valores detalhados
- valor_total: Valor total
- condicoes_pagamento: Condições de pagamento
- prazo_entrega: Prazo de entrega
- validade: Validade da proposta
- garantia: Informações de garantia""",
            "fields": ["empresa", "cliente", "descricao", "valores", "valor_total", "condicoes_pagamento", "prazo_entrega", "validade", "garantia"]
        },
        DocumentType.CONTRATO: {
            "prompt": """Extraia os dados deste contrato:
- partes: Partes envolvidas (contratante e contratada)
- objeto: Objeto do contrato
- valor: Valor do contrato
- vigencia: Período de vigência
- data_assinatura: Data de assinatura
- clausulas_importantes: Cláusulas importantes resumidas""",
            "fields": ["partes", "objeto", "valor", "vigencia", "data_assinatura", "clausulas_importantes"]
        },
        DocumentType.NOTA_FISCAL: {
            "prompt": """Extraia os dados desta nota fiscal:
- numero_nf: Número da NF
- data_emissao: Data de emissão
- emitente: Nome/CNPJ do emitente
- destinatario: Nome/CNPJ do destinatário
- itens: Lista de itens com valores
- valor_total: Valor total
- icms: Valor ICMS
- iss: Valor ISS (se aplicável)""",
            "fields": ["numero_nf", "data_emissao", "emitente", "destinatario", "itens", "valor_total", "icms", "iss"]
        },
        DocumentType.RG: {
            "prompt": """Extraia os dados deste documento de identidade (RG):
- nome: Nome completo
- rg: Número do RG
- data_nascimento: Data de nascimento
- filiacao: Filiação (pai e mãe)
- naturalidade: Naturalidade
- orgao_emissor: Órgão emissor
- data_emissao: Data de emissão""",
            "fields": ["nome", "rg", "data_nascimento", "filiacao", "naturalidade", "orgao_emissor", "data_emissao"]
        },
        DocumentType.CNH: {
            "prompt": """Extraia os dados desta CNH:
- nome: Nome completo
- cpf: CPF
- data_nascimento: Data de nascimento
- numero_registro: Número do registro
- validade: Data de validade
- categoria: Categoria da habilitação""",
            "fields": ["nome", "cpf", "data_nascimento", "numero_registro", "validade", "categoria"]
        },
        DocumentType.COMPROVANTE_RESIDENCIA: {
            "prompt": """Extraia os dados deste comprovante de residência:
- nome: Nome do titular
- endereco: Endereço completo
- cep: CEP
- cidade: Cidade
- estado: Estado
- tipo_comprovante: Tipo (conta de luz, água, telefone, etc.)
- data_referencia: Data/mês de referência""",
            "fields": ["nome", "endereco", "cep", "cidade", "estado", "tipo_comprovante", "data_referencia"]
        },
        DocumentType.FORMULARIO: {
            "prompt": """Extraia TODOS os campos preenchidos deste formulário:
Para cada campo que encontrar, retorne:
- nome_campo: Nome/label do campo
- valor: Valor preenchido

Retorne todos os campos de forma estruturada.""",
            "fields": []  # Dynamic
        },
        DocumentType.DOCUMENTO: {
            "prompt": """Extraia TODAS as informações relevantes deste documento.
Identifique:
- tipo_documento: Tipo do documento
- principais_dados: Dados principais encontrados
- valores: Quaisquer valores monetários
- datas: Quaisquer datas importantes
- nomes: Nomes de pessoas ou empresas
- outros: Outras informações relevantes""",
            "fields": ["tipo_documento", "principais_dados", "valores", "datas", "nomes", "outros"]
        }
    }

    # Document type classification keywords
    TYPE_KEYWORDS = {
        DocumentType.CONTA_LUZ: ["kwh", "energia", "distribuidora", "instalação", "eletric", "cemig", "cpfl", "enel", "light", "coelba"],
        DocumentType.CONTA_AGUA: ["m³", "água", "saneamento", "copasa", "sabesp", "cedae"],
        DocumentType.FATURA: ["fatura", "boleto", "vencimento", "código de barras", "valor a pagar"],
        DocumentType.NOTA_FISCAL: ["nota fiscal", "nf-e", "nfe", "danfe", "cfop", "icms"],
        DocumentType.ORCAMENTO: ["orçamento", "cotação", "proposta", "validade"],
        DocumentType.PROPOSTA: ["proposta comercial", "proposta de", "condições comerciais"],
        DocumentType.CONTRATO: ["contrato", "cláusula", "contratante", "contratada", "vigência"],
        DocumentType.RG: ["identidade", "registro geral", "rg", "ssp"],
        DocumentType.CNH: ["habilitação", "cnh", "detran", "categoria"],
        DocumentType.COMPROVANTE_RESIDENCIA: ["comprovante", "residência", "endereço"],
        DocumentType.FORMULARIO: ["formulário", "preencha", "campo", "assinatura"],
    }

    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize the document extractor.

        Args:
            model: OpenAI model to use (needs vision capabilities)
        """
        self.model = model
        self._client: Optional[OpenAI] = None
        self.vision_service = vision

    @property
    def client(self) -> OpenAI:
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def extract(
        self,
        document_url: Optional[str] = None,
        document_base64: Optional[str] = None,
        document_type: Optional[DocumentType] = None,
        custom_fields: Optional[List[str]] = None,
        validate: bool = True
    ) -> ExtractionResult:
        """
        Extract data from a document.

        Args:
            document_url: URL of the document image
            document_base64: Base64 encoded document image
            document_type: Optional known document type (auto-detected if not provided)
            custom_fields: Optional list of specific fields to extract
            validate: Whether to validate extracted fields

        Returns:
            ExtractionResult with all extracted data
        """
        errors = []

        # Validate input
        if not document_url and not document_base64:
            return ExtractionResult(
                success=False,
                document_type=DocumentType.DESCONHECIDO,
                document_type_confidence=0.0,
                errors=["No document provided. Provide either URL or base64."]
            )

        # Prepare image URL for API
        if document_base64:
            # Detect image type from base64 header or default to jpeg
            image_url = f"data:image/jpeg;base64,{document_base64}"
        else:
            image_url = document_url

        try:
            # Step 1: Classify document type if not provided
            if not document_type:
                document_type, type_confidence = await self._classify_document(image_url)
                logger.info(f"Document classified as {document_type.value} (confidence: {type_confidence:.2f})")
            else:
                type_confidence = 1.0

            # Step 2: Extract fields based on document type
            fields = await self._extract_fields(image_url, document_type, custom_fields)

            # Step 3: Validate fields if requested
            if validate:
                fields = self._validate_fields(fields, document_type)

            # Step 4: Generate summary
            summary = self._generate_summary(document_type, fields)

            return ExtractionResult(
                success=True,
                document_type=document_type,
                document_type_confidence=type_confidence,
                fields=fields,
                summary=summary,
                errors=errors
            )

        except Exception as e:
            logger.exception(f"Document extraction error: {e}")
            return ExtractionResult(
                success=False,
                document_type=document_type or DocumentType.DESCONHECIDO,
                document_type_confidence=0.0,
                errors=[str(e)]
            )

    async def _classify_document(self, image_url: str) -> Tuple[DocumentType, float]:
        """Classify the document type using vision API"""
        try:
            prompt = """Classifique este documento em uma das seguintes categorias:
- conta_luz: Conta de energia elétrica
- conta_agua: Conta de água
- fatura: Fatura/boleto genérico
- nota_fiscal: Nota fiscal
- orcamento: Orçamento/cotação
- proposta: Proposta comercial
- contrato: Contrato
- rg: Documento de identidade RG
- cnh: Carteira de motorista CNH
- comprovante_residencia: Comprovante de residência
- formulario: Formulário preenchido
- documento: Outro documento

Retorne um JSON com:
- tipo: código da categoria (exatamente como listado acima)
- confianca: nível de confiança de 0 a 100
- motivo: breve explicação da classificação"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em classificação de documentos. Retorne apenas JSON válido."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}}
                        ]
                    }
                ],
                max_tokens=200,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            tipo = result.get("tipo", "documento").lower()
            confidence = result.get("confianca", 50) / 100.0

            # Map to enum
            type_map = {t.value: t for t in DocumentType}
            doc_type = type_map.get(tipo, DocumentType.DOCUMENTO)

            return doc_type, confidence

        except Exception as e:
            logger.warning(f"Document classification failed: {e}")
            return DocumentType.DOCUMENTO, 0.5

    async def _extract_fields(
        self,
        image_url: str,
        document_type: DocumentType,
        custom_fields: Optional[List[str]] = None
    ) -> Dict[str, ExtractedField]:
        """Extract fields from document based on type"""

        # Get template for document type
        template = self.EXTRACTION_TEMPLATES.get(
            document_type,
            self.EXTRACTION_TEMPLATES[DocumentType.DOCUMENTO]
        )

        # Build prompt
        if custom_fields:
            fields_prompt = "Extraia os seguintes campos:\n" + "\n".join(f"- {f}" for f in custom_fields)
        else:
            fields_prompt = template["prompt"]

        prompt = f"""{fields_prompt}

INSTRUÇÕES:
1. Extraia APENAS informações claramente visíveis no documento
2. Se um campo não for encontrado, não o inclua
3. Para cada campo, indique a confiança de 0 a 100
4. Use valores formatados corretamente (datas como DD/MM/AAAA, valores com R$)

Retorne um JSON com cada campo no formato:
{{"nome_campo": {{"valor": "...", "confianca": 85}}}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em OCR e extração de dados de documentos. Retorne apenas JSON válido."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}}
                        ]
                    }
                ],
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Convert to ExtractedField objects
            fields = {}
            for field_name, data in result.items():
                if isinstance(data, dict):
                    fields[field_name] = ExtractedField(
                        field_name=field_name,
                        value=data.get("valor"),
                        confidence=data.get("confianca", 70) / 100.0
                    )
                else:
                    # Simple value without confidence
                    fields[field_name] = ExtractedField(
                        field_name=field_name,
                        value=data,
                        confidence=0.7
                    )

            return fields

        except Exception as e:
            logger.exception(f"Field extraction error: {e}")
            return {}

    def _validate_fields(
        self,
        fields: Dict[str, ExtractedField],
        document_type: DocumentType
    ) -> Dict[str, ExtractedField]:
        """Validate extracted fields based on common patterns"""

        validation_rules = {
            "cpf": (r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$", "CPF inválido"),
            "cep": (r"^\d{5}-?\d{3}$", "CEP inválido"),
            "email": (r"^[\w\.-]+@[\w\.-]+\.\w+$", "Email inválido"),
            "telefone": (r"^[\d\s\(\)\-\+]{10,}$", "Telefone inválido"),
            "rg": (r"^[\d\.\-]+$", "RG inválido"),
            "data": (r"^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$", "Data inválida"),
        }

        for field_name, field in fields.items():
            # Check for known field patterns
            for pattern_name, (pattern, error_msg) in validation_rules.items():
                if pattern_name in field_name.lower():
                    if field.value and isinstance(field.value, str):
                        if re.match(pattern, field.value.strip()):
                            field.validated = True
                        else:
                            field.validation_error = error_msg
                            field.confidence *= 0.5  # Reduce confidence
                    break
            else:
                # No specific validation, accept if confidence is high enough
                if field.confidence >= 0.6:
                    field.validated = True

        return fields

    def _generate_summary(
        self,
        document_type: DocumentType,
        fields: Dict[str, ExtractedField]
    ) -> str:
        """Generate a brief summary of extracted data"""
        if not fields:
            return "Não foi possível extrair dados do documento."

        validated_count = sum(1 for f in fields.values() if f.validated)
        avg_confidence = sum(f.confidence for f in fields.values()) / len(fields)

        type_names = {
            DocumentType.CONTA_LUZ: "Conta de Luz",
            DocumentType.FATURA: "Fatura",
            DocumentType.ORCAMENTO: "Orçamento",
            DocumentType.PROPOSTA: "Proposta",
            DocumentType.CONTRATO: "Contrato",
            DocumentType.RG: "RG",
            DocumentType.CNH: "CNH",
            DocumentType.COMPROVANTE_RESIDENCIA: "Comprovante de Residência",
            DocumentType.DOCUMENTO: "Documento",
        }

        doc_name = type_names.get(document_type, "Documento")

        return f"{doc_name}: {validated_count} de {len(fields)} campos extraídos (confiança média: {avg_confidence:.0%})"

    async def extract_for_lead(
        self,
        document_url: str,
        target_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract document data and return in lead-friendly format.

        This is a convenience method that returns data ready to be
        merged into lead.dados_coletados.

        Args:
            document_url: URL of the document
            target_fields: Optional specific fields to extract

        Returns:
            Dict ready to merge with lead data
        """
        result = await self.extract(
            document_url=document_url,
            custom_fields=target_fields
        )

        if not result.success:
            return {
                "_document_extraction_failed": True,
                "_extraction_errors": result.errors
            }

        # Get validated data
        data = result.get_validated_data()

        # Add metadata
        data["_documento_tipo"] = result.document_type.value
        data["_documento_confianca"] = result.average_confidence
        data["_extraido_em"] = result.extracted_at.isoformat()

        return data


# Singleton instance
document_extractor = DocumentExtractor()


# Convenience function
async def extract_document(
    document_url: Optional[str] = None,
    document_base64: Optional[str] = None,
    document_type: Optional[str] = None
) -> ExtractionResult:
    """
    Convenience function to extract document data.

    Args:
        document_url: URL of document image
        document_base64: Base64 encoded image
        document_type: Optional known document type

    Returns:
        ExtractionResult
    """
    doc_type = None
    if document_type:
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            pass

    return await document_extractor.extract(
        document_url=document_url,
        document_base64=document_base64,
        document_type=doc_type
    )
