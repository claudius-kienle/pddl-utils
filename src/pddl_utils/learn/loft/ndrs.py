"""Noisy Deictic Rules — minimal subset used by the operator learner.

Subset of ``ndr/ndrs.py`` from the reference implementation:
https://github.com/ronuchit/LOFT_IROS_2021
"""

from pddl_utils.structs import GroundAtom, Predicate


# A 0-arity sentinel atom indicating noise. We construct it as a GroundAtom
# directly so we can sidestep the ``Predicate.__call__`` arity-0 guard.
_NOISE_PRED = Predicate(name="noiseoutcome", types=[])
NOISE_OUTCOME = GroundAtom(_NOISE_PRED, [])


class NDR:
    """A lifted action + lifted preconditions + a distribution over effects."""

    def __init__(self, action, preconditions, effect_probs, effects,
                 require_noise_outcome=True):
        self._action = action
        self._preconditions = preconditions
        self._effect_probs = list(effect_probs)
        self._effects = list(effects)

        assert isinstance(preconditions, list)
        assert len(self._effect_probs) == len(self._effects)

        if require_noise_outcome and len(self._effects) > 0:
            assert sum(NOISE_OUTCOME in e for e in self._effects) == 1

    def __str__(self):
        effs_str = "\n        ".join(
            f"{p}: {eff}" for p, eff in zip(self.effect_probs, self.effects))
        return f"{self.action}:\n  Pre: {self.preconditions}\n  Effs: {effs_str}"

    __repr__ = __str__

    @property
    def action(self):
        return self._action

    @property
    def preconditions(self):
        return self._preconditions

    @property
    def effect_probs(self):
        return self._effect_probs

    @property
    def effects(self):
        return self._effects


class NDRSet:
    """A set of NDRs that share a lifted action, plus a default rule."""

    def __init__(self, action, ndrs, default_ndr=None):
        self.action = action
        self.ndrs = list(ndrs)
        if default_ndr is None:
            self.default_ndr = self._create_default_ndr(action)
        else:
            self.default_ndr = default_ndr

        for ndr in ndrs:
            assert len(ndr.preconditions) > 0
            assert ndr.action == action
        assert self.default_ndr.action == action

    def __iter__(self):
        return iter(self.ndrs + [self.default_ndr])

    def __len__(self):
        return len(self.ndrs) + 1

    def __str__(self):
        return "\n".join(str(r) for r in self)

    @staticmethod
    def _create_default_ndr(action):
        return NDR(action, [], [0.0, 1.0], [{NOISE_OUTCOME}, set()])
