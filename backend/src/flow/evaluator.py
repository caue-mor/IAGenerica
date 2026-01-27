"""
Condition Evaluator - Deterministic Python-based condition evaluation for flow nodes.

Evaluates conditions WITHOUT using LLM - pure Python logic for predictable results.
Supports both English and Portuguese operator names.
"""
import re
import logging
from typing import Any, Dict, Optional, List, Callable, Union

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """
    Deterministic condition evaluator for CONDITION and QUALIFICATION nodes.

    All evaluations are done in pure Python - NO LLM calls.
    This ensures predictable, fast, and consistent condition evaluation.

    Supports:
    - Basic comparisons (equals, not_equals, contains, etc.)
    - Numeric comparisons (greater_than, less_than, etc.)
    - String operations (starts_with, ends_with, matches)
    - List operations (in_list, not_in_list)
    - Existence checks (exists, not_exists, is_empty, is_not_empty)
    - Portuguese operator aliases (igual, diferente, maior, menor, contem, etc.)
    """

    # =========================================================================
    # OPERATOR DEFINITIONS - Lambda functions for each operator
    # =========================================================================

    OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
        # ----- Equality Operators -----
        "equals": lambda actual, expected: ConditionEvaluator._safe_equals(actual, expected),
        "equal": lambda actual, expected: ConditionEvaluator._safe_equals(actual, expected),
        "eq": lambda actual, expected: ConditionEvaluator._safe_equals(actual, expected),
        "==": lambda actual, expected: ConditionEvaluator._safe_equals(actual, expected),

        "not_equals": lambda actual, expected: not ConditionEvaluator._safe_equals(actual, expected),
        "not_equal": lambda actual, expected: not ConditionEvaluator._safe_equals(actual, expected),
        "neq": lambda actual, expected: not ConditionEvaluator._safe_equals(actual, expected),
        "!=": lambda actual, expected: not ConditionEvaluator._safe_equals(actual, expected),
        "<>": lambda actual, expected: not ConditionEvaluator._safe_equals(actual, expected),

        # ----- Numeric Comparisons -----
        "greater_than": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a > b),
        "greater": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a > b),
        "gt": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a > b),
        ">": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a > b),

        "less_than": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a < b),
        "less": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a < b),
        "lt": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a < b),
        "<": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a < b),

        "greater_equal": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a >= b),
        "greater_or_equal": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a >= b),
        "gte": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a >= b),
        ">=": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a >= b),

        "less_equal": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a <= b),
        "less_or_equal": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a <= b),
        "lte": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a <= b),
        "<=": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a <= b),

        # ----- String Contains -----
        "contains": lambda actual, expected: ConditionEvaluator._safe_contains(actual, expected),
        "contain": lambda actual, expected: ConditionEvaluator._safe_contains(actual, expected),

        "not_contains": lambda actual, expected: not ConditionEvaluator._safe_contains(actual, expected),
        "not_contain": lambda actual, expected: not ConditionEvaluator._safe_contains(actual, expected),

        # ----- String Starts/Ends With -----
        "starts_with": lambda actual, expected: ConditionEvaluator._safe_starts_with(actual, expected),
        "startswith": lambda actual, expected: ConditionEvaluator._safe_starts_with(actual, expected),
        "start_with": lambda actual, expected: ConditionEvaluator._safe_starts_with(actual, expected),

        "ends_with": lambda actual, expected: ConditionEvaluator._safe_ends_with(actual, expected),
        "endswith": lambda actual, expected: ConditionEvaluator._safe_ends_with(actual, expected),
        "end_with": lambda actual, expected: ConditionEvaluator._safe_ends_with(actual, expected),

        # ----- Existence Checks -----
        "exists": lambda actual, _: actual is not None,
        "exist": lambda actual, _: actual is not None,
        "is_set": lambda actual, _: actual is not None,

        "not_exists": lambda actual, _: actual is None,
        "not_exist": lambda actual, _: actual is None,
        "is_not_set": lambda actual, _: actual is None,

        "is_empty": lambda actual, _: ConditionEvaluator._is_empty(actual),
        "empty": lambda actual, _: ConditionEvaluator._is_empty(actual),

        "is_not_empty": lambda actual, _: not ConditionEvaluator._is_empty(actual),
        "not_empty": lambda actual, _: not ConditionEvaluator._is_empty(actual),

        # ----- List Operations -----
        "in_list": lambda actual, expected: ConditionEvaluator._safe_in_list(actual, expected),
        "in": lambda actual, expected: ConditionEvaluator._safe_in_list(actual, expected),

        "not_in_list": lambda actual, expected: not ConditionEvaluator._safe_in_list(actual, expected),
        "not_in": lambda actual, expected: not ConditionEvaluator._safe_in_list(actual, expected),

        # ----- Regex Match -----
        "matches": lambda actual, expected: ConditionEvaluator._safe_regex_match(actual, expected),
        "match": lambda actual, expected: ConditionEvaluator._safe_regex_match(actual, expected),
        "matches_regex": lambda actual, expected: ConditionEvaluator._safe_regex_match(actual, expected),
        "regex": lambda actual, expected: ConditionEvaluator._safe_regex_match(actual, expected),

        # =========================================================================
        # PORTUGUESE OPERATOR ALIASES
        # =========================================================================

        # Equality
        "igual": lambda actual, expected: ConditionEvaluator._safe_equals(actual, expected),
        "igual_a": lambda actual, expected: ConditionEvaluator._safe_equals(actual, expected),
        "diferente": lambda actual, expected: not ConditionEvaluator._safe_equals(actual, expected),
        "diferente_de": lambda actual, expected: not ConditionEvaluator._safe_equals(actual, expected),
        "nao_igual": lambda actual, expected: not ConditionEvaluator._safe_equals(actual, expected),

        # Numeric Comparisons
        "maior": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a > b),
        "maior_que": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a > b),
        "maior_do_que": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a > b),

        "menor": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a < b),
        "menor_que": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a < b),
        "menor_do_que": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a < b),

        "maior_igual": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a >= b),
        "maior_ou_igual": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a >= b),
        "maior_ou_igual_a": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a >= b),

        "menor_igual": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a <= b),
        "menor_ou_igual": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a <= b),
        "menor_ou_igual_a": lambda actual, expected: ConditionEvaluator._safe_compare(actual, expected, lambda a, b: a <= b),

        # Contains
        "contem": lambda actual, expected: ConditionEvaluator._safe_contains(actual, expected),
        "contem_texto": lambda actual, expected: ConditionEvaluator._safe_contains(actual, expected),
        "inclui": lambda actual, expected: ConditionEvaluator._safe_contains(actual, expected),

        "nao_contem": lambda actual, expected: not ConditionEvaluator._safe_contains(actual, expected),
        "nao_inclui": lambda actual, expected: not ConditionEvaluator._safe_contains(actual, expected),

        # Starts/Ends With
        "comeca_com": lambda actual, expected: ConditionEvaluator._safe_starts_with(actual, expected),
        "inicia_com": lambda actual, expected: ConditionEvaluator._safe_starts_with(actual, expected),

        "termina_com": lambda actual, expected: ConditionEvaluator._safe_ends_with(actual, expected),
        "finaliza_com": lambda actual, expected: ConditionEvaluator._safe_ends_with(actual, expected),

        # Existence
        "existe": lambda actual, _: actual is not None,
        "definido": lambda actual, _: actual is not None,
        "preenchido": lambda actual, _: not ConditionEvaluator._is_empty(actual),

        "nao_existe": lambda actual, _: actual is None,
        "nao_definido": lambda actual, _: actual is None,

        "vazio": lambda actual, _: ConditionEvaluator._is_empty(actual),
        "esta_vazio": lambda actual, _: ConditionEvaluator._is_empty(actual),

        "nao_vazio": lambda actual, _: not ConditionEvaluator._is_empty(actual),
        "nao_esta_vazio": lambda actual, _: not ConditionEvaluator._is_empty(actual),

        # List
        "na_lista": lambda actual, expected: ConditionEvaluator._safe_in_list(actual, expected),
        "em_lista": lambda actual, expected: ConditionEvaluator._safe_in_list(actual, expected),
        "esta_na_lista": lambda actual, expected: ConditionEvaluator._safe_in_list(actual, expected),

        "fora_da_lista": lambda actual, expected: not ConditionEvaluator._safe_in_list(actual, expected),
        "nao_na_lista": lambda actual, expected: not ConditionEvaluator._safe_in_list(actual, expected),

        # Regex
        "corresponde": lambda actual, expected: ConditionEvaluator._safe_regex_match(actual, expected),
        "padrao": lambda actual, expected: ConditionEvaluator._safe_regex_match(actual, expected),
    }

    # =========================================================================
    # MAIN EVALUATION METHOD
    # =========================================================================

    @classmethod
    def evaluate(
        cls,
        field: str,
        operator: str,
        threshold: Any,
        collected_data: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a condition DETERMINISTICALLY in Python (no LLM).

        Args:
            field: The field name to check in collected_data
            operator: The comparison operator (supports English and Portuguese)
            threshold: The value to compare against
            collected_data: Dictionary containing the field values

        Returns:
            True if condition is met, False otherwise

        Example:
            >>> data = {"idade": 25, "cidade": "Sao Paulo"}
            >>> ConditionEvaluator.evaluate("idade", "maior", 18, data)
            True
            >>> ConditionEvaluator.evaluate("cidade", "contem", "Paulo", data)
            True
        """
        # Get field value from collected_data
        field_value = cls._get_nested_value(collected_data, field)

        # Normalize operator name
        normalized_operator = cls._normalize_operator(operator)

        # Get operator function
        operator_func = cls.OPERATORS.get(normalized_operator)

        if operator_func is None:
            logger.warning(
                f"Unknown operator: '{operator}' (normalized: '{normalized_operator}'). "
                f"Available operators: {list(cls.OPERATORS.keys())[:20]}..."
            )
            return False

        try:
            result = operator_func(field_value, threshold)

            logger.debug(
                f"Condition evaluated: field='{field}', value={repr(field_value)}, "
                f"operator='{operator}', threshold={repr(threshold)} -> {result}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Error evaluating condition: field='{field}', operator='{operator}', "
                f"threshold={repr(threshold)}, error={e}"
            )
            return False

    # =========================================================================
    # HELPER METHODS FOR SAFE OPERATIONS
    # =========================================================================

    @staticmethod
    def _normalize_operator(operator: str) -> str:
        """
        Normalize operator name for lookup.
        Converts to lowercase and replaces spaces with underscores.
        """
        if not operator:
            return ""
        return operator.strip().lower().replace(" ", "_").replace("-", "_")

    @staticmethod
    def _get_nested_value(data: Dict[str, Any], field: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Example:
            >>> data = {"user": {"profile": {"name": "John"}}}
            >>> ConditionEvaluator._get_nested_value(data, "user.profile.name")
            "John"
        """
        if not data or not field:
            return None

        keys = field.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None

            if value is None:
                return None

        return value

    @staticmethod
    def _coerce_to_number(value: Any) -> Optional[float]:
        """
        Safely coerce a value to a number.

        Handles:
        - int, float -> float
        - str with numbers -> float (removes currency symbols, spaces)
        - Brazilian format: 1.234,56 -> 1234.56
        - US format: 1,234.56 -> 1234.56
        - None -> None
        - Invalid -> None
        """
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            # Remove common formatting characters
            cleaned = value.strip()

            # Remove currency symbols and whitespace
            cleaned = re.sub(r'[R$€£¥\s]', '', cleaned)

            # Handle Brazilian/European format (1.234,56) vs US format (1,234.56)
            if ',' in cleaned and '.' in cleaned:
                # If comma comes after dot, it's Brazilian/European format
                # Example: 1.500,00 -> comma is decimal separator
                if cleaned.rfind(',') > cleaned.rfind('.'):
                    # Brazilian: 1.500,00 -> remove dots (thousands), replace comma with dot
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                else:
                    # US format: 1,500.00 -> just remove commas (thousands)
                    cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                # Single comma - could be decimal separator (Brazilian) or thousands (US)
                # Check if there are exactly 2 digits after comma (decimal indicator)
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Likely decimal separator: 1500,00 -> 1500.00
                    cleaned = cleaned.replace(',', '.')
                else:
                    # Likely thousands separator: 1,500 -> 1500
                    cleaned = cleaned.replace(',', '')
            # If only dots, check if it's a thousands separator
            elif cleaned.count('.') > 1:
                # Multiple dots = thousands separators: 1.000.000 -> 1000000
                cleaned = cleaned.replace('.', '')

            try:
                return float(cleaned)
            except ValueError:
                return None

        return None

    @staticmethod
    def _normalize_string(value: Any) -> str:
        """
        Normalize a value to lowercase string for comparison.
        """
        if value is None:
            return ""
        return str(value).strip().lower()

    @staticmethod
    def _is_empty(value: Any) -> bool:
        """
        Check if a value is considered empty.

        Empty values:
        - None
        - Empty string or whitespace-only string
        - Empty list, dict, set
        - Zero is NOT considered empty
        """
        if value is None:
            return True

        if isinstance(value, str):
            return value.strip() == ""

        if isinstance(value, (list, dict, set, tuple)):
            return len(value) == 0

        return False

    # =========================================================================
    # SAFE COMPARISON IMPLEMENTATIONS
    # =========================================================================

    @staticmethod
    def _safe_equals(actual: Any, expected: Any) -> bool:
        """
        Safe equality comparison with type coercion.

        Handles:
        - None comparisons
        - Numeric comparison (with string to number conversion)
        - Case-insensitive string comparison
        - Boolean comparisons
        """
        # Both None
        if actual is None and expected is None:
            return True

        # Only one is None
        if actual is None or expected is None:
            return False

        # Boolean comparison
        if isinstance(actual, bool) or isinstance(expected, bool):
            return bool(actual) == bool(expected)

        # Try numeric comparison first
        actual_num = ConditionEvaluator._coerce_to_number(actual)
        expected_num = ConditionEvaluator._coerce_to_number(expected)

        if actual_num is not None and expected_num is not None:
            return actual_num == expected_num

        # Fall back to case-insensitive string comparison
        return ConditionEvaluator._normalize_string(actual) == ConditionEvaluator._normalize_string(expected)

    @staticmethod
    def _safe_compare(
        actual: Any,
        expected: Any,
        comparator: Callable[[float, float], bool]
    ) -> bool:
        """
        Safe numeric comparison with type coercion.

        Returns False if either value cannot be converted to a number.
        """
        actual_num = ConditionEvaluator._coerce_to_number(actual)
        expected_num = ConditionEvaluator._coerce_to_number(expected)

        if actual_num is None or expected_num is None:
            logger.debug(
                f"Numeric comparison failed: actual={repr(actual)} -> {actual_num}, "
                f"expected={repr(expected)} -> {expected_num}"
            )
            return False

        return comparator(actual_num, expected_num)

    @staticmethod
    def _safe_contains(actual: Any, expected: Any) -> bool:
        """
        Safe contains check.

        Handles:
        - String contains string (case-insensitive)
        - List contains item
        - None handling
        """
        if actual is None or expected is None:
            return False

        # List contains check
        if isinstance(actual, (list, tuple, set)):
            normalized_expected = ConditionEvaluator._normalize_string(expected)
            return any(
                ConditionEvaluator._normalize_string(item) == normalized_expected
                for item in actual
            )

        # String contains
        actual_str = ConditionEvaluator._normalize_string(actual)
        expected_str = ConditionEvaluator._normalize_string(expected)

        return expected_str in actual_str

    @staticmethod
    def _safe_starts_with(actual: Any, expected: Any) -> bool:
        """Safe starts_with check (case-insensitive)."""
        if actual is None or expected is None:
            return False

        actual_str = ConditionEvaluator._normalize_string(actual)
        expected_str = ConditionEvaluator._normalize_string(expected)

        return actual_str.startswith(expected_str)

    @staticmethod
    def _safe_ends_with(actual: Any, expected: Any) -> bool:
        """Safe ends_with check (case-insensitive)."""
        if actual is None or expected is None:
            return False

        actual_str = ConditionEvaluator._normalize_string(actual)
        expected_str = ConditionEvaluator._normalize_string(expected)

        return actual_str.endswith(expected_str)

    @staticmethod
    def _safe_in_list(actual: Any, expected: Any) -> bool:
        """
        Safe in_list check.

        Handles:
        - List input
        - Comma-separated string input
        - Case-insensitive matching
        - None handling
        """
        if actual is None:
            return False

        # Normalize actual value
        actual_normalized = ConditionEvaluator._normalize_string(actual)

        # Parse expected list
        if isinstance(expected, (list, tuple, set)):
            expected_list = expected
        elif isinstance(expected, str):
            # Support comma-separated values
            expected_list = [item.strip() for item in expected.split(",")]
        else:
            expected_list = [expected]

        # Check if actual is in the list
        for item in expected_list:
            if ConditionEvaluator._normalize_string(item) == actual_normalized:
                return True

        return False

    @staticmethod
    def _safe_regex_match(actual: Any, pattern: Any) -> bool:
        """
        Safe regex match.

        Uses re.search for partial matching (not just start of string).
        Case-insensitive by default.
        """
        if actual is None or pattern is None:
            return False

        try:
            actual_str = str(actual)
            pattern_str = str(pattern)

            return bool(re.search(pattern_str, actual_str, re.IGNORECASE))

        except re.error as e:
            logger.warning(f"Invalid regex pattern '{pattern}': {e}")
            return False
        except Exception as e:
            logger.error(f"Regex match error: {e}")
            return False

    # =========================================================================
    # BATCH EVALUATION METHODS
    # =========================================================================

    @classmethod
    def evaluate_all(
        cls,
        conditions: List[Dict[str, Any]],
        collected_data: Dict[str, Any],
        mode: str = "and"
    ) -> bool:
        """
        Evaluate multiple conditions.

        Args:
            conditions: List of condition dicts with 'field', 'operator', 'value'/'threshold'
            collected_data: Dictionary with field values
            mode: 'and' (all must match) or 'or' (any must match)

        Returns:
            True if conditions are met according to mode

        Example:
            >>> conditions = [
            ...     {"field": "idade", "operator": "maior", "value": 18},
            ...     {"field": "cidade", "operator": "igual", "value": "SP"}
            ... ]
            >>> ConditionEvaluator.evaluate_all(conditions, {"idade": 25, "cidade": "SP"}, "and")
            True
        """
        if not conditions:
            return True

        results = []

        for condition in conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "equals")
            # Support both 'value' and 'threshold' keys
            threshold = condition.get("value", condition.get("threshold"))

            result = cls.evaluate(field, operator, threshold, collected_data)
            results.append(result)

            # Short-circuit evaluation
            if mode.lower() == "or" and result:
                return True
            if mode.lower() == "and" and not result:
                return False

        if mode.lower() == "or":
            return any(results)
        return all(results)

    @classmethod
    def evaluate_expression(
        cls,
        expression: str,
        collected_data: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a complex expression with multiple conditions.

        Supports: AND, OR, E, OU (Portuguese), parentheses, field comparisons

        Example: "(interesse == 'comprar') AND (cidade == 'SP')"
        Example: "(idade > 18) E (tem_carro == True)"

        Args:
            expression: The expression to evaluate
            collected_data: Dictionary with field values

        Returns:
            True if expression evaluates to true
        """
        if not expression or not expression.strip():
            return True

        try:
            safe_expr = expression

            # Replace Portuguese logical operators
            safe_expr = re.sub(r'\bE\b', ' and ', safe_expr)
            safe_expr = re.sub(r'\bOU\b', ' or ', safe_expr)
            safe_expr = re.sub(r'\bNAO\b', ' not ', safe_expr)

            # Replace English logical operators
            safe_expr = safe_expr.replace(' AND ', ' and ')
            safe_expr = safe_expr.replace(' OR ', ' or ')
            safe_expr = safe_expr.replace(' NOT ', ' not ')

            # Replace field names with their values
            for key, value in collected_data.items():
                if isinstance(value, str):
                    safe_value = f'"{value}"'
                elif isinstance(value, bool):
                    safe_value = str(value)
                elif value is None:
                    safe_value = 'None'
                else:
                    safe_value = str(value)

                # Use word boundaries to avoid partial replacements
                safe_expr = re.sub(
                    rf'\b{re.escape(key)}\b',
                    safe_value,
                    safe_expr
                )

            # Safe eval with restricted builtins
            result = eval(
                safe_expr,
                {"__builtins__": {}},
                {"True": True, "False": False, "None": None, "true": True, "false": False}
            )

            logger.debug(f"Expression '{expression}' evaluated to {result}")
            return bool(result)

        except Exception as e:
            logger.warning(f"Error evaluating expression '{expression}': {e}")
            return False

    # =========================================================================
    # SCORING METHODS
    # =========================================================================

    @classmethod
    def evaluate_score(
        cls,
        collected_data: Dict[str, Any],
        score_config: Dict[str, int],
        min_score: Optional[int] = None
    ) -> tuple:
        """
        Calculate qualification score based on collected data.

        Args:
            collected_data: Dictionary with field values
            score_config: Dictionary mapping field names to point values
            min_score: Minimum score to be considered qualified

        Returns:
            Tuple of (total_score, is_qualified, score_breakdown)

        Example:
            >>> config = {"nome": 10, "email": 20, "telefone": 30}
            >>> data = {"nome": "John", "email": "john@email.com"}
            >>> ConditionEvaluator.evaluate_score(data, config, min_score=25)
            (30, True, {"nome": 10, "email": 20})
        """
        total_score = 0
        breakdown = {}

        for field, points in score_config.items():
            value = cls._get_nested_value(collected_data, field)

            if value is not None and not cls._is_empty(value):
                total_score += points
                breakdown[field] = points

        is_qualified = min_score is None or total_score >= min_score

        logger.debug(
            f"Score calculation: total={total_score}, min={min_score}, "
            f"qualified={is_qualified}, breakdown={breakdown}"
        )

        return total_score, is_qualified, breakdown

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    @classmethod
    def get_available_operators(cls) -> List[str]:
        """Return list of all available operator names."""
        return sorted(list(cls.OPERATORS.keys()))

    @classmethod
    def get_operator_categories(cls) -> Dict[str, List[str]]:
        """Return operators organized by category."""
        return {
            "equality": ["equals", "not_equals", "igual", "diferente"],
            "numeric": ["greater_than", "less_than", "greater_equal", "less_equal",
                       "maior", "menor", "maior_igual", "menor_igual"],
            "string": ["contains", "not_contains", "starts_with", "ends_with",
                      "contem", "nao_contem", "comeca_com", "termina_com"],
            "existence": ["exists", "not_exists", "is_empty", "is_not_empty",
                         "existe", "nao_existe", "vazio", "nao_vazio"],
            "list": ["in_list", "not_in_list", "na_lista", "fora_da_lista"],
            "regex": ["matches", "regex", "corresponde", "padrao"],
        }


# Singleton instance for convenience
evaluator = ConditionEvaluator()
