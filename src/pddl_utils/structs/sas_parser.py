import re
from pddl_utils.structs.sas_structs import SasAction, SasPlan
from python_utils.string_utils import remove_comments


def parse_sas_plan(sas_plan_str: str) -> SasPlan:
    """
    Parses a SAS plan string and returns a SasPlan object.
    """
    lines = remove_comments(sas_plan_str).strip().splitlines()
    actions = list(map(parse_sas_action, lines))
    return SasPlan(actions=actions)


def parse_sas_action(sas_action_str: str) -> SasAction:
    """
    Parses a SAS action string and returns a SasAction object.
    """
    match = re.match(r"\(([\w\-]+)(?: +([^\)]+)|\s*)\)", sas_action_str)
    assert match is not None, sas_action_str
    action_name = match.group(1)
    if match.group(2) is None:
        action_args = []
    else:
        action_args = [p.strip() for p in match.group(2).split()]
    return SasAction(name=action_name, args=action_args)
