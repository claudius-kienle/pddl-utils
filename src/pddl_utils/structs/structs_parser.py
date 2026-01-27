import re
from typing import Literal, Optional, Sequence, overload
from pddl_utils.structs.structs import (
    Exists,
    ForAll,
    GroundAtom,
    LiftedAtom,
    NamedPredicate,
    LiftedFormula,
    LiteralConjunction,
    LiteralDisjunction,
    Not,
    When, 
    Imply,
    EqualTo,
    Object,
    Operator,
    Predicate,
    Type,
    Variable,
    is_a_keyword,
)
from python_utils.string_utils import remove_comments

from pddl_utils.structs.string_utils import until_next_closing_parenthesis, parentheses_groups

name_rgx = r"[a-zA-Z0-9-_]+"


def parse_type(type_str: str) -> Type:
    type_str = type_str.strip()
    if type_str == "object":
        raise ValueError("Type 'object' is not allowed for variables, as it is the super-type of all types.")
    if is_a_keyword(type_str):
        raise ValueError(f"Syntax error: {type_str} is a keyword and cannot be used as a type")
    return Type(type_str)


def parse_types(content_str: str) -> Sequence[Type]:
    types = list()
    # First, handle types with explicit supertypes (e.g., "type1 type2 - supertype")
    typed_matches = re.findall(r"([^-]+)-\s*(\w+)", content_str)
    for type_group in typed_matches:
        type_names = type_group[0].strip().split()
        type_super = parse_type(type_group[1].strip())
        for type_name in type_names:
            if type_name.strip():
                types.append(Type(type_name.strip(), parent=type_super))
    
    # Then, handle types without explicit supertypes (e.g., "block robot")
    # Remove all typed definitions from content_str
    remaining = content_str
    for match in typed_matches:
        remaining = remaining.replace(f"{match[0]}- {match[1]}", "")
        remaining = remaining.replace(f"{match[0]}-{match[1]}", "")
    
    # Parse remaining untyped type names (they implicitly inherit from object)
    untyped_names = remaining.strip().split()
    for type_name in untyped_names:
        if type_name.strip() and not any(t.name == type_name.strip() for t in types):
            types.append(Type(type_name.strip(), parent=None))
    
    return types


def parse_variable(variables_str: str, variable_type: Optional[Type] = None) -> Variable:
    if " - " in variables_str:
        variables_str, variable_type_str = variables_str.strip().split(" - ")
        if variable_type_str is not None:
            variable_type = parse_type(variable_type_str)
    variable_name = variables_str.strip()
    if variable_type is None:
        raise ValueError(f"Syntax error: Variable {variable_name} must have a type.")
    if is_a_keyword(variable_name):
        raise ValueError(f"Syntax error: {variable_name} is a keyword and cannot be used as a variable")
    return Variable(variable_name, variable_type)


def parse_variable_definitions(variables_str: str) -> Sequence[Variable]:
    variables = []
    for var_set in re.findall(rf"(?:\?.+? +)+\- +[\w\W]+?(?=(?:\?|$))", variables_str):
        assert isinstance(var_set, str)
        variable_str, var_type = var_set.strip().split(" - ")
        variable_str = variable_str.strip().split()
        for variable_str in variable_str:
            variables.append(parse_variable(variable_str, parse_type(var_type)))
    n_vars = len(re.findall(rf"\?{name_rgx}", variables_str))
    if len(variables) != n_vars:
        raise ValueError(
            f"Syntax error: All defined variables must have a type. Found {n_vars} variables, but only {len(variables)} have types."
        )
    return variables


def parse_object(constant_str: str, constant_type: Optional[Type] = None) -> Object:
    if " - " in constant_str:
        constant_str, constant_type_str = constant_str.strip().split(" - ")
        if constant_type_str is not None:
            constant_type = parse_type(constant_type_str)
    if constant_type is None:
        raise ValueError(f"Syntax error: Constant {constant_str} must have a type.")
    if is_a_keyword(constant_str):
        raise ValueError(f"Syntax error: {constant_str} is a keyword and cannot be used as a constant")
    return Object(constant_str, constant_type)


