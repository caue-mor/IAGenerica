"""
Data Validators - Centralized validation for all collected data.

Validates and cleans data before saving to ensure data quality.
Supports: email, telefone, cpf, cnpj, cep, date, url, and custom validation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional, Callable, Dict, List
from enum import Enum


class ValidationErrorCode(str, Enum):
    """Error codes for validation failures."""
    INVALID_FORMAT = "invalid_format"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    INVALID_CHECKSUM = "invalid_checksum"
    REQUIRED = "required"
    INVALID_VALUE = "invalid_value"
    CUSTOM = "custom"


@dataclass
class ValidationResult:
    """Result of a validation attempt."""
    is_valid: bool
    cleaned_value: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[ValidationErrorCode] = None
    original_value: Optional[str] = None
    suggestions: Optional[List[str]] = None  # Suggested corrections


@dataclass
class FieldValidationConfig:
    """Configuration for field validation."""
    pattern: Optional[str] = None          # Regex pattern
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    cleaner: Optional[Callable[[str], str]] = None  # Function to clean value
    validator: Optional[str] = None        # Name of custom validator method
    error_message: str = "Valor inválido"
    normalize: Optional[Callable[[str], str]] = None  # Function to normalize value


class DataValidator:
    """
    Centralized data validator for all field types.

    Validates and cleans input data before saving.
    """

    # Field type configurations
    FIELD_CONFIGS: Dict[str, FieldValidationConfig] = {
        "email": FieldValidationConfig(
            pattern=r'^[\w\.\+\-]+@[\w\.-]+\.[a-zA-Z]{2,}$',
            min_length=5,
            max_length=254,
            cleaner=lambda x: x.strip().lower(),
            error_message="Email inválido. Exemplo: nome@email.com"
        ),
        "telefone": FieldValidationConfig(
            pattern=r'^\d{10,11}$',
            min_length=10,
            max_length=11,
            cleaner=lambda x: DataValidator._clean_phone(x),
            error_message="Telefone inválido. Informe DDD + número (ex: 11999998888)"
        ),
        "celular": FieldValidationConfig(
            pattern=r'^\d{11}$',
            min_length=11,
            max_length=11,
            cleaner=lambda x: DataValidator._clean_phone(x),
            error_message="Celular inválido. Informe DDD + 9 dígitos (ex: 11999998888)"
        ),
        "cpf": FieldValidationConfig(
            pattern=r'^\d{11}$',
            cleaner=lambda x: re.sub(r'\D', '', x),
            validator="_validate_cpf_checksum",
            error_message="CPF inválido. Verifique os dígitos informados."
        ),
        "cnpj": FieldValidationConfig(
            pattern=r'^\d{14}$',
            cleaner=lambda x: re.sub(r'\D', '', x),
            validator="_validate_cnpj_checksum",
            error_message="CNPJ inválido. Verifique os dígitos informados."
        ),
        "cep": FieldValidationConfig(
            pattern=r'^\d{8}$',
            cleaner=lambda x: re.sub(r'\D', '', x),
            error_message="CEP inválido. Informe 8 dígitos (ex: 01310100)"
        ),
        "date": FieldValidationConfig(
            pattern=r'^\d{2}/\d{2}/\d{4}$',
            validator="_validate_date",
            normalize=lambda x: DataValidator._normalize_date(x),
            error_message="Data inválida. Use o formato DD/MM/AAAA"
        ),
        "data_nascimento": FieldValidationConfig(
            pattern=r'^\d{2}/\d{2}/\d{4}$',
            validator="_validate_birth_date",
            normalize=lambda x: DataValidator._normalize_date(x),
            error_message="Data de nascimento inválida. Use o formato DD/MM/AAAA"
        ),
        "url": FieldValidationConfig(
            pattern=r'^https?://[\w\.-]+\.[a-zA-Z]{2,}.*$',
            cleaner=lambda x: x.strip(),
            error_message="URL inválida. Deve começar com http:// ou https://"
        ),
        "nome": FieldValidationConfig(
            min_length=2,
            max_length=100,
            cleaner=lambda x: ' '.join(x.strip().split()),  # Remove extra spaces
            normalize=lambda x: x.title(),  # Capitalize words
            error_message="Nome inválido. Informe pelo menos 2 caracteres."
        ),
        "cidade": FieldValidationConfig(
            min_length=2,
            max_length=100,
            cleaner=lambda x: ' '.join(x.strip().split()),
            normalize=lambda x: x.title(),
            error_message="Cidade inválida. Informe o nome da cidade."
        ),
        "endereco": FieldValidationConfig(
            min_length=5,
            max_length=200,
            cleaner=lambda x: ' '.join(x.strip().split()),
            error_message="Endereço inválido. Informe o endereço completo."
        ),
        "orcamento": FieldValidationConfig(
            cleaner=lambda x: DataValidator._clean_currency(x),
            validator="_validate_currency",
            error_message="Orçamento inválido. Informe um valor em reais."
        ),
        "urgencia": FieldValidationConfig(
            validator="_validate_urgency",
            error_message="Urgência inválida. Opções: imediata, esta semana, este mês, sem pressa"
        ),
        "interesse": FieldValidationConfig(
            min_length=3,
            max_length=500,
            cleaner=lambda x: x.strip(),
            error_message="Interesse inválido. Descreva o que você está buscando."
        ),
    }

    # Urgency level mappings
    URGENCY_MAPPINGS = {
        "imediata": ["imediato", "imediata", "urgente", "agora", "hoje", "já", "ja"],
        "esta_semana": ["semana", "essa semana", "esta semana", "proximos dias", "próximos dias"],
        "este_mes": ["mes", "mês", "esse mes", "este mês", "30 dias"],
        "sem_pressa": ["sem pressa", "sem urgencia", "pesquisando", "apenas pesquisando", "não tenho pressa", "tranquilo"]
    }

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate(self, field_type: str, value: Any, required: bool = True) -> ValidationResult:
        """
        Validate and clean a field value.

        Args:
            field_type: Type of field (email, telefone, cpf, etc.)
            value: Value to validate
            required: Whether the field is required

        Returns:
            ValidationResult with validation status and cleaned value
        """
        # Handle None/empty
        if value is None or (isinstance(value, str) and not value.strip()):
            if required:
                return ValidationResult(
                    is_valid=False,
                    error_message="Este campo é obrigatório",
                    error_code=ValidationErrorCode.REQUIRED,
                    original_value=str(value) if value else None
                )
            return ValidationResult(is_valid=True, cleaned_value=None)

        # Convert to string
        str_value = str(value).strip()
        original_value = str_value

        # Get config for field type
        config = self.FIELD_CONFIGS.get(field_type.lower())

        if not config:
            # Unknown field type - just clean and return
            return ValidationResult(
                is_valid=True,
                cleaned_value=str_value,
                original_value=original_value
            )

        # Apply cleaner
        if config.cleaner:
            try:
                str_value = config.cleaner(str_value)
            except Exception:
                pass

        # Check min length
        if config.min_length and len(str_value) < config.min_length:
            return ValidationResult(
                is_valid=False,
                error_message=config.error_message,
                error_code=ValidationErrorCode.TOO_SHORT,
                original_value=original_value
            )

        # Check max length
        if config.max_length and len(str_value) > config.max_length:
            return ValidationResult(
                is_valid=False,
                error_message=config.error_message,
                error_code=ValidationErrorCode.TOO_LONG,
                original_value=original_value
            )

        # Check pattern
        if config.pattern:
            if not re.match(config.pattern, str_value):
                return ValidationResult(
                    is_valid=False,
                    error_message=config.error_message,
                    error_code=ValidationErrorCode.INVALID_FORMAT,
                    original_value=original_value
                )

        # Run custom validator
        if config.validator and hasattr(self, config.validator):
            validator_func = getattr(self, config.validator)
            is_valid, error_msg = validator_func(str_value)
            if not is_valid:
                return ValidationResult(
                    is_valid=False,
                    error_message=error_msg or config.error_message,
                    error_code=ValidationErrorCode.INVALID_CHECKSUM,
                    original_value=original_value
                )

        # Apply normalizer
        if config.normalize:
            try:
                str_value = config.normalize(str_value)
            except Exception:
                pass

        return ValidationResult(
            is_valid=True,
            cleaned_value=str_value,
            original_value=original_value
        )

    def validate_multiple(self, data: Dict[str, Any], field_types: Dict[str, str] = None) -> Dict[str, ValidationResult]:
        """
        Validate multiple fields at once.

        Args:
            data: Dictionary of field_name -> value
            field_types: Optional mapping of field_name -> field_type
                         If not provided, field_name is used as field_type

        Returns:
            Dictionary of field_name -> ValidationResult
        """
        results = {}
        for field_name, value in data.items():
            field_type = field_types.get(field_name, field_name) if field_types else field_name
            results[field_name] = self.validate(field_type, value, required=False)
        return results

    def get_all_errors(self, results: Dict[str, ValidationResult]) -> Dict[str, str]:
        """Get all validation errors from results."""
        return {
            field: result.error_message
            for field, result in results.items()
            if not result.is_valid and result.error_message
        }

    def get_cleaned_data(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get cleaned data from validation results."""
        return {
            field: result.cleaned_value
            for field, result in results.items()
            if result.is_valid and result.cleaned_value is not None
        }

    # ==================== Custom Validators ====================

    def _validate_cpf_checksum(self, cpf: str) -> tuple[bool, Optional[str]]:
        """Validate CPF checksum (Brazilian ID number)."""
        if len(cpf) != 11:
            return False, "CPF deve ter 11 dígitos"

        # Check for known invalid CPFs
        if cpf == cpf[0] * 11:
            return False, "CPF inválido"

        # Calculate first check digit
        total = sum(int(cpf[i]) * (10 - i) for i in range(9))
        remainder = total % 11
        digit1 = 0 if remainder < 2 else 11 - remainder

        if int(cpf[9]) != digit1:
            return False, "CPF inválido - dígito verificador incorreto"

        # Calculate second check digit
        total = sum(int(cpf[i]) * (11 - i) for i in range(10))
        remainder = total % 11
        digit2 = 0 if remainder < 2 else 11 - remainder

        if int(cpf[10]) != digit2:
            return False, "CPF inválido - dígito verificador incorreto"

        return True, None

    def _validate_cnpj_checksum(self, cnpj: str) -> tuple[bool, Optional[str]]:
        """Validate CNPJ checksum (Brazilian company ID)."""
        if len(cnpj) != 14:
            return False, "CNPJ deve ter 14 dígitos"

        # Check for known invalid CNPJs
        if cnpj == cnpj[0] * 14:
            return False, "CNPJ inválido"

        # Calculate first check digit
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(int(cnpj[i]) * weights1[i] for i in range(12))
        remainder = total % 11
        digit1 = 0 if remainder < 2 else 11 - remainder

        if int(cnpj[12]) != digit1:
            return False, "CNPJ inválido - dígito verificador incorreto"

        # Calculate second check digit
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        total = sum(int(cnpj[i]) * weights2[i] for i in range(13))
        remainder = total % 11
        digit2 = 0 if remainder < 2 else 11 - remainder

        if int(cnpj[13]) != digit2:
            return False, "CNPJ inválido - dígito verificador incorreto"

        return True, None

    def _validate_date(self, date_str: str) -> tuple[bool, Optional[str]]:
        """Validate date format and value."""
        from datetime import datetime

        # Try to parse the date
        try:
            date = datetime.strptime(date_str, "%d/%m/%Y")
            # Check reasonable range
            if date.year < 1900 or date.year > 2100:
                return False, "Ano inválido"
            return True, None
        except ValueError:
            return False, "Data inválida"

    def _validate_birth_date(self, date_str: str) -> tuple[bool, Optional[str]]:
        """Validate birth date (must be in the past and reasonable)."""
        from datetime import datetime

        try:
            date = datetime.strptime(date_str, "%d/%m/%Y")
            today = datetime.now()

            # Must be in the past
            if date >= today:
                return False, "Data de nascimento deve ser no passado"

            # Must be reasonable (not more than 150 years ago)
            age = (today - date).days / 365
            if age > 150:
                return False, "Data de nascimento inválida"
            if age < 0:
                return False, "Data de nascimento deve ser no passado"

            return True, None
        except ValueError:
            return False, "Data de nascimento inválida"

    def _validate_currency(self, value: str) -> tuple[bool, Optional[str]]:
        """Validate currency value."""
        try:
            # Remove currency symbols and separators
            cleaned = re.sub(r'[R$\s.,]', '', value)
            if not cleaned:
                return False, "Valor inválido"

            # Try to parse as number
            amount = float(cleaned)
            if amount < 0:
                return False, "Valor deve ser positivo"

            return True, None
        except ValueError:
            return False, "Valor inválido"

    def _validate_urgency(self, value: str) -> tuple[bool, Optional[str]]:
        """Validate and normalize urgency value."""
        value_lower = value.lower().strip()

        # Check against mappings
        for level, keywords in self.URGENCY_MAPPINGS.items():
            for keyword in keywords:
                if keyword in value_lower or value_lower in keyword:
                    return True, None

        # If it's a reasonable text, accept it
        if len(value_lower) >= 3:
            return True, None

        return False, "Urgência não reconhecida"

    # ==================== Helper Methods ====================

    @staticmethod
    def _clean_phone(value: str) -> str:
        """
        Clean phone number, removing country code (+55 or 55) and non-digits.

        Handles:
        - +55 11 99999-8888 -> 11999998888
        - 55 11 99999-8888 -> 11999998888
        - (11) 99999-8888 -> 11999998888
        - 11999998888 -> 11999998888
        """
        # Remove all non-digits first
        digits = re.sub(r'\D', '', value)

        # If starts with 55 and has 12-13 digits, strip the country code
        if len(digits) >= 12 and digits.startswith('55'):
            digits = digits[2:]

        return digits

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """Normalize date string to DD/MM/YYYY format."""
        # Try to parse various formats
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
            "%Y-%m-%d", "%Y/%m/%d",
            "%d/%m/%y", "%d-%m-%y"
        ]

        from datetime import datetime
        for fmt in formats:
            try:
                date = datetime.strptime(date_str, fmt)
                return date.strftime("%d/%m/%Y")
            except ValueError:
                continue

        # If can't parse, return as-is
        return date_str

    @staticmethod
    def _clean_currency(value: str) -> str:
        """Clean currency value, keeping only digits and decimal separator."""
        # Remove R$ and spaces
        cleaned = re.sub(r'[R$\s]', '', value)

        # Handle Brazilian format (1.000,00 -> 1000.00)
        if ',' in cleaned and '.' in cleaned:
            # Brazilian format: 1.234,56
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned:
            # Could be 1234,56 or 1,234.56
            if cleaned.index(',') > len(cleaned) - 4:
                # Decimal comma: 1234,56
                cleaned = cleaned.replace(',', '.')
            else:
                # Thousands comma: 1,234
                cleaned = cleaned.replace(',', '')

        return cleaned

    def format_phone(self, phone: str) -> str:
        """Format phone number for display."""
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        elif len(digits) == 10:
            return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
        return phone

    def format_cpf(self, cpf: str) -> str:
        """Format CPF for display."""
        digits = re.sub(r'\D', '', cpf)
        if len(digits) == 11:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
        return cpf

    def format_cnpj(self, cnpj: str) -> str:
        """Format CNPJ for display."""
        digits = re.sub(r'\D', '', cnpj)
        if len(digits) == 14:
            return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
        return cnpj

    def format_cep(self, cep: str) -> str:
        """Format CEP for display."""
        digits = re.sub(r'\D', '', cep)
        if len(digits) == 8:
            return f"{digits[:5]}-{digits[5:]}"
        return cep

    def normalize_urgency(self, value: str) -> str:
        """Normalize urgency to standard value."""
        value_lower = value.lower().strip()

        for level, keywords in self.URGENCY_MAPPINGS.items():
            for keyword in keywords:
                if keyword in value_lower or value_lower in keyword:
                    return level

        return value_lower


# Singleton instance
data_validator = DataValidator()


def validate_field(field_type: str, value: Any, required: bool = True) -> ValidationResult:
    """
    Convenience function to validate a single field.

    Args:
        field_type: Type of field
        value: Value to validate
        required: Whether field is required

    Returns:
        ValidationResult
    """
    return data_validator.validate(field_type, value, required)


def validate_and_clean(data: Dict[str, Any], field_types: Dict[str, str] = None) -> tuple[Dict[str, Any], Dict[str, str]]:
    """
    Validate and clean multiple fields.

    Args:
        data: Dictionary of field_name -> value
        field_types: Optional mapping of field_name -> field_type

    Returns:
        Tuple of (cleaned_data, errors)
    """
    results = data_validator.validate_multiple(data, field_types)
    cleaned = data_validator.get_cleaned_data(results)
    errors = data_validator.get_all_errors(results)
    return cleaned, errors
