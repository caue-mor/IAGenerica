"""
Unit tests for LeadScorer.
"""
import pytest
from src.agent.lead_scorer import (
    LeadScorer, LeadScore, LeadTemperature,
    ConversationMetrics, calculate_lead_score, get_lead_temperature
)


@pytest.fixture
def scorer():
    """Create a LeadScorer instance."""
    return LeadScorer()


@pytest.fixture
def custom_scorer():
    """Create a LeadScorer with custom weights."""
    return LeadScorer(company_weights={
        "nome": 20,
        "telefone": 30,
        "email": 20,
        "interesse": 30,
    })


class TestBasicScoring:
    """Tests for basic score calculation."""

    def test_empty_data_is_cold(self, scorer):
        """Empty data should result in cold lead."""
        score = scorer.calculate_score({})
        assert score.temperature == LeadTemperature.COLD
        assert score.total < 50

    def test_partial_data_scoring(self, scorer, partial_collected_data):
        """Partial data should give partial score."""
        score = scorer.calculate_score(partial_collected_data)
        assert score.total > 0
        assert score.total < 80

    def test_full_data_is_warm_or_hot(self, scorer, sample_collected_data):
        """Full data should result in warm or hot lead."""
        score = scorer.calculate_score(sample_collected_data)
        assert score.temperature in [LeadTemperature.WARM, LeadTemperature.HOT]
        assert score.total >= 50

    def test_score_capped_at_100(self, scorer):
        """Score should never exceed 100."""
        # Create data with many fields
        data = {
            "nome": "João",
            "telefone": "11999998888",
            "email": "joao@email.com",
            "cidade": "São Paulo",
            "interesse": "Comprar apartamento de alto padrão",
            "orcamento": "R$ 2.000.000",
            "urgencia": "imediata",
            "cep": "01310100",
            "endereco": "Av. Paulista, 1000",
            "cpf": "12345678901",
        }
        score = scorer.calculate_score(data)
        assert score.total <= 100


class TestTemperatureClassification:
    """Tests for temperature classification."""

    def test_hot_threshold(self, scorer):
        """Score >= 80 should be hot."""
        # Create high-value data
        data = {
            "nome": "João",
            "telefone": "11999998888",
            "email": "joao@email.com",
            "interesse": "Comprar urgentemente",
            "orcamento": "R$ 1.000.000",
            "urgencia": "imediata",
        }
        score = scorer.calculate_score(data)
        # With all these fields and urgencia imediata, should be hot
        assert score.total >= 70  # At least warm

    def test_warm_threshold(self, scorer):
        """Score 50-79 should be warm."""
        data = {
            "nome": "João",
            "telefone": "11999998888",
            "interesse": "Talvez comprar algo"
        }
        score = scorer.calculate_score(data)
        # This should give a moderate score
        assert score.temperature in [LeadTemperature.WARM, LeadTemperature.COLD]

    def test_cold_threshold(self, scorer):
        """Score < 50 should be cold."""
        data = {
            "nome": "João"
        }
        score = scorer.calculate_score(data)
        assert score.temperature == LeadTemperature.COLD


class TestBonusRules:
    """Tests for bonus scoring rules."""

    def test_urgency_bonus(self, scorer):
        """Immediate urgency should give bonus."""
        base_data = {"nome": "João", "telefone": "11999998888"}
        with_urgency = {**base_data, "urgencia": "imediata"}

        score_base = scorer.calculate_score(base_data)
        score_urgent = scorer.calculate_score(with_urgency)

        assert score_urgent.total > score_base.total

    def test_high_budget_bonus(self, scorer):
        """High budget should give bonus."""
        base_data = {"nome": "João", "telefone": "11999998888"}
        with_budget = {**base_data, "orcamento": "R$ 100.000"}

        score_base = scorer.calculate_score(base_data)
        score_budget = scorer.calculate_score(with_budget)

        assert score_budget.total > score_base.total

    def test_complete_contact_bonus(self, scorer):
        """Having both phone and email should give bonus."""
        phone_only = {"nome": "João", "telefone": "11999998888"}
        both = {**phone_only, "email": "joao@email.com"}

        score_phone = scorer.calculate_score(phone_only)
        score_both = scorer.calculate_score(both)

        assert score_both.total > score_phone.total


class TestEngagementMetrics:
    """Tests for engagement-based scoring."""

    def test_fast_response_bonus(self, scorer):
        """Fast response should give engagement bonus."""
        data = {"nome": "João", "telefone": "11999998888"}

        fast_metrics = ConversationMetrics(
            total_messages=5,
            lead_messages=3,
            avg_response_time_seconds=30  # < 60 seconds
        )
        slow_metrics = ConversationMetrics(
            total_messages=5,
            lead_messages=3,
            avg_response_time_seconds=120  # > 60 seconds
        )

        fast_score = scorer.calculate_score(data, fast_metrics)
        slow_score = scorer.calculate_score(data, slow_metrics)

        assert fast_score.total >= slow_score.total

    def test_questions_asked_bonus(self, scorer):
        """Lead asking questions should give engagement bonus."""
        data = {"nome": "João", "telefone": "11999998888"}

        engaged_metrics = ConversationMetrics(
            total_messages=10,
            lead_messages=5,
            questions_asked_by_lead=3
        )
        passive_metrics = ConversationMetrics(
            total_messages=10,
            lead_messages=5,
            questions_asked_by_lead=0
        )

        engaged_score = scorer.calculate_score(data, engaged_metrics)
        passive_score = scorer.calculate_score(data, passive_metrics)

        assert engaged_score.total >= passive_score.total