def parse_objects(content_str: str) -> Sequence[Object]:
    objects = list()
    for obj_group in re.findall(r"([^-]+)-\s*(\w+)", content_str):
        obj_names = obj_group[0].strip().split()
        obj_type = parse_type(obj_group[1].strip())
        for obj_name in obj_names:
            if obj_name.strip():
                objects.append(Object(obj_name.strip(), obj_type))
    return objects


def parse_ground_atom(ground_atom_str: str, *, known_predicates: Optional[frozenset[Predicate]] = None) -> GroundAtom:
    atom = parse_formula(ground_atom_str, only_variables=False, known_predicates=known_predicates)
    assert isinstance(atom, set) and len(atom) == 1
    return next(iter(atom))


def _parse_ground_atom(ground_atom_str: str, *, known_predicates: frozenset[Predicate]) -> GroundAtom:
    assert ground_atom_str[0] == "(" and ground_atom_str[-1] == ")", "The predicate must start and end with parentheses"
    assert (
        ground_atom_str.count("(") == 1 and ground_atom_str.count(")") == 1
    ), f"Invalid syntax: '{str(ground_atom_str)}' is not a valid predicate. Maybe you forgot an operator?"

    matches = re.match(rf"\(({name_rgx}) *(?: +([\w\W]+))?\)", ground_atom_str)
    if matches is None:
        raise ValueError(
            "Syntax error: Invalid predicate definition %s (expecting ({pred_name} {pred_args..}))" % ground_atom_str
        )
    predicate_name = matches.group(1)
    predicate_args = matches.group(2)
    if predicate_args is None:
        predicate_args = []
    else:
        predicate_args = [arg.strip() for arg in predicate_args.split()]

    predicate = next((p for p in known_predicates if p.name == predicate_name), None)
    if predicate is None:
        raise ValueError(f"Predicate {predicate_name} is not known in the current context.")

    objects = [parse_object(a, t) for a, t in zip(predicate_args, predicate.types)]
    return GroundAtom(predicate, objects)


def parse_predicate(predicate_str: str, *, known_predicates: Optional[frozenset[Predicate]] = None) -> NamedPredicate:
    assert predicate_str[0] == "(" and predicate_str[-1] == ")", "The predicate must start and end with parentheses"
    assert (
        predicate_str.count("(") == 1 and predicate_str.count(")") == 1
    ), f"Invalid syntax: '{str(predicate_str)}' is not a valid predicate. Maybe you forgot an operator?"

    matches = re.match(rf"\(({name_rgx}) *(?: +([\w\W]+))?\)", predicate_str)
    if matches is None:
        raise ValueError(
            "Syntax error: Invalid predicate definition %s (expecting ({pred_name} {pred_args..}))" % predicate_str
        )
    predicate_name = matches.group(1)
    predicate_args = matches.group(2)
    if predicate_args is None:
        predicate_args = []
    else:
        predicate_args = re.findall(rf"\??{name_rgx}(?: \- {name_rgx})?", predicate_args)
        if any(arg[0] != "?" for arg in predicate_args):
            raise ValueError(
                f"Syntax error: Predicate arguments of {predicate_name} must be variables. Found: {predicate_args}"
            )

    if is_a_keyword(predicate_name):
        raise ValueError(f"Syntax error: {predicate_name} is a keyword and cannot be used as a predicate name")

    known_predicates_by_name = {p.name: p for p in known_predicates} if known_predicates else {}
    predicate = known_predicates_by_name.get(predicate_name)
    if predicate is None and (len(predicate_args) > 0 and "-" not in predicate_str):
        raise ValueError(f"Predicate {predicate_name} is not known in the current context.")
    existing_types = predicate.types if predicate else [None for _ in range(len(predicate_args))]
    variables = [parse_variable(a, t) for a, t in zip(predicate_args, existing_types)]
    return NamedPredicate(name=predicate_name, variables=variables)


