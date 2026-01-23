"""Structs used throughout the codebase."""

# copied from https://github.com/Learning-and-Intelligent-Systems/predicators/blob/master/predicators/structs.py
# and https://github.com/tomsilver/pddlgym/blob/master/pddlgym/structs.py

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, MISSING
from enum import Enum
from functools import cached_property, lru_cache
from itertools import product
from typing import (
    overload,
    Any,
    Callable,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
)


class Symbols(Enum):
    """A set of symbols that can be used in PDDL."""

    ROUND_BRACKET_LEFT = "("
    ROUND_BRACKET_RIGHT = ")"
    TYPE_SEP = "-"
    EQUAL = "="
    ACTION = ":action"
    AND = "and"
    CONSTANTS = ":constants"
    DEFINE = "define"
    DERIVED = ":derived"
    DOMAIN = "domain"
    DOMAIN_P = ":domain"
    EFFECT = ":effect"
    EITHER = "either"
    EXISTS = "exists"
    FORALL = "forall"
    GOAL = ":goal"
    IMPLY = "imply"
    INIT = ":init"
    NOT = "not"
    OBJECT = "object"
    OBJECTS = ":objects"
    ONEOF = "oneof"
    OR = "or"
    PARAMETERS = ":parameters"
    PRECONDITION = ":precondition"
    PREDICATES = ":predicates"
    PROBLEM = "problem"
    REQUIREMENTS = ":requirements"
    TYPES = ":types"
    METRIC = ":metric"
    WHEN = "when"
    GREATER_EQUAL = ">="
    GREATER = ">"
    LESSER_EQUAL = "<="
    LESSER = "<"
    MINUS = "-"
    PLUS = "+"
    TIMES = "*"
    DIVIDE = "/"
    ASSIGN = "assign"
    SCALE_UP = "scale-up"
    SCALE_DOWN = "scale-down"
    INCREASE = "increase"
    DECREASE = "decrease"
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"
    TOTAL_COST = "total-cost"


ALL_SYMBOLS: set[str] = {v.value for v in Symbols}


def is_a_keyword(word: str) -> bool:
    """Check that the word is not a keyword."""
    return word in ALL_SYMBOLS


@dataclass(frozen=True, order=True)
class Type:
    """Struct defining a type."""

    name: str
    feature_names: Sequence[str] = field(repr=False, default_factory=list)
    parent: Optional[Type] = field(default=None, repr=False)

    def __post_init__(self):
        assert isinstance(self.name, str)

    @property
    def dim(self) -> int:
        """Dimensionality of the feature vector of this object type."""
        return len(self.feature_names)

    def get_ancestors(self) -> set[Type]:
        """Get the set of all types that are ancestors (i.e. parents,
        grandparents, great-grandparents, etc.) of the current type."""
        curr_type: Optional[Type] = self
        ancestors_set = set()
        while curr_type is not None:
            ancestors_set.add(curr_type)
            curr_type = curr_type.parent
        return ancestors_set

    def __call__(self, name: str) -> _TypedEntity:
        """Convenience method for generating _TypedEntities."""
        if name.startswith("?"):
            return Variable(name, self)
        return Object(name, self)

    def __hash__(self) -> int:
        return hash((self.name, tuple(self.feature_names)))


