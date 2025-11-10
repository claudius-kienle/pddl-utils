import re
from typing import Sequence
from pddl_utils.structs.structs import GroundAtom, LiftedAtom, Object, Operator, Predicate
from pddl_utils.structs.pddl_structs import PDDLDomain, PDDLProblem


from pddl_utils.structs.string_utils import parentheses_groups, until_next_closing_parenthesis
from pddl_utils.structs.structs_parser import (
    parse_formula,
    parse_objects,
    parse_operator,
    parse_predicate,
    parse_type,
    parse_types,
    name_rgx,
)
from python_utils import remove_comments


def parse_domain(domain_str: str):
    domain_str = remove_comments(domain_str, ";")
    domain_match = re.match(rf"\(define\s+\(domain\s+({name_rgx})\)([\w\W]+)\)", domain_str.strip())
    if not domain_match:
        raise ValueError("Invalid domain definition: expected (define (domain <name>) ...)")

    domain_name = domain_match.group(1)
    domain_content = domain_match.group(2).strip()

    types = set()
    predicates: set[Predicate] = set()
    operators: list[Operator] = []
    for next_group in parentheses_groups(domain_content):
        section_match = re.match(r"\((:\w+)", next_group)
        assert section_match is not None
        section_type = section_match.group(1)
        section_content = next_group[len(section_type) + 1 : -1].strip()

        if section_type == ":requirements":
            pass
        elif section_type == ":types":
            types = parse_types(section_content)
        elif section_type == ":predicates":
            for pred_str in parentheses_groups(section_content):
                lifted_atom = parse_predicate(pred_str, only_variables=True)
                assert isinstance(lifted_atom, LiftedAtom)
                predicates.add(lifted_atom.predicate)
        elif section_type == ":action":
            assert len(predicates) > 0
            operators.append(parse_operator(next_group, known_predicates=predicates))
        elif section_type == ":constants":
            raise ValueError(
                f"Syntax error: Global constants are not supported in the domain definition. Rather use variables."
            )
        else:
            raise ValueError(f"Syntax error: type {section_type} is not supported in the domain definition")

    return PDDLDomain(
        domain_name=domain_name,
        types=set(types),
        predicates=predicates,
        operators=set(operators),
    )


def parse_problem(problem_str: str, domain: PDDLDomain) -> PDDLProblem:
    """Parse a PDDL problem string and return a PDDLProblem object."""
    problem_str = remove_comments(problem_str, ";")

    # Extract the main problem content
    problem_match = re.match(rf"\(define\s+\(problem\s+({name_rgx})\)([\w\W]+)\)", problem_str.strip())
    if not problem_match:
        raise ValueError("Invalid problem definition: expected (define (problem <name>) ...)")

    problem_name = problem_match.group(1)
    problem_content = problem_match.group(2).strip()

    # Initialize variables
    domain_name = None
    objects: Sequence[Object] = []
    init_facts = set()
    goal = None

    # Parse the problem content
    for next_group in parentheses_groups(problem_content):
        # Extract the section type
        section_match = re.match(r"\((:\w+)", next_group)
        assert section_match is not None

        section_type = section_match.group(1)
        section_content = next_group[len(section_type) + 1 : -1].strip()

        if section_type == ":domain":
            domain_name = section_content
        elif section_type == ":objects":
            # Parse objects in format: obj1 obj2 ... - type1 obj3 obj4 - type2
            if section_content.strip():
                objects = parse_objects(section_content)
        elif section_type == ":init":
            if section_content.strip():
                # Split the init content into individual facts (handle parentheses properly)
                facts_text = section_content
                for fact_str in parentheses_groups(facts_text):
                    fact_atom = parse_formula(fact_str, only_variables=False, known_predicates=domain.predicates)
                    assert isinstance(fact_atom, GroundAtom)
                    init_facts.add(fact_atom)
        elif section_type == ":goal":
            # Parse goal condition
            if section_content.strip():
                goal = parse_formula(section_content, only_variables=False, known_predicates=domain.predicates)

    # Validate required fields
    if domain_name is None:
        raise ValueError("Problem must specify a domain name")
    if goal is None:
        raise ValueError("Problem must specify a goal")

    return PDDLProblem(
        problem_name=problem_name,
        domain_name=domain_name,
        objects=set(objects),
        init=init_facts,
        goal=goal,
    )
