"""Professional Textual TUI for MCP Manager - Server Registry & Deployment."""

from pathlib import Path
from typing import Optional, Dict, Any
import structlog

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Static, Label, Button, 
    DataTable
)
from textual.reactive import reactive
from textual import events
from textual.css.query import NoMatches

from .core import MCPServerRegistry, DeploymentManager, PlatformManager, ProjectDetector

logger = structlog.get_logger()


class MCPManagerTUI(App[None]):
    """Professional MCP Manager TUI Application."""
    
    TITLE = "MCP Manager - Server Registry & Deployment"
    SUB_TITLE = "Professional MCP server management and deployment"
    
    CSS = """
    /* Professional theme inspired by RepoMap */
    
    /* Global styles */
    * {
        scrollbar-background: $surface;
        scrollbar-color: $primary;
        scrollbar-corner-color: $surface;
        scrollbar-size: 1 1;
    }
    
    /* Main layout */
    #main-container {
        height: 100%;
        width: 100%;
        layout: horizontal;
        background: $surface;
        border: none;
    }
    
    /* Left pane - Server Registry */
    #left-pane {
        width: 40%;
        height: 100%;
        layout: vertical;
        background: $surface;
        border-right: solid $primary-background;
    }
    
    /* Right pane - Details & Deployment */
    #right-pane {
        width: 60%;
        height: 100%;
        layout: vertical;
        background: $surface;
    }
    
    /* Header styling */
    Header {
        background: $primary;
        color: $text;
        text-align: center;
        height: 3;
        content-align: center middle;
    }
    
    /* Footer styling */
    Footer {
        background: $primary-background;
        color: $text;
        height: 3;
        dock: bottom;
    }
    
    /* Panel headers */
    .panel-header {
        height: 3;
        background: $primary-background;
        color: $text;
        text-align: center;
        content-align: center middle;
        text-style: bold;
        border-bottom: solid $primary;
    }
    
    /* Server registry styles */
    #server-list {
        height: 1fr;
        background: $surface;
        border: none;
    }
    
    #server-list > .datatable--header {
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    
    #server-list > .datatable--cursor {
        background: $primary 20%;
    }
    
    #server-list > .datatable--hover {
        background: $accent 10%;
    }
    
    /* Deployment matrix styles */
    #deployment-matrix {
        height: 1fr;
        background: $surface;
        border: none;
        margin: 1 0;
    }
    
    #deployment-matrix > .datatable--header {
        background: $accent;
        color: $text;
        text-style: bold;
    }
    
    #deployment-matrix > .datatable--cursor {
        background: $accent 20%;
    }
    
    /* Status panel */
    #status-panel {
        height: 8;
        background: $panel;
        border: solid $primary-background;
        border-title-color: $primary;
        border-title-style: bold;
        margin: 1;
        padding: 1;
    }
    
    /* Action buttons */
    .action-buttons {
        height: 4;
        layout: horizontal;
        align: center middle;
        background: $surface;
        padding: 1;
    }
    
    .action-button {
        margin: 0 1;
        min-width: 12;
        background: $accent;
        color: $text;
        border: solid $primary;
        text-align: center;
    }
    
    .action-button:hover {
        background: $accent 80%;
        border: solid $primary 80%;
    }
    
    .action-button.-primary {
        background: $primary;
        border: solid $primary;
    }
    
    .action-button.-primary:hover {
        background: $primary 80%;
    }
    
    /* Info display */
    .info-text {
        color: $text-muted;
        text-align: center;
        margin: 1;
    }
    
    .error-text {
        color: $error;
        text-style: bold;
    }
    
    .success-text {
        color: $success;
        text-style: bold;
    }
    
    .warning-text {
        color: $warning;
        text-style: bold;
    }
    
    /* Enhanced focus indicators */
    *:focus {
        border: solid $primary;
        box-shadow: 0 0 4 2 $primary 20%;
    }
    
    /* Loading states */
    .loading {
        background: $surface;
        color: $text-muted;
        text-align: center;
        content-align: center middle;
    }
    
    /* Dark theme optimizations */
    App.-dark-mode {
        background: #1a1a1a;
    }
    
    App.-dark-mode .panel-header {
        background: #2d2d2d;
        border-bottom: solid #404040;
    }
    
    App.-dark-mode #server-list > .datatable--header,
    App.-dark-mode #deployment-matrix > .datatable--header {
        background: #2d2d2d;
    }
    """
    
    BINDINGS = [
        Binding("a", "add_server", "Add Server", priority=True),
        Binding("e", "edit_server", "Edit Server", priority=True),
        Binding("d", "deploy", "Deploy", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("h", "health_check", "Health Check", priority=True),
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "help", "Help"),
        Binding("f1", "toggle_help", "Help"),
    ]
    
    # Reactive attributes for state management
    current_server: reactive[Optional[str]] = reactive(None)
    deployment_status: reactive[Dict[str, Any]] = reactive({})
    registry_stats: reactive[Dict[str, Any]] = reactive({})
    
    def __init__(self, registry_file: Optional[Path] = None):
        """Initialize the MCP Manager TUI.
        
        Args:
            registry_file: Path to the MCP servers registry file
        """
        super().__init__()
        self.registry_file = registry_file
        self.registry: Optional[MCPServerRegistry] = None
        self.deployment_manager: Optional[DeploymentManager] = None
        self.platform_manager: Optional[PlatformManager] = None
        self.project_detector: Optional[ProjectDetector] = None
    
    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            # Left pane: Server Registry
            with Vertical(id="left-pane"):
                yield Label("📋 Server Registry", classes="panel-header")
                yield DataTable(id="server-list")
                
                # Action buttons for server management
                with Container(classes="action-buttons"):
                    yield Button("➕ Add", id="btn-add", classes="action-button -primary")
                    yield Button("✏️ Edit", id="btn-edit", classes="action-button")
                    yield Button("🗑️ Remove", id="btn-remove", classes="action-button")
            
            # Right pane: Deployment & Details
            with Vertical(id="right-pane"):
                yield Label("🚀 Deployment Matrix", classes="panel-header")
                yield DataTable(id="deployment-matrix")
                
                # Status panel
                with Container(id="status-panel", border_title="📊 Status"):
                    yield Label("Ready to manage MCP servers", id="status-text", classes="info-text")
                    yield Label("", id="stats-text", classes="info-text")
                
                # Deployment action buttons
                with Container(classes="action-buttons"):
                    yield Button("🚀 Deploy", id="btn-deploy", classes="action-button -primary")
                    yield Button("🔄 Refresh", id="btn-refresh", classes="action-button")
                    yield Button("🏥 Health", id="btn-health", classes="action-button")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application on mount."""
        logger.info("Initializing MCP Manager TUI")
        
        try:
            # Initialize core components
            self.registry = MCPServerRegistry(self.registry_file)
            self.deployment_manager = DeploymentManager(self.registry)
            self.platform_manager = PlatformManager()
            self.project_detector = ProjectDetector()
            
            # Setup data tables
            self._setup_server_list()
            self._setup_deployment_matrix()
            
            # Load initial data
            self._refresh_data()
            
            logger.info("MCP Manager TUI initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize TUI", error=str(e))
            self._show_error(f"Initialization failed: {e}")
    
    def _setup_server_list(self) -> None:
        """Setup the server list data table."""
        try:
            server_table = self.query_one("#server-list", DataTable)
            server_table.add_columns(
                "Name",
                "Type", 
                "Status",
                "Tags",
                "Modified"
            )
            server_table.cursor_type = "row"
            server_table.zebra_stripes = True
        except NoMatches:
            logger.warning("Server list table not found during setup")
    
    def _setup_deployment_matrix(self) -> None:
        """Setup the deployment matrix data table."""
        try:
            matrix_table = self.query_one("#deployment-matrix", DataTable)
            matrix_table.add_columns(
                "Server",
                "Claude Desktop",
                "Claude Code",
                "Projects",
                "Status"
            )
            matrix_table.cursor_type = "row"
            matrix_table.zebra_stripes = True
        except NoMatches:
            logger.warning("Deployment matrix table not found during setup")
    
    def _refresh_data(self) -> None:
        """Refresh all data in the TUI."""
        if not self.registry:
            return
        
        try:
            # Update server list
            self._update_server_list()
            
            # Update deployment matrix
            self._update_deployment_matrix()
            
            # Update status and stats
            self._update_status()
            
            logger.info("Data refreshed successfully")
        except Exception as e:
            logger.error("Failed to refresh data", error=str(e))
            self._show_error(f"Refresh failed: {e}")
    
    def _update_server_list(self) -> None:
        """Update the server list table."""
        if not self.registry:
            return
        
        try:
            server_table = self.query_one("#server-list", DataTable)
            server_table.clear()
            
            servers = self.registry.list_servers()
            for name, entry in servers.items():
                status = "✅ Enabled" if entry.metadata.enabled else "❌ Disabled"
                tags_str = ", ".join(entry.metadata.tags[:2]) + ("..." if len(entry.metadata.tags) > 2 else "")
                
                server_table.add_row(
                    name,
                    entry.type.upper(),
                    status,
                    tags_str or "-",
                    entry.metadata.last_modified,
                    key=name
                )
        except NoMatches:
            logger.warning("Server list table not found during update")
        except Exception as e:
            logger.error("Failed to update server list", error=str(e))
    
    def _update_deployment_matrix(self) -> None:
        """Update the deployment matrix table."""
        if not self.deployment_manager:
            return
        
        try:
            matrix_table = self.query_one("#deployment-matrix", DataTable)
            matrix_table.clear()
            
            deployment_matrix = self.deployment_manager.get_deployment_matrix()
            
            for server_name, deployments in deployment_matrix.items():
                claude_desktop = "✅" if deployments.get("platform:claude_desktop", False) else "❌"
                claude_code = "✅" if deployments.get("platform:claude_code", False) else "❌"
                
                # Count project deployments
                project_count = sum(1 for k, v in deployments.items() 
                                  if k.startswith("project:") and v)
                projects_str = f"📁 {project_count}" if project_count > 0 else "❌"
                
                # Overall status
                total_deployed = sum(1 for v in deployments.values() if v)
                status = f"🚀 {total_deployed}/{len(deployments)}" if total_deployed > 0 else "❌ None"
                
                matrix_table.add_row(
                    server_name,
                    claude_desktop,
                    claude_code,
                    projects_str,
                    status,
                    key=server_name
                )
        except NoMatches:
            logger.warning("Deployment matrix table not found during update")
        except Exception as e:
            logger.error("Failed to update deployment matrix", error=str(e))
    
    def _update_status(self) -> None:
        """Update status information."""
        if not self.registry:
            return
        
        try:
            stats = self.registry.get_stats()
            self.registry_stats = stats
            
            status_text = self.query_one("#status-text", Label)
            stats_text = self.query_one("#stats-text", Label)
            
            status_text.update("🟢 MCP Manager Ready")
            
            stats_msg = (
                f"📊 Servers: {stats['total_servers']} total, "
                f"{stats['enabled_servers']} enabled | "
                f"🏷️ Tags: {stats['total_tags']}"
            )
            stats_text.update(stats_msg)
            
        except NoMatches:
            logger.warning("Status labels not found during update")
        except Exception as e:
            logger.error("Failed to update status", error=str(e))
    
    def _show_error(self, message: str) -> None:
        """Display an error message."""
        try:
            status_text = self.query_one("#status-text", Label)
            status_text.update(f"🔴 Error: {message}")
            status_text.add_class("error-text")
        except NoMatches:
            logger.error("Could not display error message", message=message)
    
    def _show_success(self, message: str) -> None:
        """Display a success message."""
        try:
            status_text = self.query_one("#status-text", Label)
            status_text.update(f"🟢 {message}")
            status_text.add_class("success-text")
            # Auto-clear after 3 seconds
            self.set_timer(3.0, lambda: status_text.update("🟢 MCP Manager Ready"))
        except NoMatches:
            logger.warning("Could not display success message", message=message)
    
    # Action handlers
    async def action_add_server(self) -> None:
        """Handle add server action."""
        logger.info("Add server action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Add server dialog will be implemented by Agent 2")
    
    async def action_edit_server(self) -> None:
        """Handle edit server action."""
        logger.info("Edit server action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Edit server dialog will be implemented by Agent 2")
    
    async def action_deploy(self) -> None:
        """Handle deploy action."""
        logger.info("Deploy action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Deploy dialog will be implemented by Agent 2")
    
    async def action_refresh(self) -> None:
        """Handle refresh action."""
        logger.info("Refreshing data...")
        self._refresh_data()
        self._show_success("Data refreshed successfully")
    
    async def action_health_check(self) -> None:
        """Handle health check action."""
        logger.info("Health check action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Health check will be implemented by Agent 2")
    
    async def action_help(self) -> None:
        """Show help information."""
        help_text = """
        🔧 MCP Manager - Keyboard Shortcuts:
        
        a - Add new MCP server
        e - Edit selected server
        d - Deploy servers to targets
        r - Refresh all data
        h - Run health checks
        q - Quit application
        ? - Show this help
        
        Use arrow keys to navigate tables.
        """
        self._show_success("Help: See terminal for keyboard shortcuts")
        print(help_text)
    
    async def action_toggle_help(self) -> None:
        """Toggle help display."""
        await self.action_help()
    
    # Button event handlers
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_actions = {
            "btn-add": self.action_add_server,
            "btn-edit": self.action_edit_server,
            "btn-remove": self._remove_server,
            "btn-deploy": self.action_deploy,
            "btn-refresh": self.action_refresh,
            "btn-health": self.action_health_check,
        }
        
        action = button_actions.get(event.button.id)
        if action:
            self.call_later(action)
    
    async def _remove_server(self) -> None:
        """Handle remove server action."""
        logger.info("Remove server action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Remove server confirmation will be implemented by Agent 2")
    
    # Table event handlers
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in data tables."""
        if event.data_table.id == "server-list":
            self.current_server = str(event.row_key)
            logger.info("Selected server", server=self.current_server)
        elif event.data_table.id == "deployment-matrix":
            self.current_server = str(event.row_key)
            logger.info("Selected server from matrix", server=self.current_server)


def run_tui() -> int:
    """Launch the Textual TUI interface."""
    try:
        app = MCPManagerTUI()
        app.run()
        return 0
    except KeyboardInterrupt:
        logger.info("TUI interrupted by user")
        return 0
    except Exception as e:
        logger.error("TUI crashed", error=str(e))
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_tui())