@dataclass(frozen=True, order=True, repr=False)
class _TypedEntity:
    """Struct defining an entity with some type, either an object (e.g.,
    block3) or a variable (e.g., ?block).

    Should not be instantiated externally.
    """

    name: str
    type: Type

    def __post_init__(self) -> None:
        assert isinstance(self.type, Type)

    @cached_property
    def _str(self) -> str:
        return f"{self.name}:{self.type.name}"

    @cached_property
    def _hash(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return self._str

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL
        file."""
        return f"{self.name} - {self.type.name}"

    def is_instance(self, t: Type) -> bool:
        """Return whether this entity is an instance of the given type, taking
        hierarchical typing into account."""
        cur_type: Optional[Type] = self.type
        while cur_type is not None:
            if cur_type == t:
                return True
            cur_type = cur_type.parent
        return False


@dataclass(frozen=True, order=True, repr=False)
class Object(_TypedEntity):
    """Struct defining an Object, which is just a _TypedEntity whose name does
    not start with "?"."""

    def __post_init__(self) -> None:
        assert not self.name.startswith("?")

    def __hash__(self) -> int:
        # By default, the dataclass generates a new __hash__ method when
        # frozen=True and eq=True, so we need to override it.
        return self._hash


@dataclass(frozen=True, order=True, repr=False)
class Variable(_TypedEntity):
    """Struct defining a Variable, which is just a _TypedEntity whose name
    starts with "?"."""

    def __post_init__(self) -> None:
        assert self.name.startswith("?")

    def __hash__(self) -> int:
        # By default, the dataclass generates a new __hash__ method when
        # frozen=True and eq=True, so we need to override it.
        return self._hash


@dataclass(frozen=True, order=False, repr=False)
class Predicate:
    """Struct defining a predicate (a lifted classifier over states)."""

    name: str
    types: Sequence[Type]
    is_negated: bool = field(compare=False, default=False)
    # The classifier takes in a complete state and a sequence of objects
    # representing the arguments. These objects should be the only ones
    # treated "specially" by the classifier.
    _classifier: Optional[Callable[[State, Sequence[Object]], bool]] = field(compare=False, default=None)

    def __call__(self, entities: Sequence[_TypedEntity]) -> _Atom:
        """Convenience method for generating Atoms."""
        if self.arity == 0:
            raise ValueError(
                "Cannot use __call__ on a 0-arity predicate, "
                "since we can't determine whether it becomes a "
                "LiftedAtom or a GroundAtom. Use the LiftedAtom "
                "or GroundAtom constructors directly instead"
            )
        if all(isinstance(ent, Variable) for ent in entities):
            return LiftedAtom(self, entities)
        if all(isinstance(ent, Object) for ent in entities):
            return GroundAtom(self, entities)
        raise ValueError("Cannot instantiate Atom with mix of " "variables and objects")

    @cached_property
    def _hash(self) -> int:
        return hash(str(self))

    def __hash__(self) -> int:
        return self._hash

    @cached_property
    def arity(self) -> int:
        """The arity of this predicate (number of arguments)."""
        return len(self.types)

    def holds(self, state: State, objects: Sequence[Object]) -> bool:
        """Public method for calling the classifier.

        Performs type checking first.
        """
        assert len(objects) == self.arity
        for obj, pred_type in zip(objects, self.types):
            assert isinstance(obj, Object)
            assert obj.is_instance(pred_type)
        assert self._classifier is not None
        return self._classifier(state, objects)

    def __str__(self) -> str:
        return self.name if not self.is_negated else "NOT-" + self.name

    def __repr__(self) -> str:
        return str(self)

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL
        file."""
        if self.arity == 0:
            return f"({self.name})"
        vars_str = " ".join(f"?x{i} - {t.name}" for i, t in enumerate(self.types))
        return f"({self.name} {vars_str})"

    def get_negation(self) -> Predicate:
        """Return a negated version of this predicate."""
        return Predicate(self.name, self.types, is_negated=not self.is_negated, _classifier=self._negated_classifier)

    def _negated_classifier(self, state: State, objects: Sequence[Object]) -> bool:
        # Separate this into a named function for pickling reasons.
        assert self._classifier is not None
        return not self._classifier(state, objects)

    def __lt__(self, other: Predicate) -> bool:
        return str(self) < str(other)


@dataclass(frozen=True, repr=False, eq=False)
class NamedPredicate(Predicate):
    variables: Sequence[Variable] = field(kw_only=True)
    types: Sequence[Type] = field(init=False)

    def __hash__(self) -> int:
        return super().__hash__()

    @property
    def types(self) -> Sequence[Type]:
        return [var.type for var in self.variables]

    @types.setter
    def types(self, value: Sequence[Type]) -> None:
        pass

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL
        file."""
        if self.arity == 0:
            return f"({self.name})"
        vars_str = " ".join(f"{var.name} - {var.type.name}" for var in self.variables)
        return f"({self.name} {vars_str})"

    def get_negation(self) -> NamedPredicate:
        return NamedPredicate(
            name=self.name,
            variables=self.variables,
            is_negated=not self.is_negated,
            _classifier=self._negated_classifier,
        )


@dataclass(frozen=True, repr=False, eq=False)
class _Atom:
    """Struct defining an atom (a predicate applied to either variables or
    objects).

    Should not be instantiated externally.
    """

    predicate: Predicate
    entities: Sequence[_TypedEntity]

    def __post_init__(self) -> None:
        if isinstance(self.entities, _TypedEntity):
            raise ValueError("Atoms expect a sequence of entities, not a " "single entity.")
        if len(self.entities) != self.predicate.arity:
            raise ValueError(
                f"Syntax error: Predicate {self.predicate.name} must have {self.predicate.arity} arguments. Found: {len(self.entities)}"
            )
        for ent, pred_type in zip(self.entities, self.predicate.types):
            if not ent.is_instance(pred_type):
                raise ValueError(
                    f"Syntax error: Predicate {self.predicate.name} must have argument {pred_type.name} of type {pred_type}. Found: {ent.type}"
                )

    @property
    def _str(self) -> str:
        raise NotImplementedError("Override me")

    @cached_property
    def _hash(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return str(self)

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL
        file."""
        if not self.entities:
            return f"({self.predicate.name})"
        entities_str = " ".join(e.name for e in self.entities)
        pddl_str = f"({self.predicate.name} {entities_str})"
        if self.predicate.is_negated:
            pddl_str = f"(not {pddl_str})"
        return pddl_str

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, _Atom)
        return str(self) == str(other)

    def __lt__(self, other: object) -> bool:
        assert isinstance(other, _Atom)
        return str(self) < str(other)


