"""
Unit tests for FlowGraphNavigator.
"""
import pytest
from src.agent.flow_navigator import (
    FlowGraphNavigator, FlowPosition, FlowPath,
    FlowContext, FlowPathType, ConditionEvaluator,
    create_navigator
)
from src.models.flow import FlowConfig


@pytest.fixture
def navigator(sample_flow_config):
    """Create a FlowGraphNavigator instance."""
    flow_config = FlowConfig(**sample_flow_config)
    return FlowGraphNavigator(flow_config)


@pytest.fixture
def condition_navigator(sample_condition_flow_config):
    """Create a FlowGraphNavigator with condition nodes."""
    flow_config = FlowConfig(**sample_condition_flow_config)
    return FlowGraphNavigator(flow_config)


class TestNavigatorInitialization:
    """Tests for navigator initialization."""

    def test_navigator_created(self, navigator):
        """Navigator should be created successfully."""
        assert navigator is not None
        assert navigator.current_node_id is not None

    def test_starts_at_start_node(self, navigator):
        """Navigator should start at the start node."""
        assert navigator.current_node_id == "greeting"

    def test_nodes_indexed_by_id(self, navigator):
        """All nodes should be indexed by ID."""
        assert "greeting" in navigator.nodes_by_id
        assert "ask_name" in navigator.nodes_by_id
        assert "check_budget" in navigator.nodes_by_id


class TestCurrentPosition:
    """Tests for getting current position."""

    def test_get_current_position(self, navigator):
        """Should return current position."""
        position = navigator.get_current_position()
        assert position is not None
        assert position.current_node_id == "greeting"
        assert position.current_node_type == "GREETING"

    def test_position_has_available_paths(self, navigator):
        """Position should list available paths."""
        position = navigator.get_current_position()
        assert len(position.available_paths) > 0
        assert position.available_paths[0].target_node_id == "ask_name"

    def test_data_collection_node_identified(self, navigator):
        """Data collection nodes should be identified."""
        # Move to ask_name node
        navigator.current_node_id = "ask_name"
        position = navigator.get_current_position()

        assert position.requires_data_collection
        assert position.data_field == "nome"


class TestFlowContext:
    """Tests for flow context generation."""

    def test_get_context(self, navigator):
        """Should return complete flow context."""
        context = navigator.get_current_context()
        assert context is not None
        assert context.current_position is not None

    def test_context_includes_collected_data(self, navigator):
        """Context should include collected data."""
        navigator.collected_data = {"nome": "João"}
        context = navigator.get_current_context()

        assert "nome" in context.collected_data
        assert context.collected_data["nome"] == "João"

    def test_context_indicates_what_to_collect(self, navigator):
        """Context should indicate what to collect for data nodes."""
        navigator.current_node_id = "ask_name"
        context = navigator.get_current_context()

        assert context.what_to_collect == "nome"


class TestConditionEvaluation:
    """Tests for condition evaluation."""

    def test_equals_true(self):
        """Equals operator should work correctly."""
        evaluator = ConditionEvaluator()
        from src.agent.flow_navigator import FlowCondition

        condition = FlowCondition(
            field="interesse",
            operator="equals",
            value="comprar"
        )
        result = evaluator.evaluate(condition, {"interesse": "comprar"})
        assert result is True

    def test_equals_case_insensitive(self):
        """Equals should be case insensitive."""
        evaluator = ConditionEvaluator()
        from src.agent.flow_navigator import FlowCondition

        condition = FlowCondition(
            field="interesse",
            operator="equals",
            value="COMPRAR"
        )
        result = evaluator.evaluate(condition, {"interesse": "comprar"})
        assert result is True

    def test_contains_true(self):
        """Contains operator should work correctly."""
        evaluator = ConditionEvaluator()
        from src.agent.flow_navigator import FlowCondition

        condition = FlowCondition(
            field="interesse",
            operator="contains",
            value="apartamento"
        )
        result = evaluator.evaluate(condition, {"interesse": "quero comprar um apartamento"})
        assert result is True

    def test_greater_than(self):
        """Greater than operator should work with numbers."""
        evaluator = ConditionEvaluator()
        from src.agent.flow_navigator import FlowCondition

        condition = FlowCondition(
            field="orcamento",
            operator="greater_than",
            value="50000"
        )
        result = evaluator.evaluate(condition, {"orcamento": "100000"})
        assert result is True

    def test_is_empty_true(self):
        """Is empty should detect empty values."""
        evaluator = ConditionEvaluator()
        from src.agent.flow_navigator import FlowCondition

        condition = FlowCondition(
            field="email",
            operator="is_empty",
            value=None
        )
        result = evaluator.evaluate(condition, {"email": ""})
        assert result is True

    def test_is_not_empty(self):
        """Is not empty should detect non-empty values."""
        evaluator = ConditionEvaluator()
        from src.agent.flow_navigator import FlowCondition

        condition = FlowCondition(
            field="nome",
            operator="is_not_empty",
            value=None
        )
        result = evaluator.evaluate(condition, {"nome": "João"})
        assert result is True


