from dataclasses import dataclass

from pddl_utils.structs.structs import (
    Operator,
    Predicate,
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
    predicates: set[Predicate]
    operators: set[Operator]

    def to_string(self):
        """Create PDDL string"""
        predicates = "\n\t".join([lit.pddl_str() for lit in self.predicates])
        operators = "\n\t".join([op.pddl_str() for op in self.operators])
        constants = ""
        requirements = ":typing"
        if "=" in self.predicates:
            requirements += " :equality"

        domain_str = """
(define (domain {})
  (:requirements {})
  (:types {})
  {}
  (:predicates {}
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
