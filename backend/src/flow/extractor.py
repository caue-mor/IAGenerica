"""
DataExtractor - Generic data extraction from unstructured user messages

This module provides a generic, reusable data extractor that:
- Extracts structured data from natural language using regex patterns
- Handles common Brazilian data formats (CPF, CNPJ, phone, etc.)
- Detects skip/defer responses ("nao sei", "depois", etc.)
- Provides field aliases for flexible data access
- Validates extracted values

Usage:
    extractor = DataExtractor()

    # Extract specific field
    email = extractor.extract("email", "meu email eh joao@email.com")

    # Check if user wants to skip
    if extractor.is_skip_response("nao sei agora"):
        handle_skip()

    # Validate extracted value
    if extractor.validate("cpf", "123.456.789-00"):
        save_cpf()

    # Get field with aliases
    value, field_name = extractor.get_field_with_aliases("telefone", collected_data)
"""

import re
import logging
from typing import Optional, Any, Dict, List, Tuple, Pattern, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ExtractionConfidence(Enum):
    """Confidence level for extracted values"""
    HIGH = "high"       # Perfect match with validation
    MEDIUM = "medium"   # Pattern match but partial validation
    LOW = "low"         # Fuzzy match or heuristic


@dataclass
class ExtractionResult:
    """Result of a data extraction attempt"""
    success: bool
    value: Optional[Any] = None
    raw_value: Optional[str] = None
    confidence: ExtractionConfidence = ExtractionConfidence.LOW
    field_name: Optional[str] = None
    normalized: bool = False
    validation_errors: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.success and self.value is not None


