"""
Unit tests for DataValidator.
"""
import pytest
from src.agent.validators import DataValidator, ValidationResult, ValidationErrorCode


@pytest.fixture
def validator():
    """Create a DataValidator instance."""
    return DataValidator()


class TestEmailValidation:
    """Tests for email validation."""

    def test_valid_email(self, validator):
        """Valid email should pass validation."""
        result = validator.validate("email", "test@example.com")
        assert result.is_valid
        assert result.cleaned_value == "test@example.com"

    def test_valid_email_with_subdomain(self, validator):
        """Valid email with subdomain should pass."""
        result = validator.validate("email", "user@mail.company.com")
        assert result.is_valid

    def test_valid_email_with_plus(self, validator):
        """Email with plus sign should pass."""
        result = validator.validate("email", "user+tag@example.com")
        assert result.is_valid

    def test_invalid_email_no_at(self, validator):
        """Email without @ should fail."""
        result = validator.validate("email", "testexample.com")
        assert not result.is_valid
        assert result.error_code == ValidationErrorCode.INVALID_FORMAT

    def test_invalid_email_no_domain(self, validator):
        """Email without domain should fail."""
        result = validator.validate("email", "test@")
        assert not result.is_valid

    def test_email_with_spaces_trimmed(self, validator):
        """Email with leading/trailing spaces should be trimmed."""
        result = validator.validate("email", "  test@example.com  ")
        assert result.is_valid
        assert result.cleaned_value == "test@example.com"

    def test_email_lowercased(self, validator):
        """Email should be lowercased."""
        result = validator.validate("email", "Test@Example.COM")
        assert result.is_valid
        assert result.cleaned_value == "test@example.com"


class TestPhoneValidation:
    """Tests for phone number validation."""

    def test_valid_phone_11_digits(self, validator):
        """11-digit phone with DDD should pass."""
        result = validator.validate("telefone", "11999998888")
        assert result.is_valid
        assert result.cleaned_value == "11999998888"

    def test_valid_phone_10_digits(self, validator):
        """10-digit phone (landline) should pass."""
        result = validator.validate("telefone", "1133334444")
        assert result.is_valid
        assert result.cleaned_value == "1133334444"

    def test_phone_with_formatting(self, validator):
        """Phone with formatting should be cleaned."""
        result = validator.validate("telefone", "(11) 99999-8888")
        assert result.is_valid
        assert result.cleaned_value == "11999998888"

    def test_phone_with_country_code(self, validator):
        """Phone with +55 should be cleaned."""
        result = validator.validate("telefone", "+55 11 99999-8888")
        assert result.is_valid
        # Only keeps 11 digits (removes country code)

    def test_short_phone_fails(self, validator):
        """Phone with less than 10 digits should fail."""
        result = validator.validate("telefone", "999998888")
        assert not result.is_valid

    def test_phone_with_letters_fails(self, validator):
        """Phone with letters should fail after cleaning."""
        result = validator.validate("telefone", "abc")
        assert not result.is_valid


class TestCPFValidation:
    """Tests for CPF validation."""

    def test_valid_cpf(self, validator):
        """Valid CPF should pass."""
        # Using a valid CPF for testing
        result = validator.validate("cpf", "52998224725")
        assert result.is_valid

    def test_valid_cpf_with_formatting(self, validator):
        """CPF with formatting should be cleaned."""
        result = validator.validate("cpf", "529.982.247-25")
        assert result.is_valid
        assert result.cleaned_value == "52998224725"

    def test_invalid_cpf_all_same_digits(self, validator):
        """CPF with all same digits should fail."""
        result = validator.validate("cpf", "11111111111")
        assert not result.is_valid

    def test_invalid_cpf_wrong_checksum(self, validator):
        """CPF with wrong checksum should fail."""
        result = validator.validate("cpf", "12345678901")
        assert not result.is_valid

    def test_cpf_too_short(self, validator):
        """CPF with less than 11 digits should fail."""
        result = validator.validate("cpf", "1234567890")
        assert not result.is_valid


