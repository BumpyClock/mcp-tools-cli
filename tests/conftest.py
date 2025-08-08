# ABOUTME: Global pytest configuration and fixtures for all test modules
# ABOUTME: Provides common fixtures, test configuration, and test environment setup

import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import Mock
import tempfile
import shutil

# Add src to Python path for imports
sys.path.insert(0, 'src')

from tests.fixtures.test_data_generators import TestScenarioFactory


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    if sys.platform.startswith("win") and sys.version_info >= (3, 8):
        # Use ProactorEventLoop on Windows for proper async support
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_test_dir():
    """Create temporary directory for test files."""
    temp_dir = tempfile.mkdtemp(prefix="mcp_manager_tests_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def empty_test_environment():
    """Fixture providing empty test environment."""
    return TestScenarioFactory.create_empty_environment()


@pytest.fixture
def small_test_environment():
    """Fixture providing small test environment."""
    return TestScenarioFactory.create_small_environment()


@pytest.fixture
def medium_test_environment():
    """Fixture providing medium test environment."""
    return TestScenarioFactory.create_medium_environment()


@pytest.fixture
def large_test_environment():
    """Fixture providing large test environment."""
    return TestScenarioFactory.create_large_environment()


@pytest.fixture
def problematic_test_environment():
    """Fixture providing problematic test environment."""
    return TestScenarioFactory.create_problematic_environment()


@pytest.fixture
def mock_registry():
    """Fixture providing a mock registry."""
    registry = Mock()
    registry.list_servers.return_value = []
    registry.get_server.return_value = None
    registry.add_server.return_value = True
    registry.update_server.return_value = True
    registry.remove_server.return_value = True
    return registry


@pytest.fixture
def mock_deployment_manager():
    """Fixture providing a mock deployment manager."""
    manager = Mock()
    manager.deploy_server = Mock(return_value={"status": "success"})
    manager.undeploy_server = Mock(return_value={"status": "success"})
    manager.get_deployment_status.return_value = {"deployed": True}
    manager.get_available_targets.return_value = ["project1", "project2"]
    return manager


@pytest.fixture
def mock_health_monitor():
    """Fixture providing a mock health monitor."""
    monitor = Mock()
    monitor.check_server_health = Mock(return_value={"healthy": True, "message": "OK"})
    monitor.check_all_servers = Mock(return_value={})
    return monitor


@pytest.fixture
def mock_platform_manager():
    """Fixture providing a mock platform manager."""
    manager = Mock()
    manager.detect_platforms.return_value = ["vscode", "claude-desktop"]
    manager.get_platform_config.return_value = {}
    return manager


@pytest.fixture
def mock_project_detector():
    """Fixture providing a mock project detector."""
    detector = Mock()
    detector.detect_projects.return_value = []
    detector.get_project_config.return_value = {}
    return detector


# Performance test configuration
@pytest.fixture
def performance_thresholds():
    """Performance test thresholds."""
    return {
        "startup_time_small": 2.0,      # seconds
        "startup_time_large": 5.0,      # seconds
        "operation_time": 0.1,          # seconds
        "memory_limit": 100 * 1024 * 1024,  # 100MB
        "navigation_time": 0.05,        # seconds per operation
    }


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "compatibility: Compatibility tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "smoke: Smoke tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        elif "compatibility" in str(item.fspath):
            item.add_marker(pytest.mark.compatibility)
        else:
            item.add_marker(pytest.mark.unit)
        
        # Add smoke marker for essential tests
        if "test_basic" in item.name or "test_startup" in item.name:
            item.add_marker(pytest.mark.smoke)


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture logs during tests."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


# Skip tests based on platform
def pytest_runtest_setup(item):
    """Setup function run before each test."""
    # Skip Windows-specific tests on non-Windows platforms
    if hasattr(item, 'get_closest_marker'):
        windows_only = item.get_closest_marker('windows_only')
        if windows_only and not sys.platform.startswith('win'):
            pytest.skip("Windows-only test")
        
        # Skip Unix-specific tests on Windows
        unix_only = item.get_closest_marker('unix_only') 
        if unix_only and sys.platform.startswith('win'):
            pytest.skip("Unix-only test")


# Test timeout configuration
@pytest.fixture(autouse=True)
def test_timeout():
    """Set test timeout to prevent hanging tests."""
    # Individual test timeout is handled by pytest-timeout if installed
    pass


# Memory leak detection fixture
@pytest.fixture
def memory_monitor():
    """Monitor memory usage during tests."""
    try:
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        yield process
        
        # Check for significant memory increase
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Warn if memory increased significantly (more than 50MB)
        if memory_increase > 50 * 1024 * 1024:
            import warnings
            warnings.warn(
                f"Test may have memory leak: {memory_increase / 1024 / 1024:.2f}MB increase",
                UserWarning
            )
    except ImportError:
        # psutil not available, skip memory monitoring
        yield None


# Asyncio error handling
@pytest.fixture(autouse=True)
def handle_asyncio_errors():
    """Handle asyncio errors gracefully in tests."""
    def exception_handler(loop, context):
        # Log asyncio errors but don't fail tests
        import logging
        logging.error(f"Asyncio error: {context}")
    
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(exception_handler)
    
    yield
    
    loop.set_exception_handler(None)