class TestConditionNavigation:
    """Tests for CONDITION node navigation."""

    def test_condition_true_path(self, condition_navigator):
        """Should take true path when condition is met."""
        condition_navigator.collected_data = {"urgencia": "imediata"}
        condition_navigator.current_node_id = "check_urgency"

        new_position = condition_navigator.evaluate_and_advance()

        assert new_position is not None
        assert new_position.current_node_id == "urgent_path"

    def test_condition_false_path(self, condition_navigator):
        """Should take false path when condition is not met."""
        condition_navigator.collected_data = {"urgencia": "sem pressa"}
        condition_navigator.current_node_id = "check_urgency"

        new_position = condition_navigator.evaluate_and_advance()

        assert new_position is not None
        assert new_position.current_node_id == "normal_path"


class TestSwitchNavigation:
    """Tests for SWITCH node navigation."""

    def test_switch_matches_case(self, navigator):
        """Should match switch case correctly."""
        navigator.collected_data = {"orcamento": "alto"}
        navigator.current_node_id = "check_budget"

        new_position = navigator.evaluate_and_advance()

        assert new_position is not None
        assert new_position.current_node_id == "high_value_path"

    def test_switch_default_case(self, navigator):
        """Should use default when no case matches."""
        navigator.collected_data = {"orcamento": "outro valor"}
        navigator.current_node_id = "check_budget"

        new_position = navigator.evaluate_and_advance()

        assert new_position is not None
        assert new_position.current_node_id == "default_path"


class TestSequentialNavigation:
    """Tests for sequential flow navigation."""

    def test_advance_sequential(self, navigator):
        """Should advance through sequential nodes."""
        # Start at greeting
        assert navigator.current_node_id == "greeting"

        # Advance to ask_name
        new_pos = navigator.evaluate_and_advance()
        assert new_pos.current_node_id == "ask_name"

    def test_visit_tracking(self, navigator):
        """Visited nodes should be tracked."""
        navigator.evaluate_and_advance()

        assert "greeting" in navigator.visited_nodes


class TestDataUpdates:
    """Tests for data updates."""

    def test_update_collected_data(self, navigator):
        """Should update collected data."""
        navigator.update_collected_data({"nome": "João"})
        assert navigator.collected_data["nome"] == "João"

    def test_multiple_updates(self, navigator):
        """Should merge multiple updates."""
        navigator.update_collected_data({"nome": "João"})
        navigator.update_collected_data({"telefone": "11999998888"})

        assert navigator.collected_data["nome"] == "João"
        assert navigator.collected_data["telefone"] == "11999998888"


class TestTerminalNodes:
    """Tests for terminal node detection."""

    def test_end_node_is_terminal(self, navigator):
        """END nodes should be terminal."""
        navigator.current_node_id = "end"
        position = navigator.get_current_position()

        assert position.is_terminal

    def test_handoff_has_no_next(self, navigator):
        """HANDOFF nodes should be terminal (no next_node_id)."""
        navigator.current_node_id = "high_value_path"
        position = navigator.get_current_position()

        # HANDOFF typically has no next node
        assert len(position.available_paths) == 0 or position.is_terminal


