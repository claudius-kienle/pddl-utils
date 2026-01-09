import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import docker
from docker.errors import DockerException

from pddl_utils.planning.pddl_planner import PDDLPlanner

logger = logging.getLogger(__name__)


class DockerFastDownward(PDDLPlanner):

    def __init__(self, alias_flag="--alias seq-opt-lmcut"):
        super().__init__()
        logger.debug("Instantiating FD")
        if alias_flag:
            logger.debug("with %s", alias_flag)
        self.client = docker.from_env()
        self._alias_flag = alias_flag

    def _is_docker_running(self) -> bool:
        try:
            self.client.ping()  # Sends a request to Docker to check if it's alive
            return True
        except DockerException:
            return False

    def _run(self, dom_file, prob_file, timeout):
        assert self._is_docker_running()
        # heuristics can be found at https://www.fast-downward.org/Doc/Evaluator

        with TemporaryDirectory() as docker_dir:
            docker_dir = Path(docker_dir)
            tmp_domain_file = "domain.pddl"
            tmp_problem_file = "problem.pddl"
            shutil.copy(dom_file, docker_dir / tmp_domain_file)
            shutil.copy(prob_file, docker_dir / tmp_problem_file)

            cmd = self._alias_flag or " --alias lama-first "
            cmd += f" --search-time-limit {timeout or 60} "
            cmd += " /pddls/%s /pddls/%s" % (tmp_domain_file, tmp_problem_file)

            container = self.client.containers.run(
                image="aibasel/downward",
                command=cmd,
                mem_limit="16g",
                working_dir="/pddls",
                entrypoint="/workspace/downward/fast-downward.py",
                volumes={docker_dir.absolute().as_posix(): {"bind": "/pddls", "mode": "rw"}},
                detach=True,
            )
            # result = container.wait()
            container.wait()
            # success = 0 <= result["StatusCode"] <= 3  # https://www.fast-downward.org/latest/documentation/exit-codes/
            response = container.logs().decode().strip()

        container.remove(force=True)

        return response

        # sas_plan_file = next(docker_dir.glob("sas_plan*"), None)
        # if success:
        #     assert sas_plan_file is not None
        #     sas_plan = parse_sas_plan(sas_plan_file.read_text())
        # else:
        #     sas_plan = None

        # return sas_plan, response
