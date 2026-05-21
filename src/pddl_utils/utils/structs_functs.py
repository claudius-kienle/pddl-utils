from pddl_utils import Not
from itertools import product
import re
from typing import Callable, Generator, Sequence, TypeVar
from collections import defaultdict
import numpy as np
from pddl_utils.structs.structs import (
    GroundAtom,
    GroundOperator,
    Object,
    Operator,
    Predicate,
    VarToObjSub,
    Variable,
    Type,
)


def transition(curr_state: frozenset[GroundAtom], effect: frozenset[GroundAtom]) -> frozenset[GroundAtom]:
    """Apply the effect to the current state and return the new state."""
    new_state = set(curr_state)
    for atom in effect:
        new_state.discard(GroundAtom(atom.predicate.get_negation(), atom.objects))  # remove negation if present
        new_state.add(atom)
    return frozenset(new_state)


def get_predicate_evaluation(state: frozenset[GroundAtom]) -> dict[GroundAtom, bool]:
    pred_eval = {}
    for atom in state:
        is_true = True
        if atom.predicate.is_negated:
            atom = GroundAtom(atom.predicate.get_negation(), entities=atom.entities)
            is_true = False
        if atom in pred_eval:
            raise RuntimeError("Predicate %s already evaluated." % str(atom.predicate))
        pred_eval[atom] = is_true
    return pred_eval


def get_pred_change(prior: frozenset[GroundAtom], post: frozenset[GroundAtom]):
    prior_evals = get_predicate_evaluation(prior)
    post_evals = get_predicate_evaluation(post)

    effects: set[GroundAtom] = set()
    removed: set[GroundAtom] = set()
    for predicate, prior_eval in prior_evals.items():
        post_eval = post_evals.pop(predicate, None)
        if post_eval is None:
            # if the post list does not list the predicate, we assume no effect
            removed.add(predicate)
            continue

        if prior_eval == post_eval:
            # evaluation did not change
            pass
        else:
            # evaluation did change, post eval is effect
            if post_eval:
                effects.add(predicate)
            else:
                effects.add(Not(predicate))

    added: set[GroundAtom] = {predicate if eval else Not(predicate) for predicate, eval in post_evals.items()}
    return effects, removed, added


def get_effect(
    prior_predicates: frozenset[GroundAtom], post_predicates: frozenset[GroundAtom]
) -> frozenset[GroundAtom]:
    effects, removed, added = get_pred_change(prior_predicates, post_predicates)

    for atom in added:
        if not atom.predicate.is_negated: # added means was false before, check if true now -> positive effect
            effects.add(atom)
    for atom in removed:
        if not atom.predicate.is_negated: # removed means now false, check if was true before -> negative effect
            effects.add(Not(atom))

    return frozenset(effects)


def get_substitutions(variables: Sequence[Variable], objects: frozenset[Object]) -> Generator[VarToObjSub, None, None]:
    ll_objects_per_arg = [[obj for obj in sorted(objects) if obj.type == var.type] for var in variables]
    for args in product(*ll_objects_per_arg):
        substitution = {}
        for variable, obj in zip(variables, args):
            substitution[variable] = obj
        yield substitution


def complete_state_with_false_ground_atoms(
    state: frozenset[GroundAtom], predicates: frozenset[Predicate], objects: frozenset[Object]
) -> frozenset[GroundAtom]:
    """Return a complete symbolic state by adding missing grounded atoms as false.

    The input ``state`` may only contain positive atoms (true facts), e.g. after
    parsing ``:init`` from PDDL. This function enumerates all typed groundings of
    ``predicates`` with ``objects`` and adds the negated version for any grounding
    not already present as either positive or negative.
    """
    complete_state = set(state)

    for pred in predicates:
        positive_pred = pred.get_negation() if pred.is_negated else pred
        variables = [Variable(f"?var{i}", t) for i, t in enumerate(positive_pred.types)]

        if not variables:
            positive_atom = GroundAtom(positive_pred, [])
            negative_atom = GroundAtom(positive_pred.get_negation(), [])
            if positive_atom not in complete_state and negative_atom not in complete_state:
                complete_state.add(negative_atom)
            continue

        objects_per_var = [[obj for obj in objects if obj.is_instance(var.type)] for var in variables]
        for args in product(*objects_per_var):
            positive_atom = GroundAtom(positive_pred, args)
            negative_atom = GroundAtom(positive_pred.get_negation(), args)
            if positive_atom in complete_state or negative_atom in complete_state:
                continue
            complete_state.add(negative_atom)

    return frozenset(complete_state)