class LiftedFormulaBase(ABC):
    """Abstract base class for all lifted formulas.
    
    Defines the common interface that all lifted formulas must implement.
    """
    
    @property
    @abstractmethod
    def used_predicates(self) -> set[Predicate]:
        """Return the set of predicates used in this formula."""
        ...
    
    @property
    @abstractmethod
    def exposed_variables(self) -> set[Variable]:
        """Return the set of variables exposed (not quantified) in this formula."""
        ...
    
    @abstractmethod
    def pddl_str(self) -> str:
        """Return a PDDL string representation of this formula."""
        ...
    
    @abstractmethod
    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        """Ground this formula given a variable substitution and state.
        
        Returns a set of ground atoms that represent the grounded formula.
        For constraints like EqualTo, may return empty set or raise an error.
        """
        ...
    
    @abstractmethod
    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate whether this formula holds given a substitution and state.
        
        Returns True if the formula is satisfied, False otherwise.
        """
        ...


class LiftedFormulaStrMixin:
    """Mixin providing common string representation and hashing for lifted formulas.
    
    Classes using this mixin must implement a _str property that returns the string representation.
    """
    
    @cached_property
    @abstractmethod
    def _str(self) -> str:
        """Return the string representation of this formula."""
        ...
    
    def __str__(self) -> str:
        return self._str
    
    def __repr__(self) -> str:
        return str(self)
    
    @cached_property
    def _hash(self) -> int:
        return hash(str(self))
    
    def __hash__(self) -> int:
        return self._hash
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return str(self) == str(other)


@dataclass(frozen=True, repr=False, eq=False)
class LiftedAtom(_Atom):
    """Struct defining a lifted atom (a predicate applied to variables)."""

    @cached_property
    def variables(self) -> list[Variable]:
        """Arguments for this lifted atom.

        A list of "Variable"s.
        """
        return [cast(Variable, ent) for ent in self.entities]

    @cached_property
    def used_predicates(self) -> set[Predicate]:
        return {self.predicate}

    @cached_property
    def exposed_variables(self) -> set[Variable]:
        return set(self.variables)

    @cached_property
    def _str(self) -> str:
        return str(self.predicate) + "(" + ", ".join(map(str, self.variables)) + ")"

    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        """Create a GroundAtom with a given substitution."""
        assert set(self.variables).issubset(set(sub.keys()))
        return {GroundAtom(self.predicate, [sub[v] for v in self.variables])}

    def substitute(self, sub: VarToVarSub) -> LiftedAtom:
        """Create a LiftedAtom with a given substitution."""
        assert set(self.variables).issubset(set(sub.keys()))
        return LiftedAtom(self.predicate, [sub[v] for v in self.variables])

    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate whether this lifted atom holds given a substitution and state."""
        from pddl_utils.utils.structs_functs import filter_valid_state
        return filter_valid_state(self.ground(sub, state)).issubset(state)


