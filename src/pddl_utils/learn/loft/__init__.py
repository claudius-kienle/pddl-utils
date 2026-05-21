"""Minimal LOFT operator learner, ported to pddl_utils structs.

Adapted from the reference implementation by Rohan Chitnis et al.:
https://github.com/ronuchit/LOFT_IROS_2021
(Chitnis, Silver, Kim, Kaelbling, Lozano-Pérez, "Learning Neuro-Symbolic
Relational Transition Models for Bilevel Planning", IROS 2021).

This package keeps only the operator-learning core (the LOFT/BUILP loop and
its NDR data structures) and rewrites it against ``pddl_utils`` structs, so
no pddlgym/pyperplan/pybullet dependency is needed.

Public entry point: :func:`learn_operators`.
"""

from pddl_utils.learn.loft.learn import learn_operators
from pddl_utils.learn.loft.settings import LoftConfig, default_config

__all__ = ["learn_operators", "LoftConfig", "default_config"]
