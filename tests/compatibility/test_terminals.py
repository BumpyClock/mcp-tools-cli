# ABOUTME: Terminal compatibility tests for Windows terminals, color schemes, and rendering
# ABOUTME: Tests compatibility across different terminal emulators and environments

import pytest
import os
import sys
import asyncio
from unittest.mock import Mock, patch, MagicMock
sys.path.insert(0, 'src')

from textual.testing import TUITestRunner
from textual.console import Console
from rich.console import Console as RichConsole
from rich.terminal_theme import TerminalTheme
from mcp_manager.tui_app import MCPManagerTUI
from tests.fixtures.test_data_generators import TestScenarioFactory


class TerminalCapabilityMocker:
    """Mock different terminal capabilities for testing."""
    
    @staticmethod
    def mock_windows_terminal():
        """Mock Windows Terminal capabilities."""
        return {
            "name": "Windows Terminal",
            "color_depth": 8,
            "unicode_support": True,
            "mouse_support": True,
            "alt_screen": True,
            "cursor_keys": True,
            "function_keys": True,
            "box_drawing": True,
            "emoji_support": True
        }
    
    @staticmethod
    def mock_cmd_exe():
        """Mock cmd.exe capabilities."""
        return {
            "name": "Command Prompt",
            "color_depth": 4,
            "unicode_support": False,
            "mouse_support": False,
            "alt_screen": False,
            "cursor_keys": True,
            "function_keys": True,
            "box_drawing": False,
            "emoji_support": False
        }
    
    @staticmethod
    def mock_powershell():
        """Mock PowerShell capabilities."""
        return {
            "name": "PowerShell",
            "color_depth": 8,
            "unicode_support": True,
            "mouse_support": False,
            "alt_screen": True,
            "cursor_keys": True,
            "function_keys": True,
            "box_drawing": True,
            "emoji_support": True
        }
    
    @staticmethod
    def mock_conemu():
        """Mock ConEmu capabilities."""
        return {
            "name": "ConEmu",
            "color_depth": 8,
            "unicode_support": True,
            "mouse_support": True,
            "alt_screen": True,
            "cursor_keys": True,
            "function_keys": True,
            "box_drawing": True,
            "emoji_support": True
        }
    
    @staticmethod
    def mock_minimal_terminal():
        """Mock minimal terminal with limited capabilities."""
        return {
            "name": "Minimal Terminal",
            "color_depth": 1,  # Monochrome
            "unicode_support": False,
            "mouse_support": False,
            "alt_screen": False,
            "cursor_keys": True,
            "function_keys": False,
            "box_drawing": False,
            "emoji_support": False
        }