@dataclass(frozen=True, repr=False, eq=False)
class GroundAtom(_Atom):
    """Struct defining a ground atom (a predicate applied to objects)."""

    @cached_property
    def objects(self) -> list[Object]:
        """Arguments for this ground atom.

        A list of "Object"s.
        """
        return list(cast(Object, ent) for ent in self.entities)

    @cached_property
    def _str(self) -> str:
        return str(self.predicate) + "(" + ", ".join(map(str, self.objects)) + ")"

    def lift(self, sub: ObjToVarSub) -> LiftedAtom:
        """Create a LiftedAtom with a given substitution."""
        assert set(self.objects).issubset(set(sub.keys()))
        return LiftedAtom(self.predicate, [sub[o] for o in self.objects])

    def holds(self, state: State) -> bool:
        """Check whether this ground atom holds in the given state."""
        return self.predicate.holds(state, self.objects)


@dataclass(frozen=True, repr=False, eq=False)
class LiteralConjunction(LiftedFormulaStrMixin):
    """A logical conjunction (AND) of Literals."""

    literals: Sequence[LiftedFormula]

    @cached_property
    def used_predicates(self) -> set[Predicate]:
        return {p for lit in self.literals for p in lit.used_predicates}

    @cached_property
    def exposed_variables(self) -> set[Variable]:
        """Get all variables from the literals."""
        variables = set()
        for lit in self.literals:
            variables.update(v for v in lit.exposed_variables)
        return variables

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL file."""
        if len(self.literals) == 1:
            return list(self.literals)[0].pddl_str()
        literal_strs = [lit.pddl_str() for lit in self.literals]
        return f"(and {' '.join(literal_strs)})"

    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        """Ground the existential by substituting variables with objects."""
        assert set(self.exposed_variables).issubset(set(sub.keys()))
        grounded_literals = []
        for lit in self.literals:
            assert not isinstance(lit, EqualTo)
            grounded_literals.extend(lit.ground(sub, state))
        return set(grounded_literals)

    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate whether all literals in the conjunction hold."""
        assert set(self.exposed_variables).issubset(set(sub.keys()))
        for lit in self.literals:
            if not lit.evaluate(sub, state):
                return False
        return True

    @cached_property
    def _str(self) -> str:
        return f"AND({', '.join(str(lit) for lit in self.literals)})"


@dataclass(frozen=True, repr=False, eq=False)
class LiteralDisjunction(LiftedFormulaStrMixin):
    """A logical disjunction (OR) of Literals."""

    literals: Sequence[LiftedFormula]

    @cached_property
    def used_predicates(self) -> set[Predicate]:
        return {p for lit in self.literals for p in lit.used_predicates}

    @cached_property
    def exposed_variables(self) -> set[Variable]:
        """Get all variables from the literals."""
        variables = set()
        for lit in self.literals:
            variables.update(v.name for v in lit.exposed_variables)
        return variables

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL file."""
        if len(self.literals) == 1:
            return self.literals[0].pddl_str()
        literal_strs = [lit.pddl_str() for lit in self.literals]
        return f"(or {' '.join(literal_strs)})"

    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        """Ground the existential by substituting variables with objects."""
        raise NotImplementedError()

    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate whether any literal in the disjunction holds."""
        assert set(self.exposed_variables).issubset(set(sub.keys()))
        for lit in self.literals:
            if lit.evaluate(sub, state):
                return True
        return False

    @cached_property
    def _str(self) -> str:
        return f"OR({', '.join(str(lit) for lit in self.literals)})"


