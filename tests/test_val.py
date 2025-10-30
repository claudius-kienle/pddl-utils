import pytest

from pddl_utils import LocalVAL, DockerVAL


@pytest.mark.parametrize("validator_class", [LocalVAL, DockerVAL])
class TestVAL:
    """Essential tests for VAL validators."""

    def test_validate_complete_plan(self, validator_class, simple_domain, simple_problem, valid_plan):
        """Test validating domain, problem, and plan."""
        mock_output = "Plan valid"

        validator = validator_class()
        success, output = validator.validate(simple_domain, simple_problem, valid_plan)
        assert success

    def test_validate_invalid_plan(self, validator_class, simple_domain, simple_problem, invalid_plan):
        """Test validating an invalid plan."""
        validator = validator_class()
        success, output = validator.validate(simple_domain, simple_problem, invalid_plan)
        gt_output = "(Set (holding a) to true)"
        assert gt_output in output
        assert not success