class TestCompletion:
    """Tests for flow completion."""

    def test_is_complete_at_end(self, navigator):
        """Should be complete at END node."""
        navigator.current_node_id = "end"
        assert navigator.is_complete()

    def test_not_complete_mid_flow(self, navigator):
        """Should not be complete mid-flow."""
        navigator.current_node_id = "ask_name"
        assert not navigator.is_complete()

    def test_completion_percentage(self, navigator):
        """Completion percentage should increase with visits."""
        initial = navigator.get_completion_percentage()

        navigator.evaluate_and_advance()
        navigator.evaluate_and_advance()

        after = navigator.get_completion_percentage()
        assert after > initial


class TestDataFieldListing:
    """Tests for listing data fields."""

    def test_get_all_data_fields(self, navigator):
        """Should list all data collection fields."""
        fields = navigator.get_all_data_fields()

        assert "nome" in fields
        assert "telefone" in fields
        assert "interesse" in fields


class TestPromptFormatting:
    """Tests for prompt formatting."""

    def test_format_context_for_prompt(self, navigator):
        """Should format context for AI prompt."""
        formatted = navigator.format_context_for_prompt()

        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "Posição Atual" in formatted


class TestSerialization:
    """Tests for state serialization."""

    def test_to_dict(self, navigator):
        """Should serialize to dict."""
        navigator.update_collected_data({"nome": "João"})
        navigator.evaluate_and_advance()

        state = navigator.to_dict()

        assert "current_node_id" in state
        assert "visited_nodes" in state
        assert "collected_data" in state

    def test_from_dict(self, sample_flow_config):
        """Should restore from dict."""
        flow_config = FlowConfig(**sample_flow_config)

        state = {
            "current_node_id": "ask_phone",
            "visited_nodes": ["greeting", "ask_name"],
            "collected_data": {"nome": "João"},
            "pending_parallel_paths": []
        }

        restored = FlowGraphNavigator.from_dict(flow_config, state)

        assert restored.current_node_id == "ask_phone"
        assert "greeting" in restored.visited_nodes
        assert restored.collected_data["nome"] == "João"


class TestFactoryFunction:
    """Tests for factory function."""

    def test_create_navigator(self, sample_flow_config):
        """create_navigator should work."""
        flow_config = FlowConfig(**sample_flow_config)
        nav = create_navigator(flow_config)

        assert nav is not None
        assert nav.current_node_id == "greeting"

    def test_create_with_initial_data(self, sample_flow_config):
        """create_navigator with initial data should work."""
        flow_config = FlowConfig(**sample_flow_config)
        nav = create_navigator(flow_config, {"nome": "João"})

        assert nav.collected_data["nome"] == "João"


class TestPathTypes:
    """Tests for different path types."""

    def test_sequential_path_type(self, navigator):
        """Sequential paths should have correct type."""
        position = navigator.get_current_position()

        sequential_paths = [p for p in position.available_paths
                          if p.path_type == FlowPathType.SEQUENTIAL]
        assert len(sequential_paths) > 0

    def test_condition_path_types(self, condition_navigator):
        """Condition paths should have true/false types."""
        condition_navigator.current_node_id = "check_urgency"
        position = condition_navigator.get_current_position()

        true_paths = [p for p in position.available_paths
                     if p.path_type == FlowPathType.CONDITION_TRUE]
        false_paths = [p for p in position.available_paths
                      if p.path_type == FlowPathType.CONDITION_FALSE]

        assert len(true_paths) > 0
        assert len(false_paths) > 0

    def test_switch_path_types(self, navigator):
        """Switch paths should have case types."""
        navigator.current_node_id = "check_budget"
        position = navigator.get_current_position()

        case_paths = [p for p in position.available_paths
                     if p.path_type == FlowPathType.SWITCH_CASE]
        default_paths = [p for p in position.available_paths
                        if p.path_type == FlowPathType.SWITCH_DEFAULT]

        assert len(case_paths) > 0
        assert len(default_paths) > 0
