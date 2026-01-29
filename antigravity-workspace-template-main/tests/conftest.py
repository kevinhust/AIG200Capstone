"""Pytest configuration helpers.

This conftest ensures the project root is on `sys.path` so tests can import
the `src` package regardless of how pytest is invoked in different CI or IDE
environments.
"""
import os
import sys


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
