"""MCP Manager TUI Application - Working implementation with Registry Integration."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, Static, Button
from textual.binding import Binding
from pathlib import Path
import json
from datetime import datetime
from typing import Optional

from mcp_manager.core import MCPServerRegistry, DeploymentManager, PlatformManager, ProjectDetector


class MCPManagerTUI(App):
    """Professional TUI for MCP Manager with Registry Integration."""
    
    TITLE = "MCP Manager - Server Registry & Deployment"
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #left-panel {
        width: 40%;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    #right-panel {
        width: 60%;
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }
    
    DataTable {
        height: 100%;
    }
    
    .action-button {
        margin: 1;
        width: auto;
    }
    
    #status-bar {
        dock: bottom;
        height: 3;
        border: solid $accent;
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "add_server", "Add Server"),
        Binding("space", "toggle_server", "Enable/Disable"),
        Binding("d", "deploy", "Deploy"),
        Binding("h", "health_check", "Health Check"),
    ]
    
    def __init__(self):
        super().__init__()
        # Initialize core components
        self.registry = MCPServerRegistry()
        self.deployment_manager = DeploymentManager(self.registry)
        self.platform_manager = PlatformManager()
        self.project_detector = ProjectDetector()
        self.selected_server: Optional[str] = None
        
    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header()
        
        with Horizontal():
            # Left panel - Server Registry
            with Vertical(id="left-panel"):
                yield Static("📦 MCP Server Registry", classes="panel-title")
                yield DataTable(id="server-table")
                
                with Horizontal():
                    yield Button("Add", id="add-btn", classes="action-button")
                    yield Button("Edit", id="edit-btn", classes="action-button")
                    yield Button("Remove", id="remove-btn", classes="action-button")
            
            # Right panel - Deployment Status
            with Vertical(id="right-panel"):
                yield Static("🚀 Deployment Status", classes="panel-title")
                yield DataTable(id="deployment-table")
                
                with Horizontal():
                    yield Button("Deploy", id="deploy-btn", classes="action-button")
                    yield Button("Undeploy", id="undeploy-btn", classes="action-button")
                    yield Button("Health Check", id="health-btn", classes="action-button")
        
        # Status bar
        yield Static("Ready", id="status-bar")
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize data when app mounts."""
        try:
            # Initialize registry and load data
            self.registry.clear_cache()  # Ensure fresh data
            self.load_server_registry()
            self.load_deployment_status()
            
            # Set up event handlers for table selection
            server_table = self.query_one("#server-table", DataTable)
            server_table.cursor_type = "row"
            
            stats = self.registry.get_stats()
            self.update_status(f"MCP Manager initialized - {stats['total_servers']} servers registered")
        except Exception as e:
            self.update_status(f"Error initializing: {str(e)}")
    
    def load_server_registry(self) -> None:
        """Load servers into the registry table with real registry data."""
        table = self.query_one("#server-table", DataTable)
        table.clear()
        
        # Add columns if they don't exist
        if not table.columns:
            table.add_columns("Server Name", "Type", "Status", "Description")
        
        # Load servers from registry - use the correct API that returns ServerRegistryEntry objects
        try:
            servers = self.registry.list_servers()
            for server_name, server_entry in servers.items():
                status = "✅ Enabled" if server_entry.metadata.enabled else "❌ Disabled"
                description = server_entry.metadata.description or "No description"
                # Truncate long descriptions
                if len(description) > 30:
                    description = description[:27] + "..."
                table.add_row(server_name, server_entry.type, status, description)
                
            self.update_status(f"Loaded {len(servers)} servers from registry")
        except Exception as e:
            self.update_status(f"Error loading servers: {str(e)}")
    
    def load_deployment_status(self) -> None:
        """Load deployment status into the deployment table."""
        table = self.query_one("#deployment-table", DataTable)
        table.clear()
        
        # Add columns if they don't exist
        if not table.columns:
            table.add_columns("Server", "Desktop", "Code", "VS Code")
        
        # Get deployment status for each server
        try:
            servers = self.registry.list_servers()
            platforms = self.platform_manager.get_available_platforms()
            
            for server_name in servers.keys():
                row_data = [server_name]
                for platform_key in ["desktop", "code", "vscode"]:
                    if platform_key in platforms:
                        # Check if server is deployed to this platform
                        platform_config = platforms[platform_key]
                        if platform_config and platform_config.config_path.exists():
                            config = json.loads(platform_config.config_path.read_text())
                            deployed = server_name in config.get("mcpServers", {})
                            row_data.append("✅" if deployed else "❌")
                        else:
                            row_data.append("❌")
                    else:
                        row_data.append("-")
                table.add_row(*row_data)
        except Exception as e:
            self.update_status(f"Error loading deployment status: {str(e)}")
    
    def action_refresh(self) -> None:
        """Refresh all data."""
        try:
            # Clear registry cache to ensure fresh data
            self.registry.clear_cache()
            
            # Reload data
            self.load_server_registry()
            self.load_deployment_status()
            self.update_status("Data refreshed successfully")
        except Exception as e:
            self.update_status(f"Error refreshing data: {str(e)}")
    
    def action_add_server(self) -> None:
        """Add a new server."""
        self.update_status("Add server functionality - Use tui_enhanced.py for full CRUD operations")
    
    def action_toggle_server(self) -> None:
        """Toggle enable/disable status of selected server."""
        server_name = self.get_selected_server()
        if not server_name:
            self.update_status("❌ No server selected")
            return
            
        try:
            server = self.registry.get_server(server_name)
            if not server:
                self.update_status(f"❌ Server '{server_name}' not found")
                return
                
            # Toggle enabled status
            new_status = not server.metadata.enabled
            success = self.registry.enable_server(server_name) if new_status else self.registry.disable_server(server_name)
            
            if success:
                self.load_server_registry()  # Refresh the display
                status_text = "enabled" if new_status else "disabled"
                self.update_status(f"✅ Server '{server_name}' {status_text}")
            else:
                self.update_status(f"❌ Failed to toggle server '{server_name}'")
        except Exception as e:
            self.update_status(f"❌ Error toggling server: {str(e)}")
    
    def get_selected_server(self) -> Optional[str]:
        """Get the currently selected server name."""
        try:
            server_table = self.query_one("#server-table", DataTable)
            if server_table.cursor_row is not None and server_table.cursor_row >= 0:
                row = server_table.get_row_at(server_table.cursor_row)
                return str(row[0])  # Server name is in first column
        except Exception:
            pass
        return None
    
    def action_deploy(self) -> None:
        """Deploy selected servers."""
        self.update_status("Deploy functionality coming soon...")
    
    def action_health_check(self) -> None:
        """Run health check on servers."""
        self.update_status("Health check functionality coming soon...")
    
    def update_status(self, message: str) -> None:
        """Update the status bar."""
        status_bar = self.query_one("#status-bar", Static)
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_bar.update(f"[{timestamp}] {message}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "add-btn":
            self.action_add_server()
        elif button_id == "edit-btn":
            self.update_status("Edit functionality - Use tui_enhanced.py for full CRUD operations")
        elif button_id == "remove-btn":
            self.update_status("Remove functionality - Use tui_enhanced.py for full CRUD operations")
        elif button_id == "deploy-btn":
            self.action_deploy()
        elif button_id == "undeploy-btn":
            self.update_status("Undeploy functionality coming soon...")
        elif button_id == "health-btn":
            self.action_health_check()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle server table row selection."""
        if event.data_table.id == "server-table":
            row = event.data_table.get_row_at(event.row_index)
            self.selected_server = str(row[0])
            self.update_status(f"Selected server: {self.selected_server}")


def run_tui() -> int:
    """Launch the Textual TUI interface."""
    app = MCPManagerTUI()
    app.run()
    return 0


if __name__ == "__main__":
    run_tui()