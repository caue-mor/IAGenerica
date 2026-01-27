"""
Condition Evaluator - Extended for flow nodes with additional operators
"""
import re
import logging
from typing import Any, Optional, List
from ..models.flow import Operator

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """
    Evaluates conditions for CONDITION and QUALIFICATION nodes.

    Supports:
    - Basic comparisons (equals, not_equals, contains, etc.)
    - Numeric comparisons (greater_than, less_than, etc.)
    - String operations (starts_with, ends_with, matches_regex)
    - List operations (in_list, not_in_list)
    - Complex expressions with AND, OR, ()
    """

    @staticmethod
    def evaluate(
        field_value: Any,
        operator: Operator | str,
        expected_value: Any
    ) -> bool:
        """
        Evaluate a condition.

        Args:
            field_value: The actual value from lead data
            operator: The comparison operator
            expected_value: The expected value to compare against

        Returns:
            True if condition is met, False otherwise
        """
        # Convert operator string to enum if needed
        if isinstance(operator, str):
            try:
                operator = Operator(operator)
            except ValueError:
                logger.warning(f"Unknown operator: {operator}")
                return False

        # Normalize values for comparison
        actual = ConditionEvaluator._normalize(field_value)
        expected = ConditionEvaluator._normalize(expected_value)

        try:
            if operator == Operator.EQUALS:
                return ConditionEvaluator._equals(actual, expected)

            elif operator == Operator.NOT_EQUALS:
                return not ConditionEvaluator._equals(actual, expected)

            elif operator == Operator.CONTAINS:
                return ConditionEvaluator._contains(actual, expected)

            elif operator == Operator.NOT_CONTAINS:
                return not ConditionEvaluator._contains(actual, expected)

            elif operator == Operator.STARTS_WITH:
                return ConditionEvaluator._starts_with(actual, expected)

            elif operator == Operator.ENDS_WITH:
                return ConditionEvaluator._ends_with(actual, expected)

            elif operator == Operator.GREATER_THAN:
                return ConditionEvaluator._greater_than(actual, expected)

            elif operator == Operator.LESS_THAN:
                return ConditionEvaluator._less_than(actual, expected)

            elif operator == Operator.GREATER_OR_EQUAL:
                return ConditionEvaluator._greater_or_equal(actual, expected)

            elif operator == Operator.LESS_OR_EQUAL:
                return ConditionEvaluator._less_or_equal(actual, expected)

            elif operator == Operator.IS_EMPTY:
                return ConditionEvaluator._is_empty(field_value)

            elif operator == Operator.IS_NOT_EMPTY:
                return not ConditionEvaluator._is_empty(field_value)

            elif operator == Operator.EXISTS:
                return field_value is not None

            elif operator == Operator.MATCHES_REGEX:
                return ConditionEvaluator._matches_regex(field_value, expected_value)

            elif operator == Operator.IN_LIST:
                return ConditionEvaluator._in_list(actual, expected_value)

            elif operator == Operator.NOT_IN_LIST:
                return not ConditionEvaluator._in_list(actual, expected_value)

        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False

        return False

    @staticmethod
    def _normalize(value: Any) -> Any:
        """Normalize value for comparison"""
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @staticmethod
    def _equals(actual: Any, expected: Any) -> bool:
        """Check equality"""
        if actual is None and expected is None:
            return True
        if actual is None or expected is None:
            return False

        # Try numeric comparison
        try:
            return float(actual) == float(expected)
        except (ValueError, TypeError):
            pass

        # String comparison (case insensitive)
        return str(actual).lower() == str(expected).lower()

    @staticmethod
    def _contains(actual: Any, expected: Any) -> bool:
        """Check if actual contains expected"""
        if actual is None or expected is None:
            return False

        actual_str = str(actual).lower()
        expected_str = str(expected).lower()

        return expected_str in actual_str

    @staticmethod
    def _starts_with(actual: Any, expected: Any) -> bool:
        """Check if actual starts with expected"""
        if actual is None or expected is None:
            return False

        actual_str = str(actual).lower()
        expected_str = str(expected).lower()

        return actual_str.startswith(expected_str)

    @staticmethod
    def _ends_with(actual: Any, expected: Any) -> bool:
        """Check if actual ends with expected"""
        if actual is None or expected is None:
            return False

        actual_str = str(actual).lower()
        expected_str = str(expected).lower()

        return actual_str.endswith(expected_str)

    @staticmethod
    def _greater_than(actual: Any, expected: Any) -> bool:
        """Check if actual > expected"""
        try:
            return float(actual) > float(expected)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _less_than(actual: Any, expected: Any) -> bool:
        """Check if actual < expected"""
        try:
            return float(actual) < float(expected)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _greater_or_equal(actual: Any, expected: Any) -> bool:
        """Check if actual >= expected"""
        try:
            return float(actual) >= float(expected)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _less_or_equal(actual: Any, expected: Any) -> bool:
        """Check if actual <= expected"""
        try:
            return float(actual) <= float(expected)
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_empty(value: Any) -> bool:
        """Check if value is empty"""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False

    @staticmethod
    def _matches_regex(value: Any, pattern: str) -> bool:
        """Check if value matches regex pattern"""
        if value is None or pattern is None:
            return False

        try:
            return bool(re.match(pattern, str(value), re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return False

    @staticmethod
    def _in_list(value: Any, list_value: Any) -> bool:
        """Check if value is in list"""
        if value is None:
            return False

        # Handle list input
        if isinstance(list_value, list):
            normalized_list = [str(item).lower() for item in list_value]
        elif isinstance(list_value, str):
            # Assume comma-separated values
            normalized_list = [item.strip().lower() for item in list_value.split(",")]
        else:
            return False

        return str(value).lower() in normalized_list

    @staticmethod
    def evaluate_expression(expression: str, data: dict[str, Any]) -> bool:
        """
        Evaluate a complex expression with multiple conditions.

        Supports: AND, OR, (), field comparisons
        Example: "(interesse == 'comprar') AND (cidade == 'SP')"

        Args:
            expression: The expression to evaluate
            data: Dictionary with field values

        Returns:
            True if expression evaluates to true
        """
        if not expression or not expression.strip():
            return True

        try:
            # Create safe evaluation context
            safe_expr = expression

            # Replace field names with their values
            for key, value in data.items():
                # Handle string values
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

            # Replace operators
            safe_expr = safe_expr.replace(' AND ', ' and ')
            safe_expr = safe_expr.replace(' OR ', ' or ')
            safe_expr = safe_expr.replace(' NOT ', ' not ')

            # Safe eval with restricted builtins
            result = eval(
                safe_expr,
                {"__builtins__": {}},
                {"True": True, "False": False, "None": None}
            )

            logger.debug(f"Expression '{expression}' evaluated to {result}")
            return bool(result)

        except Exception as e:
            logger.warning(f"Error evaluating expression '{expression}': {e}")
            return False

    @staticmethod
    def evaluate_all(conditions: List[dict], data: dict[str, Any], mode: str = "and") -> bool:
        """
        Evaluate multiple conditions.

        Args:
            conditions: List of condition dicts with 'field', 'operator', 'value'
            data: Dictionary with field values
            mode: 'and' (all must match) or 'or' (any must match)

        Returns:
            True if conditions are met according to mode
        """
        if not conditions:
            return True

        results = []
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            expected = condition.get("value")

            field_value = data.get(field)
            result = ConditionEvaluator.evaluate(field_value, operator, expected)
            results.append(result)

        if mode.lower() == "or":
            return any(results)
        return all(results)

    @staticmethod
    def evaluate_score(
        data: dict[str, Any],
        score_config: dict[str, int],
        min_score: Optional[int] = None
    ) -> tuple[int, bool, dict[str, int]]:
        """
        Calculate qualification score based on collected data.

        Args:
            data: Dictionary with field values
            score_config: Dictionary mapping field names to point values
            min_score: Minimum score to be considered qualified

        Returns:
            Tuple of (total_score, is_qualified, score_breakdown)
        """
        total_score = 0
        breakdown = {}

        for field, points in score_config.items():
            if field in data and data[field] is not None:
                value = data[field]

                # Check if field has a meaningful value
                if ConditionEvaluator._is_empty(value):
                    continue

                total_score += points
                breakdown[field] = points

        is_qualified = min_score is None or total_score >= min_score

        logger.debug(
            f"Score calculation: total={total_score}, min={min_score}, "
            f"qualified={is_qualified}, breakdown={breakdown}"
        )

        return total_score, is_qualified, breakdown


# Singleton instance for convenience
evaluator = ConditionEvaluator()
