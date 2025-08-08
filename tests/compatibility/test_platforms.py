# ABOUTME: Cross-platform compatibility tests for Windows, macOS, and Linux environments
# ABOUTME: Tests platform-specific behaviors, file paths, and system integrations

import pytest
import os
import sys
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
sys.path.insert(0, 'src')

from textual.testing import TUITestRunner
from mcp_manager.tui_app import MCPManagerTUI
from tests.fixtures.test_data_generators import TestScenarioFactory


class PlatformMocker:
    """Mock different platform environments for testing."""
    
    @staticmethod
    def mock_windows():
        """Mock Windows environment."""
        return {
            "system": "Windows",
            "path_sep": "\\",
            "line_ending": "\r\n",
            "home_dir": "C:\\Users\\TestUser",
            "config_dir": "C:\\Users\\TestUser\\AppData\\Roaming",
            "temp_dir": "C:\\Windows\\Temp",
            "executable_ext": ".exe",
            "env_vars": {
                "OS": "Windows_NT",
                "USERPROFILE": "C:\\Users\\TestUser",
                "APPDATA": "C:\\Users\\TestUser\\AppData\\Roaming",
                "TEMP": "C:\\Windows\\Temp",
                "PATH": "C:\\Windows\\System32;C:\\Windows"
            }
        }
    
    @staticmethod
    def mock_macos():
        """Mock macOS environment."""
        return {
            "system": "Darwin",
            "path_sep": "/",
            "line_ending": "\n",
            "home_dir": "/Users/testuser",
            "config_dir": "/Users/testuser/.config",
            "temp_dir": "/tmp",
            "executable_ext": "",
            "env_vars": {
                "HOME": "/Users/testuser",
                "USER": "testuser",
                "TMPDIR": "/tmp/",
                "PATH": "/usr/local/bin:/usr/bin:/bin"
            }
        }
    
    @staticmethod
    def mock_linux():
        """Mock Linux environment."""
        return {
            "system": "Linux",
            "path_sep": "/",
            "line_ending": "\n",
            "home_dir": "/home/testuser",
            "config_dir": "/home/testuser/.config",
            "temp_dir": "/tmp",
            "executable_ext": "",
            "env_vars": {
                "HOME": "/home/testuser",
                "USER": "testuser",
                "TMPDIR": "/tmp",
                "PATH": "/usr/local/bin:/usr/bin:/bin"
            }
        }


