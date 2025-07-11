import pytest
from ..config import initialize_system_config, AdvancedWorkflowConfig

@pytest.fixture(scope="session", autouse=True)
def system_config():
    """
    Initializes the system configuration for the entire test session.
    The `autouse=True` flag ensures this fixture is automatically used for all tests,
    so we don't need to manually add it to each test function.
    """
    config = AdvancedWorkflowConfig()
    initialize_system_config(config) 