def parse_lifted_atom(lifted_atom_str: str, *, known_predicates: Optional[frozenset[Predicate]] = None) -> LiftedAtom:
    predicate = parse_predicate(lifted_atom_str, known_predicates=known_predicates)
    return LiftedAtom(
        Predicate(
            predicate.name, types=predicate.types, is_negated=predicate.is_negated, _classifier=predicate._classifier
        ),
        predicate.variables,
    )


@overload
def parse_formula(
    formula_str: str,
    *,
    only_variables: Literal[True] = True,
    known_predicates: Optional[frozenset[Predicate]] = None,
    variables: Optional[Sequence[Variable]] = None,
    unsupported_formulas: Optional[list[str]] = None,
) -> LiftedFormula: ...
@overload
def parse_formula(
    formula_str: str,
    *,
    only_variables: Literal[False] = False,
    known_predicates: Optional[frozenset[Predicate]] = None,
    variables: Optional[Sequence[Variable]] = None,
    unsupported_formulas: Optional[list[str]] = None,
) -> frozenset[GroundAtom]: ...
def parse_formula(
    formula_str: str,
    only_variables: bool = True,
    *,
    known_predicates: Optional[frozenset[Predicate]] = None,
    variables: Optional[Sequence[Variable]] = None,
    unsupported_formulas: Optional[list[str]] = None,
) -> LiftedFormula | LiteralConjunction | frozenset[GroundAtom]:
    assert formula_str[0] == "(" and formula_str[-1] == ")", "The formula must start and end with parentheses"
    formula_str = remove_comments(formula_str)

    if formula_str in ["()", "(and)", "(and )"]:
        if only_variables:
            return LiteralConjunction([])
        else:
            return frozenset()

    matches = re.match(rf"\(([a-zA-Z0-9_\-\=]+)(?:\s+([\w\W]+))?\)", formula_str)
    if matches is None:
        raise ValueError(
            "Syntax error: Invalid formula definition %s (expecting ({formula_name} {formula_args..}))" % formula_str
        )
    formula_name = matches.group(1)
    formula_content = matches.group(2)

    if unsupported_formulas is not None and formula_name in unsupported_formulas:
        raise ValueError(f"Syntax error: Formula `{formula_name}` is not supported in the current context")

    if is_a_keyword(formula_name):
        # must be a formula
        if formula_name in ["exists", "forall"]:
            variables_str, conditions_str = parentheses_groups(formula_content.strip())
            parsed_variables = parse_variable_definitions(variables_str[1:-1])
            # Merge with existing variables
            merged_variables = list(variables) if variables else []
            merged_variables.extend(parsed_variables)
            conditions = parse_formula(
                conditions_str,
                only_variables=True,
                known_predicates=known_predicates,
                variables=merged_variables,
                unsupported_formulas=unsupported_formulas,
            )
            if formula_name == "forall":
                return ForAll(parsed_variables, conditions)
            elif formula_name == "exists":
                return Exists(parsed_variables, conditions)
        elif formula_name == "=":
            variables_by_name = {v.name: v for v in variables} if variables else {}
            terms = []
            for term_str in formula_content.split():
                term_name = term_str.strip()
                assert term_name in variables_by_name
                terms.append(variables_by_name[term_name])
            return EqualTo(*terms)

        try:
            terms = list(
                map(
                    lambda t: parse_formula(
                        t,
                        only_variables=only_variables,
                        known_predicates=known_predicates,
                        variables=variables,
                        unsupported_formulas=unsupported_formulas,
                    ),
                    parentheses_groups(formula_content.strip()) if formula_content is not None else [],
                )
            )
        except AssertionError:
            raise ValueError(f"Syntax error: {formula_content} is not a valid formula")
        if formula_name == "and":
            if only_variables:
                return LiteralConjunction(terms)
            else:
                return set(t for ts in terms for t in ts)
        elif formula_name == "or":
            assert only_variables
            return LiteralDisjunction(terms)
        elif formula_name == "not":
            if len(terms) != 1:
                raise ValueError(f"Syntax error: Not operator must have one argument: {formula_str}")
            term = terms[0]
            # if isinstance(term, ExistsCondition):
            #     raise ValueError(f"Syntax error: Not operator must not be used with quantifiers: {formula_str}")
            if isinstance(term, set):
                return {Not(t) for t in term}
            return Not(term)
        elif formula_name == "when":
            assert only_variables
            return When(condition=terms[0], effect=terms[1])
        elif formula_name == "imply":
            assert only_variables
            return Imply(*terms)
        elif formula_name in ["if", "implies"]:
            assert only_variables
            raise ValueError("invalid formula name `%s` in `%s`" % (formula_name, formula_str))
        else:
            raise ValueError("invalid formula name `%s` in `%s`" % (formula_name, formula_str))
            # raise NotImplementedError(str(formula_str))
    else:
        # predicate
        if only_variables:
            return parse_lifted_atom(formula_str, known_predicates=known_predicates)
        else:
            assert known_predicates is not None
            atom = _parse_ground_atom(formula_str, known_predicates=known_predicates)
            return {atom}


