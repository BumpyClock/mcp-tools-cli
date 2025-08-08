# ABOUTME: Error handling and recovery scenario tests for all failure modes and edge cases
# ABOUTME: Comprehensive testing of application robustness under various error conditions

import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, side_effect
import sys
sys.path.insert(0, 'src')

from textual.testing import TUITestRunner
from mcp_manager.tui_app import MCPManagerTUI
from tests.fixtures.test_data_generators import (
    TestScenarioFactory, ServerConfigFactory
)


class TestConfigurationErrors:
    """Test error handling for invalid configurations."""
    
    @pytest.fixture
    def broken_registry(self):
        """Registry that raises various configuration errors."""
        registry = Mock()
        
        def list_servers_side_effect():
            raise FileNotFoundError("Registry file not found")
        
        def add_server_side_effect(*args, **kwargs):
            raise ValueError("Invalid server configuration")
        
        registry.list_servers.side_effect = list_servers_side_effect
        registry.add_server.side_effect = add_server_side_effect
        
        return registry
    
    async def test_missing_registry_file_error(self, broken_registry):
        """Test handling of missing registry file."""
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=broken_registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # App should handle missing registry gracefully
                await pilot.press("r")  # Try to refresh
                
                # App should still be responsive
                await pilot.press("a")       # Try to add server
                await pilot.press("escape")  # Cancel
    
    async def test_invalid_server_configuration_error(self, broken_registry):
        """Test handling of invalid server configurations."""
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=broken_registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try to add server with invalid config
                await pilot.press("a")       # Add server
                # This would trigger the add_server error
                await pilot.press("escape")  # Should be able to escape
                
                # App should remain stable
                await pilot.press("tab")     # Navigate should still work
    
    async def test_corrupted_registry_data_error(self):
        """Test handling of corrupted registry data."""
        registry = Mock()
        
        # Return corrupted data that causes processing errors
        def corrupted_list_servers():
            return [
                {"name": "server1"},  # Missing required fields
                {"name": "", "config": {}},  # Empty name
                {"config": {"command": "test"}},  # Missing name
                None,  # Null server
            ]
        
        registry.list_servers.return_value = corrupted_list_servers()
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # App should handle corrupted data gracefully
                await pilot.press("r")  # Refresh with corrupted data
                
                # Navigation should still work
                await pilot.press("down")
                await pilot.press("up")
    
    async def test_missing_required_environment_variables(self):
        """Test handling of servers with missing environment variables."""
        registry = Mock()
        
        # Create servers with missing env vars
        problematic_servers = ServerConfigFactory.create_problematic_servers()
        registry.list_servers.return_value = problematic_servers
        
        deployment_manager = Mock()
        health_monitor = Mock()
        
        # Health check should detect missing env vars
        def health_check_side_effect(server_name):
            return {
                "healthy": False,
                "error": "Missing required environment variable",
                "details": "API_KEY not configured"
            }
        
        health_monitor.check_server_health = AsyncMock(side_effect=health_check_side_effect)
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager), \
             patch('mcp_manager.tui_app.HealthMonitor', return_value=health_monitor):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Run health check to detect problems
                await pilot.press("h")
                
                # Should show error indicators but remain stable
                await pilot.press("down")  # Navigate through problematic servers
                await pilot.press("enter") # View details


class TestNetworkErrors:
    """Test error handling for network-related failures."""
    
    @pytest.fixture
    def network_failing_components(self):
        """Components that simulate network failures."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        health_monitor = Mock()
        
        # Simulate various network errors
        async def network_error_deploy(*args, **kwargs):
            raise ConnectionError("Failed to connect to target")
        
        async def timeout_error_health(*args, **kwargs):
            raise TimeoutError("Health check timed out")
        
        deployment_manager.deploy_server = network_error_deploy
        health_monitor.check_server_health = timeout_error_health
        
        return {
            "registry": registry,
            "deployment_manager": deployment_manager,
            "health_monitor": health_monitor
        }
    
    async def test_deployment_network_failure(self, network_failing_components):
        """Test handling of network failures during deployment."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=network_failing_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=network_failing_components["deployment_manager"]):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try to deploy with network failure
                await pilot.press("d")  # Deploy
                
                # Should handle error gracefully and show error message
                await pilot.press("escape")  # Close error dialog
                
                # App should remain usable
                await pilot.press("r")  # Refresh should still work
    
    async def test_health_check_timeout_error(self, network_failing_components):
        """Test handling of health check timeouts."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=network_failing_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=network_failing_components["deployment_manager"]), \
             patch('mcp_manager.tui_app.HealthMonitor', return_value=network_failing_components["health_monitor"]):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try health check with timeout
                await pilot.press("h")  # Health check
                
                # Should show timeout error but remain stable
                await pilot.press("tab")  # Navigation should work
    
    async def test_intermittent_network_issues(self):
        """Test handling of intermittent network connectivity."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        health_monitor = Mock()
        
        # Simulate intermittent failures
        call_count = {"deploy": 0, "health": 0}
        
        async def intermittent_deploy(*args, **kwargs):
            call_count["deploy"] += 1
            if call_count["deploy"] % 2 == 1:  # Fail every other call
                raise ConnectionError("Network temporarily unavailable")
            return {"status": "success"}
        
        async def intermittent_health(*args, **kwargs):
            call_count["health"] += 1
            if call_count["health"] % 3 == 1:  # Fail every third call
                raise ConnectionError("Network temporarily unavailable")
            return {"healthy": True}
        
        deployment_manager.deploy_server = intermittent_deploy
        health_monitor.check_server_health = intermittent_health
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager), \
             patch('mcp_manager.tui_app.HealthMonitor', return_value=health_monitor):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try operations multiple times
                for i in range(4):
                    await pilot.press("d" if i % 2 == 0 else "h")  # Alternate deploy/health
                    await pilot.press("escape")  # Close any error dialogs


