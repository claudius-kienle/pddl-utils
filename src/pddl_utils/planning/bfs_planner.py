from typing import Generator

from pddl_utils.structs.pddl_structs import PDDLDomain, PDDLProblem
from pddl_utils.structs.sas_structs import SasAction, SasPlan
from pddl_utils.utils.structs_functs import get_substitutions, transition


def plan_generator(
    domain: PDDLDomain,
    problem: PDDLProblem,
    max_depth: int = 10,
) -> Generator[SasPlan, None, None]:
    """DFS over the state space, yielding every plan that reaches the goal within max_depth.

    Args:
        domain: Parsed PDDL domain.
        problem: Parsed PDDL problem.
        max_depth: Maximum plan length to explore.

    Yields:
        SasPlan for each goal-reaching path found within max_depth.
    """
    goal = problem.goal
    objects = problem.objects
    operators = list(domain.operators)

    def _dfs(state: frozenset, actions: list, visited: frozenset) -> Generator[SasPlan, None, None]:
        if goal is None or goal.evaluate({}, state):
            print(SasPlan(actions=actions))
            yield SasPlan(actions=actions)
            return
        if len(actions) >= max_depth:
            return
        for operator in operators:
            for sub in get_substitutions(operator.parameters, objects):
                obj_tuple = tuple(sub[v] for v in operator.parameters)
                ground_op = operator.ground(obj_tuple, state)
                if not ground_op.preconditions:
                    continue
                new_state = transition(state, ground_op.effects)
                if new_state not in visited:
                    yield from _dfs(
                        new_state,
                        actions + [SasAction(name=operator.name, args=[o.name for o in obj_tuple])],
                        visited | {new_state},
                    )

    yield from _dfs(problem.init, [], frozenset({problem.init}))
