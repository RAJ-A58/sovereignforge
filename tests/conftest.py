# tests/conftest.py
"""
Pytest configuration and shared fixtures for SovereignForge tests.
"""
import sys
from pathlib import Path

# Add backend to Python path so test files can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import pytest


@pytest.fixture(scope="session")
def backend_root():
    return Path(__file__).parent.parent / "backend"


@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).parent.parent
