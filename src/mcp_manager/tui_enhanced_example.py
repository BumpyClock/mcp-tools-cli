# ABOUTME: Example integration of SelectionManager with Textual TUI widgets
# ABOUTME: Demonstrates Enter/Spacebar patterns, Tab navigation, and visual feedback

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Tree, DataTable, Static, Footer, Header
from textual import events

from .selection_manager import SelectionManager, SelectionMode, FocusArea


class EnhancedServerTree(Tree):
    """Example Tree widget with SelectionManager integration."""
    
    def __init__(self, selection_manager: SelectionManager):
        super().__init__("📦 MCP Servers")
        self.selection_manager = selection_manager
        self.can_focus = True
    
    def on_mount(self) -> None:
        """Add sample data when mounted."""
        root = self.root
        servers = root.add("🖥️ Servers")
        servers.add_leaf("postgres-server", data="postgres-server")
        servers.add_leaf("file-server", data="file-server") 
        servers.add_leaf("web-server", data="web-server")
        servers.expand()
    
    async def on_key(self, event: events.Key) -> None:
        """Handle enhanced keyboard navigation."""
        if event.key == "enter":
            if self.cursor_node and self.cursor_node.data:
                advance = self.selection_manager.handle_enter(self.cursor_node.data)
                if advance:
                    self.selection_manager.set_focus_area(FocusArea.DEPLOYMENT_MATRIX)
            event.prevent_default()
        
        elif event.key == "space":
            if self.cursor_node and self.cursor_node.data:
                self.selection_manager.handle_spacebar(self.cursor_node.data)
            event.prevent_default()
        
        else:
            await super().on_key(event)


class EnhancedDeploymentMatrix(DataTable):
    """Example DataTable widget with SelectionManager integration."""
    
    def __init__(self, selection_manager: SelectionManager):
        super().__init__()
        self.selection_manager = selection_manager
        self.can_focus = True
        self.cursor_type = "cell"
    
    def on_mount(self) -> None:
        """Add sample data when mounted."""
        self.add_column("Server", width=15)
        self.add_column("Docker", width=8)
        self.add_column("Claude", width=8)
        self.add_column("Local", width=8)
        
        self.add_row("postgres-server", "✅", "❌", "✅", key="postgres")
        self.add_row("file-server", "❌", "✅", "✅", key="file")
        self.add_row("web-server", "✅", "✅", "❌", key="web")
    
    async def on_key(self, event: events.Key) -> None:
        """Handle enhanced keyboard navigation."""
        if event.key == "enter":
            cursor_cell = self.cursor_cell
            if cursor_cell and cursor_cell.column > 0:
                row_key = self.get_row_key_from_coordinate(cursor_cell)
                cell_data = {
                    "server": row_key,
                    "platform": self.columns[cursor_cell.column].label,
                    "row": cursor_cell.row,
                    "col": cursor_cell.column
                }
                advance = self.selection_manager.handle_enter(cell_data)
                if advance:
                    self.selection_manager.set_focus_area(FocusArea.DETAILS_PANE)
            event.prevent_default()
        
        elif event.key == "space":
            cursor_cell = self.cursor_cell
            if cursor_cell and cursor_cell.column > 0:
                row_key = self.get_row_key_from_coordinate(cursor_cell)
                cell_data = {
                    "server": row_key,
                    "platform": self.columns[cursor_cell.column].label,
                    "row": cursor_cell.row,
                    "col": cursor_cell.column
                }
                self.selection_manager.handle_spacebar(cell_data)
            event.prevent_default()
        
        else:
            await super().on_key(event)


class EnhancedDetailsPane(Static):
    """Example Static widget with SelectionManager integration."""
    
    def __init__(self, selection_manager: SelectionManager):
        super().__init__("Select an item to see details")
        self.selection_manager = selection_manager
        self.can_focus = True
        self.current_item = None
        
        # Listen for selection changes
        self.selection_manager.register_callback("selection_changed", self._update_display)
    
    def _update_display(self, selections):
        """Update display when selections change."""
        if self.selection_manager.state.mode == SelectionMode.SINGLE:
            if selections:
                self.current_item = selections
                self.update(f"Selected: {selections}")
            else:
                self.current_item = None
                self.update("No selection")
        else:
            if selections:
                items = list(selections)
                self.current_item = items
                self.update(f"Multi-select: {len(items)} items\n" + "\n".join(str(item) for item in items))
            else:
                self.current_item = None
                self.update("Multi-select: No items selected")
    
    async def on_key(self, event: events.Key) -> None:
        """Handle enhanced keyboard navigation."""
        if event.key == "enter":
            if self.current_item:
                self.selection_manager.handle_enter(self.current_item)
            event.prevent_default()
        
        elif event.key == "space":
            if self.current_item:
                self.selection_manager.handle_spacebar(self.current_item)
            event.prevent_default()


class StatusBar(Static):
    """Status bar showing selection information and mode."""
    
    def __init__(self, selection_manager: SelectionManager):
        super().__init__()
        self.selection_manager = selection_manager
        
        # Register for all selection events
        self.selection_manager.register_callback("selection_changed", self.update_status)
        self.selection_manager.register_callback("mode_changed", self.update_status)
        self.selection_manager.register_callback("focus_changed", self.update_status)
        
        self.update_status()
    
    def update_status(self, *args):
        """Update the status bar display."""
        mode = self.selection_manager.state.mode.value.upper()
        focus = self.selection_manager.state.focus_area.value.replace("_", " ").title()
        selection_info = self.selection_manager.get_selection_info()
        
        status = f"Mode: {mode} | {selection_info} | Focus: {focus}"
        self.update(status)


