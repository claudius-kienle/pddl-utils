import logging
from typing import List

from pddl_utils import GroundAtom, Not, PDDLDomain, PDDLProblem, SasPlan, SasAction, Object

logger = logging.getLogger(__name__)


def get_states(domain: PDDLDomain, problem: PDDLProblem, actions: SasPlan) -> list[frozenset[GroundAtom]]:
    action_states = [problem.init]

    if len(actions) == 0:
        return action_states

    pre_state = problem.init
    post_state = set(pre_state)
    for action in actions:
        operator = domain.get_operator_by_name(action.name)
        assert operator is not None, f"Operator {action.name} not found in domain."

        objects = action.get_objects(problem.objects)

        ground_op = operator.ground(objects, pre_state)

        for effect in ground_op.effects:
            post_state -= {Not(effect)}
            post_state |= {effect}

        action_states.append(frozenset(post_state))
        pre_state = frozenset(post_state)

    return action_states


def get_goal_state(domain: PDDLDomain, problem: PDDLProblem, actions: SasPlan) -> frozenset[GroundAtom]:
    return get_states(domain=domain, problem=problem, actions=actions)[-1]


def get_next_state(
    domain: PDDLDomain, current_state: frozenset[GroundAtom], objects: frozenset[Object], action: SasAction
) -> frozenset[GroundAtom]:
    problem = PDDLProblem(
        domain_name=domain.domain_name,
        problem_name="ai_problem",
        objects=objects,
        init=current_state,
        goal=frozenset(),
    )
    next_state = get_states(domain=domain, problem=problem, actions=SasPlan(actions=[action]))[-1]
    return next_state


def get_next_problem(
    domain: PDDLDomain,
    current_state: frozenset[GroundAtom],
    objects: frozenset[Object],
    action: SasAction,
    effects_for_goal: bool = False,
) -> PDDLProblem:
    next_state = get_next_state(domain=domain, current_state=current_state, objects=objects, action=action)

    if effects_for_goal:
        goal = next_state - current_state

    return PDDLProblem(
        domain_name=domain.domain_name,
        problem_name="ai_subproblem",
        objects=objects,
        init=current_state,
        goal=goal,
    )


def get_problems(domain: PDDLDomain, problem: PDDLProblem, actions: SasPlan) -> List[PDDLProblem]:
    state_transitions = get_states(domain=domain, problem=problem, actions=actions)

    problems = []
    for i in range(len(state_transitions) - 1):
        step_problem = PDDLProblem(
            problem_name="problem_state_%d" % i,
            domain_name=domain.domain_name,
            objects=problem.objects,
            init=state_transitions[i],
            goal=state_transitions[i + 1],
        )
        problems.append(step_problem)

    return problems
