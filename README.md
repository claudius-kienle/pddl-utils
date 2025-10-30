# PDDL Utils
A Python package providing utilities for PDDL (Planning Domain Definition Language) planning, including wrappers for Fast Downward planner and VAL validator with both local and Docker-based execution options.

## Features

- **Fast Downward Integration**: Easy-to-use Python wrapper for the Fast Downward planner
- **VAL Integration**: Plan validation using the VAL validator
- **Local & Docker Execution**: Choose between local installation or Docker containers
- **Automatic Installation**: Automatically downloads and compiles required tools (local mode)
- **Statistics Tracking**: Planning statistics including search time, node expansions, and plan quality

## Installation

```bash
pip install -e .
```

### Dependencies

#### For Local Execution
The package will automatically download and compile:
- [Fast Downward](http://www.fast-downward.org/) - A classical planning system
- [VAL](https://github.com/KCL-Planning/VAL) - A plan validation tool

**Compilation requirements**:
- Git
- CMake  
- Make  
- GCC/G++ compiler
- Python development headers

```bash
sudo apt-get install git cmake make build-essential python3-dev
```

## Quick Start

### Planning with Fast Downward
```python
from pddl_utils import LocalFastDownward, DockerFastDownward

# Initialize planner
planner = LocalFastDownward()
# or 
planner = DockerFastDownward()

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
from pddl_utils import LocalVAL, DockerVAL

# Initialize validator
validator = LocalVAL()
# or
validator = DockerVAL()

# Validate a plan
output, success = validator.validate(
    dom_file="domain.pddl",
    prob_file="problem.pddl",
    plan_file="plan.txt"
)

print("Validation output:", output)
print("Plan is valid:", success)
```