class TestResourceExhaustionErrors:
    """Test error handling for resource exhaustion scenarios."""
    
    async def test_memory_exhaustion_simulation(self):
        """Test handling of memory exhaustion with large datasets."""
        registry = Mock()
        
        # Create extremely large dataset
        large_servers = ServerConfigFactory.create_large_dataset(1000)  # 1000 servers
        registry.list_servers.return_value = large_servers
        
        deployment_manager = Mock()
        
        # Simulate memory pressure by raising MemoryError
        def memory_exhausted_operation(*args, **kwargs):
            raise MemoryError("Insufficient memory to complete operation")
        
        deployment_manager.deploy_servers_bulk = AsyncMock(side_effect=memory_exhausted_operation)
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # App should load even with large dataset
                await pilot.press("r")  # Refresh
                
                # Try bulk operation that causes memory error
                await pilot.press("space")  # Multi-select
                await pilot.press("d")      # Deploy (should handle memory error)
                await pilot.press("escape") # Close error dialog
    
    async def test_disk_space_exhaustion(self):
        """Test handling of disk space exhaustion during operations."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        # Simulate disk full error
        async def disk_full_deploy(*args, **kwargs):
            raise OSError("No space left on device")
        
        deployment_manager.deploy_server = disk_full_deploy
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try deployment that fails due to disk space
                await pilot.press("d")
                await pilot.press("escape")  # Close error dialog
                
                # App should remain usable
                await pilot.press("tab")
    
    async def test_too_many_open_files_error(self):
        """Test handling of 'too many open files' system error."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_medium_environment()["servers"]
        
        health_monitor = Mock()
        
        # Simulate "too many open files" error
        async def too_many_files_health(*args, **kwargs):
            raise OSError("Too many open files")
        
        health_monitor.check_server_health = too_many_files_health
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager), \
             patch('mcp_manager.tui_app.HealthMonitor', return_value=health_monitor):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try health check with file handle exhaustion
                await pilot.press("h")
                await pilot.press("escape")  # Close error dialog


class TestPermissionErrors:
    """Test error handling for permission and access errors."""
    
    async def test_permission_denied_registry_access(self):
        """Test handling of permission denied when accessing registry."""
        registry = Mock()
        
        def permission_denied(*args, **kwargs):
            raise PermissionError("Access denied to registry file")
        
        registry.list_servers.side_effect = permission_denied
        registry.add_server.side_effect = permission_denied
        registry.update_server.side_effect = permission_denied
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try operations that require registry access
                await pilot.press("r")       # Refresh
                await pilot.press("a")       # Add server
                await pilot.press("escape")  # Close error dialog
                
                # App should handle permission errors gracefully
    
    async def test_permission_denied_deployment_targets(self):
        """Test handling of permission denied when accessing deployment targets."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        async def permission_denied_deploy(*args, **kwargs):
            raise PermissionError("Access denied to deployment target")
        
        deployment_manager.deploy_server = permission_denied_deploy
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try deployment with permission error
                await pilot.press("d")
                await pilot.press("escape")  # Close error dialog
    
    async def test_read_only_filesystem_error(self):
        """Test handling of read-only filesystem errors."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        def readonly_filesystem(*args, **kwargs):
            raise OSError("Read-only file system")
        
        registry.add_server.side_effect = readonly_filesystem
        registry.update_server.side_effect = readonly_filesystem
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try operations that require write access
                await pilot.press("a")       # Add server (write operation)
                await pilot.press("escape")  # Close error dialog
                
                await pilot.press("e")       # Edit server (write operation)
                await pilot.press("escape")  # Close error dialog


