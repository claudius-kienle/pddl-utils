"""Default config for the LOFT learning step."""

from dataclasses import dataclass


@dataclass
class LoftConfig:
    builp_learn_probabilities: bool = False
    builp_learn_empty_effects: bool = False
    builp_max_preconditions_per_effect: int = 100_000
    builp_max_search_iters: int = 100
    builp_max_rule_size: float = float("inf")
    builp_true_pos_weight: float = 10
    builp_false_pos_weight: float = 1
    builp_var_count_weight: float = 1e-1
    builp_rule_size_weight: float = 1e-2
    builp_referenced_objects_only: bool = True
    # When True, every transition becomes its own effect-partition instead of being
    # merged with others that share a lifted effect. Each partition then yields one
    # operator, and BUILP learns its preconditions against *all* other transitions
    # (negatives), so same-effect edges that differ in context (e.g. grasp-before-
    # vs grasp-after-twist) stay separate operators rather than collapsing into one
    # over-general rule. Useful when a downstream per-operator cost must match a
    # single edge exactly.
    builp_one_operator_per_transition: bool = False
    effect_prob_threshold: float = 0.001


def default_config(**overrides) -> LoftConfig:
    cfg = LoftConfig()
    for k, v in overrides.items():
        if not hasattr(cfg, k):
            raise AttributeError(f"Unknown config field: {k}")
        setattr(cfg, k, v)
    return cfg
