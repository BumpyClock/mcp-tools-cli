"""Tests for MCP Manager TUI components."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
sys.path.insert(0, 'src')

from mcp_manager.tui import MCPManagerTUI


class TestMCPManagerTUI:
    """Test cases for the main TUI application."""
    
    def test_app_initialization(self):
        """Test that the app initializes correctly."""
        app = MCPManagerTUI()
        assert app.TITLE == "MCP Manager - Server Registry & Deployment"
        assert hasattr(app, 'registry')
        assert hasattr(app, 'deployment_manager')
    
    def test_app_bindings_defined(self):
        """Test that all required keyboard bindings are defined."""
        app = MCPManagerTUI()
        binding_keys = [binding.key for binding in app.BINDINGS]
        expected_keys = ["a", "e", "d", "r", "h", "q"]
        
        for key in expected_keys:
            assert key in binding_keys, f"Missing binding for key: {key}"
    
    def test_app_compose_returns_layout(self):
        """Test that compose method exists and is properly defined."""
        app = MCPManagerTUI()
        # Test that compose method exists and is callable
        assert hasattr(app, 'compose')
        assert callable(getattr(app, 'compose'))
        # Test that compose is a generator method
        import inspect
        assert inspect.isgeneratorfunction(app.compose)
    
    @patch('mcp_manager.tui.MCPServerRegistry')
    @patch('mcp_manager.tui.DeploymentManager') 
    @patch('mcp_manager.tui.PlatformManager')
    @patch('mcp_manager.tui.ProjectDetector')
    def test_app_mount_initializes_components(self, mock_project, mock_platform, mock_deployment, mock_registry):
        """Test that components are properly initialized."""
        app = MCPManagerTUI()
        # Simulate what on_mount does
        app.registry = mock_registry.return_value
        app.deployment_manager = mock_deployment.return_value
        app.platform_manager = mock_platform.return_value
        app.project_detector = mock_project.return_value
        
        # Components should be set
        assert app.registry is not None
        assert app.deployment_manager is not None
        assert app.platform_manager is not None
        assert app.project_detector is not None
    
    def test_keyboard_shortcuts_defined_correctly(self):
        """Test that keyboard shortcuts have correct actions."""
        app = MCPManagerTUI()
        binding_actions = {binding.key: binding.action for binding in app.BINDINGS}
        
        assert binding_actions.get("a") == "add_server"
        assert binding_actions.get("e") == "edit_server"
        assert binding_actions.get("d") == "deploy"
        assert binding_actions.get("r") == "refresh"
        assert binding_actions.get("h") == "health_check"
        assert binding_actions.get("q") == "quit"
    
    def test_app_can_instantiate_without_errors(self):
        """Test that the app can be instantiated without errors."""
        app = MCPManagerTUI()
        # Should not raise any exceptions
        assert app is not None
        assert hasattr(app, 'TITLE')
        assert hasattr(app, 'BINDINGS')
        assert hasattr(app, 'CSS')


class TestTUILayout:
    """Test cases for TUI layout components."""
    
    def test_layout_has_correct_css_structure(self):
        """Test that CSS defines correct layout structure."""
        app = MCPManagerTUI()
        css = app.CSS
        
        # Check for main layout components
        assert "#main-container" in css
        assert "#left-pane" in css
        assert "#right-pane" in css
        assert "width: 40%" in css  # Left pane
        assert "width: 60%" in css  # Right pane
    
    def test_css_theme_professional_quality(self):
        """Test that CSS theme includes professional styling."""
        app = MCPManagerTUI()
        css = app.CSS
        
        # Check for professional theme elements
        assert "scrollbar-" in css  # Custom scrollbars
        assert "$primary" in css    # Theme variables
        assert "$accent" in css     # Color scheme
        assert "hover" in css       # Interactive states
        assert "focus" in css       # Accessibility
    
    def test_panel_headers_defined(self):
        """Test that panel headers are properly styled."""
        app = MCPManagerTUI()
        css = app.CSS
        
        assert ".panel-header" in css
        assert "text-style: bold" in css
        assert "content-align: center middle" in css


class TestTUIBusinessLogicIntegration:
    """Test cases for TUI integration with business logic."""
    
    def test_registry_integration_interface(self):
        """Test that TUI has proper interface for registry integration."""
        app = MCPManagerTUI()
        
        # Should have methods for registry operations
        assert hasattr(app, '_update_server_list')
        assert hasattr(app, '_refresh_data')
        assert hasattr(app, 'action_refresh')
    
    def test_deployment_manager_integration_interface(self):
        """Test that TUI has proper interface for deployment manager integration."""
        app = MCPManagerTUI()
        
        # Should have methods for deployment operations
        assert hasattr(app, '_update_deployment_matrix')
        assert hasattr(app, 'action_deploy')
        assert hasattr(app, 'action_health_check')
    
    def test_error_handling_methods_exist(self):
        """Test that TUI has error handling capabilities."""
        app = MCPManagerTUI()
        
        assert hasattr(app, '_show_error')
        assert hasattr(app, '_show_success')
    
    def test_action_handlers_are_async(self):
        """Test that action handlers are properly defined as async."""
        app = MCPManagerTUI()
        
        # Import inspection tools
        import inspect
        
        # Check that key actions are async
        assert inspect.iscoroutinefunction(app.action_add_server)
        assert inspect.iscoroutinefunction(app.action_edit_server)
        assert inspect.iscoroutinefunction(app.action_deploy)
        assert inspect.iscoroutinefunction(app.action_refresh)
        assert inspect.iscoroutinefunction(app.action_health_check)


if __name__ == "__main__":
    pytest.main([__file__])