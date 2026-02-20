"""General interface for a planner.

Code copied from https://github.com/ronuchit/pddlgym_planners/blob/master/pddlgym_planners/fd.py
"""

import os
import time
import abc
from typing import Literal, Union, overload

from pddl_utils.structs.sas_parser import parse_sas_plan
from pddl_utils.structs.sas_structs import SasPlan, SasAction
from pddl_utils.structs.pddl_structs_parser import parse_domain


class Planner:
    """An abstract planner."""

    def __init__(self):
        self._statistics = {}

    @overload
    def plan_from_pddl(
        self,
        dom_file: str,
        prob_file: str,
        horizon=float("inf"),
        timeout: int = 10,
        remove_files: bool = False,
        return_output: Literal[True] = True,
        fix_capitalization: bool = True,
    ) -> tuple[SasPlan, str]: ...
    @overload
    def plan_from_pddl(
        self,
        dom_file: str,
        prob_file: str,
        horizon=float("inf"),
        timeout: int = 10,
        remove_files: bool = False,
        return_output: Literal[False] = False,
        fix_capitalization: bool = True,
    ) -> SasPlan: ...
    def plan_from_pddl(
        self, dom_file, prob_file, horizon=float("inf"), timeout=10, remove_files=False, return_output=False, fix_capitalization=True
    ) -> Union[SasPlan, tuple[SasPlan, str]]:
        """PDDL-specific planning method."""
        start_time = time.time()
        output = self._run(dom_file, prob_file, timeout)
        if remove_files:
            os.remove(dom_file)
            os.remove(prob_file)
        self._cleanup()
        if time.time() - start_time > timeout:
            raise PlanningTimeout("Planning timed out!")
        pddl_plan_str = self._output_to_plan(output)
        if len(pddl_plan_str) > horizon:
            raise PlanningFailure("PDDL planning failed due to horizon")

        pddl_plan = parse_sas_plan("\n".join(pddl_plan_str))
        
        # Map lowercase action names to correctly capitalized operator names from domain
        if fix_capitalization:
            pddl_plan = self._fix_action_capitalization(pddl_plan, dom_file)
        
        if return_output:
            return pddl_plan, output
        else:
            return pddl_plan

    @abc.abstractmethod
    def _run(self, dom_file, prob_file, timeout) -> str:
        raise NotImplementedError("Override me!")

    @abc.abstractmethod
    def _output_to_plan(self, output):
        raise NotImplementedError("Override me!")

    def _fix_action_capitalization(self, plan: SasPlan, dom_file: str) -> SasPlan:
        """Fix action names to match the capitalization in the domain file.
        
        Fast Downward outputs lowercase action names, but the original domain may have
        capitalized operator names. This method reads the domain and maps the lowercase
        names to their correctly capitalized versions.
        """
        with open(dom_file, 'r') as f:
            domain_str = f.read()
        domain = parse_domain(domain_str)
        
        # Create case-insensitive mapping from lowercase to correct name
        operator_map = {op.name.lower(): op.name for op in domain.operators}
        
        # Update action names in the plan
        fixed_actions = []
        for action in plan.actions:
            correct_name = operator_map.get(action.name.lower(), action.name)
            fixed_actions.append(SasAction(name=correct_name, args=action.args))
        
        return SasPlan(actions=fixed_actions)

    def _cleanup(self):
        """Allow subclasses to run cleanup after planning"""
        pass

    def reset_statistics(self):
        """Reset the internal statistics dictionary."""
        self._statistics = {}

    def get_statistics(self):
        """Get the internal statistics dictionary."""
        return self._statistics


class PlanningFailure(Exception):
    """Exception raised when planning fails."""

    pass


class PlanningTimeout(Exception):
    """Exception raised when planning times out."""

    pass