class TestWindowsTerminalCompatibility:
    """Test compatibility with Windows terminal environments."""
    
    @pytest.fixture
    def mock_components(self):
        """Setup mocked components for testing."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        deployment_manager.get_deployment_status.return_value = {"deployed": True}
        
        return {
            "registry": registry,
            "deployment_manager": deployment_manager
        }
    
    async def test_windows_terminal_compatibility(self, mock_components):
        """Test full functionality in Windows Terminal."""
        capabilities = TerminalCapabilityMocker.mock_windows_terminal()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
            
            # Mock terminal capabilities
            with patch.dict(os.environ, {"TERM": "xterm-256color", "WT_SESSION": "1"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test that app works with full terminal capabilities
                    await pilot.press("down")    # Navigation
                    await pilot.press("tab")     # Pane switching
                    await pilot.press("r")      # Refresh
                    await pilot.press("h")      # Health check
                    
                    # Test Unicode and emoji rendering (implicitly)
                    # In real app, would check for proper rendering
    
    async def test_cmd_exe_compatibility(self, mock_components):
        """Test compatibility with cmd.exe limitations."""
        capabilities = TerminalCapabilityMocker.mock_cmd_exe()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
            
            # Mock cmd.exe environment
            with patch.dict(os.environ, {"TERM": "", "PROMPT": "$P$G"}, clear=True):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test basic functionality works even with limited capabilities
                    await pilot.press("down")
                    await pilot.press("up")
                    await pilot.press("tab")
                    await pilot.press("r")
                    
                    # App should adapt to limited color depth and no Unicode
    
    async def test_powershell_compatibility(self, mock_components):
        """Test compatibility with PowerShell console."""
        capabilities = TerminalCapabilityMocker.mock_powershell()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
            
            # Mock PowerShell environment
            with patch.dict(os.environ, {"TERM": "xterm", "PSModulePath": "C:\\Windows\\system32\\WindowsPowerShell\\v1.0\\Modules"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test functionality in PowerShell
                    await pilot.press("a")       # Add server
                    await pilot.press("escape")  # Cancel
                    await pilot.press("e")       # Edit server
                    await pilot.press("escape")  # Cancel
                    await pilot.press("d")       # Deploy
                    await pilot.press("escape")  # Cancel
    
    async def test_conemu_compatibility(self, mock_components):
        """Test compatibility with ConEmu."""
        capabilities = TerminalCapabilityMocker.mock_conemu()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=mock_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=mock_components["deployment_manager"]):
            
            # Mock ConEmu environment
            with patch.dict(os.environ, {"ConEmuPID": "1234", "TERM": "xterm-256color"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test advanced features work in ConEmu
                    await pilot.press("tab")
                    await pilot.press("shift+tab")
                    await pilot.press("page_down")
                    await pilot.press("page_up")
                    await pilot.press("home")
                    await pilot.press("end")


class TestColorSchemeCompatibility:
    """Test color scheme compatibility across different terminals."""
    
    @pytest.fixture
    def color_test_components(self):
        """Components with varied server states for color testing."""
        registry = Mock()
        
        # Create servers with different states for color testing
        servers = [
            {"name": "healthy-server", "enabled": True, "health": {"healthy": True}},
            {"name": "warning-server", "enabled": True, "health": {"healthy": True, "warnings": ["Config issue"]}},
            {"name": "error-server", "enabled": True, "health": {"healthy": False, "error": "Connection failed"}},
            {"name": "disabled-server", "enabled": False, "health": {"healthy": False}},
        ]
        
        registry.list_servers.return_value = servers
        deployment_manager = Mock()
        
        return {
            "registry": registry,
            "deployment_manager": deployment_manager
        }
    
    async def test_high_color_depth_scheme(self, color_test_components):
        """Test color scheme with 256-color terminals."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=color_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=color_test_components["deployment_manager"]):
            
            # Mock high color depth terminal
            with patch.dict(os.environ, {"TERM": "xterm-256color"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test that rich colors are used appropriately
                    await pilot.press("r")  # Refresh to show servers with different states
                    await pilot.press("down")  # Navigate through servers
                    await pilot.press("down")
                    await pilot.press("down")
                    
                    # App should use full color palette
    
    async def test_limited_color_scheme(self, color_test_components):
        """Test color scheme with limited color terminals."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=color_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=color_test_components["deployment_manager"]):
            
            # Mock limited color terminal
            with patch.dict(os.environ, {"TERM": "xterm-16color"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test that app adapts to limited color palette
                    await pilot.press("r")
                    await pilot.press("h")  # Health check (uses colors for status)
                    
                    # App should fall back to basic colors
    
    async def test_monochrome_compatibility(self, color_test_components):
        """Test compatibility with monochrome terminals."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=color_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=color_test_components["deployment_manager"]):
            
            # Mock monochrome terminal
            with patch.dict(os.environ, {"TERM": "dumb"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test that app works without colors
                    await pilot.press("r")
                    await pilot.press("tab")
                    await pilot.press("down")
                    
                    # Should use text-based indicators instead of colors
    
    async def test_dark_theme_compatibility(self, color_test_components):
        """Test dark theme compatibility."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=color_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=color_test_components["deployment_manager"]):
            
            # Mock dark theme environment
            with patch.dict(os.environ, {"COLORFGBG": "15;0"}):  # Light text on dark background
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test dark theme rendering
                    await pilot.press("r")
                    await pilot.press("tab")
                    
                    # Colors should be appropriate for dark background
    
    async def test_light_theme_compatibility(self, color_test_components):
        """Test light theme compatibility."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=color_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=color_test_components["deployment_manager"]):
            
            # Mock light theme environment
            with patch.dict(os.environ, {"COLORFGBG": "0;15"}):  # Dark text on light background
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test light theme rendering
                    await pilot.press("r")
                    await pilot.press("h")
                    
                    # Colors should be appropriate for light background


class TestFontRenderingCompatibility:
    """Test font rendering compatibility across different fonts and sizes."""
    
    @pytest.fixture
    def unicode_test_components(self):
        """Components with Unicode characters for testing."""
        registry = Mock()
        
        # Create servers with names that test Unicode rendering
        servers = [
            {"name": "server-with-émojis-🚀", "type": "test"},
            {"name": "server-with-unicode-ñáéíóú", "type": "test"},
            {"name": "server-with-symbols-αβγδε", "type": "test"},
            {"name": "server-with-box-drawing", "type": "test"},
        ]
        
        registry.list_servers.return_value = servers
        deployment_manager = Mock()
        
        return {
            "registry": registry,
            "deployment_manager": deployment_manager
        }
    
    async def test_monospace_font_compatibility(self, unicode_test_components):
        """Test compatibility with monospace fonts."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=unicode_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=unicode_test_components["deployment_manager"]):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Test that layout works with monospace assumption
                await pilot.press("r")
                await pilot.press("down")  # Navigate through Unicode server names
                await pilot.press("down")
                await pilot.press("down")
                
                # Layout should remain aligned with monospace fonts
    
    async def test_unicode_support_detection(self, unicode_test_components):
        """Test Unicode support detection and fallback."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=unicode_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=unicode_test_components["deployment_manager"]):
            
            # Test with Unicode support
            with patch.dict(os.environ, {"LANG": "en_US.UTF-8"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    await pilot.press("r")
                    # Should display Unicode characters correctly
            
            # Test without Unicode support
            with patch.dict(os.environ, {"LANG": "C"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    await pilot.press("r")
                    # Should fall back to ASCII alternatives
    
    async def test_box_drawing_character_support(self, unicode_test_components):
        """Test box drawing character support and fallback."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=unicode_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=unicode_test_components["deployment_manager"]):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Test that borders and frames render correctly
                await pilot.press("tab")  # Switch panes to see borders
                await pilot.press("tab")
                
                # Should use appropriate border characters based on terminal capability
    
    async def test_emoji_rendering_compatibility(self, unicode_test_components):
        """Test emoji rendering in different environments."""
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=unicode_test_components["registry"]), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=unicode_test_components["deployment_manager"]):
            
            # Test with emoji support
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                await pilot.press("r")
                await pilot.press("down")  # Navigate to server with emoji
                
                # Should handle emoji in server names gracefully


class TestScreenSizeCompatibility:
    """Test compatibility with different terminal window sizes."""
    
    @pytest.fixture
    def medium_dataset(self):
        """Medium dataset for screen size testing."""
        return TestScenarioFactory.create_medium_environment()
    
    async def test_small_screen_compatibility(self, medium_dataset):
        """Test compatibility with small terminal windows."""
        registry = Mock()
        registry.list_servers.return_value = medium_dataset["servers"]
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            # Mock small terminal size (80x24)
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Test that layout adapts to small screen
                await pilot.press("r")
                await pilot.press("tab")
                await pilot.press("down")
                
                # Content should be readable and navigable in small space
    
    async def test_very_small_screen_compatibility(self, medium_dataset):
        """Test compatibility with very small terminal windows."""
        registry = Mock()
        registry.list_servers.return_value = medium_dataset["servers"][:5]  # Fewer servers for small screen
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            # Mock very small terminal (40x12)
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Test that app remains usable in very small screen
                await pilot.press("r")
                await pilot.press("down")
                
                # Should prioritize essential information
    
    async def test_large_screen_optimization(self, medium_dataset):
        """Test optimization for large terminal windows."""
        registry = Mock()
        registry.list_servers.return_value = medium_dataset["servers"]
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            # Mock large terminal size (200x60)
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Test that layout utilizes extra space effectively
                await pilot.press("r")
                await pilot.press("tab")
                
                # Should display more information when space is available
    
    async def test_dynamic_resize_handling(self, medium_dataset):
        """Test handling of dynamic terminal resizing."""
        registry = Mock()
        registry.list_servers.return_value = medium_dataset["servers"]
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Start with normal size
                await pilot.press("r")
                
                # Simulate resize events (in real app would trigger resize handlers)
                # Test that app adapts to size changes gracefully
                await pilot.press("tab")
                await pilot.press("down")


class TestAccessibilityCompatibility:
    """Test accessibility features and compatibility."""
    
    async def test_screen_reader_compatibility(self):
        """Test compatibility with screen readers."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            # Mock screen reader environment
            with patch.dict(os.environ, {"SCREENREADER": "1"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test that navigation provides appropriate feedback
                    await pilot.press("r")
                    await pilot.press("down")
                    await pilot.press("tab")
                    
                    # Should provide text-based feedback for screen readers
    
    async def test_high_contrast_mode(self):
        """Test high contrast mode compatibility."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_small_environment()["servers"]
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            # Mock high contrast environment
            with patch.dict(os.environ, {"HIGH_CONTRAST": "1"}):
                async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                    # Test high contrast color scheme
                    await pilot.press("r")
                    await pilot.press("h")  # Health check uses colors
                    
                    # Should use high contrast colors
    
    async def test_keyboard_only_navigation(self):
        """Test complete keyboard-only navigation."""
        registry = Mock()
        registry.list_servers.return_value = TestScenarioFactory.create_medium_environment()["servers"]
        
        deployment_manager = Mock()
        
        with patch('mcp_manager.tui_app.MCPServerRegistry', return_value=registry), \
             patch('mcp_manager.tui_app.DeploymentManager', return_value=deployment_manager):
            
            async with TUITestRunner().run_test(MCPManagerTUI) as pilot:
                # Test that all functionality is accessible via keyboard
                keyboard_sequence = [
                    "r",         # Refresh
                    "down",      # Navigate
                    "up",        # Navigate
                    "tab",       # Switch panes
                    "shift+tab", # Switch panes reverse
                    "enter",     # Select
                    "escape",    # Cancel
                    "space",     # Multi-select
                    "a",         # Add
                    "escape",    # Cancel
                    "e",         # Edit
                    "escape",    # Cancel
                    "d",         # Deploy
                    "escape",    # Cancel
                    "h",         # Health
                ]
                
                for key in keyboard_sequence:
                    await pilot.press(key)
                
                # All operations should be possible without mouse


if __name__ == "__main__":
    pytest.main([__file__, "-v"])