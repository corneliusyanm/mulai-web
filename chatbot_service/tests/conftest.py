"""
Pytest configuration and fixtures.
Ensures consistent test environment.
"""

import os
import pytest

# Force mock data for all tests
os.environ["USE_MOCK_DATA"] = "true"


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Reset settings cache before each test to ensure clean state."""
    from app.config import get_settings

    # Clear the LRU cache
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def reset_mock_data():
    """Reset mock data state between tests to prevent test pollution."""
    from app import mock_data

    # Store original state
    original_classes = mock_data._mock_classes.copy() if mock_data._mock_classes else []
    original_date = mock_data._last_generated_date

    yield

    # Restore original state (or clear for fresh generation next time)
    mock_data._mock_classes = []
    mock_data._last_generated_date = None
