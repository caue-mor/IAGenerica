"""
Lead Scorer - Dynamic lead scoring system.

Classifies leads as Hot/Warm/Cold based on:
- Collected data completeness
- Response quality
- Engagement level
- Urgency indicators
- Behavioral signals

The scorer is configurable per company and adapts to different industries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum


class LeadTemperature(str, Enum):
    """Lead temperature classification."""
    HOT = "hot"       # 80-100 points - Ready to buy
    WARM = "warm"     # 50-79 points - Interested, needs nurturing
    COLD = "cold"     # 0-49 points - Low interest or incomplete data


class ScoreCategory(str, Enum):
    """Categories of scoring factors."""
    DATA_COMPLETENESS = "data_completeness"
    ENGAGEMENT = "engagement"
    URGENCY = "urgency"
    QUALIFICATION = "qualification"
    BEHAVIOR = "behavior"


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of score components."""
    category: ScoreCategory
    points: int
    max_points: int
    factors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "points": self.points,
            "max_points": self.max_points,
            "factors": self.factors,
            "percentage": round((self.points / self.max_points) * 100, 1) if self.max_points > 0 else 0
        }


@dataclass
class LeadScore:
    """Complete lead score with breakdown and analysis."""
    total: int
    max_possible: int = 100
    temperature: LeadTemperature = LeadTemperature.COLD
    breakdown: Dict[str, ScoreBreakdown] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    scoring_timestamp: datetime = field(default_factory=datetime.now)

    @property
    def percentage(self) -> float:
        """Score as percentage."""
        return round((self.total / self.max_possible) * 100, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "max_possible": self.max_possible,
            "percentage": self.percentage,
            "temperature": self.temperature.value,
            "breakdown": {k: v.to_dict() for k, v in self.breakdown.items()},
            "reasons": self.reasons,
            "recommendations": self.recommendations,
            "scoring_timestamp": self.scoring_timestamp.isoformat()
        }


@dataclass
class ConversationMetrics:
    """Metrics from conversation history."""
    total_messages: int = 0
    lead_messages: int = 0
    agent_messages: int = 0
    avg_response_time_seconds: float = 0
    total_duration_minutes: float = 0
    retries_per_field: Dict[str, int] = field(default_factory=dict)
    fields_collected_count: int = 0
    questions_asked_by_lead: int = 0
    sentiment_scores: List[str] = field(default_factory=list)  # positive, neutral, negative


