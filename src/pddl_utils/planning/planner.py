"""General interface for a planner.

Code copied from https://github.com/ronuchit/pddlgym_planners/blob/master/pddlgym_planners/fd.py
"""

import os
import time
import abc
import subprocess
import numpy as np


class Planner:
    """An abstract planner."""

    def __init__(self):
        self._statistics = {}

    def plan_from_pddl(self, dom_file, prob_file, horizon=np.inf, timeout=10, remove_files=False):
        """PDDL-specific planning method."""
        start_time = time.time()
        output = self._run(dom_file, prob_file, timeout)
        if remove_files:
            os.remove(dom_file)
            os.remove(prob_file)
        self._cleanup()
        if time.time() - start_time > timeout:
            raise PlanningTimeout("Planning timed out!")
        pddl_plan = self._output_to_plan(output)
        if len(pddl_plan) > horizon:
            raise PlanningFailure("PDDL planning failed due to horizon")
        return pddl_plan

    @abc.abstractmethod
    def _run(self, dom_file, prob_file, timeout) -> str:
        raise NotImplementedError("Override me!")

    @abc.abstractmethod
    def _output_to_plan(self, output):
        raise NotImplementedError("Override me!")

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
