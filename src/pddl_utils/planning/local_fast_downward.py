"""Fast-downward planner.
http://www.fast-downward.org/ObtainingAndRunningFastDownward

Code copied from https://github.com/ronuchit/pddlgym_planners/blob/master/pddlgym_planners/fd.py
"""

import logging
import os
import sys
import subprocess
import tempfile
from pddl_utils.planning.pddl_planner import PDDLPlanner


logger = logging.getLogger(__name__)

FD_URL = "https://github.com/aibasel/downward.git"


class LocalFastDownward(PDDLPlanner):
    """Fast-downward planner."""

    def __init__(self, alias_flag="--alias seq-opt-lmcut", final_flags=""):
        super().__init__()
        dirname = os.path.dirname(os.path.realpath(__file__))
        self._exec = os.path.join(dirname, "FD/fast-downward.py")
        _bin_exec = os.path.join(dirname, "FD/builds/release/bin/downward")
        logger.debug("Instantiating FD")
        if alias_flag:
            logger.debug("with %s", alias_flag)
        if final_flags:
            logger.debug("with %s", final_flags)
        self._alias_flag = alias_flag
        self._final_flags = final_flags
        if not os.path.exists(self._exec) or not os.path.exists(_bin_exec):
            self._install_fd()

    def plan_all_from_pddl(self, dom_file: str, prob_file: str, timeout: int) -> "list[SasPlan]":
        """Run FD and return all improving plans LAMA writes to disk (sas_plan.1, .2, ...)."""
        from pathlib import Path
        from pddl_utils.structs.sas_parser import parse_sas_plan
        from pddl_utils.structs.sas_structs import SasPlan

        with tempfile.TemporaryDirectory() as plan_dir:
            plan_base = os.path.join(plan_dir, "sas_plan")
            sas_file = tempfile.NamedTemporaryFile(delete=False).name
            timeout_cmd = "gtimeout" if sys.platform == "darwin" else "timeout"
            cmd_str = "{} {} {} {} --plan-file {} --sas-file {} {} {} {}".format(
                timeout_cmd, timeout, self._exec, self._alias_flag,
                plan_base, sas_file, dom_file, prob_file, self._final_flags,
            )
            subprocess.getoutput(cmd_str)
            self._cleanup()

            plans = []
            for plan_file in sorted(Path(plan_dir).glob("sas_plan.[0-9]*")):
                try:
                    plan = parse_sas_plan(plan_file.read_text())
                    plan = self._fix_capitalization(plan, dom_file, prob_file)
                    plans.append(plan)
                except Exception:
                    pass
            return plans

    def _run(self, dom_file, prob_file, timeout):
        sas_file = tempfile.NamedTemporaryFile(delete=False).name
        timeout_cmd = "gtimeout" if sys.platform == "darwin" else "timeout"
        cmd_str = "{} {} {} {} --sas-file {} {} {} {}".format(
            timeout_cmd, timeout, self._exec, self._alias_flag, sas_file, dom_file, prob_file, self._final_flags
        )
        output = subprocess.getoutput(cmd_str)
        return output

    def _cleanup(self):
        """Run FD cleanup"""
        cmd_str = "{} --cleanup".format(self._exec)
        subprocess.getoutput(cmd_str)

    def _install_fd(self):
        loc = os.path.dirname(self._exec)
        # Install and compile FD.
        if not os.path.exists(loc):
            res_code = os.system("git clone {} {}".format(FD_URL, loc))
            assert res_code == 0, "Could not clone Fast-Downward from {}".format(FD_URL)
        res_code = os.system(
            f"cd {loc} && git checkout release-24.06.1 && " "CXXFLAGS='-include limits' ./build.py && cd -"
        )
        assert res_code == 0, "Could not build Fast-Downward in {}".format(loc)
        assert os.path.exists(self._exec)
