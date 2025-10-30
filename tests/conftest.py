import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def fixture_dir():
    """Get the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def simple_domain(fixture_dir):
    """Path to simple domain PDDL file."""
    return str(fixture_dir / "simple_domain.pddl")

@pytest.fixture
def simple_problem(fixture_dir):
    """Path to simple problem PDDL file."""
    return str(fixture_dir / "simple_problem.pddl")

@pytest.fixture
def impossible_problem(fixture_dir):
    """Path to impossible problem PDDL file."""
    return str(fixture_dir / "impossible_problem.pddl")

@pytest.fixture
def valid_plan(fixture_dir):
    """Path to valid plan file."""
    return str(fixture_dir / "valid_plan.txt")

@pytest.fixture
def invalid_plan(fixture_dir):
    """Path to invalid plan file."""
    return str(fixture_dir / "invalid_plan.txt")

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir