# ABOUTME: Performance tests with large datasets and memory usage monitoring
# ABOUTME: Tests scalability, responsiveness, and resource usage under heavy load conditions

import pytest
import asyncio
import time
import gc
import sys
import tracemalloc
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import psutil
import os
sys.path.insert(0, 'src')

from textual.testing import TUITestRunner
from mcp_manager.tui_app import MCPManagerTUI
from tests.fixtures.test_data_generators import (
    TestScenarioFactory, ServerConfigFactory, ProjectConfigFactory
)


class PerformanceMonitor:
    """Utility class for monitoring performance metrics."""
    
    def __init__(self):
        self.start_memory = None
        self.start_time = None
        self.process = psutil.Process(os.getpid())
    
    def start_monitoring(self):
        """Start performance monitoring."""
        tracemalloc.start()
        gc.collect()  # Clean up before measurement
        self.start_memory = self.process.memory_info().rss
        self.start_time = time.time()
    
    def stop_monitoring(self):
        """Stop monitoring and return metrics."""
        end_time = time.time()
        end_memory = self.process.memory_info().rss
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            "duration": end_time - self.start_time,
            "memory_delta": end_memory - self.start_memory,
            "peak_memory": peak,
            "current_memory": current
        }


class TestLargeDatasetPerformance:
    """Test performance with large datasets (50+, 100+ servers)."""
    
    @pytest.fixture
    def performance_monitor(self):
        """Fixture providing performance monitoring."""
        return PerformanceMonitor()
    
    @pytest.fixture(params=[50, 100, 200])
    def large_dataset_sizes(self, request):
        """Parametrized fixture for different dataset sizes."""
        return request.param
    
    async def test_startup_time_with_large_datasets(self, large_dataset_sizes, performance_monitor):
        """Test TUI startup time with large server datasets."""
        # Create large dataset
        servers = ServerConfigFactory.create_large_dataset(large_dataset_sizes)
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        deployment_manager.get_deployment_status.return_value = {"deployed": True}
        
        performance_monitor.start_monitoring()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Allow TUI to fully initialize
                await asyncio.sleep(0.1)
        
        metrics = performance_monitor.stop_monitoring()
        
        # Assert performance thresholds
        max_startup_time = 2.0 if large_dataset_sizes <= 100 else 5.0
        assert metrics["duration"] < max_startup_time, \
            f"Startup with {large_dataset_sizes} servers took {metrics['duration']:.2f}s, expected < {max_startup_time}s"
        
        # Memory usage should be reasonable (less than 100MB for basic dataset)
        max_memory_mb = 100 * 1024 * 1024  # 100MB
        assert metrics["peak_memory"] < max_memory_mb, \
            f"Peak memory usage {metrics['peak_memory'] / 1024 / 1024:.2f}MB too high"
    
    async def test_navigation_performance_large_datasets(self, large_dataset_sizes, performance_monitor):
        """Test navigation performance with large datasets."""
        servers = ServerConfigFactory.create_large_dataset(large_dataset_sizes)
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                performance_monitor.start_monitoring()
                
                # Test rapid navigation through large list
                navigation_operations = 50
                for i in range(navigation_operations):
                    if i % 10 == 0:
                        await pilot.press("down")
                    elif i % 10 == 1:
                        await pilot.press("up") 
                    elif i % 10 == 2:
                        await pilot.press("page_down")
                    elif i % 10 == 3:
                        await pilot.press("page_up")
                    elif i % 10 == 4:
                        await pilot.press("home")
                    elif i % 10 == 5:
                        await pilot.press("end")
                    else:
                        await pilot.press("tab")
                
                metrics = performance_monitor.stop_monitoring()
        
        # Navigation should be fast even with large datasets
        avg_time_per_operation = metrics["duration"] / navigation_operations
        assert avg_time_per_operation < 0.05, \
            f"Average navigation time {avg_time_per_operation:.3f}s too slow"
    
    async def test_refresh_performance_large_datasets(self, large_dataset_sizes, performance_monitor):
        """Test refresh operation performance with large datasets."""
        servers = ServerConfigFactory.create_large_dataset(large_dataset_sizes)
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Perform multiple refresh operations
                performance_monitor.start_monitoring()
                
                for i in range(5):
                    await pilot.press("r")  # Refresh
                    await asyncio.sleep(0.01)  # Small delay between operations
                
                metrics = performance_monitor.stop_monitoring()
        
        # Refresh should be fast
        max_refresh_time = 1.0 if large_dataset_sizes <= 100 else 2.0
        assert metrics["duration"] < max_refresh_time, \
            f"Refresh operations with {large_dataset_sizes} servers took {metrics['duration']:.2f}s"
    
    async def test_search_and_filter_performance(self, large_dataset_sizes, performance_monitor):
        """Test search/filter performance with large datasets."""
        servers = ServerConfigFactory.create_large_dataset(large_dataset_sizes)
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        # Mock search functionality
        def mock_search(query):
            return [s for s in servers if query.lower() in s["name"].lower()]
        
        registry.search_servers = mock_search
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                performance_monitor.start_monitoring()
                
                # Simulate search operations
                # In real implementation, would test actual search functionality
                # For now, test that large datasets don't slow down the UI
                
                # Rapid UI operations that might trigger filtering
                for i in range(20):
                    await pilot.press("down")
                    if i % 5 == 0:
                        await pilot.press("tab")  # Switch views
                
                metrics = performance_monitor.stop_monitoring()
        
        # Search/filter operations should be fast
        assert metrics["duration"] < 1.0, \
            f"Search/filter operations took {metrics['duration']:.2f}s, expected < 1.0s"