class TestCEPValidation:
    """Tests for CEP validation."""

    def test_valid_cep(self, validator):
        """Valid CEP should pass."""
        result = validator.validate("cep", "01310100")
        assert result.is_valid
        assert result.cleaned_value == "01310100"

    def test_valid_cep_with_dash(self, validator):
        """CEP with dash should be cleaned."""
        result = validator.validate("cep", "01310-100")
        assert result.is_valid
        assert result.cleaned_value == "01310100"

    def test_cep_too_short(self, validator):
        """CEP with less than 8 digits should fail."""
        result = validator.validate("cep", "0131010")
        assert not result.is_valid


class TestNameValidation:
    """Tests for name validation."""

    def test_valid_name(self, validator):
        """Valid name should pass."""
        result = validator.validate("nome", "João Silva")
        assert result.is_valid
        assert result.cleaned_value == "João Silva"

    def test_name_capitalized(self, validator):
        """Name should be properly capitalized."""
        result = validator.validate("nome", "joao silva")
        assert result.is_valid
        assert result.cleaned_value == "Joao Silva"

    def test_name_extra_spaces_removed(self, validator):
        """Extra spaces should be removed."""
        result = validator.validate("nome", "João    Silva")
        assert result.is_valid
        assert result.cleaned_value == "João Silva"

    def test_name_too_short(self, validator):
        """Single character name should fail."""
        result = validator.validate("nome", "J")
        assert not result.is_valid


class TestCurrencyValidation:
    """Tests for currency/budget validation."""

    def test_valid_currency_simple(self, validator):
        """Simple number should pass."""
        result = validator.validate("orcamento", "50000")
        assert result.is_valid

    def test_valid_currency_with_symbol(self, validator):
        """Currency with R$ should be cleaned."""
        result = validator.validate("orcamento", "R$ 50.000,00")
        assert result.is_valid

    def test_valid_currency_american_format(self, validator):
        """American format should work."""
        result = validator.validate("orcamento", "50,000.00")
        assert result.is_valid


class TestRequiredFields:
    """Tests for required field handling."""

    def test_empty_required_field_fails(self, validator):
        """Empty value for required field should fail."""
        result = validator.validate("nome", "", required=True)
        assert not result.is_valid
        assert result.error_code == ValidationErrorCode.REQUIRED

    def test_none_required_field_fails(self, validator):
        """None value for required field should fail."""
        result = validator.validate("nome", None, required=True)
        assert not result.is_valid

    def test_empty_optional_field_passes(self, validator):
        """Empty value for optional field should pass."""
        result = validator.validate("nome", "", required=False)
        assert result.is_valid
        assert result.cleaned_value is None


class TestMultipleValidation:
    """Tests for validating multiple fields."""

    def test_validate_multiple_fields(self, validator):
        """Should validate multiple fields at once."""
        data = {
            "nome": "João Silva",
            "email": "joao@email.com",
            "telefone": "11999998888"
        }
        results = validator.validate_multiple(data)

        assert results["nome"].is_valid
        assert results["email"].is_valid
        assert results["telefone"].is_valid

    def test_get_all_errors(self, validator):
        """Should return all validation errors."""
        data = {
            "nome": "J",  # Too short
            "email": "invalid",  # Invalid format
            "telefone": "123"  # Too short
        }
        results = validator.validate_multiple(data)
        errors = validator.get_all_errors(results)

        assert "nome" in errors
        assert "email" in errors
        assert "telefone" in errors

    def test_get_cleaned_data(self, validator):
        """Should return cleaned data for valid fields."""
        data = {
            "nome": "  joão silva  ",
            "email": "JOAO@EMAIL.COM",
            "invalid_field": "J"  # This might fail
        }
        results = validator.validate_multiple(data)
        cleaned = validator.get_cleaned_data(results)

        assert cleaned.get("nome") == "João Silva"
        assert cleaned.get("email") == "joao@email.com"


class TestFormatters:
    """Tests for formatting methods."""

    def test_format_phone(self, validator):
        """Phone should be formatted correctly."""
        formatted = validator.format_phone("11999998888")
        assert formatted == "(11) 99999-8888"

    def test_format_cpf(self, validator):
        """CPF should be formatted correctly."""
        formatted = validator.format_cpf("52998224725")
        assert formatted == "529.982.247-25"

    def test_format_cep(self, validator):
        """CEP should be formatted correctly."""
        formatted = validator.format_cep("01310100")
        assert formatted == "01310-100"
