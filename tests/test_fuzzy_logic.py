"""Tests for Mamdani fuzzy inference engine and membership functions."""

import pytest
from game.fuzzy_logic import (
    GhostFuzzyEngine, TriangularMF, TrapezoidalMF,
)


def test_triangular_membership():
    mf = TriangularMF(2.0, 5.0, 8.0)
    assert mf.evaluate(1.0) == 0.0
    assert mf.evaluate(2.0) == 0.0
    assert mf.evaluate(3.5) == 0.5
    assert mf.evaluate(5.0) == 1.0
    assert mf.evaluate(6.5) == 0.5
    assert mf.evaluate(8.0) == 0.0
    assert mf.evaluate(9.0) == 0.0


def test_trapezoidal_membership():
    mf = TrapezoidalMF(2.0, 4.0, 6.0, 8.0)
    assert mf.evaluate(1.0) == 0.0
    assert mf.evaluate(2.0) == 0.0
    assert mf.evaluate(3.0) == 0.5
    assert mf.evaluate(4.0) == 1.0
    assert mf.evaluate(5.0) == 1.0
    assert mf.evaluate(6.0) == 1.0
    assert mf.evaluate(7.0) == 0.5
    assert mf.evaluate(8.0) == 0.0
    assert mf.evaluate(10.0) == 0.0


def test_fuzzy_aggression_close_and_few_pellets():
    """When Pac-Man is close and few pellets remain, ghost should be highly aggressive."""
    engine = GhostFuzzyEngine()
    result = engine.evaluate(distance=2.0, pellet_ratio=0.1, threat=0.0)

    assert result.aggression_level > 0.70
    assert result.speed_multiplier > 1.05
    assert result.output_profile["RELENTLESS"] > 0.6


def test_fuzzy_aggression_far_and_many_pellets():
    """When ghost is far and many pellets remain (early game), aggression should be timid."""
    engine = GhostFuzzyEngine()
    result = engine.evaluate(distance=30.0, pellet_ratio=0.9, threat=0.0)

    assert result.aggression_level < 0.40
    assert result.speed_multiplier < 1.02
    assert result.output_profile["PASSIVE"] > 0.5


def test_fuzzy_threat_override():
    """Active power pellet threat should suppress aggression regardless of proximity."""
    engine = GhostFuzzyEngine()
    # Close distance but extreme threat
    result = engine.evaluate(distance=2.0, pellet_ratio=0.1, threat=0.9)

    # Passive retreat should dominate
    assert result.output_profile["PASSIVE"] > 0.8
    assert result.aggression_level < 0.55


def test_fuzzy_monotonic_aggression_increase():
    """As distance to Pac-Man shrinks, aggression should monotonically increase."""
    engine = GhostFuzzyEngine()
    agg_far = engine.evaluate(distance=35.0, pellet_ratio=0.3, threat=0.0).aggression_level
    agg_med = engine.evaluate(distance=12.0, pellet_ratio=0.3, threat=0.0).aggression_level
    agg_close = engine.evaluate(distance=2.0, pellet_ratio=0.3, threat=0.0).aggression_level

    assert agg_close > agg_med > agg_far