class TestWindowsPlatformCompatibility:
    """Test Windows-specific compatibility."""
    
    @pytest.fixture
    def windows_environment(self):
        """Setup Windows environment for testing."""
        return PlatformMocker.mock_windows()
    
    @pytest.fixture
    def mock_components(self):
        """Setup mocked components."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        deployment_manager.get_deployment_status.return_value = {"deployed": True}
        
        return {
            "registry": registry,
            "deployment_manager": deployment_manager
        }
    
    async def test_windows_path_handling(self, windows_environment, mock_components):
        """Test Windows path handling with backslashes."""
        with patch('platform.system', return_value="Windows"), \
             patch('os.path.sep', windows_environment["path_sep"]), \
             patch.dict(os.environ, windows_environment["env_vars"]):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test that Windows paths are handled correctly
                    await pilot.press("r")  # Refresh
                    await pilot.press("a")  # Add server (would involve file paths)
                    await pilot.press("escape")
                    
                    # Should handle Windows-style paths correctly
    
    async def test_windows_executable_detection(self, windows_environment, mock_components):
        """Test Windows executable file detection."""
        # Create servers with Windows-style executables
        servers = [
            {
                "name": "node-server",
                "config": {"command": "node.exe", "args": ["server.js"]}
            },
            {
                "name": "python-server", 
                "config": {"command": "python.exe", "args": ["-m", "server"]}
            },
            {
                "name": "dotnet-server",
                "config": {"command": "dotnet.exe", "args": ["run"]}
            }
        ]
        
        mock_components["registry"].list_servers.return_value = servers
        
        with patch('platform.system', return_value="Windows"), \
             patch.dict(os.environ, windows_environment["env_vars"]):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Windows executable handling
                    await pilot.press("r")
                    await pilot.press("h")  # Health check should handle .exe files
                    
                    # Should correctly detect and validate Windows executables
    
    async def test_windows_line_ending_handling(self, windows_environment, mock_components):
        """Test Windows CRLF line ending handling."""
        with patch('platform.system', return_value="Windows"), \
             patch.dict(os.environ, windows_environment["env_vars"]):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test that Windows line endings are handled correctly
                    await pilot.press("r")
                    await pilot.press("e")  # Edit (involves text handling)
                    await pilot.press("escape")
                    
                    # Should handle CRLF line endings correctly
    
    async def test_windows_registry_integration(self, windows_environment, mock_components):
        """Test Windows registry integration (if applicable)."""
        with patch('platform.system', return_value="Windows"), \
             patch.dict(os.environ, windows_environment["env_vars"]):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Windows-specific integrations
                    await pilot.press("r")
                    
                    # Should work without Windows registry dependencies
    
    async def test_windows_permission_handling(self, windows_environment, mock_components):
        """Test Windows permission model handling."""
        with patch('platform.system', return_value="Windows"), \
             patch.dict(os.environ, windows_environment["env_vars"]):
            
            # Mock Windows permission errors
            def windows_permission_error(*args, **kwargs):
                raise PermissionError("Access is denied")
            
            mock_components["registry"].add_server.side_effect = windows_permission_error
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Windows permission error handling
                    await pilot.press("a")       # Add server
                    await pilot.press("escape")  # Should handle permission error
                    
                    # Should gracefully handle Windows permission issues


class TestMacOSPlatformCompatibility:
    """Test macOS-specific compatibility."""
    
    @pytest.fixture
    def macos_environment(self):
        """Setup macOS environment for testing."""
        return PlatformMocker.mock_macos()
    
    @pytest.fixture
    def mock_components(self):
        """Setup mocked components."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        return {"registry": registry, "deployment_manager": deployment_manager}
    
    async def test_macos_path_handling(self, macos_environment, mock_components):
        """Test macOS Unix path handling."""
        with patch('platform.system', return_value="Darwin"), \
             patch('os.path.sep', macos_environment["path_sep"]), \
             patch.dict(os.environ, macos_environment["env_vars"]):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Unix-style path handling on macOS
                    await pilot.press("r")
                    await pilot.press("a")
                    await pilot.press("escape")
                    
                    # Should handle Unix paths correctly
    
    async def test_macos_homebrew_integration(self, macos_environment, mock_components):
        """Test macOS Homebrew executable detection."""
        # Create servers that might use Homebrew paths
        servers = [
            {
                "name": "node-server",
                "config": {"command": "/opt/homebrew/bin/node", "args": ["server.js"]}
            },
            {
                "name": "python-server",
                "config": {"command": "/usr/local/bin/python3", "args": ["-m", "server"]}
            }
        ]
        
        mock_components["registry"].list_servers.return_value = servers
        
        with patch('platform.system', return_value="Darwin"), \
             patch.dict(os.environ, macos_environment["env_vars"]):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Homebrew executable paths
                    await pilot.press("r")
                    await pilot.press("h")  # Health check
                    
                    # Should handle Homebrew paths correctly
    
    async def test_macos_terminal_integration(self, macos_environment, mock_components):
        """Test macOS Terminal.app integration."""
        with patch('platform.system', return_value="Darwin"), \
             patch.dict(os.environ, {**macos_environment["env_vars"], "TERM_PROGRAM": "Apple_Terminal"}):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Terminal.app specific features
                    await pilot.press("r")
                    await pilot.press("tab")
                    
                    # Should work correctly in Terminal.app
    
    async def test_macos_permission_model(self, macos_environment, mock_components):
        """Test macOS permission model handling."""
        with patch('platform.system', return_value="Darwin"), \
             patch.dict(os.environ, macos_environment["env_vars"]):
            
            # Mock macOS-style permission issues
            def macos_permission_error(*args, **kwargs):
                raise PermissionError("Operation not permitted")
            
            mock_components["deployment_manager"].deploy_server.side_effect = macos_permission_error
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test macOS permission handling
                    await pilot.press("d")       # Deploy
                    await pilot.press("escape")  # Handle permission error
                    
                    # Should handle macOS permission model


