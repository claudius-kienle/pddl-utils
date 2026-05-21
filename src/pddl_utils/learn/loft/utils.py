"""Learning-only utilities, ported to pddl_utils structs."""

import functools
import itertools
from typing import Iterable

from pddl_utils.structs import (
    GroundAtom,
    LiteralConjunction,
    Object,
    Operator,
    Predicate,
    Variable,
)
from pddl_utils.structs.structs import _Atom, LiftedAtom

from pddl_utils.learn.loft.inference import find_satisfying_assignments
from pddl_utils.learn.loft.ndrs import NOISE_OUTCOME


def make_atom(pred: Predicate, entities) -> _Atom:
    """Construct an atom regardless of arity / variable mix.

    Mirrors ``Predicate.__call__`` but also tolerates 0-arity preds and
    empty entity lists, which the upstream ``__call__`` rejects.
    """
    entities = list(entities)
    if len(entities) == 0:
        # For 0-arity, the lifted/ground distinction is purely cosmetic
        # because equality is by string.
        return LiftedAtom(pred, entities)
    if all(isinstance(e, Variable) for e in entities):
        return LiftedAtom(pred, entities)
    if all(isinstance(e, Object) for e in entities):
        return GroundAtom(pred, entities)
    return LiftedAtom(pred, entities)


def anti(atom: _Atom) -> _Atom:
    """Toggle the atom's `is_negated` flag (delete-effect marker for LOFT)."""
    return make_atom(atom.predicate.get_negation(), atom.entities)


def is_anti(atom: _Atom) -> bool:
    return atom.predicate.is_negated


def inverted_anti(atom: _Atom) -> _Atom:
    return anti(atom)


def ground_literal(lifted_lit: _Atom, sub) -> _Atom:
    return make_atom(lifted_lit.predicate,
                     [sub[e] for e in lifted_lit.entities])


def construct_effects(state, next_state):
    """Diff two atom sets, returning a set of effect atoms.

    Deletions become negated atoms (`anti(lit)`); additions stay positive.
    """
    effects = set()
    for lit in state - next_state:
        effects.add(anti(lit))
    for lit in next_state - state:
        effects.add(lit)
    return effects


@functools.lru_cache(maxsize=100000)
def preconditions_covered(transition, preconditions, lifted_action,
                          ret_assignments=False):
    state, action, _ = transition
    kb = state | {action}
    conditions = preconditions | {lifted_action}
    assignments = find_satisfying_assignments(
        kb, conditions, allow_redundant_variables=True,
        max_assignment_count=float("inf"))
    covered = (len(assignments) > 0)
    if ret_assignments:
        return covered, assignments
    return covered


def effects_covered(lifted_effects, ground_effects, pre_assignments,
                    ret_assignments=False):
    valid_assignments = []
    for assignment in pre_assignments:
        poss_ground_effects = substitute(lifted_effects, assignment)
        to_remove = set()
        for eff in poss_ground_effects:
            if is_anti(eff) and inverted_anti(eff) in poss_ground_effects:
                to_remove.add(eff)
                to_remove.add(inverted_anti(eff))
        for rem in to_remove:
            poss_ground_effects.discard(rem)
        if poss_ground_effects == ground_effects:
            if not ret_assignments:
                return True
            valid_assignments.append(assignment)
    if not ret_assignments:
        return False
    return len(valid_assignments) > 0, valid_assignments


@functools.lru_cache(maxsize=100000)
def transition_covered(transition, preconditions, lifted_action,
                       lifted_effects, ret_assignments=False):
    covered, assignments = preconditions_covered(
        transition, preconditions, lifted_action, ret_assignments=True)
    if not covered:
        return False
    _, _, ground_effects = transition
    result = effects_covered(lifted_effects, ground_effects, assignments)
    if ret_assignments:
        return result, assignments
    return result


def substitute(literals: Iterable[_Atom], sub):
    """Apply a (Variable -> entity) substitution to a set of atoms."""
    out = set()
    for lit in literals:
        new_ents = [sub[e] if isinstance(e, Variable) and e in sub else e
                    for e in lit.entities]
        out.add(make_atom(lit.predicate, new_ents))
    return out


@functools.lru_cache(maxsize=100000)
def unify(lits1, lits2):
    """Cached wrapper around :func:`inference.unify`."""
    from pddl_utils.learn.loft.inference import unify as _unify
    return _unify(lits1, lits2)


def lift_lit_set(literal_set, obj_to_var):
    """Replace entities by fresh ``?xN`` Variables. ``obj_to_var`` is mutated."""
    if obj_to_var:
        next_var_id = max(int(v.name[2:]) for v in obj_to_var.values()) + 1
    else:
        next_var_id = 0
    var_count = itertools.count(next_var_id)
    for lit in sorted(literal_set):
        for ent in sorted(lit.entities):
            if ent not in obj_to_var:
                obj_to_var[ent] = Variable(f"?x{next(var_count)}", ent.type)
    return {ground_literal(lit, obj_to_var) for lit in literal_set}


def prune_redundancies(formula):
    """Drop atoms whose variables are redundant under bisimulation."""
    all_variables = {v for lit in formula for v in lit.entities}
    var_to_lits = {v: sorted([lit for lit in formula if v in lit.entities])
                   for v in all_variables}
    var_to_lifted_id = {v: _compute_lifted_variable_id(v, var_to_lits)
                        for v in all_variables}
    vars_to_keep = set()
    kept_lifted_ids = set()
    for v in sorted(all_variables):
        lifted_id = var_to_lifted_id[v]
        if lifted_id not in kept_lifted_ids:
            vars_to_keep.add(v)
            kept_lifted_ids.add(lifted_id)
    return {lit for lit in formula
            if all(e in vars_to_keep for e in lit.entities)}


def _compute_lifted_variable_id(main_v, var_to_lits):
    var_to_num = {main_v: 0}
    queue = sorted(var_to_lits[main_v])
    all_visited_lits = set()
    while queue:
        lit = queue.pop()
        all_visited_lits.add(lit)
        for v in lit.entities:
            if v not in var_to_num:
                var_to_num[v] = max(var_to_num.values()) + 1
                for new_lit in var_to_lits[v]:
                    if any(vp not in var_to_num for vp in new_lit.entities):
                        queue.append(new_lit)
    lifted_lits = set()
    for lit in all_visited_lits:
        lifted_lits.add(
            (lit.predicate, tuple(var_to_num[a] for a in lit.entities)))
    return frozenset(lifted_lits)


def ndrs_to_operators(all_ndrs, include_empty_effects=False,
                      effect_threshold=0.):
    """Determinize a dict of NDRSets into a list of pddl_utils Operators."""
    operators = []
    for action in sorted(all_ndrs):
        ndr_set = all_ndrs[action]
        cnt = 0
        for ndr in ndr_set:
            for effects, effect_prob in zip(ndr.effects, ndr.effect_probs):
                if NOISE_OUTCOME in effects:
                    continue
                if not include_empty_effects and len(effects) == 0:
                    continue
                if effect_prob < effect_threshold:
                    continue
                name = f"{ndr.action.predicate.name}{cnt}"
                cnt += 1
                # Preconds: keep all *non-action* lifted atoms plus the action.
                precond_lits = sorted(ndr.preconditions) + [action]
                preconds = LiteralConjunction(precond_lits)
                params = sorted({e for lit in precond_lits
                                 for e in lit.entities
                                 if isinstance(e, Variable)},
                                key=lambda v: v.name)
                effs = LiteralConjunction(sorted(effects))
                operators.append(Operator(name=name, parameters=params,
                                          preconditions=preconds,
                                          effects=effs))
    return operators