class LeadScorer:
    """
    Dynamic lead scoring system.

    Calculates scores based on multiple factors:
    1. Data completeness (fields collected)
    2. Engagement (response behavior)
    3. Urgency indicators
    4. Qualification signals
    5. Behavioral patterns
    """

    # Default weights for each collected field
    DEFAULT_FIELD_WEIGHTS = {
        "nome": 10,
        "telefone": 15,
        "email": 10,
        "cidade": 5,
        "interesse": 20,
        "orcamento": 25,
        "urgencia": 15,
        "cep": 5,
        "endereco": 5,
        "cpf": 5,
        "data_nascimento": 3,
        "produto": 10,
        "modelo": 8,
    }

    # Bonus rules that add points
    BONUS_RULES = {
        "urgencia_imediata": {
            "points": 15,
            "condition": lambda data: data.get("urgencia", "").lower() in ["imediata", "urgente", "imediato", "agora", "hoje"]
        },
        "orcamento_alto": {
            "points": 10,
            "condition": lambda data: LeadScorer._parse_budget(data.get("orcamento", "")) > 50000
        },
        "orcamento_medio": {
            "points": 5,
            "condition": lambda data: 10000 <= LeadScorer._parse_budget(data.get("orcamento", "")) <= 50000
        },
        "interesse_especifico": {
            "points": 8,
            "condition": lambda data: len(data.get("interesse", "")) > 20
        },
        "contato_completo": {
            "points": 10,
            "condition": lambda data: data.get("telefone") and data.get("email")
        },
        "identificacao_completa": {
            "points": 5,
            "condition": lambda data: data.get("nome") and data.get("cpf")
        },
        "localizacao_completa": {
            "points": 5,
            "condition": lambda data: data.get("cidade") and (data.get("cep") or data.get("endereco"))
        },
    }

    # Penalty rules that subtract points
    PENALTY_RULES = {
        "muitos_retries": {
            "points": -10,
            "condition": lambda data, metrics: max(metrics.retries_per_field.values()) > 3 if metrics.retries_per_field else False
        },
        "respostas_muito_curtas": {
            "points": -5,
            "condition": lambda data, metrics: metrics.lead_messages > 0 and metrics.avg_response_time_seconds < 2
        },
        "demora_responder": {
            "points": -5,
            "condition": lambda data, metrics: metrics.avg_response_time_seconds > 300  # > 5 min
        },
        "conversa_muito_longa": {
            "points": -5,
            "condition": lambda data, metrics: metrics.total_duration_minutes > 60  # > 1 hour
        },
        "sentimento_negativo": {
            "points": -10,
            "condition": lambda data, metrics: "negative" in metrics.sentiment_scores
        },
    }

    # Engagement bonuses based on conversation metrics
    ENGAGEMENT_BONUSES = {
        "resposta_rapida": {
            "points": 5,
            "condition": lambda metrics: metrics.avg_response_time_seconds < 60
        },
        "multiplas_perguntas": {
            "points": 5,
            "condition": lambda metrics: metrics.questions_asked_by_lead >= 2
        },
        "conversa_engajada": {
            "points": 5,
            "condition": lambda metrics: metrics.lead_messages >= 5
        },
        "todas_respostas": {
            "points": 5,
            "condition": lambda metrics: metrics.fields_collected_count >= 5
        },
    }

    # Urgency keywords and their scores
    URGENCY_KEYWORDS = {
        "imediata": 20,
        "urgente": 20,
        "imediato": 20,
        "agora": 18,
        "hoje": 18,
        "amanha": 15,
        "amanhã": 15,
        "esta semana": 12,
        "essa semana": 12,
        "esse mes": 8,
        "este mês": 8,
        "proximo mes": 5,
        "próximo mês": 5,
        "pesquisando": 2,
        "sem pressa": 1,
    }

    def __init__(self, company_weights: Dict[str, int] = None):
        """
        Initialize the scorer.

        Args:
            company_weights: Custom field weights for this company
        """
        self.field_weights = company_weights or self.DEFAULT_FIELD_WEIGHTS.copy()

    def calculate_score(
        self,
        collected_data: Dict[str, Any],
        conversation_metrics: ConversationMetrics = None,
        custom_bonuses: Dict[str, int] = None
    ) -> LeadScore:
        """
        Calculate comprehensive lead score.

        Args:
            collected_data: Dictionary of collected field data
            conversation_metrics: Metrics from the conversation
            custom_bonuses: Additional custom bonuses

        Returns:
            LeadScore with full breakdown
        """
        metrics = conversation_metrics or ConversationMetrics()

        # Calculate each category
        data_score = self._calculate_data_score(collected_data)
        engagement_score = self._calculate_engagement_score(metrics)
        urgency_score = self._calculate_urgency_score(collected_data)
        qualification_score = self._calculate_qualification_score(collected_data)
        behavior_score = self._calculate_behavior_score(collected_data, metrics)

        # Apply custom bonuses
        custom_points = sum(custom_bonuses.values()) if custom_bonuses else 0

        # Calculate total
        total = (
            data_score.points +
            engagement_score.points +
            urgency_score.points +
            qualification_score.points +
            behavior_score.points +
            custom_points
        )

        # Clamp to 0-100
        total = max(0, min(100, total))

        # Determine temperature
        temperature = self._get_temperature(total)

        # Build reasons
        reasons = self._build_reasons(
            collected_data,
            metrics,
            data_score,
            engagement_score,
            urgency_score,
            qualification_score,
            behavior_score
        )

        # Build recommendations
        recommendations = self._build_recommendations(
            total,
            temperature,
            collected_data,
            data_score,
            urgency_score
        )

        return LeadScore(
            total=total,
            temperature=temperature,
            breakdown={
                ScoreCategory.DATA_COMPLETENESS.value: data_score,
                ScoreCategory.ENGAGEMENT.value: engagement_score,
                ScoreCategory.URGENCY.value: urgency_score,
                ScoreCategory.QUALIFICATION.value: qualification_score,
                ScoreCategory.BEHAVIOR.value: behavior_score,
            },
            reasons=reasons,
            recommendations=recommendations
        )

    def _calculate_data_score(self, data: Dict[str, Any]) -> ScoreBreakdown:
        """Calculate score from collected data."""
        points = 0
        factors = []
        max_points = sum(self.field_weights.values())

        for field, weight in self.field_weights.items():
            if field in data and data[field]:
                points += weight
                factors.append(f"{field}: +{weight}")

        return ScoreBreakdown(
            category=ScoreCategory.DATA_COMPLETENESS,
            points=min(points, 50),  # Cap at 50 for data alone
            max_points=50,
            factors=factors
        )

    def _calculate_engagement_score(self, metrics: ConversationMetrics) -> ScoreBreakdown:
        """Calculate score from engagement metrics."""
        points = 0
        factors = []

        for name, rule in self.ENGAGEMENT_BONUSES.items():
            try:
                if rule["condition"](metrics):
                    points += rule["points"]
                    factors.append(f"{name}: +{rule['points']}")
            except Exception:
                pass

        return ScoreBreakdown(
            category=ScoreCategory.ENGAGEMENT,
            points=min(points, 20),  # Cap at 20
            max_points=20,
            factors=factors
        )

    def _calculate_urgency_score(self, data: Dict[str, Any]) -> ScoreBreakdown:
        """Calculate score from urgency indicators."""
        points = 0
        factors = []

        urgency = str(data.get("urgencia", "")).lower()

        # Check urgency keywords
        for keyword, score in self.URGENCY_KEYWORDS.items():
            if keyword in urgency:
                points = max(points, score)
                factors.append(f"urgencia '{keyword}': +{score}")
                break

        # Also check interest field for urgency indicators
        interesse = str(data.get("interesse", "")).lower()
        urgency_words = ["urgente", "preciso", "rapido", "rápido", "imediato"]
        for word in urgency_words:
            if word in interesse:
                points += 5
                factors.append(f"interesse indica urgência: +5")
                break

        return ScoreBreakdown(
            category=ScoreCategory.URGENCY,
            points=min(points, 20),  # Cap at 20
            max_points=20,
            factors=factors
        )

    def _calculate_qualification_score(self, data: Dict[str, Any]) -> ScoreBreakdown:
        """Calculate score from qualification bonuses."""
        points = 0
        factors = []

        for name, rule in self.BONUS_RULES.items():
            try:
                if rule["condition"](data):
                    points += rule["points"]
                    factors.append(f"{name}: +{rule['points']}")
            except Exception:
                pass

        return ScoreBreakdown(
            category=ScoreCategory.QUALIFICATION,
            points=max(0, min(points, 30)),  # Cap at 30
            max_points=30,
            factors=factors
        )

    def _calculate_behavior_score(
        self,
        data: Dict[str, Any],
        metrics: ConversationMetrics
    ) -> ScoreBreakdown:
        """Calculate score from behavioral patterns (including penalties)."""
        points = 0
        factors = []

        # Apply penalties
        for name, rule in self.PENALTY_RULES.items():
            try:
                if rule["condition"](data, metrics):
                    points += rule["points"]  # Negative
                    factors.append(f"{name}: {rule['points']}")
            except Exception:
                pass

        # Base behavior score (neutral start)
        base_points = 10
        points += base_points

        return ScoreBreakdown(
            category=ScoreCategory.BEHAVIOR,
            points=max(-10, min(points, 10)),  # Range: -10 to 10
            max_points=10,
            factors=factors if factors else ["comportamento neutro: +10"]
        )

    def _get_temperature(self, score: int) -> LeadTemperature:
        """Get temperature classification from score."""
        if score >= 80:
            return LeadTemperature.HOT
        elif score >= 50:
            return LeadTemperature.WARM
        return LeadTemperature.COLD

    def _build_reasons(
        self,
        data: Dict[str, Any],
        metrics: ConversationMetrics,
        *breakdowns: ScoreBreakdown
    ) -> List[str]:
        """Build human-readable reasons for the score."""
        reasons = []

        # Data completeness
        data_fields = [k for k, v in data.items() if v]
        if len(data_fields) >= 5:
            reasons.append(f"Dados completos ({len(data_fields)} campos coletados)")
        elif len(data_fields) >= 3:
            reasons.append(f"Dados parciais ({len(data_fields)} campos coletados)")
        else:
            reasons.append(f"Poucos dados coletados ({len(data_fields)} campos)")

        # Contact info
        if data.get("telefone") and data.get("email"):
            reasons.append("Contato completo (telefone e email)")
        elif data.get("telefone"):
            reasons.append("Telefone informado")
        elif data.get("email"):
            reasons.append("Email informado")

        # Urgency
        urgency = str(data.get("urgencia", "")).lower()
        if any(kw in urgency for kw in ["imediata", "urgente", "imediato"]):
            reasons.append("Urgência alta")
        elif any(kw in urgency for kw in ["semana", "esta"]):
            reasons.append("Urgência média")

        # Budget
        budget = self._parse_budget(data.get("orcamento", ""))
        if budget > 50000:
            reasons.append(f"Orçamento alto (R$ {budget:,.0f})")
        elif budget > 10000:
            reasons.append(f"Orçamento médio (R$ {budget:,.0f})")

        # Engagement
        if metrics.questions_asked_by_lead >= 2:
            reasons.append("Lead fez perguntas (engajamento alto)")

        return reasons

    def _build_recommendations(
        self,
        total: int,
        temperature: LeadTemperature,
        data: Dict[str, Any],
        data_score: ScoreBreakdown,
        urgency_score: ScoreBreakdown
    ) -> List[str]:
        """Build recommendations based on score."""
        recommendations = []

        if temperature == LeadTemperature.HOT:
            recommendations.append("Entrar em contato imediatamente")
            recommendations.append("Preparar proposta personalizada")
        elif temperature == LeadTemperature.WARM:
            recommendations.append("Enviar mais informações")
            if not data.get("email"):
                recommendations.append("Tentar coletar email para follow-up")
            recommendations.append("Agendar follow-up em 24h")
        else:
            recommendations.append("Nutrir com conteúdo educativo")
            recommendations.append("Agendar follow-up em 3-5 dias")

        # Missing data recommendations
        missing = []
        if not data.get("telefone"):
            missing.append("telefone")
        if not data.get("email"):
            missing.append("email")
        if not data.get("orcamento"):
            missing.append("orçamento")

        if missing:
            recommendations.append(f"Coletar: {', '.join(missing)}")

        return recommendations

    @staticmethod
    def _parse_budget(value: Any) -> float:
        """Parse budget value to float."""
        if not value:
            return 0

        import re
        str_value = str(value)

        # Remove currency symbols and common text
        cleaned = re.sub(r'[R$\s,.]', '', str_value)
        cleaned = re.sub(r'(mil|reais|k|K)', '', cleaned)

        # Try to parse
        try:
            number = float(cleaned)
            # If original had 'mil' or 'k', multiply
            if 'mil' in str_value.lower() or 'k' in str_value.lower():
                number *= 1000
            return number
        except ValueError:
            return 0

    def quick_score(self, collected_data: Dict[str, Any]) -> tuple[int, LeadTemperature]:
        """
        Quick scoring without full breakdown.

        Args:
            collected_data: Dictionary of collected fields

        Returns:
            Tuple of (score, temperature)
        """
        score = self.calculate_score(collected_data, ConversationMetrics())
        return score.total, score.temperature


# Singleton instance
lead_scorer = LeadScorer()


def calculate_lead_score(
    collected_data: Dict[str, Any],
    conversation_metrics: ConversationMetrics = None,
    company_weights: Dict[str, int] = None
) -> LeadScore:
    """
    Convenience function to calculate lead score.

    Args:
        collected_data: Dictionary of collected data
        conversation_metrics: Optional conversation metrics
        company_weights: Optional custom weights

    Returns:
        LeadScore with full breakdown
    """
    scorer = LeadScorer(company_weights) if company_weights else lead_scorer
    return scorer.calculate_score(collected_data, conversation_metrics)


def get_lead_temperature(collected_data: Dict[str, Any]) -> LeadTemperature:
    """
    Get lead temperature from collected data.

    Args:
        collected_data: Dictionary of collected data

    Returns:
        LeadTemperature (HOT, WARM, or COLD)
    """
    _, temperature = lead_scorer.quick_score(collected_data)
    return temperature