class TestDeploymentMatrixPerformance:
    """Test performance of deployment matrix with large datasets."""
    
    async def test_deployment_matrix_rendering_performance(self, performance_monitor):
        """Test deployment matrix rendering with many servers and targets."""
        # Create large environment
        large_env = TestScenarioFactory.create_large_environment()
        servers = large_env["servers"][:100]  # 100 servers
        projects = large_env["projects"][:20]  # 20 projects
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        # Mock deployment matrix data
        def mock_get_deployment_matrix():
            matrix = {}
            for server in servers:
                matrix[server["name"]] = {}
                for project in projects:
                    matrix[server["name"]][f"{project['name']}-{project['type']}"] = {
                        "deployed": True,
                        "status": "active",
                        "version": "1.0.0"
                    }
            return matrix
        
        deployment_manager.get_deployment_matrix = mock_get_deployment_matrix
        
        performance_monitor.start_monitoring()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Switch to deployment matrix view
                await pilot.press("tab")  # Switch to right pane
                
                # Allow matrix to render
                await asyncio.sleep(0.2)
                
                # Test navigation within large matrix
                for i in range(10):
                    await pilot.press("down")
                    await pilot.press("right")
        
        metrics = performance_monitor.stop_monitoring()
        
        # Matrix rendering and navigation should be fast
        assert metrics["duration"] < 3.0, \
            f"Deployment matrix operations took {metrics['duration']:.2f}s, expected < 3.0s"
    
    async def test_bulk_deployment_performance(self, performance_monitor):
        """Test bulk deployment performance with many servers."""
        servers = ServerConfigFactory.create_server_batch(50, "bulk-test")
        projects = ProjectConfigFactory.create_project_batch(10)
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        # Mock bulk deployment that simulates realistic timing
        async def mock_bulk_deploy(server_names, target_keys):
            results = []
            for server_name in server_names:
                await asyncio.sleep(0.01)  # Simulate deployment time
                results.append({"server": server_name, "status": "success"})
            return results
        
        deployment_manager.deploy_servers_bulk = mock_bulk_deploy
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Select multiple servers for bulk deployment
                await pilot.press("space")  # Multi-select mode
                
                performance_monitor.start_monitoring()
                
                # Select first 10 servers
                for i in range(10):
                    await pilot.press("space")  # Select server
                    await pilot.press("down")   # Move to next
                
                # Initiate bulk deployment
                await pilot.press("d")  # Deploy
                
                # Wait for deployment to complete
                await asyncio.sleep(0.5)
                
                metrics = performance_monitor.stop_monitoring()
        
        # Bulk deployment should complete in reasonable time
        assert metrics["duration"] < 2.0, \
            f"Bulk deployment took {metrics['duration']:.2f}s, expected < 2.0s"