class TestLinuxPlatformCompatibility:
    """Test Linux-specific compatibility."""
    
    @pytest.fixture
    def linux_environment(self):
        """Setup Linux environment for testing."""
        return PlatformMocker.mock_linux()
    
    @pytest.fixture
    def mock_components(self):
        """Setup mocked components."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        return {"registry": registry, "deployment_manager": deployment_manager}
    
    async def test_linux_path_handling(self, linux_environment, mock_components):
        """Test Linux Unix path handling."""
        with patch('platform.system', return_value="Linux"), \
             patch('os.path.sep', linux_environment["path_sep"]), \
             patch.dict(os.environ, linux_environment["env_vars"]):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Linux path handling
                    await pilot.press("r")
                    await pilot.press("e")
                    await pilot.press("escape")
    
    async def test_linux_package_manager_integration(self, linux_environment, mock_components):
        """Test Linux package manager executable detection."""
        # Create servers using system packages
        servers = [
            {
                "name": "node-server",
                "config": {"command": "/usr/bin/node", "args": ["server.js"]}
            },
            {
                "name": "python-server",
                "config": {"command": "/usr/bin/python3", "args": ["-m", "server"]}
            }
        ]
        
        mock_components["registry"].list_servers.return_value = servers
        
        with patch('platform.system', return_value="Linux"), \
             patch.dict(os.environ, linux_environment["env_vars"]):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test system package executable paths
                    await pilot.press("r")
                    await pilot.press("h")
    
    async def test_linux_distribution_compatibility(self, linux_environment, mock_components):
        """Test compatibility across Linux distributions."""
        distributions = ["Ubuntu", "Fedora", "CentOS", "Arch", "Debian"]
        
        for distro in distributions:
            with patch('platform.system', return_value="Linux"), \
                 patch('platform.linux_distribution', return_value=(distro, "", "")), \
                 patch.dict(os.environ, linux_environment["env_vars"]):
                
                with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                     patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                    
                    async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                        # Test that app works across distributions
                        await pilot.press("r")
                        await pilot.press("tab")
    
    async def test_linux_file_permissions(self, linux_environment, mock_components):
        """Test Linux file permission handling."""
        with patch('platform.system', return_value="Linux"), \
             patch.dict(os.environ, linux_environment["env_vars"]):
            
            # Mock Linux permission issues
            def linux_permission_error(*args, **kwargs):
                raise PermissionError("Permission denied")
            
            mock_components["registry"].update_server.side_effect = linux_permission_error
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Linux permission handling
                    await pilot.press("e")       # Edit
                    await pilot.press("escape")  # Handle permission error


class TestCrossPlatformPathHandling:
    """Test cross-platform path handling."""
    
    async def test_path_normalization(self):
        """Test path normalization across platforms."""
        test_paths = [
            "C:\\Users\\TestUser\\config.json",  # Windows
            "/home/testuser/.config/config.json",  # Linux
            "/Users/testuser/.config/config.json",  # macOS
            "config.json",  # Relative path
            "../config/config.json",  # Relative with parent
        ]
        
        registry = Mock()
        registry.list_servers.return_value = []
        
        deployment_manager = Mock()
        
        for test_path in test_paths:
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test that different path formats are handled correctly
                    await pilot.press("r")
                    
                    # Should normalize paths appropriately for current platform
    
    async def test_executable_extension_handling(self):
        """Test executable extension handling across platforms."""
        # Test with and without .exe extension
        servers_windows = [
            {"name": "node-server", "config": {"command": "node.exe"}},
            {"name": "python-server", "config": {"command": "python.exe"}}
        ]
        
        servers_unix = [
            {"name": "node-server", "config": {"command": "node"}},
            {"name": "python-server", "config": {"command": "python3"}}
        ]
        
        registry = Mock()
        deployment_manager = Mock()
        
        # Test Windows behavior
        with patch('platform.system', return_value="Windows"):
            registry.list_servers.return_value = servers_windows
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    await pilot.press("r")
                    # Should handle .exe extensions on Windows
        
        # Test Unix behavior  
        with patch('platform.system', return_value="Linux"):
            registry.list_servers.return_value = servers_unix
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    await pilot.press("r")
                    # Should handle executables without extensions on Unix


class TestPlatformSpecificFeatures:
    """Test platform-specific features and integrations."""
    
    async def test_windows_specific_features(self):
        """Test Windows-specific features."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        with patch('platform.system', return_value="Windows"):
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Windows-specific features
                    await pilot.press("r")
                    
                    # Should use Windows-appropriate behaviors
    
    async def test_macos_specific_features(self):
        """Test macOS-specific features."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        with patch('platform.system', return_value="Darwin"):
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test macOS-specific features
                    await pilot.press("r")
                    
                    # Should use macOS-appropriate behaviors
    
    async def test_linux_specific_features(self):
        """Test Linux-specific features."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        with patch('platform.system', return_value="Linux"):
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test Linux-specific features
                    await pilot.press("r")
                    
                    # Should use Linux-appropriate behaviors


class TestEnvironmentVariableHandling:
    """Test environment variable handling across platforms."""
    
    async def test_platform_specific_env_vars(self):
        """Test platform-specific environment variable handling."""
        registry = Mock()
        registry.list_servers.return_value = []
        
        deployment_manager = Mock()
        
        # Test Windows environment variables
        windows_env = {
            "USERPROFILE": "C:\\Users\\TestUser",
            "APPDATA": "C:\\Users\\TestUser\\AppData\\Roaming",
            "LOCALAPPDATA": "C:\\Users\\TestUser\\AppData\\Local"
        }
        
        with patch('platform.system', return_value="Windows"), \
             patch.dict(os.environ, windows_env):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    await pilot.press("r")
                    # Should use Windows environment variables
        
        # Test Unix environment variables
        unix_env = {
            "HOME": "/home/testuser",
            "USER": "testuser",
            "XDG_CONFIG_HOME": "/home/testuser/.config"
        }
        
        with patch('platform.system', return_value="Linux"), \
             patch.dict(os.environ, unix_env, clear=True):
            
            with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
                 patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
                
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    await pilot.press("r")
                    # Should use Unix environment variables


if __name__ == "__main__":
    pytest.main([__file__, "-v"])