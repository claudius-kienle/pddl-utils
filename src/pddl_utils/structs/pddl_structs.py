from dataclasses import dataclass

from pddl_utils.structs.structs import (
    Operator,
    NamedPredicate,
    Type,
    Object,
    GroundAtom,
    LiteralConjunction,
    LiteralDisjunction,
)


@dataclass(frozen=True, repr=False, eq=False)
class PDDLDomain:
    """A PDDL domain."""

    domain_name: str
    types: set[Type]
    predicates: set[NamedPredicate]
    operators: set[Operator]

    def __post_init__(self):
        assert all(not p.is_negated for p in self.predicates)

    def to_string(self):
        """Create PDDL string"""
        predicates = "\n\t".join([lit.pddl_str() for lit in self.predicates])
        operators = "\n".join([op.pddl_str() for op in self.operators])
        constants = ""
        requirements = ":typing"
        if "=" in self.predicates:
            requirements += " :equality"

        domain_str = """
(define (domain {})
  (:requirements {})
  (:types {})
  {}
  (:predicates 
\t{}
  )

  {}
)
        """.format(
            self.domain_name,
            requirements,
            self._types_pddl_str(),
            constants,
            predicates,
            operators,
        )
        return domain_str

    def get_operator_by_name(self, name: str) -> Operator | None:
        """Get an operator by its name."""
        for op in self.operators:
            if op.name == name:
                return op
        return None

    def write(self, fname):
        """Write the domain PDDL string to a file."""
        domain_str = self.to_string()

        with open(fname, "w") as f:
            f.write(domain_str)

    def parent_types(self, type: Type) -> list[Type]:
        assert type in self.types
        p_type = type.parent

        all_types = [type]
        if p_type is not None:
            p_types = self.parent_types(p_type)
            all_types.extend(p_types)
        return all_types

    def _types_pddl_str(self):
        types_str = []
        for type in self.types:
            if type.parent:
                types_str.append("{} - {}".format(type.name, type.parent.name))
            else:
                types_str.append("{}".format(type.name))
        return " ".join(types_str)

    def copy_with(self, domain_name=None, types=None, predicates=None, operators=None):
        return PDDLDomain(
            domain_name=domain_name if domain_name is not None else self.domain_name,
            types=types if types is not None else self.types,
            predicates=predicates if predicates is not None else self.predicates,
            operators=operators if operators is not None else self.operators,
        )


@dataclass(frozen=True, repr=False, eq=False)
class PDDLProblem:
    """A PDDL problem."""

    problem_name: str
    domain_name: str
    objects: set[Object]
    init: set[GroundAtom]
    goal: LiteralConjunction | GroundAtom

    def __post_init__(self):
        if isinstance(self.goal, LiteralConjunction):
            assert all(isinstance(lit, GroundAtom) for lit in self.goal.literals)
        elif isinstance(self.goal, GroundAtom):
            pass
        elif self.goal is not None:
            raise ValueError("Goal must be a GroundAtom or LiteralConjunction.")

    @property
    def goal_list(self) -> set[GroundAtom]:
        if self.goal is None:
            return set()
        elif isinstance(self.goal, LiteralConjunction):
            assert all(isinstance(lit, GroundAtom) for lit in self.goal.literals)
            return self.goal.literals
        else:
            return {self.goal}

    def to_string(self):
        """Create PDDL problem string"""
        objects_str = self.objects_pddl_str()

        init_str = "\n\t".join([atom.pddl_str() for atom in sorted(self.init, key=str)])
        goal_str = self.goal.pddl_str()

        problem_str = f"""
(define (problem {self.problem_name})
  (:domain {self.domain_name})
  (:objects {objects_str})
  (:init 
    {init_str}
  )
  (:goal {goal_str})
)
        """.strip()

        return problem_str

    def write(self, fname):
        """Write the problem PDDL string to a file."""
        problem_str = self.to_string()

        with open(fname, "w") as f:
            f.write(problem_str)

    def objects_pddl_str(self):
        """Create PDDL string for objects grouped by type."""
        objects_strs = []
        for obs in self.objects:
            objects_strs.append(f"{obs.name} - {obs.type.name}")
        return " ".join(objects_strs)

    def copy_with(
        self,
        problem_name: str =None,
        domain_name: str =None,
        objects: set[Object] =None,
        init: set[GroundAtom] =None,
        goal: LiteralConjunction | GroundAtom =None,
    ):
        return PDDLProblem(
            problem_name=problem_name if problem_name is not None else self.problem_name,
            domain_name=domain_name if domain_name is not None else self.domain_name,
            objects=objects if objects is not None else self.objects,
            init=init if init is not None else self.init,
            goal=goal if goal is not None else self.goal,
        )


def adl_requirements() -> list[str]:
    return [
        ":disjunctive-preconditions",
        ":typing",
        ":strips",
        ":existential-preconditions",
        ":universal-preconditions",
        ":equality",
        ":negative-preconditions",
        ":conditional-effects",
    ]
