from unittest.mock import patch

from pddl_utils import VAL


class TestVAL:
    """Essential tests for VAL validator."""

    def test_init(self):
        """Test VAL initialization."""
        with patch('os.path.exists', return_value=True):
            validator = VAL()
            assert hasattr(validator, '_exec')
            assert validator._exec.endswith('VAL/validate')

    @patch('subprocess.getoutput')
    def test_validate_complete_plan(self, mock_getoutput, simple_domain, simple_problem, valid_plan):
        """Test validating domain, problem, and plan."""
        mock_output = "Plan valid"
        mock_getoutput.return_value = mock_output
        
        with patch('os.path.exists', return_value=True):
            validator = VAL()
            success, output = validator.validate(simple_domain, simple_problem, valid_plan)
            
            assert success is True
            assert output == mock_output

    @patch('subprocess.getoutput')
    def test_validate_invalid_plan(self, mock_getoutput, simple_domain, simple_problem, invalid_plan):
        """Test validating an invalid plan."""
        mock_output = "Plan failed to execute"
        mock_getoutput.return_value = mock_output
        
        with patch('os.path.exists', return_value=True):
            validator = VAL()
            success, output = validator.validate(simple_domain, simple_problem, invalid_plan)
            
            assert success is True  # Function call succeeded
            assert "Plan failed" in output  # But plan validation failed