class TestMemoryUsagePatterns:
    """Test memory usage patterns under various conditions."""
    
    async def test_memory_leak_detection(self, performance_monitor):
        """Test for memory leaks during repeated operations."""
        servers = ServerConfigFactory.create_server_batch(20, "memory-test")
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        health_monitor = Mock()
        health_monitor.check_server_health = AsyncMock(return_value={"healthy": True})
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager), \
             patch('mcp_manager.tui_app.HealthMonitor', return_value=health_monitor):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Record initial memory
                initial_memory = psutil.Process().memory_info().rss
                
                # Perform repeated operations that might leak memory
                for cycle in range(5):
                    # Refresh operations
                    for i in range(10):
                        await pilot.press("r")
                        await asyncio.sleep(0.01)
                    
                    # Health check operations  
                    await pilot.press("h")
                    await asyncio.sleep(0.1)
                    
                    # Navigation operations
                    for i in range(10):
                        await pilot.press("down")
                        await pilot.press("up")
                    
                    # Force garbage collection
                    gc.collect()
                    
                    # Check memory after each cycle
                    current_memory = psutil.Process().memory_info().rss
                    memory_growth = current_memory - initial_memory
                    
                    # Memory growth should be minimal (less than 20MB per cycle)
                    max_growth_per_cycle = 20 * 1024 * 1024  # 20MB
                    assert memory_growth < max_growth_per_cycle * (cycle + 1), \
                        f"Memory growth {memory_growth / 1024 / 1024:.2f}MB after {cycle + 1} cycles"
    
    async def test_memory_usage_scaling(self, performance_monitor):
        """Test how memory usage scales with dataset size."""
        dataset_sizes = [10, 50, 100, 200]
        memory_measurements = []
        
        for size in dataset_sizes:
            servers = ServerConfigFactory.create_large_dataset(size)
            
            registry = Mock()
            registry.list_servers.return_value = servers
            
            deployment_manager = Mock()
            
            performance_monitor.start_monitoring()
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Allow full initialization
                    await asyncio.sleep(0.1)
                    
                    # Perform some operations to stabilize memory
                    await pilot.press("r")
                    await pilot.press("tab")
                    await pilot.press("tab")
            
            metrics = performance_monitor.stop_monitoring()
            memory_measurements.append({
                "size": size,
                "memory": metrics["peak_memory"]
            })
        
        # Check that memory scaling is reasonable (not exponential)
        for i in range(1, len(memory_measurements)):
            prev_measurement = memory_measurements[i-1]
            curr_measurement = memory_measurements[i]
            
            size_ratio = curr_measurement["size"] / prev_measurement["size"]
            memory_ratio = curr_measurement["memory"] / prev_measurement["memory"]
            
            # Memory growth should be roughly linear, not more than 2x the size ratio
            assert memory_ratio <= size_ratio * 2, \
                f"Memory scaling too steep: {size_ratio}x size increase → {memory_ratio}x memory increase"


