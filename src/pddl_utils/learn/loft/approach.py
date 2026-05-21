"""LOFT operator-learning algorithm, ported to pddl_utils structs.

Mirrors ``approaches/loft.py`` from the reference implementation:
https://github.com/ronuchit/LOFT_IROS_2021
"""

from collections import defaultdict
from itertools import count
import functools
import heapq as hq

import numpy as np

from pddl_utils.structs import Variable

from pddl_utils.learn.loft.ndrs import NDR, NDRSet, NOISE_OUTCOME
from pddl_utils.learn.loft.utils import (
    construct_effects,
    lift_lit_set,
    make_atom,
    ndrs_to_operators,
    preconditions_covered,
    prune_redundancies,
    transition_covered,
    unify,
)

VERBOSE = False


class LOFT:
    """Run with `train((transitions, []))` then read `self.operators`."""

    def __init__(self, config):
        self._cf = config
        self._neg_cache = None
        self.operators = None

    def train(self, data):
        demos, _ = data
        ndrs = self._learn_all_ndrs(demos)
        self.operators = ndrs_to_operators(ndrs)
        print("Learned operators:")
        for op in self.operators:
            print(op)
        return self.operators

    def _learn_all_ndrs(self, transitions):
        print(f"Running BUILP on {len(transitions)} transitions")
        transitions_by_action = defaultdict(list)
        for state, action, next_state in transitions:
            assert len(set(action.entities)) == len(action.entities), \
                "Action arguments are assumed to be unique"
            effects = construct_effects(state, next_state)
            transitions_by_action[action.predicate].append(
                (frozenset(state), action, frozenset(effects)))

        ndrs = {}
        for act_pred in sorted(transitions_by_action):
            act_transitions = transitions_by_action[act_pred]
            act_ndrs, lifted_act = self._learn_ndrs(act_pred, act_transitions)
            ndrs[lifted_act] = act_ndrs

        if self._cf.builp_learn_probabilities:
            new_ndrs = {}
            for lifted_act, ndr_set in ndrs.items():
                act_pred = lifted_act.predicate
                act_transitions = transitions_by_action[act_pred]
                ndr_set = self._recover_ndr_probabilities(ndr_set, act_transitions)
                ndr_set = self._determinize_ndrs(ndr_set)
                new_ndrs[lifted_act] = ndr_set
            ndrs = new_ndrs

        return ndrs

    def _learn_ndrs(self, act_pred, transitions):
        action_vars = [Variable(f"?x{i}", t) for i, t in enumerate(act_pred.types)]
        lifted_action = make_atom(act_pred, action_vars)

        lifted_effects, partitioned_transitions = \
            self._partition_transitions_by_lifted_effects(
                transitions, lifted_action)

        ndrs = []
        score = 0.
        default_ndr = None
        for i, positive_transitions in enumerate(partitioned_transitions):
            score -= self._get_min_possible_score(len(positive_transitions))
            if not self._cf.builp_learn_empty_effects and not lifted_effects[i]:
                continue
            negative_transitions = tuple(
                e for j, group in enumerate(partitioned_transitions)
                if i != j for e in group)
            if VERBOSE:
                print(f"Learning preconditions for action: {lifted_action}")
                print(f"with effects: {lifted_effects[i]}")
                print(f"and with {len(positive_transitions)} positives")
                print(f"and with {len(negative_transitions)} negatives")
            lifted_preconditions, pre_score = self._learn_preconditions(
                lifted_action, lifted_effects[i],
                positive_transitions, negative_transitions)
            score += pre_score
            assert score >= 0.

            default_ndr = None
            for pre in lifted_preconditions:
                ndr = NDR(lifted_action, list(pre), [1.0, 0.0],
                          [lifted_effects[i], {NOISE_OUTCOME}])
                if not pre:
                    assert default_ndr is None
                    default_ndr = ndr
                else:
                    ndrs.append(ndr)

        return NDRSet(lifted_action, ndrs, default_ndr=default_ndr), \
            lifted_action

    @staticmethod
    def _partition_transitions_by_lifted_effects(transitions, lifted_action):
        lifted_effects = []
        partitions = []
        for transition in transitions:
            _, ground_action, effects = transition
            assert unify(frozenset({ground_action}),
                         frozenset({lifted_action}))[0]
            partition_index = None
            for i, lifted_eff in enumerate(lifted_effects):
                if unify(effects | {ground_action},
                         lifted_eff | {lifted_action})[0]:
                    partition_index = i
                    break
            if partition_index is None:
                partitions.append([transition])
                obj_to_var = dict(zip(ground_action.entities,
                                      lifted_action.entities))
                lifted_eff = frozenset(lift_lit_set(effects, obj_to_var))
                assert lifted_eff not in lifted_effects
                lifted_effects.append(lifted_eff)
            else:
                partitions[partition_index].append(transition)
        assert sum(int(not eff) for eff in lifted_effects) <= 1
        return lifted_effects, partitions

    def _learn_preconditions(self, lifted_action, lifted_effects,
                             positive_transitions, negative_transitions):
        all_preconditions = []
        remaining_positives = list(positive_transitions)
        score = float("inf")

        for _ in range(self._cf.builp_max_preconditions_per_effect):
            new_preconditions, new_score = self._learn_single_preconditions(
                lifted_action, lifted_effects,
                remaining_positives, negative_transitions)

            if new_preconditions is not None:
                new_remaining_positives = []
                for t in remaining_positives:
                    if not transition_covered(t, new_preconditions,
                                              lifted_action, lifted_effects):
                        new_remaining_positives.append(t)
                    else:
                        negative_transitions = negative_transitions + (t,)
                remaining_positives = new_remaining_positives

            if new_preconditions is None or new_score == float("inf"):
                break

            score = new_score
            assert new_preconditions not in all_preconditions
            all_preconditions.append(new_preconditions)

            if not remaining_positives:
                break

        assert score != -float("inf")
        return all_preconditions, score

    def _learn_single_preconditions(self, lifted_action, lifted_effects,
                                    positive_transitions, negative_transitions):
        tiebreak = count()
        queue = []
        best_score = float("inf")
        best_preconditions = None
        visited = set()
        hq.heappush(queue, (None, None, None))
        self._neg_cache = {None: set()}

        for _ in range(self._cf.builp_max_search_iters):
            if not queue:
                break
            _, _, preconditions = hq.heappop(queue)

            for child in self._get_precond_successors(
                    preconditions, positive_transitions,
                    lifted_action, lifted_effects):
                if child in visited:
                    continue
                if len(child) > self._cf.builp_max_rule_size:
                    continue
                child_score = self._score_preconditions(
                    child, lifted_action, lifted_effects,
                    positive_transitions, negative_transitions,
                    preconditions)
                if child_score < best_score and \
                        not self._preconditions_malformed(
                            child, lifted_action, lifted_effects):
                    best_score = child_score
                    best_preconditions = child
                hq.heappush(queue, (child_score, next(tiebreak), child))
                visited.add(child)

        return best_preconditions, best_score

    def _get_initial_preconditions(self, positive_transitions,
                                   lifted_action, lifted_effects):
        initial_preconditions = set()
        for state, action, effects in positive_transitions:
            state = prune_redundancies(state)
            if self._cf.builp_referenced_objects_only:
                referenced_objs = set(action.entities) | \
                    {o for lit in effects for o in lit.entities}
                state = {lit for lit in state
                         if all(o in referenced_objs for o in lit.entities)}
            obj_to_var = unify(
                effects | {action}, lifted_effects | {lifted_action})[1]
            lifted_preconditions = frozenset(
                lift_lit_set(state, obj_to_var))
            initial_preconditions.add(lifted_preconditions)
        return initial_preconditions

    def _get_precond_successors(self, preconditions, positive_transitions,
                                lifted_action, lifted_effects):
        if preconditions is None:
            all_initial = self._get_initial_preconditions(
                positive_transitions, lifted_action, lifted_effects)
            for initial in all_initial:
                self._neg_cache[initial] = set()
            return all_initial
        successors = []
        preconditions = sorted(preconditions)
        for i in range(len(preconditions)):
            successor = preconditions[:i] + preconditions[i + 1:]
            successors.append(frozenset(successor))
        return successors

    def _get_min_possible_score(self, num_examples):
        return -self._cf.builp_true_pos_weight * num_examples

    def _score_preconditions(self, preconditions, lifted_action, lifted_effects,
                             positive_transitions, negative_transitions,
                             parent):
        assert parent in self._neg_cache
        self._neg_cache[preconditions] = set()
        if self._preconditions_malformed(preconditions, lifted_action,
                                         lifted_effects):
            return 0.

        num_true_positives = 0
        num_false_positives = 0
        for transition in positive_transitions:
            _, assignments = preconditions_covered(
                transition, preconditions, lifted_action, ret_assignments=True)
            if len(assignments) != 1:
                continue
            if transition_covered(transition, preconditions,
                                  lifted_action, lifted_effects):
                num_true_positives += 1
            else:
                num_false_positives += 1

        num_false_positives += self._tally_false_positives(
            preconditions, negative_transitions, lifted_action, parent)

        score = self._cf.builp_false_pos_weight * num_false_positives - \
            self._cf.builp_true_pos_weight * num_true_positives
        all_vars = {v for lit in preconditions for v in lit.entities}
        score += self._cf.builp_var_count_weight * len(all_vars)
        score += self._cf.builp_rule_size_weight * len(preconditions)
        return score

    @functools.lru_cache(maxsize=100000)
    def _tally_false_positives(self, preconditions, negative_transitions,
                               lifted_action, parent):
        num_false_positives = 0
        for i, transition in enumerate(negative_transitions):
            if i in self._neg_cache[parent]:
                num_false_positives += 1
                self._neg_cache[preconditions].add(i)
            else:
                if preconditions_covered(transition, preconditions,
                                         lifted_action):
                    num_false_positives += 1
                    self._neg_cache[preconditions].add(i)
        return num_false_positives

    @staticmethod
    def _preconditions_malformed(preconditions, lifted_action, lifted_effects):
        effect_vars = {e for eff in lifted_effects for e in eff.entities
                       if isinstance(e, Variable)}
        action_vars = {e for e in lifted_action.entities
                       if isinstance(e, Variable)}
        precondition_vars = {e for pre in preconditions for e in pre.entities
                             if isinstance(e, Variable)}
        return not effect_vars.issubset(precondition_vars | action_vars)

    def _recover_ndr_probabilities(self, ndr_set, act_transitions):
        lifted_action = ndr_set.action
        never_covered_transitions = set(act_transitions)
        preconditions_to_effects = defaultdict(set)
        for ndr in ndr_set:
            pre = frozenset(ndr.preconditions)
            for eff in ndr.effects:
                if NOISE_OUTCOME in eff:
                    continue
                preconditions_to_effects[pre].add(frozenset(eff))
        new_ndrs = []
        for pre in sorted(preconditions_to_effects):
            if len(pre) == 0:
                continue
            pre_transitions = []
            for transition in act_transitions:
                if preconditions_covered(transition, pre, lifted_action):
                    pre_transitions.append(transition)
                    never_covered_transitions.discard(transition)
            outcomes = sorted(preconditions_to_effects[pre])
            probs = self._recover_single_ndr_probabilities(
                pre_transitions, outcomes, pre, lifted_action)
            new_ndrs.append(NDR(lifted_action, list(pre), probs, outcomes,
                                require_noise_outcome=False))
        pre = frozenset()
        pre_transitions = never_covered_transitions
        if len(pre_transitions) == 0:
            outcomes = [frozenset()]
            probs = [1.0]
        else:
            outcomes = sorted(preconditions_to_effects[pre])
            probs = self._recover_single_ndr_probabilities(
                pre_transitions, outcomes, pre, lifted_action)
        default_ndr = NDR(lifted_action, list(pre), probs, outcomes,
                          require_noise_outcome=False)
        return NDRSet(lifted_action, new_ndrs, default_ndr=default_ndr)

    @staticmethod
    def _recover_single_ndr_probabilities(pre_transitions, outcomes,
                                          pre, lifted_action):
        probs = []
        for outcome in outcomes:
            num_covered = 0
            num_not_covered = 0
            for transition in pre_transitions:
                covered, assigns = transition_covered(
                    transition, pre, lifted_action, outcome,
                    ret_assignments=True)
                if not covered or len(assigns) > 1:
                    num_not_covered += 1
                else:
                    num_covered += 1
            probs.append(num_covered / (num_covered + num_not_covered))
        return probs

    def _determinize_ndrs(self, ndr_set):
        new_ndrs = []
        lifted_action = ndr_set.action
        default_ndr = None
        for ndr in ndr_set:
            split_ndrs = self._determinize_ndr(ndr)
            if len(ndr.preconditions) == 0:
                assert len(split_ndrs) == 1
                assert default_ndr is None
                default_ndr = split_ndrs[0]
            else:
                new_ndrs.extend(split_ndrs)
        assert default_ndr is not None
        return NDRSet(lifted_action, new_ndrs, default_ndr=default_ndr)

    def _determinize_ndr(self, ndr):
        pre = ndr.preconditions
        lifted_action = ndr.action
        if len(pre) == 0:
            max_prob_idx = np.argmax(ndr.effect_probs)
            max_prob_outcome = ndr.effects[max_prob_idx]
            return [NDR(lifted_action, list(pre), [1.0, 0.0],
                        [max_prob_outcome, {NOISE_OUTCOME}])]
        split_ndrs = []
        for prob, outcome in zip(ndr.effect_probs, ndr.effects):
            if prob < self._cf.effect_prob_threshold:
                continue
            split_ndrs.append(NDR(lifted_action, list(pre), [1.0, 0.0],
                                  [outcome, {NOISE_OUTCOME}]))
        return split_ndrs
