# ABOUTME: Advanced selection and interaction management system for MCP Manager TUI
# ABOUTME: Provides multi-select, keyboard navigation, visual feedback, and state persistence

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable


class SelectionMode(Enum):
    """Selection mode enumeration."""
    SINGLE = "single"
    MULTI = "multi"


class FocusArea(Enum):
    """Focus area enumeration for navigation."""
    SERVER_TREE = "server_tree"
    DEPLOYMENT_MATRIX = "deployment_matrix"
    DETAILS_PANE = "details_pane"


@dataclass
class SelectionState:
    """Represents the current selection state."""
    mode: SelectionMode = SelectionMode.SINGLE
    single_selection: Optional[Any] = None
    multi_selections: Set[Any] = field(default_factory=set)
    focus_area: FocusArea = FocusArea.SERVER_TREE
    
    def clear_selections(self) -> None:
        """Clear all selections."""
        self.single_selection = None
        self.multi_selections.clear()
    
    def get_selected_items(self) -> Union[Any, Set[Any]]:
        """Return current selections based on mode."""
        if self.mode == SelectionMode.SINGLE:
            return self.single_selection
        return self.multi_selections.copy()
    
    def has_selections(self) -> bool:
        """Check if there are any selections."""
        if self.mode == SelectionMode.SINGLE:
            return self.single_selection is not None
        return bool(self.multi_selections)


class SelectionManager:
    """Manages selection state and provides selection logic."""
    
    def __init__(self) -> None:
        self.state = SelectionState()
        self._callbacks: Dict[str, List[Callable]] = {
            "selection_changed": [],
            "mode_changed": [],
            "focus_changed": [],
        }
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback for selection events."""
        if event_type in self._callbacks:
            self._callbacks[event_type].append(callback)
    
    def _notify_callbacks(self, event_type: str, *args: Any) -> None:
        """Notify registered callbacks of events."""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(*args)
            except Exception:
                # Log error but don't break the selection logic
                pass
    
    def toggle_mode(self) -> SelectionMode:
        """Switch between single and multi-select modes."""
        if self.state.mode == SelectionMode.SINGLE:
            self.state.mode = SelectionMode.MULTI
            # Convert single selection to multi if exists
            if self.state.single_selection is not None:
                self.state.multi_selections.add(self.state.single_selection)
                self.state.single_selection = None
        else:
            self.state.mode = SelectionMode.SINGLE
            # Convert multi to single (take first item)
            if self.state.multi_selections:
                self.state.single_selection = next(iter(self.state.multi_selections))
                self.state.multi_selections.clear()
        
        self._notify_callbacks("mode_changed", self.state.mode)
        return self.state.mode
    
    def handle_enter(self, item: Any) -> bool:
        """Handle Enter key press - context-aware selection + advance."""
        if self.state.mode == SelectionMode.SINGLE:
            self.state.single_selection = item
            self.state.multi_selections.clear()
        else:
            # In multi mode, Enter adds to selection
            self.state.multi_selections.add(item)
        
        self._notify_callbacks("selection_changed", self.state.get_selected_items())
        return True  # Advance to next pane
    
    def handle_spacebar(self, item: Any) -> bool:
        """Handle Spacebar press - toggle multi-select mode."""
        if self.state.mode == SelectionMode.SINGLE:
            # Switch to multi-select mode and add item
            self.toggle_mode()
            self.state.multi_selections.add(item)
        else:
            # Toggle item in multi-selection
            if item in self.state.multi_selections:
                self.state.multi_selections.remove(item)
            else:
                self.state.multi_selections.add(item)
        
        self._notify_callbacks("selection_changed", self.state.get_selected_items())
        return False  # Don't advance pane
    
    def set_focus_area(self, area: FocusArea) -> None:
        """Change the focused area."""
        if self.state.focus_area != area:
            self.state.focus_area = area
            self._notify_callbacks("focus_changed", area)
    
    def clear_selections(self) -> None:
        """Clear all selections."""
        self.state.clear_selections()
        self._notify_callbacks("selection_changed", self.state.get_selected_items())
    
    def get_selected_items(self) -> Union[Any, Set[Any]]:
        """Return current selections."""
        return self.state.get_selected_items()
    
    def get_selection_info(self) -> str:
        """Get human-readable selection information for status display."""
        if self.state.mode == SelectionMode.SINGLE:
            if self.state.single_selection is not None:
                return f"Selected: {self.state.single_selection}"
            return "No selection"
        else:
            count = len(self.state.multi_selections)
            if count == 0:
                return "Multi-select mode: No selections"
            elif count == 1:
                item = next(iter(self.state.multi_selections))
                return f"Multi-select: {item}"
            else:
                return f"Multi-select: {count} items selected"