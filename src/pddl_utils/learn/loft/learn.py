"""Public entry point for the LOFT learner."""

from typing import FrozenSet, Optional, Sequence, Tuple

from pddl_utils.structs import GroundAtom, Operator

from pddl_utils.learn.loft.approach import LOFT
from pddl_utils.learn.loft.settings import LoftConfig, default_config

Transition = Tuple[FrozenSet[GroundAtom], GroundAtom, FrozenSet[GroundAtom]]


def learn_operators(
    transitions: Sequence[Transition],
    config: Optional[LoftConfig] = None,
) -> list[Operator]:
    """Learn lifted operators from a sequence of ground transitions.

    Each transition is ``(state_atoms, action_atom, next_state_atoms)``. The
    action atom's predicate identifies which action this transition is an
    instance of — transitions sharing the same action predicate are grouped
    together when learning that action's operator.

    Returns a list of :class:`pddl_utils.Operator`. The returned operators'
    preconditions include the action atom; strip it on the caller side if you
    don't want it in your domain.
    """
    cfg = config or default_config()
    approach = LOFT(cfg)
    approach.train((list(transitions), []))
    return approach.operators