class DataExtractor:
    """
    Generic data extractor for unstructured user messages.

    Extracts common data fields using regex patterns and provides
    validation, normalization, and skip detection functionality.

    Attributes:
        EXTRACTION_PATTERNS: Regex patterns for each field type
        SKIP_PATTERNS: Patterns to detect skip/defer responses
        FIELD_ALIASES: Mapping of field names to their aliases
        VALIDATION_PATTERNS: Patterns for value validation
    """

    # ==================== Extraction Patterns ====================
    # These patterns extract values from natural language messages

    EXTRACTION_PATTERNS: Dict[str, List[Pattern]] = {
        # Name extraction - captures names with 2-5 words
        "nome": [
            re.compile(r'(?:me\s+chamo|meu\s+nome\s+[e\xe9]|sou\s+o?a?\s*)\s*([A-Z\xc0-\xdca-z\xe0-\xfc]{2,}(?:\s+[A-Z\xc0-\xdca-z\xe0-\xfc]{2,}){0,4})', re.IGNORECASE),
            re.compile(r'(?:nome|name)[\s:]+([A-Z\xc0-\xdca-z\xe0-\xfc]{2,}(?:\s+[A-Z\xc0-\xdca-z\xe0-\xfc]{2,}){0,4})', re.IGNORECASE),
            re.compile(r'^([A-Z\xc0-\xdc][a-z\xe0-\xfc]+(?:\s+[A-Z\xc0-\xdca-z\xe0-\xfc]{2,}){1,4})$', re.MULTILINE),
        ],

        # Email extraction
        "email": [
            re.compile(r'[\w\.\-\+]+@[\w\.\-]+\.[a-zA-Z]{2,}', re.IGNORECASE),
            re.compile(r'(?:email|e-mail|mail)[\s:]+([^\s]+@[^\s]+)', re.IGNORECASE),
        ],

        # Phone/Celular extraction (Brazilian format)
        "telefone": [
            # Full format with country code: +55 11 99999-9999
            re.compile(r'\+?55\s*\(?\d{2}\)?\s*9?\d{4}[\s\-]?\d{4}'),
            # Format with area code: (11) 99999-9999 or 11 99999-9999
            re.compile(r'\(?\d{2}\)?\s*9?\d{4}[\s\-]?\d{4}'),
            # Only digits: 11999999999
            re.compile(r'\b\d{10,11}\b'),
            # With prefix: cel/tel/fone
            re.compile(r'(?:cel|tel|fone|whats?|zap)[\w]*[\s:\.]+\s*([\d\s\(\)\-\+]{8,20})', re.IGNORECASE),
        ],

        # Celular - alias for telefone with mobile-specific patterns
        "celular": [
            re.compile(r'\+?55\s*\(?\d{2}\)?\s*9\d{4}[\s\-]?\d{4}'),
            re.compile(r'\(?\d{2}\)?\s*9\d{4}[\s\-]?\d{4}'),
            re.compile(r'\b\d{2}9\d{8}\b'),
        ],

        # CPF extraction (Brazilian individual taxpayer ID)
        "cpf": [
            re.compile(r'\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[\-\s]?\d{2}'),
            re.compile(r'(?:cpf|documento)[\s:]+\s*(\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[\-\s]?\d{2})', re.IGNORECASE),
            re.compile(r'\b\d{11}\b'),  # Only digits
        ],

        # CNPJ extraction (Brazilian company taxpayer ID)
        "cnpj": [
            re.compile(r'\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\/\s]?\d{4}[\-\s]?\d{2}'),
            re.compile(r'(?:cnpj|empresa)[\s:]+\s*(\d{2}[\.\s]?\d{3}[\.\s]?\d{3}[\/\s]?\d{4}[\-\s]?\d{2})', re.IGNORECASE),
            re.compile(r'\b\d{14}\b'),  # Only digits
        ],

        # Generic number extraction
        "numero": [
            re.compile(r'(?:numero|num|n[\xba\xb0]?)[\s:]+\s*(\d+(?:[\.,]\d+)?)', re.IGNORECASE),
            re.compile(r'(\d+(?:[\.,]\d+)?)'),
        ],

        # Integer extraction
        "inteiro": [
            re.compile(r'\b(\d+)\b'),
        ],

        # Decimal/Currency extraction
        "decimal": [
            re.compile(r'R?\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+(?:,\d{2})?)', re.IGNORECASE),
            re.compile(r'(\d+[\.,]\d+)'),
        ],

        # Yes/No boolean extraction
        "sim_nao": [
            re.compile(r'\b(sim|s|yes|y|ok|claro|certo|isso|exato|positivo|afirmativo|com\s*certeza|pode\s*ser|quero|aceito|confirmo)\b', re.IGNORECASE),
            re.compile(r'\b(n[a\xe3]o|n|no|nao|nunca|negativo|nope|nem\s*pensar|de\s*jeito\s*nenhum|jamais)\b', re.IGNORECASE),
        ],

        # Date extraction (Brazilian format DD/MM/YYYY)
        # Note: These use non-capturing groups for delimiters to return full date match
        "data": [
            re.compile(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})'),
            re.compile(r'(?:data|dia)[\s:]+\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', re.IGNORECASE),
            # Natural date: "15 de janeiro de 2024"
            re.compile(r'(\d{1,2}\s*(?:de\s*)?(?:janeiro|fevereiro|mar[c\xe7]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s*(?:de\s*)?\d{2,4})', re.IGNORECASE),
        ],

        # Time extraction
        "hora": [
            re.compile(r'(\d{1,2}[\:h]\d{2})(?:\s*(?:am|pm|hrs?|horas?))?', re.IGNORECASE),
            re.compile(r'(?:[a\xe0]s?\s*)(\d{1,2}[\:h]\d{2})', re.IGNORECASE),
            re.compile(r'(\d{1,2})h(\d{2})?', re.IGNORECASE),  # 14h or 14h30
        ],

        # City extraction
        "cidade": [
            re.compile(r'(?:cidade|city|moro\s+em|sou\s+de|em)[\s:]+\s*([A-Z\xc0-\xdca-z\xe0-\xfc\s]{2,50})', re.IGNORECASE),
            re.compile(r'([A-Z\xc0-\xdc][a-z\xe0-\xfc]+(?:\s+(?:do|da|de|dos|das)\s+)?[A-Z\xc0-\xdc]?[a-z\xe0-\xfc]*)', re.IGNORECASE),
        ],

        # State extraction (Brazilian states)
        "estado": [
            re.compile(r'\b(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b', re.IGNORECASE),
            re.compile(r'(?:estado|uf)[\s:]+\s*([A-Za-z]{2})', re.IGNORECASE),
        ],

        # CEP (Brazilian postal code)
        "cep": [
            re.compile(r'\d{5}[\-\s]?\d{3}'),
            re.compile(r'(?:cep|codigo\s*postal)[\s:]+\s*(\d{5}[\-\s]?\d{3})', re.IGNORECASE),
            re.compile(r'\b\d{8}\b'),  # Only digits
        ],

        # Address extraction
        "endereco": [
            re.compile(r'(?:endereco|endere[c\xe7]o|rua|av(?:enida)?|alameda|travessa)[\s:,]+\s*(.+?)(?:,\s*n[\xba\xb0]?|\s*-\s*|\n|$)', re.IGNORECASE),
            re.compile(r'(?:rua|av(?:enida)?|alameda|travessa)\s+[A-Z\xc0-\xdca-z\xe0-\xfc\s\d,\-\.]+', re.IGNORECASE),
        ],

        # RG (Brazilian ID card)
        "rg": [
            re.compile(r'(?:rg|identidade)[\s:]+\s*([\d\.\-]+)', re.IGNORECASE),
            re.compile(r'\b(\d{1,2}[\.\s]?\d{3}[\.\s]?\d{3}[\-\s]?[\dxX])\b'),
        ],

        # URL extraction
        "url": [
            re.compile(r'https?://[^\s]+', re.IGNORECASE),
            re.compile(r'www\.[^\s]+', re.IGNORECASE),
        ],

        # Quantity extraction
        "quantidade": [
            re.compile(r'(\d+)\s*(?:unidades?|un|pcs?|pe[c\xe7]as?|itens?|items?)', re.IGNORECASE),
            re.compile(r'(?:quantidade|qtd|qty)[\s:]+\s*(\d+)', re.IGNORECASE),
        ],

        # Percentage extraction
        "porcentagem": [
            re.compile(r'(\d+(?:[\.,]\d+)?)\s*%'),
            re.compile(r'(?:porcentagem|percentual|percent)[\s:]+\s*(\d+(?:[\.,]\d+)?)', re.IGNORECASE),
        ],
    }

    # ==================== Skip/Defer Patterns ====================
    # Patterns to detect when user wants to skip or defer a question

    SKIP_PATTERNS: List[Pattern] = [
        # Don't know
        re.compile(r'\b(?:n[a\xe3]o\s+sei|nao\s+sei|sei\s+n[a\xe3]o|desconhe[c\xe7]o)\b', re.IGNORECASE),

        # Later/After
        re.compile(r'\b(?:depois|mais\s+tarde|outra\s+hora|agora\s+n[a\xe3]o|ainda\s+n[a\xe3]o)\b', re.IGNORECASE),

        # Skip/Pass
        re.compile(r'\b(?:pular|pula|skip|passar|passa|pr[o\xf3]ximo|pr[o\xf3]xima)\b', re.IGNORECASE),

        # Don't want to say
        re.compile(r'\b(?:prefiro\s+n[a\xe3]o|n[a\xe3]o\s+quero|n[a\xe3]o\s+vou)\b', re.IGNORECASE),

        # None/Nothing
        re.compile(r'\b(?:nenhum|nenhuma|nada|sem|n\/a|na|ningum)\b', re.IGNORECASE),

        # Don't have
        re.compile(r'\b(?:n[a\xe3]o\s+tenho|tenho\s+n[a\xe3]o|sem\s+isso)\b', re.IGNORECASE),

        # Whatever
        re.compile(r'\b(?:tanto\s+faz|qualquer|sei\s+l[a\xe1])\b', re.IGNORECASE),
    ]

    # ==================== Field Aliases ====================
    # Maps primary field names to all possible aliases

    FIELD_ALIASES: Dict[str, List[str]] = {
        "nome": ["name", "nome_completo", "nome_cliente", "cliente_nome", "full_name"],
        "email": ["e-mail", "mail", "email_cliente", "cliente_email", "email_contato"],
        "telefone": ["phone", "celular", "cel", "mobile", "fone", "whatsapp", "zap",
                     "telefone_cliente", "cliente_telefone", "numero_telefone"],
        "cpf": ["documento", "doc", "cpf_cliente", "cliente_cpf"],
        "cnpj": ["cnpj_empresa", "empresa_cnpj", "documento_empresa"],
        "cidade": ["city", "cidade_cliente", "cliente_cidade", "municipio"],
        "estado": ["state", "uf", "estado_cliente", "cliente_estado"],
        "endereco": ["address", "endereco_completo", "rua", "logradouro"],
        "cep": ["postal_code", "codigo_postal", "zip", "zipcode"],
        "data": ["date", "data_nascimento", "dt_nascimento", "birthday", "aniversario"],
        "hora": ["time", "horario", "hora_preferida", "horario_preferido"],
    }

    # ==================== Validation Patterns ====================
    # Stricter patterns for validating extracted values

    VALIDATION_PATTERNS: Dict[str, Pattern] = {
        "email": re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        "telefone": re.compile(r'^[\d\s\(\)\-\+]{8,20}$'),
        "celular": re.compile(r'^[\d\s\(\)\-\+]{10,20}$'),
        "cpf": re.compile(r'^\d{3}\.?\d{3}\.?\d{3}\-?\d{2}$'),
        "cnpj": re.compile(r'^\d{2}\.?\d{3}\.?\d{3}\/?\d{4}\-?\d{2}$'),
        "cep": re.compile(r'^\d{5}\-?\d{3}$'),
        "data": re.compile(r'^\d{2}[\/\-]\d{2}[\/\-]\d{4}$'),
        "hora": re.compile(r'^\d{1,2}[\:h]\d{2}$'),
        "url": re.compile(r'^https?:\/\/[^\s]+$'),
        "estado": re.compile(r'^(AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)$', re.IGNORECASE),
        "rg": re.compile(r'^[\d\.\-]{5,15}$'),
    }

    # ==================== Normalization Functions ====================

    MONTH_MAP: Dict[str, str] = {
        "janeiro": "01", "fevereiro": "02", "marco": "03", "mar\xe7o": "03",
        "abril": "04", "maio": "05", "junho": "06",
        "julho": "07", "agosto": "08", "setembro": "09",
        "outubro": "10", "novembro": "11", "dezembro": "12"
    }

    def __init__(
        self,
        custom_patterns: Optional[Dict[str, List[Pattern]]] = None,
        custom_skip_patterns: Optional[List[Pattern]] = None,
        custom_aliases: Optional[Dict[str, List[str]]] = None,
        custom_validators: Optional[Dict[str, Pattern]] = None
    ):
        """
        Initialize the DataExtractor with optional custom patterns.

        Args:
            custom_patterns: Additional extraction patterns to merge
            custom_skip_patterns: Additional skip patterns to add
            custom_aliases: Additional field aliases to merge
            custom_validators: Additional validation patterns to merge
        """
        # Merge custom patterns with defaults
        self.extraction_patterns = dict(self.EXTRACTION_PATTERNS)
        if custom_patterns:
            for field_key, patterns in custom_patterns.items():
                if field_key in self.extraction_patterns:
                    self.extraction_patterns[field_key].extend(patterns)
                else:
                    self.extraction_patterns[field_key] = patterns

        # Merge skip patterns
        self.skip_patterns = list(self.SKIP_PATTERNS)
        if custom_skip_patterns:
            self.skip_patterns.extend(custom_skip_patterns)

        # Merge aliases
        self.field_aliases = dict(self.FIELD_ALIASES)
        if custom_aliases:
            for field_key, aliases in custom_aliases.items():
                if field_key in self.field_aliases:
                    self.field_aliases[field_key].extend(aliases)
                else:
                    self.field_aliases[field_key] = aliases

        # Merge validators
        self.validation_patterns = dict(self.VALIDATION_PATTERNS)
        if custom_validators:
            self.validation_patterns.update(custom_validators)

        logger.debug(f"DataExtractor initialized with {len(self.extraction_patterns)} field types")

    # ==================== Main Extraction Methods ====================

    def extract(
        self,
        field_name: str,
        user_message: str,
        normalize: bool = True
    ) -> Optional[Any]:
        """
        Extract a specific field from user message.

        Args:
            field_name: Name of the field to extract (e.g., "email", "cpf")
            user_message: The raw user message to extract from
            normalize: Whether to normalize the extracted value

        Returns:
            Extracted value or None if not found
        """
        result = self.extract_with_details(field_name, user_message, normalize)
        return result.value if result.success else None

    def extract_with_details(
        self,
        field_name: str,
        user_message: str,
        normalize: bool = True
    ) -> ExtractionResult:
        """
        Extract a field with detailed result information.

        Args:
            field_name: Name of the field to extract
            user_message: The raw user message
            normalize: Whether to normalize the extracted value

        Returns:
            ExtractionResult with full details
        """
        if not user_message or not user_message.strip():
            return ExtractionResult(success=False, field_name=field_name)

        message = user_message.strip()
        field_lower = field_name.lower()

        # Get patterns for this field
        patterns = self.extraction_patterns.get(field_lower, [])

        # Also check aliases
        for primary, aliases in self.field_aliases.items():
            if field_lower in aliases:
                patterns = self.extraction_patterns.get(primary, [])
                field_lower = primary
                break

        if not patterns:
            logger.warning(f"No extraction patterns for field: {field_name}")
            return ExtractionResult(
                success=False,
                field_name=field_name,
                validation_errors=[f"Unknown field type: {field_name}"]
            )

        # Try each pattern
        for pattern in patterns:
            match = pattern.search(message)
            if match:
                # Get the captured group or full match
                raw_value = match.group(1) if match.groups() else match.group(0)
                raw_value = raw_value.strip()

                # Normalize if requested
                if normalize:
                    normalized_value = self._normalize_value(field_lower, raw_value)
                else:
                    normalized_value = raw_value

                # Validate
                is_valid = self.validate(field_lower, normalized_value)
                confidence = ExtractionConfidence.HIGH if is_valid else ExtractionConfidence.MEDIUM

                logger.debug(
                    f"Extracted {field_name}: '{normalized_value}' "
                    f"(raw: '{raw_value}', confidence: {confidence.value})"
                )

                return ExtractionResult(
                    success=True,
                    value=normalized_value,
                    raw_value=raw_value,
                    confidence=confidence,
                    field_name=field_lower,
                    normalized=normalize
                )

        # No match found
        return ExtractionResult(success=False, field_name=field_name)

    def extract_all(
        self,
        user_message: str,
        fields: Optional[List[str]] = None,
        normalize: bool = True
    ) -> Dict[str, ExtractionResult]:
        """
        Extract multiple fields from a message.

        Args:
            user_message: The raw user message
            fields: List of fields to extract (None = all available)
            normalize: Whether to normalize values

        Returns:
            Dictionary of field names to ExtractionResults
        """
        fields_to_extract = fields or list(self.extraction_patterns.keys())
        results = {}

        for field_key in fields_to_extract:
            result = self.extract_with_details(field_key, user_message, normalize)
            if result.success:
                results[field_key] = result

        return results

    def extract_boolean(self, user_message: str) -> Optional[bool]:
        """
        Extract a boolean (yes/no) response from user message.

        Args:
            user_message: The raw user message

        Returns:
            True for affirmative, False for negative, None if unclear
        """
        if not user_message:
            return None

        message = user_message.strip().lower()

        # Check for NEGATIVE patterns FIRST (more specific, avoids "nao quero" matching "quero")
        negative_patterns = [
            r'\b(n[a\xe3]o|nao)\s+(quero|posso|vou|sei|tenho|preciso|desejo|aceito)\b',
            r'\b(n[a\xe3]o|nao)\b',
            r'^\s*(n|no)\s*$',  # Just "n" or "no" alone
            r'\b(nunca|negativo|nope|jamais)\b',
            r'\b(nem\s*pensar|de\s*jeito\s*nenhum)\b',
            r'\b(falso|errado|incorreto|discordo)\b',
        ]

        for pattern in negative_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return False

        # Check for affirmative patterns
        affirmative_patterns = [
            r'\b(sim|yes|ok|claro|certo|isso|exato|positivo|afirmativo)\b',
            r'^\s*(s|y)\s*$',  # Just "s" or "y" alone
            r'\b(com\s*certeza|pode\s*ser|quero|aceito|confirmo|concordo)\b',
            r'\b(verdade|verdadeiro|correto|perfeito)\b',
        ]

        for pattern in affirmative_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True

        return None

    # ==================== Skip Detection ====================

    def is_skip_response(self, user_message: str) -> bool:
        """
        Check if user message indicates they want to skip/defer.

        Args:
            user_message: The raw user message

        Returns:
            True if user wants to skip, False otherwise
        """
        if not user_message:
            return False

        message = user_message.strip()

        for pattern in self.skip_patterns:
            if pattern.search(message):
                logger.debug(f"Skip response detected: '{message}'")
                return True

        return False

    def get_skip_type(self, user_message: str) -> Optional[str]:
        """
        Get the type of skip response.

        Args:
            user_message: The raw user message

        Returns:
            Type of skip: "dont_know", "later", "skip", "refuse", "none", "dont_have"
        """
        if not user_message:
            return None

        message = user_message.strip().lower()

        skip_types = {
            "dont_know": [r'n[a\xe3]o\s+sei', r'sei\s+n[a\xe3]o', r'desconhe[c\xe7]o'],
            "later": [r'depois', r'mais\s+tarde', r'outra\s+hora', r'agora\s+n[a\xe3]o'],
            "skip": [r'pular', r'skip', r'passar', r'pr[o\xf3]ximo'],
            "refuse": [r'prefiro\s+n[a\xe3]o', r'n[a\xe3]o\s+quero', r'n[a\xe3]o\s+vou'],
            "none": [r'nenhum', r'nada', r'n\/a'],
            "dont_have": [r'n[a\xe3]o\s+tenho', r'tenho\s+n[a\xe3]o', r'sem\s+isso'],
        }

        for skip_type, patterns in skip_types.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    return skip_type

        return None

    # ==================== Validation ====================

    def validate(self, field_name: str, value: Any) -> bool:
        """
        Validate an extracted or provided value.

        Args:
            field_name: Name of the field
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        if value is None:
            return False

        str_value = str(value).strip()
        if not str_value:
            return False

        field_lower = field_name.lower()

        # Get validation pattern
        pattern = self.validation_patterns.get(field_lower)

        # Also check aliases
        if not pattern:
            for primary, aliases in self.field_aliases.items():
                if field_lower in aliases:
                    pattern = self.validation_patterns.get(primary)
                    field_lower = primary
                    break

        # If no specific pattern, perform basic validation
        if not pattern:
            return len(str_value) > 0

        # Match against pattern
        is_valid = bool(pattern.match(str_value))

        # Additional validation for specific types
        if is_valid:
            if field_lower == "cpf":
                is_valid = self._validate_cpf(str_value)
            elif field_lower == "cnpj":
                is_valid = self._validate_cnpj(str_value)
            elif field_lower == "email":
                is_valid = self._validate_email(str_value)

        return is_valid

    def _validate_cpf(self, cpf: str) -> bool:
        """Validate CPF using checksum algorithm"""
        # Remove non-digits
        digits = re.sub(r'\D', '', cpf)

        if len(digits) != 11:
            return False

        # Check for known invalid CPFs
        if digits == digits[0] * 11:
            return False

        # Validate checksum
        def calc_digit(digits_slice: str, weights: List[int]) -> int:
            total = sum(int(d) * w for d, w in zip(digits_slice, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder

        # First check digit
        weights1 = [10, 9, 8, 7, 6, 5, 4, 3, 2]
        if calc_digit(digits[:9], weights1) != int(digits[9]):
            return False

        # Second check digit
        weights2 = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        if calc_digit(digits[:10], weights2) != int(digits[10]):
            return False

        return True

    def _validate_cnpj(self, cnpj: str) -> bool:
        """Validate CNPJ using checksum algorithm"""
        # Remove non-digits
        digits = re.sub(r'\D', '', cnpj)

        if len(digits) != 14:
            return False

        # Check for known invalid CNPJs
        if digits == digits[0] * 14:
            return False

        # Validate checksum
        def calc_digit(digits_slice: str, weights: List[int]) -> int:
            total = sum(int(d) * w for d, w in zip(digits_slice, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder

        # First check digit
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        if calc_digit(digits[:12], weights1) != int(digits[12]):
            return False

        # Second check digit
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        if calc_digit(digits[:13], weights2) != int(digits[13]):
            return False

        return True

    def _validate_email(self, email: str) -> bool:
        """Additional email validation"""
        # Basic pattern check
        if not self.validation_patterns["email"].match(email):
            return False

        # Check for common typos
        invalid_domains = ["gmial.com", "gmal.com", "hotmal.com", "yahooo.com"]
        domain = email.split("@")[1].lower() if "@" in email else ""

        if domain in invalid_domains:
            logger.warning(f"Possible typo in email domain: {domain}")
            # Still return True but log warning

        return True

    # ==================== Field Aliases ====================

    def get_field_with_aliases(
        self,
        field_name: str,
        collected_data: Dict[str, Any]
    ) -> Tuple[Optional[Any], str]:
        """
        Get a field value checking all possible aliases.

        Args:
            field_name: Primary field name to look for
            collected_data: Dictionary of collected data

        Returns:
            Tuple of (value, actual_field_name) or (None, field_name) if not found
        """
        field_lower = field_name.lower()

        # Check primary field name first
        if field_lower in collected_data:
            return collected_data[field_lower], field_lower

        # Get all aliases for this field
        aliases = self.field_aliases.get(field_lower, [])

        # Also check if field_name is itself an alias
        for primary, alias_list in self.field_aliases.items():
            if field_lower in alias_list:
                # Check primary name
                if primary in collected_data:
                    return collected_data[primary], primary
                # Add other aliases
                aliases.extend([a for a in alias_list if a != field_lower])

        # Check all aliases
        for alias in aliases:
            if alias in collected_data:
                return collected_data[alias], alias
            # Also check case variations
            for key in collected_data.keys():
                if key.lower() == alias.lower():
                    return collected_data[key], key

        return None, field_name

    def resolve_field_name(self, field_name: str) -> str:
        """
        Resolve a field alias to its primary field name.

        Args:
            field_name: Field name or alias

        Returns:
            Primary field name
        """
        field_lower = field_name.lower()

        # Check if it's a primary field
        if field_lower in self.field_aliases:
            return field_lower

        # Check if it's an alias
        for primary, aliases in self.field_aliases.items():
            if field_lower in [a.lower() for a in aliases]:
                return primary

        return field_lower

    # ==================== Normalization ====================

    def _normalize_value(self, field_name: str, value: str) -> Any:
        """
        Normalize an extracted value based on field type.

        Args:
            field_name: Name of the field
            value: Raw extracted value

        Returns:
            Normalized value
        """
        if not value:
            return value

        normalizers = {
            "telefone": self._normalize_phone,
            "celular": self._normalize_phone,
            "cpf": self._normalize_cpf,
            "cnpj": self._normalize_cnpj,
            "email": self._normalize_email,
            "cep": self._normalize_cep,
            "nome": self._normalize_name,
            "data": self._normalize_date,
            "hora": self._normalize_time,
            "decimal": self._normalize_decimal,
        }

        normalizer = normalizers.get(field_name.lower())
        if normalizer:
            return normalizer(value)

        return value.strip()

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to standard format"""
        # Remove non-digits
        digits = re.sub(r'\D', '', phone)

        # Handle Brazilian mobile format
        if len(digits) == 11:  # Brazilian mobile with area code
            return f"+55{digits}"
        elif len(digits) == 10:  # Brazilian landline with area code
            return f"+55{digits}"
        elif len(digits) == 13 and digits.startswith('55'):
            return f"+{digits}"
        elif len(digits) == 9 and digits.startswith('9'):  # Mobile without area code
            return digits  # Return as-is, needs area code

        return phone

    def _normalize_cpf(self, cpf: str) -> str:
        """Normalize CPF to formatted string"""
        digits = re.sub(r'\D', '', cpf)
        if len(digits) == 11:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        return cpf

    def _normalize_cnpj(self, cnpj: str) -> str:
        """Normalize CNPJ to formatted string"""
        digits = re.sub(r'\D', '', cnpj)
        if len(digits) == 14:
            return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        return cnpj

    def _normalize_email(self, email: str) -> str:
        """Normalize email to lowercase"""
        return email.lower().strip()

    def _normalize_cep(self, cep: str) -> str:
        """Normalize CEP to formatted string"""
        digits = re.sub(r'\D', '', cep)
        if len(digits) == 8:
            return f"{digits[:5]}-{digits[5:]}"
        return cep

    def _normalize_name(self, name: str) -> str:
        """Normalize name to title case"""
        # List of words to keep lowercase
        lowercase_words = {'de', 'da', 'do', 'das', 'dos', 'e'}

        words = name.strip().split()
        normalized_words = []

        for i, word in enumerate(words):
            if i > 0 and word.lower() in lowercase_words:
                normalized_words.append(word.lower())
            else:
                normalized_words.append(word.capitalize())

        return ' '.join(normalized_words)

    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to DD/MM/YYYY format"""
        # Try to parse natural date
        for month_name, month_num in self.MONTH_MAP.items():
            if month_name in date_str.lower():
                match = re.search(r'(\d{1,2})\s*(?:de\s*)?' + month_name + r'\s*(?:de\s*)?(\d{2,4})', date_str, re.IGNORECASE)
                if match:
                    day = match.group(1).zfill(2)
                    year = match.group(2)
                    if len(year) == 2:
                        year = '20' + year if int(year) < 50 else '19' + year
                    return f"{day}/{month_num}/{year}"

        # Try to parse numeric date
        match = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', date_str)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).zfill(2)
            year = match.group(3)
            if len(year) == 2:
                year = '20' + year if int(year) < 50 else '19' + year
            return f"{day}/{month}/{year}"

        return date_str

    def _normalize_time(self, time_str: str) -> str:
        """Normalize time to HH:MM format"""
        # Handle formats like "14h30" or "14:30" or "14h"
        match = re.search(r'(\d{1,2})[\:h](\d{2})?', time_str)
        if match:
            hour = match.group(1).zfill(2)
            minute = match.group(2) if match.group(2) else '00'
            return f"{hour}:{minute}"
        return time_str

    def _normalize_decimal(self, value: str) -> float:
        """Normalize decimal/currency to float"""
        # Remove currency symbol and spaces
        cleaned = re.sub(r'[R\$\s]', '', value)
        # Handle Brazilian format (1.234,56 -> 1234.56)
        if ',' in cleaned:
            cleaned = cleaned.replace('.', '').replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    # ==================== Utility Methods ====================

    def get_supported_fields(self) -> List[str]:
        """Get list of all supported field types"""
        return list(self.extraction_patterns.keys())

    def get_field_aliases_list(self, field_name: str) -> List[str]:
        """Get all aliases for a field"""
        return self.field_aliases.get(field_name.lower(), [])

    def add_pattern(self, field_name: str, pattern: Union[str, Pattern]) -> None:
        """Add a new extraction pattern for a field"""
        if isinstance(pattern, str):
            pattern = re.compile(pattern, re.IGNORECASE)

        field_lower = field_name.lower()
        if field_lower not in self.extraction_patterns:
            self.extraction_patterns[field_lower] = []

        self.extraction_patterns[field_lower].append(pattern)
        logger.debug(f"Added pattern for field: {field_name}")

    def add_skip_pattern(self, pattern: Union[str, Pattern]) -> None:
        """Add a new skip detection pattern"""
        if isinstance(pattern, str):
            pattern = re.compile(pattern, re.IGNORECASE)

        self.skip_patterns.append(pattern)
        logger.debug("Added skip pattern")

    def add_alias(self, primary_field: str, alias: str) -> None:
        """Add an alias for a field"""
        primary_lower = primary_field.lower()
        if primary_lower not in self.field_aliases:
            self.field_aliases[primary_lower] = []

        self.field_aliases[primary_lower].append(alias.lower())
        logger.debug(f"Added alias '{alias}' for field: {primary_field}")


# ==================== Factory Functions ====================

def create_extractor(
    custom_patterns: Optional[Dict[str, List[Pattern]]] = None,
    custom_skip_patterns: Optional[List[Pattern]] = None,
    custom_aliases: Optional[Dict[str, List[str]]] = None,
    custom_validators: Optional[Dict[str, Pattern]] = None
) -> DataExtractor:
    """
    Factory function to create a DataExtractor instance.

    Args:
        custom_patterns: Additional extraction patterns
        custom_skip_patterns: Additional skip patterns
        custom_aliases: Additional field aliases
        custom_validators: Additional validation patterns

    Returns:
        Configured DataExtractor instance
    """
    return DataExtractor(
        custom_patterns=custom_patterns,
        custom_skip_patterns=custom_skip_patterns,
        custom_aliases=custom_aliases,
        custom_validators=custom_validators
    )


# Default extractor instance
extractor = DataExtractor()


# ==================== Convenience Functions ====================

def extract_field(field_name: str, message: str) -> Optional[Any]:
    """Extract a field using the default extractor"""
    return extractor.extract(field_name, message)


def is_skip(message: str) -> bool:
    """Check if message is a skip response using default extractor"""
    return extractor.is_skip_response(message)


def validate_field(field_name: str, value: Any) -> bool:
    """Validate a field value using default extractor"""
    return extractor.validate(field_name, value)