def parse_operator(
    operator_str: str, *, previous_action: Optional[Operator] = None, known_predicates: Optional[frozenset[Predicate]] = None
):
    operator_str = remove_comments(operator_str)
    matches = re.match(rf"\(:action ({name_rgx})([\w\W]+)\)", operator_str.strip())
    if matches is None:
        if previous_action is None:
            raise ValueError(f"Syntax error: {operator_str} is not a valid action definition")
        else:
            action_name = previous_action.name
            after_group = operator_str
    else:
        action_name = matches.group(1)
        after_group = matches.group(2)

    if previous_action is not None:
        parameters = previous_action.parameters
        preconditions = previous_action.preconditions
        effects = previous_action.effects
    else:
        parameters = None
        preconditions = None
        effects = None

    while after_group != "":
        matches = re.match(rf"(:{name_rgx})([\w\W]+)", after_group.strip())

        if matches is None:
            raise ValueError(
                "Syntax error: Invalid pddl action definition for action %s:\n`%s`" % (action_name, after_group.strip())
            )

        var_type = matches.group(1)
        var_content = matches.group(2)
        var_content, after_group = until_next_closing_parenthesis(var_content.strip())
        var_content = var_content.strip()

        supported_var_types = [":parameters", ":precondition", ":effect"]

        if var_type == ":parameters":
            try:
                parameters = parse_variable_definitions(var_content[1:-1])
            except ValueError as e:
                raise ValueError("Parsing parameters in `%s`: %s" % (action_name, str(e)))
        elif var_type == ":precondition":
            try:
                preconditions = parse_formula(var_content, known_predicates=known_predicates, variables=parameters)
            except ValueError as e:
                raise ValueError("Parsing precondition in `%s`: %s" % (action_name, str(e)))
        elif var_type == ":effect":
            try:
                effects = parse_formula(
                    var_content, known_predicates=known_predicates, variables=parameters, unsupported_formulas=["or", "exists"]
                )
            except ValueError as e:
                raise ValueError("Parsing effect in `%s`: %s" % (action_name, str(e)))
        else:
            raise ValueError(
                f"Syntax error: {var_type} is an invalid type for an action definition (supported are: %s). Correct the syntax of action %s"
                % (", ".join(supported_var_types), action_name)
            )

    if parameters is None:
        raise ValueError(f"Syntax error: Action {action_name} must have parameters")
    if preconditions is None:
        raise ValueError(f"Syntax error: Action {action_name} must have a precondition")
    if effects is None:
        raise ValueError(f"Syntax error: Action {action_name} must have an effect")

    return Operator(
        name=action_name,
        parameters=parameters,
        preconditions=preconditions,
        effects=effects,
    )