@dataclass(frozen=True, repr=False, eq=False)
class ForAll(LiftedFormulaStrMixin):
    """Represents a universal quantification (ForAll) over the given variables in the given body."""

    variables: Sequence[Variable]
    body: LiftedFormula
    is_negative: bool = False

    @cached_property
    def used_predicates(self) -> set[Predicate]:
        return self.body.used_predicates

    @cached_property
    def exposed_variables(self) -> set[Variable]:
        return self.body.exposed_variables - set(self.variables)

    @cached_property
    def positive(self) -> ForAll:
        """Return the positive version of this ForAll."""
        return ForAll(self.variables, self.body, is_negative=False)

    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        from pddl_utils.utils.structs_functs import get_objects_in_state, get_objects_by_type

        objects = get_objects_in_state(state)
        objs_by_type = get_objects_by_type(objects)

        # Get objects for each variable type
        objs_for_vars = []
        for var in self.variables:
            objs_w_type = objs_by_type.get(var.type, set())
            objs_for_vars.append(list(objs_w_type))

        # Generate all combinations using product
        all_grounded = set()
        for obj_combo in product(*objs_for_vars):
            var_sub = dict(sub)
            var_sub.update(dict(zip(self.variables, obj_combo)))
            grounded_body = self.body.ground(var_sub, state)
            all_grounded.update(grounded_body)

        return all_grounded

    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate whether the forall quantification holds."""
        raise RuntimeError("ForAll is a effect.")

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL file."""
        body_str = self.body.pddl_str()
        var_str = " ".join(f"{v.name} - {v.type.name}" for v in self.variables)
        forall_str = f"(forall ({var_str}) {body_str})"
        if self.is_negative:
            return f"(not {forall_str})"
        return forall_str

    @cached_property
    def _str(self) -> str:
        forall_str = f"FORALL({[v.name for v in self.variables]}) : {self.body}"
        if self.is_negative:
            return "NOT-" + forall_str
        return forall_str


@dataclass(frozen=True, repr=False, eq=False)
class Exists(LiftedFormulaStrMixin):
    """Represents an existential quantification (Exists) over the given variables in the given body."""

    variables: Sequence[Variable]
    body: LiftedFormula
    is_negative: bool = False

    @cached_property
    def used_predicates(self) -> set[Predicate]:
        return self.body.used_predicates

    @cached_property
    def exposed_variables(self) -> set[Variable]:
        return self.body.exposed_variables - set(self.variables)

    @cached_property
    def positive(self) -> Exists:
        """Return the positive version of this Exists."""
        return Exists(self.variables, self.body, is_negative=False)

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL file."""
        body_str = self.body.pddl_str()
        var_str = " ".join(f"{v.name} - {v.type.name}" for v in self.variables)
        exists_str = f"(exists ({var_str}) {body_str})"
        if self.is_negative:
            return f"(not {exists_str})"
        return exists_str

    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        raise NotImplementedError()

    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate whether the existential quantification holds."""
        from pddl_utils.utils.structs_functs import get_objects_in_state, get_objects_by_type

        objects = get_objects_in_state(state)
        objs_by_type = get_objects_by_type(objects)

        # Get objects for each variable type
        objs_for_vars = []
        for var in self.variables:
            objs_w_type = objs_by_type.get(var.type, set())
            objs_for_vars.append(list(objs_w_type))

        # Check if body holds for any combination
        for obj_combo in product(*objs_for_vars):
            var_sub = dict(sub)
            var_sub.update(dict(zip(self.variables, obj_combo)))
            if self.body.evaluate(var_sub, state):
                return False if self.is_negative else True

        # Body doesn't hold for any combination
        return True if self.is_negative else False

    @cached_property
    def _str(self) -> str:
        exists_str = f"EXISTS({[v.name for v in self.variables]}) : {self.body}"
        if self.is_negative:
            return "NOT-" + exists_str
        return exists_str


