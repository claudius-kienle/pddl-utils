from dataclasses import dataclass
from functools import cached_property

from pddl_utils.structs.pddl_structs import PDDLDomain
from pddl_utils.structs.structs import Object


@dataclass(frozen=True, repr=False, eq=False)
class SasAction:
    name: str
    args: list[str]

    def __post_init__(self):
        object.__setattr__(self, "name", self.name.lower())

    def validate(self, domain: PDDLDomain, objects: list[Object]) -> list[str]:
        """
        Validates the action against the domain.
        :returns a list of errors if the action is invalid, otherwise an empty list.
        """
        known_operators = {op.name: op for op in domain.operators}
        if self.name not in known_operators:
            return [f"Unknown action: {self.name}"]

        if len(self.args) != len(known_operators[self.name].parameters):
            return [
                f"Action {self.name} expects {len(known_operators[self.name].parameters)} arguments, but got {len(self.args)}."
            ]

        action = known_operators[self.name]
        for arg_name, param in zip(self.args, action.parameters):
            arg = next(filter(lambda o: o.name == arg_name, objects), None)
            if arg is None:
                return [f"Unknown object: {arg_name}"]

            if param.type not in domain.parent_types(arg.type):
                return [
                    f"Object {arg_name} of type {arg.type} is not a valid parameter for action {self.name} of type {param.type}."
                ]

        return []

    def to_string(self) -> str:
        """Create a PDDL action string"""
        return f"({self.name} {' '.join(self.args)})"

    @cached_property
    def _str(self) -> str:
        return self.to_string()

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return self._str

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass(frozen=True, repr=False, eq=False)
class SasPlan:
    actions: list[SasAction]

    def validate(self, domain: PDDLDomain, objects: list[Object]) -> list[str]:
        """
        Validates the plan against the domain.
        :return : A list of error messages if the plan is invalid, otherwise an empty list.
        """
        errors = []
        for action in self.actions:
            action_errors = action.validate(domain=domain, objects=objects)
            errors.extend(action_errors)
        return errors

    def to_string(self) -> str:
        """
        Converts the SasPlan object to a string representation.
        """
        return "\n".join([action.to_string() for action in self.actions])

    @cached_property
    def _str(self) -> str:
        return self.to_string()

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return self._str

    def __hash__(self) -> int:
        return hash(str(self))
