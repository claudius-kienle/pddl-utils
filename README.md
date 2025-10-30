# PDDL Utils
A Python package providing utilities for PDDL (Planning Domain Definition Language) planning, including wrappers for Fast Downward planner and VAL validator.

## Features

- **Fast Downward Integration**: Easy-to-use Python wrapper for the Fast Downward planner
- **VAL Integration**: Plan validation using the VAL validator
- **Automatic Installation**: Automatically downloads and compiles required tools
- **Statistics Tracking**: Planning statistics including search time, node expansions, and plan quality

## Installation

### Using Pixi (Recommended)

```bash
git clone <repository-url>
cd pddlgym-planners
pixi install
```

### Using pip

```bash
pip install -e .
```

### System Dependencies

The package will automatically download and compile:
- [Fast Downward](http://www.fast-downward.org/) - A classical planning system
- [VAL](https://github.com/KCL-Planning/VAL) - A plan validation tool

**Note**: Compilation requires:
- Git
- Make
- GCC/G++ compiler
- Python development headers

On Ubuntu/Debian:
```bash
sudo apt-get install git make build-essential python3-dev
```

On macOS:
```bash
brew install git make
# Xcode command line tools for compiler
```

## Quick Start

### Basic Planning with Fast Downward

```python
from pddl_utils import FastDownward

# Initialize planner
planner = FastDownward()

# Plan from PDDL files
plan = planner.plan_from_pddl(
    dom_file="domain.pddl",
    prob_file="problem.pddl",
    timeout=30
)

# Get planning statistics
stats = planner.get_statistics()
print(f"Plan length: {stats.get('plan_length', 'N/A')}")
print(f"Search time: {stats.get('search_time', 'N/A')}s")
```

### Plan Validation with VAL

```python
from pddl_utils import VAL

# Initialize validator
validator = VAL()

# Validate a plan
is_valid, output = validator.validate(
    dom_file="domain.pddl",
    prob_file="problem.pddl", 
    plan_file="plan.txt"
)

print("Validation output:", output)
```

### Complete Planning and Validation Workflow

```python
import tempfile
from pddl_utils import FastDownward, VAL

# Initialize tools
planner = FastDownward()
validator = VAL()

# Generate plan
plan = planner.plan_from_pddl("domain.pddl", "problem.pddl")

# Save plan to temporary file
with tempfile.NamedTemporaryFile(mode='w', suffix='.plan', delete=False) as f:
    for action in plan:
        f.write(f"({action})\n")
    plan_file = f.name

# Validate the plan
is_valid, output = validator.validate("domain.pddl", "problem.pddl", plan_file)

if "Valid plan" in output:
    print("Plan is valid!")
else:
    print("Plan validation failed:", output)
```

## API Reference

### FastDownward

#### Constructor

```python
FastDownward(alias_flag="--alias seq-opt-lmcut", final_flags="")
```

- `alias_flag`: Fast Downward search configuration alias
- `final_flags`: Additional command line flags

#### Methods

##### `plan_from_pddl(dom_file, prob_file, horizon=inf, timeout=10, remove_files=False)`

Plan from PDDL domain and problem files.

**Parameters:**
- `dom_file` (str): Path to domain PDDL file
- `prob_file` (str): Path to problem PDDL file  
- `horizon` (float): Maximum plan length
- `timeout` (int): Planning timeout in seconds
- `remove_files` (bool): Remove input files after planning

**Returns:**
- `list`: List of action strings representing the plan

**Raises:**
- `PlanningFailure`: When no plan is found
- `PlanningTimeout`: When planning exceeds timeout

##### `plan_from_sas(sas_file, horizon=inf, timeout=10)`

Plan from preprocessed SAS file.

**Parameters:**
- `sas_file` (str): Path to SAS file
- `horizon` (float): Maximum plan length
- `timeout` (int): Planning timeout in seconds

**Returns:**
- `list`: List of action strings representing the plan

##### `get_statistics()`

Get planning statistics.

**Returns:**
- `dict`: Statistics including:
  - `plan_length`: Number of actions in plan
  - `plan_cost`: Total plan cost
  - `search_time`: Time spent in search (seconds)
  - `total_time`: Total planning time (seconds)
  - `num_node_expansions`: Number of search nodes expanded

##### `reset_statistics()`

Reset internal statistics tracking.

### VAL

#### Constructor

```python
VAL()
```

#### Methods

##### `validate(dom_file, prob_file=None, plan_file=None, remove_files=False)`

Validate a plan against domain and problem.

**Parameters:**
- `dom_file` (str): Path to domain PDDL file
- `prob_file` (str, optional): Path to problem PDDL file
- `plan_file` (str, optional): Path to plan file
- `remove_files` (bool): Remove files after validation

**Returns:**
- `tuple`: (success_bool, output_string)

## Common Search Configurations

Fast Downward supports many search algorithms. Common configurations:

```python
# Optimal planning with landmark cut heuristic (default)
planner = FastDownward(alias_flag="--alias seq-opt-lmcut")

# Fast satisficing planning
planner = FastDownward(alias_flag="--alias lama-first")

# Custom configuration
planner = FastDownward(
    alias_flag="--search", 
    final_flags="astar(lmcut())"
)
```

## Error Handling

The package defines custom exceptions:

- `PlanningFailure`: Raised when planning fails to find a solution
- `PlanningTimeout`: Raised when planning exceeds the specified timeout

```python
from pddl_utils import FastDownward
from pddl_utils.planner import PlanningFailure, PlanningTimeout

planner = FastDownward()

try:
    plan = planner.plan_from_pddl("domain.pddl", "problem.pddl", timeout=10)
except PlanningTimeout:
    print("Planning timed out")
except PlanningFailure as e:
    print(f"Planning failed: {e}")
```

## Testing

Run the test suite:

```bash
# Using pixi
pixi run pytest

# Using pip
pytest tests/
```

## Development

### Project Structure

```
src/
├── pddl_utils/
│   ├── __init__.py
│   ├── fast_downward.py    # Fast Downward wrapper
│   ├── val.py             # VAL wrapper  
│   └── planner.py         # Base planner interface
tests/
├── test_fast_downward.py  # Fast Downward tests
├── test_val.py           # VAL tests
├── test_integration.py   # Integration tests
└── fixtures/             # Test PDDL files
    ├── simple_domain.pddl
    └── simple_problem.pddl
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the terms specified in LICENSE.md.

## Acknowledgments

- [Fast Downward](http://www.fast-downward.org/) team for the planning system
- [VAL](https://github.com/KCL-Planning/VAL) team for the validation tools
- Original [pddlgym_planners](https://github.com/ronuchit/pddlgym_planners) implementation

## Troubleshooting

### Compilation Issues

If you encounter compilation errors:

1. **Missing dependencies**: Install build tools and development headers
2. **Permission errors**: Ensure write access to the package directory
3. **Network issues**: Check internet connection for downloading repositories

### Planning Issues

1. **PlanningFailure**: Check PDDL syntax and problem solvability
2. **PlanningTimeout**: Increase timeout or try a different search configuration
3. **Installation errors**: Remove generated directories and reinstall

For more help, please open an issue on the project repository.