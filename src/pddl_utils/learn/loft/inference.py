"""CSP-style unification over pddl_utils atoms.

This module replaces ``pddlgym.inference.find_satisfying_assignments`` (used
by the reference LOFT at https://github.com/ronuchit/LOFT_IROS_2021) for the
operator-learning use case: given a knowledge base of atoms and a sequence of
condition atoms with free Variables, enumerate variable substitutions that
make every condition match an atom in the KB.

LOFT never feeds *negated* conditions through this path — delete-effects are
represented as atoms whose predicate has ``is_negated=True`` and they match
KB atoms of the same negated predicate symbol.
"""

from collections import defaultdict
from typing import Iterable, List

from pddl_utils.structs import Variable
from pddl_utils.structs.structs import _Atom, _TypedEntity


def find_satisfying_assignments(
    kb: Iterable[_Atom],
    conds: Iterable[_Atom],
    allow_redundant_variables: bool = True,
    max_assignment_count: float = float("inf"),
) -> List[dict]:
    """Return all variable substitutions making every cond match some kb atom.

    Substitution keys are the free Variables appearing in ``conds``; values
    are the entities they get bound to (typically Objects, but for unification
    between two lifted atom sets they may be Variables).
    """
    conds = list(conds)

    # Index kb by (predicate name, is_negated).
    kb_by_pred = defaultdict(list)
    for atom in kb:
        key = (atom.predicate.name, atom.predicate.is_negated)
        kb_by_pred[key].append(atom)

    free_vars: List[Variable] = []
    seen: set = set()
    for c in conds:
        for ent in c.entities:
            if isinstance(ent, Variable) and ent not in seen:
                free_vars.append(ent)
                seen.add(ent)

    results: List[dict] = []

    def backtrack(sub: dict, idx: int) -> None:
        if len(results) >= max_assignment_count:
            return
        if idx == len(conds):
            results.append(dict(sub))
            return
        cond = conds[idx]
        key = (cond.predicate.name, cond.predicate.is_negated)
        for kb_atom in kb_by_pred.get(key, []):
            if len(kb_atom.entities) != len(cond.entities):
                continue
            new_bindings: dict = {}
            ok = True
            for c_ent, k_ent in zip(cond.entities, kb_atom.entities):
                if isinstance(c_ent, Variable):
                    bound = sub.get(c_ent, new_bindings.get(c_ent))
                    if bound is not None:
                        if bound != k_ent:
                            ok = False
                            break
                    else:
                        if not _entity_type_matches(k_ent, c_ent):
                            ok = False
                            break
                        if not allow_redundant_variables:
                            taken = set(sub.values()) | set(new_bindings.values())
                            if k_ent in taken:
                                ok = False
                                break
                        new_bindings[c_ent] = k_ent
                else:
                    if c_ent != k_ent:
                        ok = False
                        break
            if not ok:
                continue
            sub.update(new_bindings)
            backtrack(sub, idx + 1)
            for v in new_bindings:
                del sub[v]
            if len(results) >= max_assignment_count:
                return

    backtrack({}, 0)
    return results


def _entity_type_matches(entity: _TypedEntity, variable: Variable) -> bool:
    """Treat type equality leniently — pddl_utils Types compare by name."""
    return entity.is_instance(variable.type)


def unify(lits1, lits2):
    """Match lits1 (typically ground) against lits2 (typically lifted).

    Returns ``(success, mapping)`` where ``mapping`` maps the entities of
    ``lits1`` (Objects) to the Variables of ``lits2``, mirroring pddlgym's
    direction (so callers can pass the dict straight into ``lift_lit_set``).
    """
    if sorted(p.name for p in {lit.predicate for lit in lits1}) != \
            sorted(p.name for p in {lit.predicate for lit in lits2}):
        return False, None
    assignments = find_satisfying_assignments(
        lits1, lits2, allow_redundant_variables=False, max_assignment_count=1)
    if not assignments:
        return False, None
    # Invert Variable -> Object into Object -> Variable.
    inverted = {v: k for k, v in assignments[0].items()}
    return True, inverted
