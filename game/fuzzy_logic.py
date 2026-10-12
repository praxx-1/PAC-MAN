"""Pure-Python Mamdani Fuzzy Inference System for adaptive ghost behavior."""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple


class MembershipFunction:
    """Base class for fuzzy set membership functions."""
    def evaluate(self, x: float) -> float:
        raise NotImplementedError


class TriangularMF(MembershipFunction):
    """Triangular fuzzy membership: 0 at a, 1 at b, 0 at c."""
    def __init__(self, a: float, b: float, c: float) -> None:
        assert a <= b <= c, f"Invalid triangle parameters: {a}, {b}, {c}"
        self.a = float(a)
        self.b = float(b)
        self.c = float(c)

    def evaluate(self, x: float) -> float:
        if x <= self.a or x >= self.c:
            return 0.0
        if x == self.b:
            return 1.0
        if x < self.b:
            return (x - self.a) / (self.b - self.a) if self.b != self.a else 1.0
        return (self.c - x) / (self.c - self.b) if self.c != self.b else 1.0


class TrapezoidalMF(MembershipFunction):
    """Trapezoidal fuzzy membership: 0 at a, 1 from b to c, 0 at d."""
    def __init__(self, a: float, b: float, c: float, d: float) -> None:
        assert a <= b <= c <= d, f"Invalid trapezoid parameters: {a}, {b}, {c}, {d}"
        self.a = float(a)
        self.b = float(b)
        self.c = float(c)
        self.d = float(d)

    def evaluate(self, x: float) -> float:
        if x <= self.a or x >= self.d:
            return 0.0
        if self.b <= x <= self.c:
            return 1.0
        if x < self.b:
            return (x - self.a) / (self.b - self.a) if self.b != self.a else 1.0
        return (self.d - x) / (self.d - self.c) if self.d != self.c else 1.0


@dataclass
class FuzzyRule:
    """Represents an IF-THEN fuzzy rule with conjunction (MIN) antecedent."""
    name: str
    antecedents: List[Tuple[str, str]]  # List of (variable_name, term_name)
    consequent_term: str                # Target term in output variable
    weight: float = 1.0


@dataclass
class FuzzyInferenceResult:
    """Diagnostics and defuzzified output from the inference engine."""
    crisp_output: float
    aggression_level: float
    speed_multiplier: float
    memberships: Dict[str, Dict[str, float]] = field(default_factory=dict)
    rule_activations: Dict[str, float] = field(default_factory=dict)
    output_profile: Dict[str, float] = field(default_factory=dict)


