"""
Pytest fixtures shared across ILbuy test suite.
"""
import json
import os
import sys

import pytest

# Make scripts importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))


@pytest.fixture(scope="session")
def generator():
    """Return a seeded EcommerceProductGenerator for reproducible tests."""
    from generate_ecommerce_test_data import EcommerceProductGenerator
    return EcommerceProductGenerator(seed=42)


@pytest.fixture(scope="session")
def test_dataset(generator):
    """20-product dataset generated once per test session."""
    return generator.generate_test_dataset(20)


@pytest.fixture(scope="session")
def multimodal_dataset(generator):
    """Multimodal test-case dataset generated once per session."""
    return generator.generate_for_multimodal_test()


@pytest.fixture
def gateway_url():
    return os.getenv("ILBUY_GATEWAY_URL", "http://localhost:8080")


@pytest.fixture
def buyer_credentials():
    return {
        "username": os.getenv("ILBUY_USERNAME", "buyer01"),
        "password": os.getenv("ILBUY_PASSWORD", "Test@123456"),
    }
