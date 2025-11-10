from itertools import product
from typing import Callable, Generator, Sequence, TypeVar
import numpy as np
from pddl_utils.structs.structs import GroundAtom, GroundOperator, Object, Operator, Predicate, VarToObjSub, Variable


def transition(curr_state: set[GroundAtom], effect: set[GroundAtom]) -> set[GroundAtom]:
    """Apply the effect to the current state and return the new state."""
    new_state = set(curr_state)
    for atom in effect:
        new_state.discard(GroundAtom(atom.predicate.get_negation(), atom.objects))  # remove negation if present
        new_state.add(atom)
    return new_state


def get_substitutions(variables: Sequence[Variable], objects: set[Object]) -> Generator[VarToObjSub, None, None]:
    ll_objects_per_arg = [[obj for obj in objects if obj.type == var.type] for var in variables]
    for args in product(*ll_objects_per_arg):
        substitution = {}
        for variable, obj in zip(variables, args):
            substitution[variable] = obj
        yield substitution


def sample_ground_operator(
    objects: set[Object], sym_state: set[GroundAtom], operator: Operator
) -> Generator[GroundOperator, None, None]:
    for sub in get_substitutions(operator.parameters, objects):
        ground_op = operator.ground(tuple(sub[v] for v in operator.parameters), frozenset(sym_state))

        if not ground_op.preconditions <= sym_state:  # subset
            continue

        yield ground_op


T = TypeVar("T")


def abstract_state(
    predicates: set[Predicate], objects: set[Object], x: T, classifier: Callable[[GroundAtom, T], np.ndarray]
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