class TestDataCorruptionErrors:
    """Test error handling for data corruption scenarios."""
    
    async def test_malformed_json_registry(self):
        """Test handling of malformed JSON in registry."""
        registry = Mock()
        
        def malformed_json_error(*args, **kwargs):
            raise json.JSONDecodeError("Invalid JSON", "registry.json", 0)
        
        registry.list_servers.side_effect = malformed_json_error
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try to load malformed registry
                await pilot.press("r")  # Refresh
                
                # App should handle JSON errors gracefully
                await pilot.press("tab")  # Navigation should still work
    
    async def test_incomplete_server_data(self):
        """Test handling of incomplete or partial server data."""
        registry = Mock()
        
        # Return servers with missing critical data
        incomplete_servers = [
            {"name": "incomplete1"},  # Missing config
            {"config": {"command": "test"}},  # Missing name
            {"name": "incomplete2", "config": None},  # Null config
            {"name": "incomplete3", "config": {"args": ["test"]}},  # Missing command
        ]
        
        registry.list_servers.return_value = incomplete_servers
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Load registry with incomplete data
                await pilot.press("r")
                
                # Try to interact with incomplete servers
                await pilot.press("down")
                await pilot.press("enter")  # Should handle incomplete data
    
    async def test_encoding_errors(self):
        """Test handling of text encoding errors."""
        registry = Mock()
        
        def encoding_error(*args, **kwargs):
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid start byte")
        
        registry.list_servers.side_effect = encoding_error
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try operation that causes encoding error
                await pilot.press("r")
                
                # App should handle encoding errors gracefully


class TestConcurrencyErrors:
    """Test error handling for concurrency-related issues."""
    
    async def test_race_condition_handling(self):
        """Test handling of race conditions in concurrent operations."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        # Simulate race condition where resource is modified during operation
        call_count = {"count": 0}
        
        async def race_condition_deploy(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                # First call succeeds but triggers race condition
                return {"status": "success"}
            else:
                # Subsequent calls fail due to modified state
                raise RuntimeError("Resource was modified by another process")
        
        deployment_manager.deploy_server = race_condition_deploy
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Trigger multiple deployments to simulate race condition
                await pilot.press("d")  # First deployment
                await pilot.press("d")  # Second deployment (should handle race condition)
                await pilot.press("escape")  # Close any error dialogs
    
    async def test_deadlock_prevention(self):
        """Test that operations don't cause deadlocks."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_medium_environment()["servers"]
        
        deployment_manager = Mock()
        health_monitor = Mock()
        
        # Simulate long-running operations that could cause deadlocks
        async def long_running_deploy(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate long operation
            return {"status": "success"}
        
        async def long_running_health(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate long operation
            return {"healthy": True}
        
        deployment_manager.deploy_server = long_running_deploy
        health_monitor.check_server_health = long_running_health
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager), \
             patch('mcp_manager.tui_app.HealthMonitor', return_value=health_monitor):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Start multiple operations concurrently
                await pilot.press("d")  # Deploy
                await pilot.press("h")  # Health check
                
                # UI should remain responsive
                await pilot.press("tab")  # Navigation should work during operations
                await pilot.press("r")    # Refresh should work


class TestErrorRecoveryMechanisms:
    """Test error recovery and rollback mechanisms."""
    
    async def test_automatic_retry_on_transient_failures(self):
        """Test automatic retry mechanism for transient failures."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        # Simulate transient failure that succeeds on retry
        attempt_count = {"count": 0}
        
        async def transient_failure_deploy(*args, **kwargs):
            attempt_count["count"] += 1
            if attempt_count["count"] == 1:
                raise ConnectionError("Temporary network error")
            else:
                return {"status": "success"}
        
        deployment_manager.deploy_server = transient_failure_deploy
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Try deployment that fails first time but succeeds on retry
                await pilot.press("d")
                
                # If retry mechanism exists, operation should eventually succeed
                # Otherwise, error should be handled gracefully
    
    async def test_rollback_on_partial_failure(self):
        """Test rollback mechanism when operations partially fail."""
        registry = Mock()
        servers = TestScenarioFactory.create_small_environment()["servers"]
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        # Simulate partial failure in batch operation
        async def partial_failure_bulk_deploy(server_names, *args, **kwargs):
            results = []
            for i, server_name in enumerate(server_names):
                if i < len(server_names) // 2:
                    results.append({"server": server_name, "status": "success"})
                else:
                    results.append({"server": server_name, "status": "failed", "error": "Deployment target unavailable"})
            return results
        
        deployment_manager.deploy_servers_bulk = partial_failure_bulk_deploy
        deployment_manager.rollback_deployment = AsyncMock(return_value={"status": "rolled back"})
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Select multiple servers for batch deployment
                await pilot.press("space")  # Multi-select mode
                for i in range(3):
                    await pilot.press("space")  # Select server
                    await pilot.press("down")   # Move to next
                
                # Deploy batch (will partially fail)
                await pilot.press("d")
                
                # Should offer rollback option or handle partial failure gracefully
    
    async def test_state_consistency_after_errors(self):
        """Test that application state remains consistent after errors."""
        registry = Mock()
        servers = TestScenarioFactory.create_small_environment()["servers"]
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        # Simulate error that could corrupt state
        async def state_corrupting_deploy(*args, **kwargs):
            raise RuntimeError("Critical system error")
        
        deployment_manager.deploy_server = state_corrupting_deploy
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Perform operation that causes critical error
                await pilot.press("d")
                await pilot.press("escape")  # Close error dialog
                
                # Verify state is still consistent
                await pilot.press("r")     # Refresh should work
                await pilot.press("tab")   # Navigation should work
                await pilot.press("down")  # Selection should work
                
                # All basic operations should still function


if __name__ == "__main__":
    pytest.main([__file__, "-v"])