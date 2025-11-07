"""
Tests for ScoringEngine and ScoringConfig.

Tests scoring algorithms, component calculations, configuration validation,
and score explanations.
"""

import warnings
from datetime import datetime, timedelta

import pytest

from axon.core.scoring import ScoringConfig, ScoringEngine
from axon.models.entry import MemoryEntry


def create_test_entry(
    content: str = "test content",
    importance: float = 0.5,
    access_count: int = 0,
    last_accessed: datetime = None,
    created_at: datetime = None,
) -> MemoryEntry:
    """Helper to create test memory entries."""
    if created_at is None:
        created_at = datetime.now()

    metadata_dict = {"importance": importance}

    if access_count > 0:
        metadata_dict["access_count"] = access_count

    if last_accessed is not None:
        metadata_dict["last_accessed_at"] = last_accessed  # Use correct field name

    if created_at is not None:
        metadata_dict["created_at"] = created_at

    entry = MemoryEntry(text=content, metadata=metadata_dict)

    return entry


class TestScoringConfig:
    """Test ScoringConfig validation and defaults."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ScoringConfig()

        # Check promotion weights sum to ~1.0
        promo_sum = (
            config.promotion_frequency_weight
            + config.promotion_importance_weight
            + config.promotion_recency_weight
            + config.promotion_velocity_weight
        )
        assert abs(promo_sum - 1.0) < 0.01

        # Check demotion weights sum to ~1.0
        demo_sum = (
            config.demotion_decay_weight
            + config.demotion_importance_weight
            + config.demotion_capacity_weight
            + config.demotion_staleness_weight
        )
        assert abs(demo_sum - 1.0) < 0.01

        # Check threshold ranges
        assert 0.0 <= config.promotion_threshold <= 1.0
        assert 0.0 <= config.demotion_threshold <= 1.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = ScoringConfig(
            promotion_frequency_weight=0.4,
            promotion_importance_weight=0.3,
            promotion_recency_weight=0.2,
            promotion_velocity_weight=0.1,
            promotion_threshold=0.8,
        )

        assert config.promotion_frequency_weight == 0.4
        assert config.promotion_threshold == 0.8

    def test_invalid_weight_raises(self):
        """Test that invalid weights raise ValueError."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            ScoringConfig(promotion_frequency_weight=1.5)

        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            ScoringConfig(demotion_decay_weight=-0.1)

    def test_invalid_threshold_raises(self):
        """Test that invalid thresholds raise ValueError."""
        with pytest.raises(ValueError, match="promotion_threshold must be between"):
            ScoringConfig(promotion_threshold=1.5)

        with pytest.raises(ValueError, match="demotion_threshold must be between"):
            ScoringConfig(demotion_threshold=-0.1)

    def test_weight_sum_warning(self):
        """Test warning when weights don't sum to ~1.0."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ScoringConfig(
                promotion_frequency_weight=0.1,
                promotion_importance_weight=0.1,
                promotion_recency_weight=0.1,
                promotion_velocity_weight=0.1,
            )
            assert len(w) == 1
            assert "Promotion weights sum to" in str(w[0].message)


class TestFrequencyScore:
    """Test frequency score calculation."""

    def test_zero_accesses(self):
        """Test frequency score for zero accesses."""
        engine = ScoringEngine()
        entry = create_test_entry(access_count=0)

        score = engine._calculate_frequency_score(entry)
        assert score == 0.0

    def test_low_accesses(self):
        """Test frequency score for low access count."""
        engine = ScoringEngine()
        entry = create_test_entry(access_count=10)

        score = engine._calculate_frequency_score(entry)
        assert 0.4 < score < 0.6  # Should be ~0.52

    def test_high_accesses(self):
        """Test frequency score for high access count."""
        engine = ScoringEngine()
        entry = create_test_entry(access_count=100)

        score = engine._calculate_frequency_score(entry)
        assert score >= 0.99  # Should be ~1.0

    def test_frequency_scaling(self):
        """Test logarithmic scaling of frequency."""
        engine = ScoringEngine()

        # Should have logarithmic growth
        score_1 = engine._calculate_frequency_score(create_test_entry(access_count=1))
        score_10 = engine._calculate_frequency_score(create_test_entry(access_count=10))
        score_100 = engine._calculate_frequency_score(create_test_entry(access_count=100))

        # Scores should be increasing
        assert score_1 < score_10 < score_100

        # 100 accesses should be close to 1.0
        assert score_100 >= 0.99


class TestRecencyScore:
    """Test recency score calculation."""

    def test_just_accessed(self):
        """Test recency score for just accessed entry."""
        engine = ScoringEngine()
        entry = create_test_entry(last_accessed=datetime.now())

        score = engine._calculate_recency_score(entry)
        assert score >= 0.99  # Should be ~1.0

    def test_one_day_ago(self):
        """Test recency score for 24 hours ago (one half-life)."""
        engine = ScoringEngine(ScoringConfig(recency_half_life_hours=24.0))
        last_accessed = datetime.now() - timedelta(hours=24)
        entry = create_test_entry(last_accessed=last_accessed)

        score = engine._calculate_recency_score(entry)
        assert 0.48 < score < 0.52  # Should be ~0.5

    def test_two_days_ago(self):
        """Test recency score for 48 hours ago (two half-lives)."""
        engine = ScoringEngine(ScoringConfig(recency_half_life_hours=24.0))
        last_accessed = datetime.now() - timedelta(hours=48)
        entry = create_test_entry(last_accessed=last_accessed)

        score = engine._calculate_recency_score(entry)
        assert 0.23 < score < 0.27  # Should be ~0.25

    def test_never_accessed_uses_created_at(self):
        """Test that entries without last_accessed use created_at."""
        engine = ScoringEngine()
        created_at = datetime.now() - timedelta(hours=24)
        entry = create_test_entry(created_at=created_at)

        # Should not be 1.0 since created 24 hours ago
        score = engine._calculate_recency_score(entry)
        assert score < 0.6


class TestVelocityScore:
    """Test velocity score calculation."""

    def test_zero_velocity(self):
        """Test velocity score for no accesses."""
        engine = ScoringEngine()
        entry = create_test_entry(access_count=0)

        score = engine._calculate_velocity_score(entry)
        assert score == 0.0

    def test_moderate_velocity(self):
        """Test velocity score for moderate access rate."""
        engine = ScoringEngine(ScoringConfig(velocity_window_hours=24.0))
        created_at = datetime.now() - timedelta(hours=24)
        entry = create_test_entry(access_count=120, created_at=created_at)

        # 120 accesses / 24 hours = 5 per hour → 0.5 score
        score = engine._calculate_velocity_score(entry)
        assert 0.48 < score < 0.52

    def test_high_velocity(self):
        """Test velocity score for high access rate."""
        engine = ScoringEngine(ScoringConfig(velocity_window_hours=24.0))
        created_at = datetime.now() - timedelta(hours=24)
        entry = create_test_entry(access_count=240, created_at=created_at)

        # 240 accesses / 24 hours = 10 per hour → 1.0 score
        score = engine._calculate_velocity_score(entry)
        assert score >= 0.99

    def test_velocity_window_limit(self):
        """Test that velocity uses window limit."""
        engine = ScoringEngine(ScoringConfig(velocity_window_hours=24.0))

        # Old entry with many accesses
        created_at = datetime.now() - timedelta(hours=100)
        entry = create_test_entry(access_count=240, created_at=created_at)

        # Should use 24-hour window, not full 100 hours
        # 240 / 24 = 10 per hour → 1.0
        score = engine._calculate_velocity_score(entry)
        assert score >= 0.99


class TestDecayAndStalenessScores:
    """Test decay and staleness score calculations."""

    def test_decay_is_inverse_recency(self):
        """Test that decay is 1 - recency."""
        engine = ScoringEngine()
        entry = create_test_entry(last_accessed=datetime.now())

        recency = engine._calculate_recency_score(entry)
        decay = engine._calculate_decay_score(entry)

        assert abs((recency + decay) - 1.0) < 0.01

    def test_staleness_below_threshold(self):
        """Test staleness score below threshold."""
        engine = ScoringEngine(ScoringConfig(staleness_threshold_days=30))
        last_accessed = datetime.now() - timedelta(days=20)
        entry = create_test_entry(last_accessed=last_accessed)

        score = engine._calculate_staleness_score(entry)
        assert score == 0.0

    def test_staleness_at_threshold(self):
        """Test staleness score at threshold."""
        engine = ScoringEngine(ScoringConfig(staleness_threshold_days=30))
        last_accessed = datetime.now() - timedelta(days=30)
        entry = create_test_entry(last_accessed=last_accessed)

        score = engine._calculate_staleness_score(entry)
        assert score >= 0.0 and score < 0.1

    def test_staleness_above_threshold(self):
        """Test staleness score above threshold."""
        engine = ScoringEngine(ScoringConfig(staleness_threshold_days=30))
        last_accessed = datetime.now() - timedelta(days=60)
        entry = create_test_entry(last_accessed=last_accessed)

        score = engine._calculate_staleness_score(entry)
        assert score >= 0.99  # Should be ~1.0


class TestPromotionScore:
    """Test promotion score calculation."""

    def test_high_importance_high_score(self):
        """Test that high importance gives high promotion score."""
        engine = ScoringEngine()
        entry = create_test_entry(importance=0.9, access_count=50, last_accessed=datetime.now())

        score, details = engine.calculate_promotion_score(entry)

        assert score > 0.7
        assert details["should_promote"] is True

    def test_low_importance_low_score(self):
        """Test that low importance gives low promotion score."""
        engine = ScoringEngine()
        entry = create_test_entry(
            importance=0.1, access_count=1, last_accessed=datetime.now() - timedelta(days=10)
        )

        score, details = engine.calculate_promotion_score(entry)

        assert score < 0.3
        assert details["should_promote"] is False

    def test_promotion_score_components(self):
        """Test that promotion score includes all components."""
        engine = ScoringEngine()
        entry = create_test_entry(
            importance=0.8,
            access_count=20,
            last_accessed=datetime.now() - timedelta(hours=12),
            created_at=datetime.now() - timedelta(days=1),
        )

        score, details = engine.calculate_promotion_score(entry)

        assert "frequency" in details
        assert "importance" in details
        assert "recency" in details
        assert "velocity" in details
        assert "total" in details
        assert "should_promote" in details

        # Check importance is correct
        assert details["importance"] == 0.8

    def test_promotion_threshold(self):
        """Test promotion threshold logic."""
        config = ScoringConfig(promotion_threshold=0.8)
        engine = ScoringEngine(config)

        # Entry below threshold - low importance, few accesses, older
        old_time = datetime.now() - timedelta(days=5)
        entry_below = create_test_entry(
            importance=0.4, access_count=2, created_at=old_time, last_accessed=old_time
        )
        score_below, details_below = engine.calculate_promotion_score(entry_below)

        # Entry above threshold - high importance, many accesses, very recent
        recent_time = datetime.now() - timedelta(minutes=5)
        entry_above = create_test_entry(
            importance=0.95, access_count=100, created_at=recent_time, last_accessed=datetime.now()
        )
        score_above, details_above = engine.calculate_promotion_score(entry_above)

        assert not details_below[
            "should_promote"
        ], f"Expected entry_below not to promote but got score {score_below}"
        assert details_above[
            "should_promote"
        ], f"Expected entry_above to promote but got score {score_above}"


class TestDemotionScore:
    """Test demotion score calculation."""

    def test_old_low_importance_high_score(self):
        """Test that old, unimportant entries get high demotion scores."""
        engine = ScoringEngine()
        entry = create_test_entry(
            importance=0.2, access_count=1, last_accessed=datetime.now() - timedelta(days=60)
        )

        score, details = engine.calculate_demotion_score(entry, capacity_pressure=0.8)

        assert score > 0.6
        assert details["should_demote"] is True

    def test_recent_important_low_score(self):
        """Test that recent, important entries get low demotion scores."""
        engine = ScoringEngine()
        entry = create_test_entry(importance=0.9, access_count=50, last_accessed=datetime.now())

        score, details = engine.calculate_demotion_score(entry, capacity_pressure=0.0)

        assert score < 0.4
        assert details["should_demote"] is False

    def test_demotion_score_components(self):
        """Test that demotion score includes all components."""
        engine = ScoringEngine()
        entry = create_test_entry(importance=0.5, last_accessed=datetime.now() - timedelta(days=40))

        score, details = engine.calculate_demotion_score(entry, capacity_pressure=0.5)

        assert "decay" in details
        assert "importance_drop" in details
        assert "capacity_pressure" in details
        assert "staleness" in details
        assert "total" in details
        assert "should_demote" in details

        # Check capacity pressure is passed through
        assert details["capacity_pressure"] == 0.5

    def test_capacity_pressure_effect(self):
        """Test that capacity pressure affects demotion score."""
        engine = ScoringEngine()
        entry = create_test_entry(importance=0.5)

        score_low, _ = engine.calculate_demotion_score(entry, capacity_pressure=0.0)
        score_high, _ = engine.calculate_demotion_score(entry, capacity_pressure=1.0)

        # Higher capacity pressure should increase demotion score
        assert score_high > score_low


class TestScoreExplanation:
    """Test score explanation formatting."""

    def test_explain_promotion_score(self):
        """Test explanation of promotion score."""
        engine = ScoringEngine()
        entry = create_test_entry(importance=0.8, access_count=20)

        score, details = engine.calculate_promotion_score(entry)
        explanation = engine.explain_score(details)

        assert "Total Score:" in explanation
        assert "Threshold:" in explanation
        assert "Component Breakdown:" in explanation
        assert "frequency" in explanation
        assert "importance" in explanation
        assert "recency" in explanation
        assert "velocity" in explanation

    def test_explain_demotion_score(self):
        """Test explanation of demotion score."""
        engine = ScoringEngine()
        entry = create_test_entry(importance=0.2)

        score, details = engine.calculate_demotion_score(entry, capacity_pressure=0.7)
        explanation = engine.explain_score(details)

        assert "Total Score:" in explanation
        assert "decay" in explanation
        assert "importance_drop" in explanation
        assert "capacity_pressure" in explanation
        assert "staleness" in explanation

    def test_explanation_shows_decision(self):
        """Test that explanation shows decision."""
        config = ScoringConfig(promotion_threshold=0.7)
        engine = ScoringEngine(config)

        # High score
        entry_high = create_test_entry(importance=0.9, access_count=50)
        _, details_high = engine.calculate_promotion_score(entry_high)
        explanation_high = engine.explain_score(details_high)
        assert "✅ YES" in explanation_high

        # Low score
        entry_low = create_test_entry(importance=0.1, access_count=1)
        _, details_low = engine.calculate_promotion_score(entry_low)
        explanation_low = engine.explain_score(details_low)
        assert "❌ NO" in explanation_low
