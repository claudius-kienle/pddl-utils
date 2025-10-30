import os
import subprocess
from typing import Optional

VAL_URL = "https://github.com/KCL-Planning/VAL.git"


class VAL:
    """VAL validator"""

    def __init__(self):
        super().__init__()
        dirname = os.path.dirname(os.path.realpath(__file__))
        self._exec = os.path.join(dirname, "VAL/validate")
        print("Instantiating VAL", end=" ")
        print()
        if not os.path.exists(self._exec):
            self._install_val()

    def validate(self, dom_file: str, prob_file: Optional[str], plan_file: Optional[str], remove_files=False):
        """PDDL-specific planning method."""
        cmd_str = "{} -v {}".format(
            self._exec, dom_file
        )
        if prob_file is not None:
            cmd_str += " {}".format(prob_file)
        if plan_file is not None:
            cmd_str += " {}".format(plan_file)
        output = subprocess.getoutput(cmd_str)
        if remove_files:
            os.remove(dom_file)
            if prob_file is not None:
                os.remove(prob_file)
            if plan_file is not None:
                os.remove(plan_file)
        return True, output

    def _install_val(self):
        loc = os.path.dirname(self._exec)
        # Install and compile VAL.
        if not os.path.exists(loc):
            res_code = os.system("git clone {} {}".format(VAL_URL, loc))
            assert res_code == 0, "Could not clone VAL from {}".format(VAL_URL)
        res_code = os.system(
            "cd {} && git checkout a5565396007eee73ac36527fbf904142b3077c74 &&  make clean && sed -i 's/-Werror //g' Makefile && make && cd -".format(
                loc
            )
        )
        assert res_code == 0, "Could not build Fast-Downward in {}".format(loc)
        assert os.path.exists(self._exec)
