# ABOUTME: Comprehensive tests for the SelectionManager and interaction logic
# ABOUTME: Tests single/multi selection modes, keyboard handling, and state management

import pytest
from unittest.mock import Mock, call

from mcp_manager.selection_manager import (
    SelectionManager,
    SelectionMode,
    FocusArea,
    SelectionState,
)


class TestSelectionState:
    """Tests for SelectionState dataclass."""
    
    def test_initial_state(self):
        """Test initial state is properly set."""
        state = SelectionState()
        assert state.mode == SelectionMode.SINGLE
        assert state.single_selection is None
        assert len(state.multi_selections) == 0
        assert state.focus_area == FocusArea.SERVER_TREE
    
    def test_clear_selections(self):
        """Test clearing all selections."""
        state = SelectionState()
        state.single_selection = "test-server"
        state.multi_selections.add("server1")
        state.multi_selections.add("server2")
        
        state.clear_selections()
        
        assert state.single_selection is None
        assert len(state.multi_selections) == 0
    
    def test_get_selected_items_single_mode(self):
        """Test getting selections in single mode."""
        state = SelectionState()
        state.single_selection = "test-server"
        
        result = state.get_selected_items()
        assert result == "test-server"
    
    def test_get_selected_items_multi_mode(self):
        """Test getting selections in multi mode."""
        state = SelectionState(mode=SelectionMode.MULTI)
        state.multi_selections.add("server1")
        state.multi_selections.add("server2")
        
        result = state.get_selected_items()
        assert isinstance(result, set)
        assert "server1" in result
        assert "server2" in result
    
    def test_has_selections(self):
        """Test selection detection."""
        state = SelectionState()
        
        # No selections initially
        assert not state.has_selections()
        
        # Single selection
        state.single_selection = "test-server"
        assert state.has_selections()
        
        # Multi selections
        state.mode = SelectionMode.MULTI
        state.single_selection = None
        assert not state.has_selections()
        
        state.multi_selections.add("server1")
        assert state.has_selections()


class TestSelectionManager:
    """Tests for SelectionManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SelectionManager()
        self.callback_mock = Mock()
    
    def test_initial_state(self):
        """Test initial manager state."""
        assert self.manager.state.mode == SelectionMode.SINGLE
        assert not self.manager.state.has_selections()
    
    def test_register_callback(self):
        """Test callback registration."""
        self.manager.register_callback("selection_changed", self.callback_mock)
        
        # Trigger a selection change
        self.manager.handle_enter("test-item")
        
        self.callback_mock.assert_called_once()
    
    def test_toggle_mode_single_to_multi(self):
        """Test toggling from single to multi mode."""
        callback_mock = Mock()
        self.manager.register_callback("mode_changed", callback_mock)
        
        # Set a single selection
        self.manager.handle_enter("server1")
        assert self.manager.state.single_selection == "server1"
        
        # Toggle to multi mode
        result = self.manager.toggle_mode()
        
        assert result == SelectionMode.MULTI
        assert self.manager.state.mode == SelectionMode.MULTI
        assert self.manager.state.single_selection is None
        assert "server1" in self.manager.state.multi_selections
        callback_mock.assert_called_once_with(SelectionMode.MULTI)
    
    def test_toggle_mode_multi_to_single(self):
        """Test toggling from multi to single mode."""
        # Start in multi mode with selections
        self.manager.toggle_mode()  # Switch to multi
        self.manager.state.multi_selections.add("server1")
        self.manager.state.multi_selections.add("server2")
        
        callback_mock = Mock()
        self.manager.register_callback("mode_changed", callback_mock)
        
        # Toggle back to single mode
        result = self.manager.toggle_mode()
        
        assert result == SelectionMode.SINGLE
        assert self.manager.state.mode == SelectionMode.SINGLE
        assert self.manager.state.single_selection in ["server1", "server2"]
        assert len(self.manager.state.multi_selections) == 0
        callback_mock.assert_called_once_with(SelectionMode.SINGLE)
    
    def test_handle_enter_single_mode(self):
        """Test Enter key handling in single mode."""
        callback_mock = Mock()
        self.manager.register_callback("selection_changed", callback_mock)
        
        result = self.manager.handle_enter("test-server")
        
        assert result is True  # Should advance pane
        assert self.manager.state.single_selection == "test-server"
        callback_mock.assert_called_once()
    
    def test_handle_enter_multi_mode(self):
        """Test Enter key handling in multi mode."""
        self.manager.toggle_mode()  # Switch to multi mode
        callback_mock = Mock()
        self.manager.register_callback("selection_changed", callback_mock)
        
        result = self.manager.handle_enter("server1")
        
        assert result is True  # Should advance pane
        assert "server1" in self.manager.state.multi_selections
        callback_mock.assert_called_once()
    
    def test_handle_spacebar_single_to_multi(self):
        """Test Spacebar key handling - switch to multi mode."""
        callback_mock_mode = Mock()
        callback_mock_selection = Mock()
        self.manager.register_callback("mode_changed", callback_mock_mode)
        self.manager.register_callback("selection_changed", callback_mock_selection)
        
        result = self.manager.handle_spacebar("server1")
        
        assert result is False  # Should not advance pane
        assert self.manager.state.mode == SelectionMode.MULTI
        assert "server1" in self.manager.state.multi_selections
        callback_mock_mode.assert_called_once_with(SelectionMode.MULTI)
        callback_mock_selection.assert_called_once()
    
    def test_handle_spacebar_multi_mode_toggle(self):
        """Test Spacebar key handling in multi mode - toggle selection."""
        self.manager.toggle_mode()  # Switch to multi mode
        callback_mock = Mock()
        self.manager.register_callback("selection_changed", callback_mock)
        
        # Add item
        result1 = self.manager.handle_spacebar("server1")
        assert result1 is False
        assert "server1" in self.manager.state.multi_selections
        
        # Toggle same item off
        result2 = self.manager.handle_spacebar("server1")
        assert result2 is False
        assert "server1" not in self.manager.state.multi_selections
        
        # Should have been called twice
        assert callback_mock.call_count == 2
    
    def test_set_focus_area(self):
        """Test focus area changes."""
        callback_mock = Mock()
        self.manager.register_callback("focus_changed", callback_mock)
        
        self.manager.set_focus_area(FocusArea.DEPLOYMENT_MATRIX)
        
        assert self.manager.state.focus_area == FocusArea.DEPLOYMENT_MATRIX
        callback_mock.assert_called_once_with(FocusArea.DEPLOYMENT_MATRIX)
    
    def test_set_focus_area_no_change(self):
        """Test focus area doesn't trigger callback when unchanged."""
        callback_mock = Mock()
        self.manager.register_callback("focus_changed", callback_mock)
        
        # Set to same area (initial value)
        self.manager.set_focus_area(FocusArea.SERVER_TREE)
        
        callback_mock.assert_not_called()
    
    def test_clear_selections(self):
        """Test clearing all selections."""
        # Set up selections
        self.manager.handle_enter("server1")
        self.manager.toggle_mode()  # Switch to multi
        self.manager.handle_spacebar("server2")
        
        callback_mock = Mock()
        self.manager.register_callback("selection_changed", callback_mock)
        
        self.manager.clear_selections()
        
        assert not self.manager.state.has_selections()
        callback_mock.assert_called_once()
    
    def test_get_selection_info_single_mode(self):
        """Test selection info string in single mode."""
        # No selection
        info = self.manager.get_selection_info()
        assert info == "No selection"
        
        # With selection
        self.manager.handle_enter("test-server")
        info = self.manager.get_selection_info()
        assert "Selected: test-server" in info
    
    def test_get_selection_info_multi_mode(self):
        """Test selection info string in multi mode."""
        self.manager.toggle_mode()  # Switch to multi mode
        
        # No selections
        info = self.manager.get_selection_info()
        assert "Multi-select mode: No selections" in info
        
        # One selection
        self.manager.handle_spacebar("server1")
        info = self.manager.get_selection_info()
        assert "Multi-select: server1" in info
        
        # Multiple selections
        self.manager.handle_spacebar("server2")
        info = self.manager.get_selection_info()
        assert "Multi-select: 2 items selected" in info
    
    def test_callback_error_handling(self):
        """Test that callback errors don't break the manager."""
        # Register a callback that throws an exception
        def failing_callback(*args):
            raise Exception("Test error")
        
        self.manager.register_callback("selection_changed", failing_callback)
        
        # This should not raise an exception
        self.manager.handle_enter("test-server")
        
        # State should still be updated
        assert self.manager.state.single_selection == "test-server"


