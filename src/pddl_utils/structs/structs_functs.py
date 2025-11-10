from pddl_utils.structs.structs import GroundAtom


def transition(curr_state: set[GroundAtom], effect: set[GroundAtom]) -> set[GroundAtom]:
    """Apply the effect to the current state and return the new state."""
    new_state = set(curr_state)
    for atom in effect:
        new_state.discard(GroundAtom(atom.predicate.get_negation(), atom.objects))  # remove negation if present
        new_state.add(atom)
    return new_state
