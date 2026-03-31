from pddl_utils.structs.structs_parser import parse_ground_formula
from pddl_utils.structs.structs_parser import collect_inferred_predicates
import re
from pddl_utils.structs.structs import (
    NamedPredicate,
    Object,
    Operator,
)
from pddl_utils.structs.pddl_structs import PDDLDomain, PDDLProblem


from pddl_utils.structs.string_utils import remove_comments, parentheses_groups
from pddl_utils.structs.structs_parser import (
    parse_ground_atom,
    parse_objects,
    parse_operator,
    parse_predicate,
    parse_types,
    name_rgx,
)


def parse_domain(domain_str: str):
    domain_str = remove_comments(domain_str, ";")
    domain_match = re.match(rf"\(define\s+\(domain\s+({name_rgx})\)([\w\W]+)\)", domain_str.strip())
    if not domain_match:
        raise ValueError("Invalid domain definition: expected (define (domain <name>) ...)")

    domain_name = domain_match.group(1)
    domain_content = domain_match.group(2).strip()

    types = set()
    predicates: set[NamedPredicate] = set()
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
                predicates.add(parse_predicate(pred_str))
        elif section_type == ":action":
            assert len(predicates) > 0
            operators.append(parse_operator(next_group, known_predicates=frozenset(predicates)))
        elif section_type == ":constants":
            raise ValueError(
                f"Syntax error: Global constants are not supported in the domain definition. Rather use variables."
            )
        else:
            raise ValueError(f"Syntax error: type {section_type} is not supported in the domain definition")

    return PDDLDomain(
        domain_name=domain_name,
        types=frozenset(types),
        predicates=frozenset(predicates),
        operators=frozenset(operators),
    )


def parse_problem(
    problem_str: str,
    domain: PDDLDomain | None,
    predicates: frozenset[NamedPredicate] | None = None,
) -> PDDLProblem:
    """Parse a PDDL problem string and return a PDDLProblem object.

    Predicate resolution priority:
    1. If *domain* is given, its predicates are used for type-checking.
    2. If *predicates* is given directly, those are used.
    3. If neither is provided, predicates are inferred from the ground atoms
       in :init and :goal by matching argument positions to the declared object types.
    """
    if domain is not None:
        assert predicates is None, "Cannot specify both a domain and predicates"
        predicates = frozenset(domain.predicates)

    problem_str = remove_comments(problem_str, ";")

    # Extract the main problem content
    problem_match = re.match(rf"\(define\s+\(problem\s+({name_rgx})\)([\w\W]+)\)", problem_str.strip())
    if not problem_match:
        raise ValueError("Invalid problem definition: expected (define (problem <name>) ...)")

    problem_name = problem_match.group(1)
    problem_content = problem_match.group(2).strip()

    # Initialize variables
    domain_name = None
    objects: frozenset[Object] = frozenset()
    init_facts = set()
    goal = None

    # Determine whether to infer predicates from ground atoms.
    infer_predicates = predicates is None
    known_predicates: set[NamedPredicate] = set(predicates) if predicates is not None else set()

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
                objects = frozenset(parse_objects(section_content))
        elif section_type == ":init":
            if section_content.strip():
                for fact_str in parentheses_groups(section_content):
                    if infer_predicates:
                        known_predicates |= collect_inferred_predicates(fact_str, objects)
                    fact_atom = parse_ground_atom(fact_str, known_predicates=frozenset(known_predicates))
                    init_facts.add(fact_atom)
        elif section_type == ":goal":
            # Parse goal condition
            if section_content.strip():
                if infer_predicates:
                    known_predicates |= collect_inferred_predicates(section_content, objects)
                goal = parse_ground_formula(
                    section_content,
                    known_predicates=frozenset(known_predicates),
                )

    # Validate required fields
    if domain_name is None:
        raise ValueError("Problem must specify a domain name")
    if goal is None:
        raise ValueError("Problem must specify a goal")

    return PDDLProblem(
        problem_name=problem_name,
        domain_name=domain_name,
        objects=objects,
        init=frozenset(init_facts),
        goal=goal,
    )