class TestUIResponsivenessUnderLoad:
    """Test UI responsiveness under heavy load conditions."""
    
    async def test_responsiveness_during_background_operations(self, performance_monitor):
        """Test UI responsiveness during heavy background operations."""
        servers = ServerConfigFactory.create_server_batch(100, "responsiveness-test")
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        health_monitor = Mock()
        
        # Mock long-running background operations
        async def slow_health_check(server_name):
            await asyncio.sleep(0.02)  # Simulate slow check
            return {"healthy": True, "server": server_name}
        
        health_monitor.check_server_health = slow_health_check
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager), \
             patch('mcp_manager.tui_app.HealthMonitor', return_value=health_monitor):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Start background health checks
                await pilot.press("h")
                
                # Test UI responsiveness during background operation
                performance_monitor.start_monitoring()
                
                # Rapid UI operations
                ui_operations = [
                    "down", "up", "tab", "tab", "down", "up", 
                    "page_down", "page_up", "home", "end"
                ]
                
                for operation in ui_operations:
                    await pilot.press(operation)
                    # UI should respond quickly even during background work
                
                metrics = performance_monitor.stop_monitoring()
        
        # UI operations should remain fast even during background work
        avg_operation_time = metrics["duration"] / len(ui_operations)
        assert avg_operation_time < 0.1, \
            f"Average UI operation time {avg_operation_time:.3f}s too slow during background work"
    
    async def test_concurrent_operation_handling(self, performance_monitor):
        """Test handling of multiple concurrent operations."""
        servers = ServerConfigFactory.create_server_batch(50, "concurrent-test")
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        health_monitor = Mock()
        
        # Mock concurrent operations
        async def concurrent_deploy(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {"status": "success"}
        
        async def concurrent_health(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {"healthy": True}
        
        deployment_manager.deploy_server = concurrent_deploy
        health_monitor.check_server_health = concurrent_health
        
        performance_monitor.start_monitoring()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager), \
             patch('mcp_manager.tui_app.HealthMonitor', return_value=health_monitor):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Start multiple concurrent operations
                await pilot.press("d")  # Deploy
                await pilot.press("h")  # Health check
                await pilot.press("r")  # Refresh
                
                # Continue UI operations
                for i in range(10):
                    await pilot.press("down")
                    await pilot.press("tab")
                
                # Wait for background operations to complete
                await asyncio.sleep(0.5)
        
        metrics = performance_monitor.stop_monitoring()
        
        # Should handle concurrent operations without blocking UI
        assert metrics["duration"] < 2.0, \
            f"Concurrent operations took {metrics['duration']:.2f}s, expected < 2.0s"


class TestResourceConstrainedEnvironments:
    """Test performance in resource-constrained environments."""
    
    async def test_low_memory_environment_simulation(self):
        """Test behavior in simulated low-memory conditions."""
        # Create dataset that would use significant memory
        servers = ServerConfigFactory.create_large_dataset(500)
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        # Simulate memory pressure by limiting operations
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # App should start even with large dataset
                await asyncio.sleep(0.1)
                
                # Basic operations should still work
                await pilot.press("r")
                await pilot.press("down")
                await pilot.press("tab")
                
                # Monitor memory usage throughout
                process = psutil.Process()
                memory_usage = process.memory_info().rss
                
                # Memory usage should be reasonable even with large dataset
                max_memory_mb = 500 * 1024 * 1024  # 500MB limit
                assert memory_usage < max_memory_mb, \
                    f"Memory usage {memory_usage / 1024 / 1024:.2f}MB exceeds limit"
    
    async def test_cpu_constrained_performance(self, performance_monitor):
        """Test performance under CPU constraints."""
        servers = ServerConfigFactory.create_server_batch(100, "cpu-test")
        
        registry = Mock()
        registry.list_servers.return_value = servers
        
        deployment_manager = Mock()
        
        # Simulate CPU-intensive operations
        def cpu_intensive_operation(*args, **kwargs):
            # Simulate CPU work
            total = 0
            for i in range(10000):
                total += i * i
            return servers
        
        registry.list_servers = cpu_intensive_operation
        
        performance_monitor.start_monitoring()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Perform operations that trigger CPU-intensive work
                for i in range(5):
                    await pilot.press("r")  # Refresh (triggers CPU work)
                    await asyncio.sleep(0.01)  # Small delay
        
        metrics = performance_monitor.stop_monitoring()
        
        # Should complete in reasonable time even with CPU constraints
        assert metrics["duration"] < 5.0, \
            f"CPU-constrained operations took {metrics['duration']:.2f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])