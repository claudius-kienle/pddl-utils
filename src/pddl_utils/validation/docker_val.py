import logging
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from typing import Optional

import docker
from docker.errors import DockerException
from pddl_utils.validation.val import VAL

logger = logging.getLogger(__name__)


class DockerVAL(VAL):

    def __init__(self):
        self.client = docker.from_env()

    def _is_docker_running(self) -> bool:
        try:
            self.client.ping()  # Sends a request to Docker to check if it's alive
            return True
        except DockerException:
            return False

    def _validate(self, dom_file: str, prob_file: Optional[str], plan_file: Optional[str]) -> tuple[bool, str]:
        with TemporaryDirectory() as docker_dir:
            docker_dir = Path(docker_dir)
            domain_file = docker_dir / "domain.pddl"
            shutil.copy(dom_file, domain_file)
            options = "-v"
            cmd = options + " /pddls/domain.pddl "
            if prob_file is not None:
                shutil.copy(prob_file, docker_dir / "problem.pddl")
                cmd += "/pddls/problem.pddl "

            if plan_file is not None:
                assert prob_file is not None
                shutil.copy(plan_file, docker_dir / "actions")
                cmd += "/pddls/actions"

            assert self._is_docker_running()
            container = self.client.containers.run(
                image="claudiusk/val:latest",
                command=cmd,
                volumes={docker_dir.absolute().as_posix(): {"bind": "/pddls", "mode": "rw"}},
                detach=True,
            )
            result = container.wait()
            response = container.logs().decode().strip()
            success = result["StatusCode"] == 0
            container.remove()

        return success, response