@dataclass(frozen=True, repr=False, eq=False)
class When(LiftedFormulaStrMixin):
    """Represents a conditional (When) statement - when condition holds, apply the effect."""

    condition: LiftedFormula
    effect: LiftedFormula

    @cached_property
    def used_predicates(self) -> set[Predicate]:
        return self.condition.used_predicates | self.effect.used_predicates

    @cached_property
    def exposed_variables(self) -> set[Variable]:
        return self.condition.exposed_variables | self.effect.exposed_variables

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL file."""
        condition_str = self.condition.pddl_str()
        effect_str = self.effect.pddl_str()
        return f"(when {condition_str} {effect_str})"

    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        """Ground the when statement by substituting variables with objects."""
        assert set(self.exposed_variables).issubset(set(sub.keys()))
        # Use evaluate to check if condition holds
        if self.condition.evaluate(sub, state):
            return self.effect.ground(sub, state)
        return set()

    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate the when statement - returns true if condition implies effect."""
        raise RuntimeError("When is an effect.")

    @cached_property
    def _str(self) -> str:
        return f"WHEN({self.condition}) : {self.effect}"


@dataclass(frozen=True, repr=False, eq=False)
class Imply(LiftedFormulaStrMixin):
    """Represents a logical implication (Imply) - if antecedent, then consequent."""

    antecedent: LiftedFormula
    consequent: LiftedFormula

    @cached_property
    def used_predicates(self) -> set[Predicate]:
        return self.antecedent.used_predicates | self.consequent.used_predicates

    @cached_property
    def exposed_variables(self) -> set[Variable]:
        return self.antecedent.exposed_variables | self.consequent.exposed_variables

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL file."""
        antecedent_str = self.antecedent.pddl_str()
        consequent_str = self.consequent.pddl_str()
        return f"(imply {antecedent_str} {consequent_str})"

    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        """Ground the implication by substituting variables with objects."""
        raise RuntimeError("Imply is a logical constraint, not an effect.")

    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate the implication - returns true if antecedent is false OR consequent is true."""
        assert set(self.exposed_variables).issubset(set(sub.keys()))
        if self.antecedent.evaluate(sub, state):
            return self.consequent.evaluate(sub, state)
        return True

    @cached_property
    def _str(self) -> str:
        return f"IMPLY({self.antecedent}) => {self.consequent}"


