import pytest
import tempfile
from unittest.mock import patch

from pddl_utils import FastDownward, VAL


class TestIntegration:
    """Essential integration tests for planning and validation."""

    @patch('subprocess.getoutput')
    def test_plan_and_validate_workflow(self, mock_getoutput, simple_domain, simple_problem):
        """Test complete workflow: plan with FD, then validate with VAL."""
        # Mock FastDownward output
        fd_output = """
        Solution found!
        Plan length: 2 step(s).
        pick-up a (1)
        stack a b (1)
        """
        
        # Mock VAL output
        val_output = "Plan valid"
        
        # Set up mock to return different outputs for different commands
        def mock_subprocess(cmd):
            if "fast-downward.py" in cmd:
                return fd_output
            elif "validate" in cmd:
                return val_output
            return ""
        
        mock_getoutput.side_effect = mock_subprocess
        
        with patch('os.path.exists', return_value=True):
            # Plan with FastDownward
            planner = FastDownward()
            plan = planner.plan_from_pddl(simple_domain, simple_problem)
            
            assert len(plan) == 2
            assert plan[0] == "(pick-up a)"
            assert plan[1] == "(stack a b)"
            
            # Create temporary plan file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.plan', delete=False) as f:
                for action in plan:
                    f.write(f"{action}\n")
                plan_file = f.name
            
            # Validate with VAL
            validator = VAL()
            success, output = validator.validate(simple_domain, simple_problem, plan_file)
            
            assert success is True
            assert "valid" in output.lower()

    @patch('subprocess.getoutput')
    def test_impossible_problem_workflow(self, mock_getoutput, simple_domain, impossible_problem):
        """Test workflow with impossible problem."""
        mock_getoutput.return_value = "No solution found"
        
        with patch('os.path.exists', return_value=True):
            planner = FastDownward()
            
            # Should fail to find plan
            with pytest.raises(Exception):  # Could be PlanningFailure
                planner.plan_from_pddl(simple_domain, impossible_problem)