def sample_ground_operator(
    objects: frozenset[Object], sym_state: frozenset[GroundAtom], operator: Operator
) -> Generator[GroundOperator, None, None]:
    for sub in get_substitutions(operator.parameters, objects):
        ground_op = operator.ground(tuple(sub[v] for v in operator.parameters), frozenset(sym_state))

        if not ground_op.preconditions:  # subset
            continue

        yield ground_op


T = TypeVar("T")


def abstract_state(
    predicates: set[Predicate], objects: frozenset[Object], x: T, classifier: Callable[[GroundAtom, T], np.ndarray]
) -> set[GroundAtom]:
    state = set()
    for pred in predicates:
        vars = [Variable(f"?var{i}", t) for i, t in enumerate(pred.types)]
        for sub in get_substitutions(vars, objects):
            objs = [sub[var] for var in vars]
            obj_names = [obj.name for obj in objs]
            if len(set(obj_names)) != len(obj_names):
                continue  # skip if there are duplicate objects

            ground = GroundAtom(pred, objs)
            prob = classifier(ground, x)

            if prob.item() < 0.5:
                s_pred = pred.get_negation()
            else:
                s_pred = pred

            state.add(GroundAtom(s_pred, objs))
    return state


def filter_state(
    state: frozenset[GroundAtom], known_predicates: list[str] | None, *, inverse: bool = False
) -> frozenset[GroundAtom]:
    if known_predicates is None:
        # we actually don't want to filter anything
        if inverse:
            return frozenset()
        else:
            return state

    filtered_state = set()
    for atom in state:
        assert isinstance(atom, GroundAtom)
        if (inverse and atom.predicate.name not in known_predicates) or (
            not inverse and atom.predicate.name in known_predicates
        ):
            filtered_state.add(atom)
    return frozenset(filtered_state)


def filter_valid_state(state: frozenset[GroundAtom]) -> frozenset[GroundAtom]:
    filtered_state = set()
    for atom in state:
        assert isinstance(atom, GroundAtom)
        if atom.predicate.is_negated:
            continue
        filtered_state.add(atom)
    return frozenset(filtered_state)


def state_to_str(state: frozenset[GroundAtom], *, separator: str = " ") -> str:
    return separator.join([atom.pddl_str() for atom in state])


def get_objects_in_state(state: frozenset[GroundAtom]) -> frozenset[Object]:
    return frozenset({obj for atom in state for obj in atom.objects})


def get_objects_by_type(objects: frozenset[Object]) -> dict[Type, set[Object]]:
    objects_by_type: dict[Type, set[Object]] = defaultdict(set)
    for obj in objects:
        objects_by_type[obj.type].add(obj)
    return objects_by_type


def get_predicates_in_state(state: set[GroundAtom]) -> set[Predicate]:
    predicates = set()
    for atom in state:
        predicates.add(atom.predicate)
    return predicates


def remove_types_from_domain(domain_str: str) -> str:
    """Remove types from the domain."""
    while True:
        match = re.search(r"(\?\w+) \- \w+", domain_str)
        if match is None:
            break
        domain_str = domain_str[: match.start()] + match.group(1) + domain_str[match.end() :]

    domain_str = re.sub(r"\(:types [\w\W]+?\)*(\((?::constants|:predicates|:functions|:derived))", r"\1", domain_str)

    return domain_str
