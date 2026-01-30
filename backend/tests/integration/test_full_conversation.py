"""
Integration tests for full conversation flow.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.brain import AIBrain, BrainDecision, CompanyContext
from src.agent.flow_navigator import FlowGraphNavigator, create_navigator
from src.agent.flow_interpreter import FlowInterpreter, FlowIntent
from src.agent.goal_tracker import GoalTracker
from src.agent.memory import UnifiedMemory
from src.agent.validators import DataValidator
from src.agent.lead_scorer import LeadScorer, LeadTemperature
from src.models.flow import FlowConfig


@pytest.fixture
def company_context():
    """Create company context for testing."""
    return CompanyContext(
        company_name="Imobiliária Teste",
        agent_name="Ana",
        agent_tone="amigavel",
        use_emojis=False
    )


@pytest.fixture
def flow_config(sample_flow_config):
    """Create FlowConfig from sample data."""
    return FlowConfig(**sample_flow_config)


@pytest.fixture
def memory():
    """Create UnifiedMemory for testing."""
    return UnifiedMemory(lead_id=1, conversation_id=1)


@pytest.fixture
def flow_intent(flow_config):
    """Create FlowIntent from config."""
    interpreter = FlowInterpreter(flow_config)
    return interpreter.interpret()


@pytest.fixture
def goal_tracker(flow_intent, memory):
    """Create GoalTracker."""
    return GoalTracker(flow_intent, memory)


@pytest.fixture
def navigator(flow_config):
    """Create FlowGraphNavigator."""
    return create_navigator(flow_config)


class TestComponentIntegration:
    """Tests for component integration."""

    def test_validator_works_with_scorer(self):
        """Validator and scorer should work together."""
        validator = DataValidator()
        scorer = LeadScorer()

        # Validate and clean data
        raw_data = {
            "nome": "  joão silva  ",
            "email": "JOAO@EMAIL.COM",
            "telefone": "(11) 99999-8888"
        }

        cleaned_data = {}
        for field, value in raw_data.items():
            result = validator.validate(field, value)
            if result.is_valid:
                cleaned_data[field] = result.cleaned_value

        # Score the cleaned data
        score = scorer.calculate_score(cleaned_data)

        assert score.total > 0
        assert cleaned_data["nome"] == "João Silva"
        assert cleaned_data["email"] == "joao@email.com"

    def test_navigator_with_interpreter(self, flow_config):
        """Navigator and interpreter should work together."""
        # Create both from same config
        interpreter = FlowInterpreter(flow_config)
        intent = interpreter.interpret()
        navigator = create_navigator(flow_config)

        # Both should have same fields to collect
        navigator_fields = navigator.get_all_data_fields()
        intent_fields = [g.field_name for g in intent.goals]

        # There should be overlap
        common_fields = set(navigator_fields) & set(intent_fields)
        assert len(common_fields) > 0

    def test_goal_tracker_with_navigator(
        self, flow_intent, memory, navigator
    ):
        """GoalTracker and Navigator should coordinate."""
        goal_tracker = GoalTracker(flow_intent, memory)

        # Collect some data
        from src.agent.goal_tracker import ExtractionResult

        extractions = [
            ExtractionResult(field="nome", value="João", confidence=0.9),
            ExtractionResult(field="telefone", value="11999998888", confidence=0.9)
        ]

        goal_tracker.update_from_extractions(extractions)

        # Navigator should reflect the same data
        navigator.update_collected_data({
            "nome": "João",
            "telefone": "11999998888"
        })

        # Both should show progress
        progress = goal_tracker.get_progress()
        assert progress.completed >= 2

        context = navigator.get_current_context()
        assert "nome" in context.collected_data


class TestDataFlowIntegration:
    """Tests for data flow through the system."""

    def test_extraction_to_validation_to_scoring(self):
        """Data should flow: extraction -> validation -> scoring."""
        validator = DataValidator()
        scorer = LeadScorer()

        # Simulate extracted data (as would come from AI)
        extractions = [
            {"field": "nome", "value": "maria silva"},
            {"field": "email", "value": "maria@email.com"},
            {"field": "telefone", "value": "(11) 98765-4321"},
            {"field": "interesse", "value": "quero comprar um apartamento"},
            {"field": "urgencia", "value": "imediata"}
        ]

        # Validate each extraction
        validated_data = {}
        for ext in extractions:
            result = validator.validate(ext["field"], ext["value"])
            if result.is_valid:
                validated_data[ext["field"]] = result.cleaned_value

        # All should be valid
        assert len(validated_data) == 5

        # Score the validated data
        score = scorer.calculate_score(validated_data)

        # Should be warm or hot with this data
        assert score.temperature in [LeadTemperature.WARM, LeadTemperature.HOT]

    def test_flow_navigation_updates_context(self, flow_config):
        """Navigation through flow should update context correctly."""
        navigator = create_navigator(flow_config)

        # Start position
        context = navigator.get_current_context()
        assert context.current_position.current_node_type == "GREETING"

        # Advance and check
        navigator.evaluate_and_advance()
        context = navigator.get_current_context()
        assert context.current_position.current_node_type == "NOME"
        assert context.what_to_collect == "nome"

        # Add data and advance
        navigator.update_collected_data({"nome": "João"})
        navigator.evaluate_and_advance()
        context = navigator.get_current_context()
        assert context.current_position.current_node_type == "TELEFONE"


class TestScoreBasedDecisions:
    """Tests for score-based decision making."""

    def test_hot_lead_triggers_notification(self):
        """Hot lead should trigger notification."""
        scorer = LeadScorer()

        hot_data = {
            "nome": "João",
            "telefone": "11999998888",
            "email": "joao@email.com",
            "interesse": "Quero comprar um apartamento de alto padrão",
            "orcamento": "R$ 2.000.000",
            "urgencia": "imediata"
        }

        score = scorer.calculate_score(hot_data)

        # Should be hot with this data
        assert score.temperature == LeadTemperature.HOT
        assert score.total >= 80

        # Recommendations should include immediate contact
        recommendations_text = " ".join(score.recommendations).lower()
        assert "contato" in recommendations_text or "imediatamente" in recommendations_text

    def test_cold_lead_gets_nurturing_recommendations(self):
        """Cold lead should get nurturing recommendations."""
        scorer = LeadScorer()

        cold_data = {
            "nome": "Maria"
        }

        score = scorer.calculate_score(cold_data)

        assert score.temperature == LeadTemperature.COLD

        # Recommendations should include nurturing
        recommendations_text = " ".join(score.recommendations).lower()
        assert "nutrir" in recommendations_text or "follow" in recommendations_text or "coletar" in recommendations_text


class TestConditionBasedBranching:
    """Tests for condition-based flow branching."""

    def test_urgency_condition_routes_correctly(self, sample_condition_flow_config):
        """Urgency condition should route to correct path."""
        flow_config = FlowConfig(**sample_condition_flow_config)
        navigator = create_navigator(flow_config)

        # Advance to condition node
        navigator.evaluate_and_advance()  # greeting -> check_urgency
        assert navigator.current_node_id == "check_urgency"

        # Test urgent path
        navigator.update_collected_data({"urgencia": "imediata"})
        navigator.evaluate_and_advance()
        assert navigator.current_node_id == "urgent_path"

    def test_non_urgent_routes_to_normal(self, sample_condition_flow_config):
        """Non-urgent should route to normal path."""
        flow_config = FlowConfig(**sample_condition_flow_config)
        navigator = create_navigator(flow_config)

        navigator.evaluate_and_advance()  # greeting -> check_urgency
        navigator.update_collected_data({"urgencia": "sem pressa"})
        navigator.evaluate_and_advance()

        assert navigator.current_node_id == "normal_path"


class TestSwitchBasedBranching:
    """Tests for switch-based flow branching."""

    def test_switch_routes_to_high_value(self, sample_flow_config):
        """Switch should route high value to premium path."""
        flow_config = FlowConfig(**sample_flow_config)
        navigator = create_navigator(flow_config)

        # Navigate to switch node
        while navigator.current_node_id != "check_budget":
            navigator.evaluate_and_advance()

        # Set high budget
        navigator.update_collected_data({"orcamento": "alto"})
        navigator.evaluate_and_advance()

        assert navigator.current_node_id == "high_value_path"

    def test_switch_uses_default_for_unknown(self, sample_flow_config):
        """Switch should use default for unknown values."""
        flow_config = FlowConfig(**sample_flow_config)
        navigator = create_navigator(flow_config)

        while navigator.current_node_id != "check_budget":
            navigator.evaluate_and_advance()

        navigator.update_collected_data({"orcamento": "não informado"})
        navigator.evaluate_and_advance()

        assert navigator.current_node_id == "default_path"


class TestValidationErrorHandling:
    """Tests for validation error handling in flow."""

    def test_invalid_phone_caught(self):
        """Invalid phone should be caught by validator."""
        validator = DataValidator()

        result = validator.validate("telefone", "123")
        assert not result.is_valid
        assert "telefone" in result.error_message.lower() or "inválido" in result.error_message.lower()

    def test_invalid_email_caught(self):
        """Invalid email should be caught by validator."""
        validator = DataValidator()

        result = validator.validate("email", "not-an-email")
        assert not result.is_valid

    def test_valid_data_passes(self):
        """Valid data should pass validation."""
        validator = DataValidator()

        results = validator.validate_multiple({
            "nome": "João Silva",
            "email": "joao@email.com",
            "telefone": "11999998888"
        })

        errors = validator.get_all_errors(results)
        assert len(errors) == 0


class TestMemoryIntegration:
    """Tests for memory system integration."""

    def test_memory_tracks_collected_data(self, memory):
        """Memory should track collected data."""
        memory.update_collected_data("nome", "João")
        memory.update_collected_data("telefone", "11999998888")

        assert memory.collected_data["nome"] == "João"
        assert memory.collected_data["telefone"] == "11999998888"

    def test_goal_tracker_syncs_with_memory(self, flow_intent, memory):
        """GoalTracker should sync with memory."""
        # Pre-populate memory
        memory.update_collected_data("nome", "João")
        memory.update_collected_data("telefone", "11999998888")

        # Create tracker - should sync
        tracker = GoalTracker(flow_intent, memory)

        # Check that goals are marked as collected
        nome_goal = next((g for g in tracker.flow_intent.goals if g.field_name == "nome"), None)
        if nome_goal:
            assert nome_goal.collected
            assert nome_goal.value == "João"
