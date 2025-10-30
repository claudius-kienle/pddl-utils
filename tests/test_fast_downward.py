import pytest
from unittest.mock import patch

from pddl_utils import FastDownward
from pddl_utils.planner import PlanningFailure


class TestFastDownward:
    """Essential tests for FastDownward planner."""

    def test_init(self):
        """Test initialization when executable exists."""
        with patch('os.path.exists', return_value=True):
            planner = FastDownward()
            assert hasattr(planner, '_exec')
            assert planner._exec.endswith('FD/fast-downward.py')

    @patch('subprocess.getoutput')
    def test_successful_planning(self, mock_getoutput, simple_domain, simple_problem):
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
        mock_getoutput.return_value = mock_output
        
        with patch('os.path.exists', return_value=True):
            planner = FastDownward()
            plan = planner.plan_from_pddl(simple_domain, simple_problem)
            
            assert len(plan) == 2
            assert plan[0] == "(pick-up a)"
            assert plan[1] == "(stack a b)"
            
            # Check basic statistics
            stats = planner.get_statistics()
            assert stats['plan_length'] == 2

    @patch('subprocess.getoutput')
    def test_planning_failure(self, mock_getoutput, simple_domain, impossible_problem):
        """Test planning failure with impossible problem."""
        mock_output = "No solution found"
        mock_getoutput.return_value = mock_output
        
        with patch('os.path.exists', return_value=True):
            planner = FastDownward()
            with pytest.raises(PlanningFailure):
                planner.plan_from_pddl(simple_domain, impossible_problem)

    @patch('subprocess.getoutput')
    def test_empty_plan(self, mock_getoutput, simple_domain, simple_problem):
        """Test when goal is already satisfied (empty plan)."""
        mock_output = """
        Solution found!
        Plan length: 0 step(s).
        """
        mock_getoutput.return_value = mock_output
        
        with patch('os.path.exists', return_value=True):
            planner = FastDownward()
            plan = planner.plan_from_pddl(simple_domain, simple_problem)
            
            assert plan == []