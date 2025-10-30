import logging
import re
from typing import Optional, Tuple
from pddl.core import Formula, Problem, Domain
from tp_lodge.utils.pddl_utils import get_constants_in_term, get_list_of_predicates


logger = logging.getLogger(__name__)


class AIValidator:

    def validate_plan_executes_successfully(self, domain: str, problem: str, plan: str):
        response, success = self.validate(domain=domain, problem=problem, plan=plan, options="-v")
        successful = "Plan executed successfully" in response
        if not successful:
            assert not success, response
            if "Bad plan description" in response:
                match = re.search("Type problem in action([\w\W]+)Bad plan", response)
            else:
                match = re.search("Plan Repair Advice:([\w\W]+)Failed plans:", response)
            assert match is not None
            repair_advice = match.group(1)
        else:
            repair_advice = None
        return successful, repair_advice

    def state_fulfills_goal(self, domain: Domain, state: Formula, goal: Formula) -> bool:
        objects = set(get_constants_in_term(state)) | set(get_constants_in_term(goal))
        problem = Problem(
            name="test-problem",
            objects=objects,
            domain_name=domain.name,
            init=get_list_of_predicates(state),
            goal=goal,
        )
        response, success = self.validate(domain=str(domain), problem=str(problem), plan="", options="-v")

        return "The goal is not satisfied" not in response and "Goal not satisfied" not in response

    def validate(
        self, domain: str, problem: Optional[str], plan: Optional[str], options: Optional[str]
    ) -> Tuple[str, bool]:
        response, success = self._validate(domain=domain, problem=problem, plan=plan, options=options)
        if plan is not None:
            failed_plan = "Failed plans:" in response
            if not failed_plan:
                assert success
            success = success and not failed_plan


        if not success and "Plan Repair Advice" in response:
            # repair_advice = re.findall(r".*Plan Repair Advice:(.*)Failed plans:.*", response)
            repair_advice = re.findall(r"Plan Repair Advice:\n([\w\W]*?)\nFailed plans:", response)[0]
            lines = repair_advice.strip().splitlines()
            assert len(lines) >= 2

            if "has an unsatisfied precondition" in lines[0] or "The goal is not satisfied" in lines[0]:
                predicates = [re.findall(r"(\([\w\-]+[\w ]*\))", line) for line in lines[1:]]
                predicates_new = [re.findall(r"(\([\w\-]+[\w ]*\)) to (false|true)", line) for line in lines[1:]]
                assert len(predicates) == len(predicates_new)
                predicates = [
                    p[0][0] if p[0][1] == "true" else ("(not %s)" % p[0][0]) for p in predicates_new if len(p) > 0
                ]
                predicate = ", ".join(predicates)

                response = response.replace(
                    repair_advice, ("Predicate that leads to unsatisfied precondition: %s\n" % predicate)
                )

        return response, success

    def _validate(
        self, domain: str, problem: Optional[str], plan: Optional[str], options: Optional[str]
    ) -> Tuple[str, bool]:
        raise NotImplementedError()
