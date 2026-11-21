"""Offline-first evaluation harness for the bounded agent workflow.

This package is test/evaluation infrastructure only. It does not change any
production code path and never calls an external model unless ``--live`` is
passed explicitly to :mod:`evaluations.evaluate`.
"""

from __future__ import annotations