class SelectionDemoApp(App):
    """Demonstration app showcasing advanced selection and interaction logic."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #main-container {
        layout: horizontal;
        height: 1fr;
    }
    
    #left-pane, #center-pane, #right-pane {
        width: 1fr;
        border: solid $primary;
        margin: 1;
    }
    
    #status-bar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    
    /* Focus indicators */
    Tree:focus {
        border: solid $accent;
        border-title-color: $accent;
    }
    
    DataTable:focus {
        border: solid $accent;
        border-title-color: $accent;
    }
    
    Static:focus {
        border: solid $accent;
        border-title-color: $accent;
    }
    
    /* Multi-select mode styling */
    .multi-select-mode Tree {
        border-title-color: $warning;
    }
    
    .multi-select-mode DataTable {
        border-title-color: $warning;
    }
    
    .multi-select-mode Static {
        border-title-color: $warning;
    }
    """
    
    BINDINGS = [
        Binding("tab", "next_pane", "Next Pane", priority=True),
        Binding("shift+tab", "prev_pane", "Previous Pane", priority=True),
        Binding("escape", "clear_selections", "Clear Selections"),
        Binding("ctrl+m", "toggle_mode", "Toggle Mode"),
        Binding("q", "quit", "Quit"),
        Binding("?", "show_help", "Help"),
    ]
    
    def __init__(self):
        super().__init__()
        self.selection_manager = SelectionManager()
        self.widgets = {}
    
    def compose(self) -> ComposeResult:
        """Create the app layout."""
        yield Header()
        
        with Horizontal(id="main-container"):
            # Left pane - Server tree
            tree = EnhancedServerTree(self.selection_manager)
            tree.border_title = "Server Tree"
            self.widgets["tree"] = tree
            yield tree
            
            # Center pane - Deployment matrix
            matrix = EnhancedDeploymentMatrix(self.selection_manager)
            matrix.border_title = "Deployment Matrix"
            self.widgets["matrix"] = matrix
            yield matrix
            
            # Right pane - Details
            details = EnhancedDetailsPane(self.selection_manager)
            details.border_title = "Details"
            self.widgets["details"] = details
            yield details
        
        # Status bar
        status = StatusBar(self.selection_manager)
        self.widgets["status"] = status
        yield status
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application."""
        # Set up callbacks
        self.selection_manager.register_callback("focus_changed", self._handle_focus_change)
        self.selection_manager.register_callback("mode_changed", self._handle_mode_change)
        
        # Set initial focus
        self.set_focus(self.widgets["tree"])
    
    def _handle_focus_change(self, focus_area: FocusArea):
        """Handle focus area changes."""
        widget_map = {
            FocusArea.SERVER_TREE: "tree",
            FocusArea.DEPLOYMENT_MATRIX: "matrix",
            FocusArea.DETAILS_PANE: "details",
        }
        
        widget_key = widget_map.get(focus_area)
        if widget_key and widget_key in self.widgets:
            self.set_focus(self.widgets[widget_key])
    
    def _handle_mode_change(self, mode: SelectionMode):
        """Handle selection mode changes."""
        if mode == SelectionMode.MULTI:
            self.add_class("multi-select-mode")
        else:
            self.remove_class("multi-select-mode")
    
    def action_next_pane(self):
        """Move focus to next pane."""
        current_focus = self.selection_manager.state.focus_area
        
        if current_focus == FocusArea.SERVER_TREE:
            self.selection_manager.set_focus_area(FocusArea.DEPLOYMENT_MATRIX)
        elif current_focus == FocusArea.DEPLOYMENT_MATRIX:
            self.selection_manager.set_focus_area(FocusArea.DETAILS_PANE)
        else:
            self.selection_manager.set_focus_area(FocusArea.SERVER_TREE)
    
    def action_prev_pane(self):
        """Move focus to previous pane."""
        current_focus = self.selection_manager.state.focus_area
        
        if current_focus == FocusArea.SERVER_TREE:
            self.selection_manager.set_focus_area(FocusArea.DETAILS_PANE)
        elif current_focus == FocusArea.DEPLOYMENT_MATRIX:
            self.selection_manager.set_focus_area(FocusArea.SERVER_TREE)
        else:
            self.selection_manager.set_focus_area(FocusArea.DEPLOYMENT_MATRIX)
    
    def action_clear_selections(self):
        """Clear all selections."""
        self.selection_manager.clear_selections()
    
    def action_toggle_mode(self):
        """Toggle selection mode."""
        self.selection_manager.toggle_mode()
    
    def action_show_help(self):
        """Show help information."""
        help_text = """
        🔧 Selection & Interaction Demo - Keyboard Shortcuts:
        
        SELECTION PATTERNS:
        Enter  - Select item and advance to next pane (single mode)
               - Add item to selection and advance (multi mode)
        Space  - Toggle multi-select mode
               - Toggle item in/out of multi-selection
        
        NAVIGATION:
        Tab         - Move focus to next pane
        Shift+Tab   - Move focus to previous pane
        Arrow Keys  - Navigate within current widget
        
        MODES:
        Ctrl+M      - Toggle between single/multi-select modes
        Escape      - Clear all selections
        
        OTHER:
        q - Quit
        ? - Show this help
        
        VISUAL INDICATORS:
        - Focused widgets have accent borders
        - Multi-select mode widgets have warning-colored borders
        - Status bar shows current mode, selections, and focus
        """
        self.bell()  # Audio feedback
        # In a real app, this would show a modal or log to a dedicated area
        print(help_text)


def run_selection_demo() -> int:
    """Run the selection and interaction demo."""
    try:
        app = SelectionDemoApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"Demo failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_selection_demo())