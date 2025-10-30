import pytest

from pddl_utils import LocalFastDownward, DockerFastDownward
from pddl_utils.planning.planner import PlanningFailure


@pytest.mark.parametrize("planner_class", [LocalFastDownward, DockerFastDownward])
class TestFastDownward:
    """Essential tests for FastDownward planners."""

    def test_successful_planning(self, planner_class, simple_domain, simple_problem):
        """Test successful planning with valid domain and problem."""
        mock_output = """
        Solution found!
        Plan length: 2 step(s).
        Plan cost: 2
        Evaluated 6 state(s).
        Search time: 0.01s
        Total time: 0.05s
        pick-up a (1)
        stack a b (1)
        """

        planner = planner_class()
        plan = planner.plan_from_pddl(simple_domain, simple_problem)

        assert len(plan) == 4
        assert plan[0] == "(pick-up b)"
        assert plan[1] == "(stack b c)"
        assert plan[2] == "(pick-up a)"
        assert plan[3] == "(stack a b)"

        # Check basic statistics
        stats = planner.get_statistics()
        assert stats["plan_length"] == 4

    def test_planning_failure(self, planner_class, simple_domain, impossible_problem):
        """Test planning failure with impossible problem."""
        mock_output = "No solution found"

        planner = planner_class()
        with pytest.raises(PlanningFailure):
            planner.plan_from_pddl(simple_domain, impossible_problem)