@dataclass(frozen=True, repr=False, eq=False)
class EqualTo(LiftedFormulaStrMixin):
    """Represents an equality comparison (=) between two variables."""

    left: Variable
    right: Variable
    is_negative: bool = False

    def __post_init__(self) -> None:
        # Both entities should be of compatible types
        if not (self.left.is_instance(self.right.type) or self.right.is_instance(self.left.type)):
            raise ValueError(
                f"Type mismatch in equality: {self.left.name}:{self.left.type.name} and {self.right.name}:{self.right.type.name}"
            )

    @cached_property
    def used_predicates(self) -> set[Predicate]:
        return set()

    @cached_property
    def exposed_variables(self) -> set[Variable]:
        """Get all variables from the entities."""
        return {self.left, self.right}

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL file."""
        eq_str = f"(= {self.left.name} {self.right.name})"
        if self.is_negative:
            return f"(not {eq_str})"
        return eq_str

    def ground(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> set[GroundAtom]:
        raise RuntimeError("Cannot ground an equality constraint into atoms.")

    def evaluate(self, sub: VarToObjSub, state: frozenset[GroundAtom]) -> bool:
        """Evaluate whether the equality holds given a substitution.

        Note: state parameter is unused but kept for consistency with other evaluate methods.
        """
        left_obj = sub[self.left]
        right_obj = sub[self.right]
        result = left_obj == right_obj
        return (not result) if self.is_negative else result

    @cached_property
    def _str(self) -> str:
        eq_str = f"{self.left.name} = {self.right.name}"
        if self.is_negative:
            return f"NOT({eq_str})"
        return eq_str


@dataclass(frozen=True, repr=False, eq=False)
class Operator:
    """Struct defining a symbolic operator (as in STRIPS).

    Lifted! Note here that the ignore_effects - unlike the
    add_effects and delete_effects - are universally
    quantified over all possible groundings.
    """

    name: str
    parameters: Sequence[Variable]
    preconditions: LiftedFormula
    effects: LiftedFormula

    def __post_init__(self) -> None:
        remaining_precond_vars = self.preconditions.exposed_variables - set(self.parameters)
        if len(remaining_precond_vars) > 0:
            raise ValueError(
                f"Syntax error: Action {self.name} has undeclared variables in precondition: {remaining_precond_vars}"
            )
        remaining_effect_vars = self.effects.exposed_variables - set(self.parameters)
        if len(remaining_effect_vars) > 0:
            raise ValueError(
                f"Syntax error: Action {self.name} has undeclared variables in effect: {remaining_effect_vars}"
            )
        if len(self.effects.used_predicates) == 0:
            raise ValueError(
                f"Action `{self.name}` has no effects. Every action must have at least one effect. If necessary, define new predicates."
            )

    # @lru_cache(maxsize=None)
    def ground(self, objects: tuple[Object, ...], state: frozenset[GroundAtom]) -> GroundOperator:
        """Ground into a _GroundOperator, given objects.

        Insist that objects are tuple for hashing in cache.
        """
        assert isinstance(objects, tuple)
        assert len(objects) == len(self.parameters)
        assert all(o.is_instance(p.type) for o, p in zip(objects, self.parameters))
        sub = dict(zip(self.parameters, objects))

        preconditions = self.preconditions.evaluate(sub, state)
        effects = self.effects.ground(sub, state)
        return GroundOperator(self, list(objects), preconditions, effects)

    @cached_property
    def _str(self) -> str:
        return f"""STRIPS-{self.name}:
    Parameters: {self.parameters}
    Preconditions: {self.preconditions}
    Effects: {self.effects}"""

    @cached_property
    def _hash(self) -> int:
        return hash(str(self))

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return str(self)

    def pddl_str(self) -> str:
        """Get a string representation suitable for writing out to a PDDL
        file."""
        params_str = " ".join(f"{p.name} - {p.type.name}" for p in self.parameters)
        preconds_str = "\n        ".join(self.preconditions.pddl_str().splitlines())
        effects_str = "\n        ".join(self.effects.pddl_str().splitlines())
        return f"""(:action {self.name}
    :parameters ({params_str})
    :precondition {preconds_str}
    :effect {effects_str}
  )"""

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, Operator)
        return str(self) == str(other)

    def __lt__(self, other: object) -> bool:
        assert isinstance(other, Operator)
        return str(self) < str(other)

    def __gt__(self, other: object) -> bool:
        assert isinstance(other, Operator)
        return str(self) > str(other)

    def copy_with(self, **kwargs: Any) -> Operator:
        """Create a copy of the operator, optionally while replacing any of the
        arguments."""
        default_kwargs = dict(
            name=self.name,
            parameters=self.parameters,
            preconditions=self.preconditions,
            effects=self.effects,
        )
        assert set(kwargs.keys()).issubset(default_kwargs.keys())
        default_kwargs.update(kwargs)
        # mypy is known to have issues with this pattern:
        # https://github.com/python/mypy/issues/5382
        return Operator(**default_kwargs)  # type: ignore

    def get_complexity(self) -> float:
        """Get the complexity of this operator.

        We only care about the arity of the operator, since that is what
        affects grounding. We'll use 2^arity as a measure of grounding
        effort.
        """
        return float(2 ** len(self.parameters))


@dataclass(frozen=True, repr=False, eq=False)
class GroundOperator:
    """A Operator + objects.

    Should not be instantiated externally.
    """

    parent: Operator
    objects: Sequence[Object]
    preconditions: bool
    effects: set[GroundAtom]

    @cached_property
    def _str(self) -> str:
        return f"""GroundSTRIPS-{self.name}:
    Parameters: {self.objects}
    Preconditions: {self.preconditions}
    Effects: {sorted(self.effects, key=str)}"""

    @cached_property
    def _hash(self) -> int:
        return hash(str(self))

    @property
    def name(self) -> str:
        """Name of this ground Operator."""
        return self.parent.name

    @property
    def short_str(self) -> str:
        """Abbreviated name, not necessarily unique."""
        obj_str = ", ".join([o.name for o in self.objects])
        return f"{self.name}({obj_str})"

    def __str__(self) -> str:
        return self._str

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: object) -> bool:
        assert isinstance(other, GroundOperator)
        return str(self) == str(other)

    def __lt__(self, other: object) -> bool:
        assert isinstance(other, GroundOperator)
        return str(self) < str(other)

    def __gt__(self, other: object) -> bool:
        assert isinstance(other, GroundOperator)
        return str(self) > str(other)


# Helper functions for creating negated predicates and literals
@overload
def Not(x: Predicate) -> Predicate: ...


@overload
def Not(x: LiftedAtom) -> LiftedAtom: ...


@overload
def Not(x: GroundAtom) -> GroundAtom: ...


@overload
def Not(x: ForAll) -> ForAll: ...


@overload
def Not(x: Exists) -> Exists: ...


@overload
def Not(x: When) -> When: ...


@overload
def Not(x: Imply) -> Imply: ...


@overload
def Not(x: EqualTo) -> EqualTo: ...


@overload
def Not(x: LiteralConjunction) -> LiteralDisjunction: ...


@overload
def Not(x: LiteralDisjunction) -> LiteralConjunction: ...


def Not(
    x: Union[
        Predicate, LiftedAtom, GroundAtom, ForAll, Exists, When, Imply, EqualTo, LiteralConjunction, LiteralDisjunction
    ],
) -> Union[
    Predicate, LiftedAtom, GroundAtom, ForAll, Exists, When, Imply, EqualTo, LiteralConjunction, LiteralDisjunction
]:
    """Negate a Predicate, Atom, or other logical structure."""
    if isinstance(x, Predicate):
        return x.get_negation()

    if isinstance(x, ForAll):
        return ForAll(x.variables, x.body, is_negative=(not x.is_negative))

    if isinstance(x, Exists):
        return Exists(x.variables, x.body, is_negative=(not x.is_negative))

    if isinstance(x, When):
        # NOT(WHEN(cond, eff)) = WHEN(cond, NOT(eff))
        return When(x.condition, Not(x.effect))

    if isinstance(x, Imply):
        # NOT(A => B) = A AND NOT(B)
        negated_consequent = Not(x.consequent)
        if isinstance(negated_consequent, (LiftedAtom, GroundAtom)):
            return LiteralConjunction([x.antecedent, negated_consequent])
        raise ValueError(f"Cannot negate Imply with consequent of type {type(x.consequent)}")

    if isinstance(x, EqualTo):
        # NOT(x = y) toggles is_negative
        return EqualTo(x.left, x.right, is_negative=(not x.is_negative))

    if isinstance(x, LiteralConjunction):
        # Apply De Morgan's law: NOT(A AND B) = (NOT A) OR (NOT B)
        negated_literals = []
        for lit in x.literals:
            negated_lit = Not(lit)
            if isinstance(negated_lit, (LiftedAtom, GroundAtom)):
                negated_literals.append(negated_lit)
        return LiteralDisjunction(negated_literals)

    if isinstance(x, LiteralDisjunction):
        # Apply De Morgan's law: NOT(A OR B) = (NOT A) AND (NOT B)
        negated_literals = []
        for lit in x.literals:
            negated_lit = Not(lit)
            if isinstance(negated_lit, (LiftedAtom, GroundAtom)):
                negated_literals.append(negated_lit)
        return LiteralConjunction(negated_literals)

    if isinstance(x, (LiftedAtom, GroundAtom)):
        # Create a negated predicate and apply it to the same entities
        negated_predicate = Not(x.predicate)
        if isinstance(x, LiftedAtom):
            return LiftedAtom(negated_predicate, x.variables)
        else:  # GroundAtom
            return GroundAtom(negated_predicate, x.objects)

    raise ValueError(f"Cannot negate object of type {type(x)}")


# Convenience higher-order types useful throughout the code
State = Any
ObjToVarSub = dict[Object, Variable]
ObjToObjSub = dict[Object, Object]
VarToObjSub = dict[Variable, Object]
VarToVarSub = dict[Variable, Variable]
LiftedOrGroundAtom = TypeVar("LiftedOrGroundAtom", LiftedAtom, GroundAtom, _Atom)
ObjectOrVariable = TypeVar("ObjectOrVariable", bound=_TypedEntity)

# Type alias for all lifted formula types that implement LiftedFormulaBase interface
LiftedFormula = Union[
    LiftedAtom,
    LiteralConjunction,
    LiteralDisjunction,
    ForAll,
    Exists,
    When,
    Imply,
    EqualTo,
]
