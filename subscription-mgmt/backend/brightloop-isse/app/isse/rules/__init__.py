"""
Deterministic rule-based layer: velocity, geo-mismatch, trial-abuse,
and data-integrity checks. All rules are pure functions returning a RuleVerdict.
"""

from app.isse.rules.engine import run_all_rules, worst_rule_decision
from app.isse.rules import velocity, geo_mismatch, trial_abuse, integrity

__all__ = [
    "run_all_rules",
    "worst_rule_decision",
    "velocity",
    "geo_mismatch",
    "trial_abuse",
    "integrity",
]