class TestIntegrationScenarios:
    """Integration tests for common usage scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SelectionManager()
    
    def test_single_selection_workflow(self):
        """Test complete single selection workflow."""
        # Select server
        advance = self.manager.handle_enter("postgres-server")
        assert advance is True
        assert self.manager.get_selected_items() == "postgres-server"
        
        # Navigate to next pane
        self.manager.set_focus_area(FocusArea.DEPLOYMENT_MATRIX)
        
        # Select deployment cell
        cell_data = {"server": "postgres-server", "platform": "docker"}
        advance = self.manager.handle_enter(cell_data)
        assert advance is True
        assert self.manager.get_selected_items() == cell_data
        
        # Navigate to details pane
        self.manager.set_focus_area(FocusArea.DETAILS_PANE)
        
        # Confirm selection
        advance = self.manager.handle_enter("postgres-server-details")
        assert advance is True
    
    def test_multi_selection_workflow(self):
        """Test complete multi-selection workflow."""
        # Start multi-select with spacebar
        advance = self.manager.handle_spacebar("server1")
        assert advance is False
        assert self.manager.state.mode == SelectionMode.MULTI
        
        # Add more servers
        self.manager.handle_spacebar("server2")
        self.manager.handle_spacebar("server3")
        
        selections = self.manager.get_selected_items()
        assert len(selections) == 3
        assert "server1" in selections
        assert "server2" in selections
        assert "server3" in selections
        
        # Remove one server
        self.manager.handle_spacebar("server2")
        selections = self.manager.get_selected_items()
        assert len(selections) == 2
        assert "server2" not in selections
        
        # Confirm with enter (should advance)
        advance = self.manager.handle_enter("server4")
        assert advance is True
        
        # Server4 should now also be in selections
        selections = self.manager.get_selected_items()
        assert "server4" in selections
    
    def test_mode_switching_preserves_data(self):
        """Test that mode switching preserves selections appropriately."""
        # Start with single selection
        self.manager.handle_enter("initial-server")
        
        # Switch to multi mode - should preserve selection
        self.manager.toggle_mode()
        selections = self.manager.get_selected_items()
        assert "initial-server" in selections
        
        # Add more selections
        self.manager.handle_spacebar("server2")
        self.manager.handle_spacebar("server3")
        
        # Switch back to single mode - should take first item
        self.manager.toggle_mode()
        selection = self.manager.get_selected_items()
        assert selection in ["initial-server", "server2", "server3"]
        
        # Multi selections should be cleared
        assert len(self.manager.state.multi_selections) == 0


if __name__ == "__main__":
    pytest.main([__file__])