class GhostFuzzyEngine:
    """Mamdani Fuzzy Inference System for adaptive ghost aggression."""

    def __init__(self) -> None:
        # 1. Distance Linguistic Variable (tiles: 0 to 40)
        self.distance_terms: Dict[str, MembershipFunction] = {
            "CLOSE": TrapezoidalMF(0.0, 0.0, 4.0, 8.0),
            "MEDIUM": TriangularMF(6.0, 12.0, 18.0),
            "FAR": TrapezoidalMF(14.0, 20.0, 40.0, 50.0),
        }

        # 2. Pellet Ratio Linguistic Variable (remaining / total: 0.0 to 1.0)
        self.pellet_terms: Dict[str, MembershipFunction] = {
            "FEW": TrapezoidalMF(0.0, 0.0, 0.15, 0.35),    # End-game pressure
            "HALF": TriangularMF(0.25, 0.5, 0.75),         # Mid-game
            "MANY": TrapezoidalMF(0.65, 0.8, 1.0, 1.0),    # Early-game
        }

        # 3. Threat / Power Pellet State (0.0 = Safe, 1.0 = Highly Vulnerable)
        self.threat_terms: Dict[str, MembershipFunction] = {
            "SAFE": TrapezoidalMF(0.0, 0.0, 0.15, 0.4),
            "DANGEROUS": TrapezoidalMF(0.3, 0.6, 1.0, 1.0),
        }

        # 4. Output: Aggression Level (0.0 = Passive/Scatter, 1.0 = Relentless Chase)
        self.aggression_terms: Dict[str, MembershipFunction] = {
            "PASSIVE": TrapezoidalMF(0.0, 0.0, 0.2, 0.35),
            "BALANCED": TriangularMF(0.25, 0.5, 0.75),
            "RELENTLESS": TrapezoidalMF(0.65, 0.8, 1.0, 1.0),
        }

        # Rule Base
        self.rules: List[FuzzyRule] = [
            # High danger overrides aggression
            FuzzyRule("R1_FrightenedRetreat", [("threat", "DANGEROUS")], "PASSIVE", weight=1.2),

            # Close proximity dynamics
            FuzzyRule("R2_CloseFewPellets", [("distance", "CLOSE"), ("pellets", "FEW")], "RELENTLESS", weight=1.0),
            FuzzyRule("R3_CloseHalfPellets", [("distance", "CLOSE"), ("pellets", "HALF")], "RELENTLESS", weight=0.9),
            FuzzyRule("R4_CloseManyPellets", [("distance", "CLOSE"), ("pellets", "MANY")], "BALANCED", weight=0.8),

            # Medium distance dynamics
            FuzzyRule("R5_MedFewPellets", [("distance", "MEDIUM"), ("pellets", "FEW")], "RELENTLESS", weight=0.85),
            FuzzyRule("R6_MedHalfPellets", [("distance", "MEDIUM"), ("pellets", "HALF")], "BALANCED", weight=0.7),
            FuzzyRule("R7_MedManyPellets", [("distance", "MEDIUM"), ("pellets", "MANY")], "PASSIVE", weight=0.6),

            # Far distance dynamics
            FuzzyRule("R8_FarFewPellets", [("distance", "FAR"), ("pellets", "FEW")], "BALANCED", weight=0.75),
            FuzzyRule("R9_FarManyPellets", [("distance", "FAR"), ("pellets", "MANY")], "PASSIVE", weight=0.9),
        ]

    def fuzzify(
        self,
        distance: float,
        pellet_ratio: float,
        threat: float,
    ) -> Dict[str, Dict[str, float]]:
        """Fuzzifies crisp inputs into membership degrees."""
        memberships: Dict[str, Dict[str, float]] = {
            "distance": {},
            "pellets": {},
            "threat": {},
        }

        for term, mf in self.distance_terms.items():
            memberships["distance"][term] = mf.evaluate(distance)

        for term, mf in self.pellet_terms.items():
            memberships["pellets"][term] = mf.evaluate(pellet_ratio)

        for term, mf in self.threat_terms.items():
            memberships["threat"][term] = mf.evaluate(threat)

        return memberships

    def evaluate(
        self,
        distance: float,
        pellet_ratio: float,
        threat: float = 0.0,
    ) -> FuzzyInferenceResult:
        """Runs the complete Mamdani fuzzy inference cycle."""
        # 1. Fuzzification
        memberships = self.fuzzify(distance, pellet_ratio, threat)

        # 2. Rule evaluation (Mamdani MIN conjunction & implication)
        rule_activations: Dict[str, float] = {}
        consequent_cuts: Dict[str, float] = {
            "PASSIVE": 0.0,
            "BALANCED": 0.0,
            "RELENTLESS": 0.0,
        }

        for rule in self.rules:
            # Find minimum degree among antecedents
            antecedent_degrees = []
            for var_name, term_name in rule.antecedents:
                deg = memberships.get(var_name, {}).get(term_name, 0.0)
                antecedent_degrees.append(deg)

            firing_strength = (min(antecedent_degrees) if antecedent_degrees else 0.0) * rule.weight
            rule_activations[rule.name] = firing_strength

            # Aggregate using MAX (s-norm)
            consequent = rule.consequent_term
            consequent_cuts[consequent] = max(consequent_cuts[consequent], firing_strength)

        # 3. Defuzzification (Centroid method across discrete samples)
        # Sample x in [0.0, 1.0] at 100 intervals
        steps = 100
        numerator = 0.0
        denominator = 0.0

        for i in range(steps + 1):
            x = i / float(steps)
            # Find aggregated membership at point x using clipping (MIN with cut) and MAX
            mu_x = 0.0
            for term_name, cut in consequent_cuts.items():
                if cut > 0.0:
                    term_mf = self.aggression_terms[term_name]
                    clipped_deg = min(cut, term_mf.evaluate(x))
                    mu_x = max(mu_x, clipped_deg)

            numerator += x * mu_x
            denominator += mu_x

        # Fallback to midpoint if no rules fired
        crisp_aggression = numerator / denominator if denominator > 1e-6 else 0.5

        # Bound output
        crisp_aggression = max(0.0, min(1.0, crisp_aggression))

        # Dynamic speed multiplier (e.g. 0.88x when passive up to 1.18x when relentless)
        speed_multiplier = 0.88 + (0.30 * crisp_aggression)

        return FuzzyInferenceResult(
            crisp_output=crisp_aggression,
            aggression_level=crisp_aggression,
            speed_multiplier=speed_multiplier,
            memberships=memberships,
            rule_activations=rule_activations,
            output_profile=consequent_cuts,
        )