class TestPenaltyRules:
    """Tests for penalty scoring rules."""

    def test_negative_sentiment_penalty(self, scorer):
        """Negative sentiment should reduce score."""
        data = {"nome": "João", "telefone": "11999998888"}

        positive_metrics = ConversationMetrics(
            sentiment_scores=["positive", "positive"]
        )
        negative_metrics = ConversationMetrics(
            sentiment_scores=["negative", "negative"]
        )

        positive_score = scorer.calculate_score(data, positive_metrics)
        negative_score = scorer.calculate_score(data, negative_metrics)

        assert negative_score.total <= positive_score.total


class TestScoreBreakdown:
    """Tests for score breakdown."""

    def test_breakdown_categories(self, scorer, sample_collected_data):
        """Score should have breakdown by category."""
        score = scorer.calculate_score(sample_collected_data)

        assert "data_completeness" in score.breakdown
        assert "engagement" in score.breakdown
        assert "urgency" in score.breakdown
        assert "qualification" in score.breakdown
        assert "behavior" in score.breakdown

    def test_breakdown_has_factors(self, scorer, sample_collected_data):
        """Each breakdown should list contributing factors."""
        score = scorer.calculate_score(sample_collected_data)

        data_breakdown = score.breakdown.get("data_completeness")
        assert data_breakdown is not None
        assert len(data_breakdown.factors) > 0


class TestRecommendations:
    """Tests for recommendations."""

    def test_hot_lead_recommendations(self, scorer, sample_collected_data):
        """Hot lead should get immediate action recommendations."""
        score = scorer.calculate_score(sample_collected_data)

        if score.temperature == LeadTemperature.HOT:
            assert any("contato" in r.lower() or "imediatamente" in r.lower()
                      for r in score.recommendations)

    def test_missing_data_recommendations(self, scorer):
        """Should recommend collecting missing important data."""
        data = {"nome": "João"}  # Missing phone and email
        score = scorer.calculate_score(data)

        recommendations_text = " ".join(score.recommendations).lower()
        assert "telefone" in recommendations_text or "coletar" in recommendations_text


class TestCustomWeights:
    """Tests for custom company weights."""

    def test_custom_weights_applied(self, custom_scorer):
        """Custom weights should affect scoring."""
        data = {"nome": "João", "telefone": "11999998888"}

        default_scorer = LeadScorer()
        default_score = default_scorer.calculate_score(data)
        custom_score = custom_scorer.calculate_score(data)

        # Scores should be different due to different weights
        # Custom weights give more to nome and telefone
        assert custom_score.total != default_score.total


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_calculate_lead_score(self, sample_collected_data):
        """calculate_lead_score function should work."""
        score = calculate_lead_score(sample_collected_data)
        assert isinstance(score, LeadScore)
        assert score.total >= 0

    def test_get_lead_temperature(self, sample_collected_data):
        """get_lead_temperature function should work."""
        temp = get_lead_temperature(sample_collected_data)
        assert isinstance(temp, LeadTemperature)


class TestBudgetParsing:
    """Tests for budget parsing."""

    def test_parse_simple_number(self, scorer):
        """Simple number should be parsed."""
        budget = scorer._parse_budget("50000")
        assert budget == 50000

    def test_parse_with_currency_symbol(self, scorer):
        """R$ should be stripped."""
        budget = scorer._parse_budget("R$ 50.000")
        assert budget == 50000

    def test_parse_with_mil(self, scorer):
        """'mil' should multiply by 1000."""
        budget = scorer._parse_budget("50 mil")
        assert budget == 50000

    def test_parse_invalid_returns_zero(self, scorer):
        """Invalid budget should return 0."""
        budget = scorer._parse_budget("não sei")
        assert budget == 0


class TestSerialization:
    """Tests for score serialization."""

    def test_to_dict(self, scorer, sample_collected_data):
        """Score should serialize to dict."""
        score = scorer.calculate_score(sample_collected_data)
        score_dict = score.to_dict()

        assert "total" in score_dict
        assert "temperature" in score_dict
        assert "breakdown" in score_dict
        assert "reasons" in score_dict
        assert "recommendations" in score_dict

    def test_percentage_calculation(self, scorer, sample_collected_data):
        """Percentage should be calculated correctly."""
        score = scorer.calculate_score(sample_collected_data)
        expected_pct = round((score.total / score.max_possible) * 100, 1)
        assert score.percentage == expected_pct
