"""
pytest configuration for NORNBRAIN test suite.
"""
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a running Creatures 3 engine on TCP 20001"
        " (skip with: pytest -m 'not integration')",
    )
