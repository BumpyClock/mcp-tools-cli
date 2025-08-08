"""MCP Manager TUI Application - Enhanced with Registry Integration."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    Header, Footer, DataTable, Static, Button, 
    Input, TextArea, Label
)
from textual.screen import ModalScreen
from textual.binding import Binding
from pathlib import Path
import json
from datetime import datetime
from typing import Optional, Dict, Any

from mcp_manager.core import MCPServerRegistry, DeploymentManager, PlatformManager, ProjectDetector


class AddServerScreen(ModalScreen):
    """Modal screen for adding a new MCP server."""
    
    DEFAULT_CSS = """
    AddServerScreen {
        align: center middle;
    }
    
    #add-server-dialog {
        width: 80;
        height: 30;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    .input-field {
        margin: 1 0;
    }
    
    #dialog-buttons {
        height: 3;
        dock: bottom;
        margin: 1 0;
    }
    
    .dialog-button {
        margin: 0 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        """Compose the add server dialog."""
        with Container(id="add-server-dialog"):
            yield Label("Add New MCP Server", classes="dialog-title")
            
            yield Label("Server Name:")
            yield Input(placeholder="Enter server name", id="server-name", classes="input-field")
            
            yield Label("Server Type:")
            yield Input(placeholder="stdio, http, or docker", id="server-type", classes="input-field")
            
            yield Label("Command (for stdio):")
            yield Input(placeholder="path/to/executable", id="server-command", classes="input-field")
            
            yield Label("Args (comma-separated):")
            yield Input(placeholder="arg1, arg2, arg3", id="server-args", classes="input-field")
            
            yield Label("URL (for http):")
            yield Input(placeholder="http://localhost:3000", id="server-url", classes="input-field")
            
            yield Label("Description:")
            yield TextArea(placeholder="Optional description", id="server-description", classes="input-field")
            
            with Horizontal(id="dialog-buttons"):
                yield Button("Add", id="add-confirm-btn", classes="dialog-button", variant="success")
                yield Button("Cancel", id="add-cancel-btn", classes="dialog-button")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the dialog."""
        if event.button.id == "add-confirm-btn":
            # Collect input values
            name = self.query_one("#server-name", Input).value.strip()
            server_type = self.query_one("#server-type", Input).value.strip().lower()
            command = self.query_one("#server-command", Input).value.strip()
            args_str = self.query_one("#server-args", Input).value.strip()
            url = self.query_one("#server-url", Input).value.strip()
            description = self.query_one("#server-description", TextArea).text.strip()
            
            # Validate inputs
            if not name:
                return  # Could add validation feedback
            
            if server_type not in ["stdio", "http", "docker"]:
                server_type = "stdio"  # Default fallback
            
            # Build server config
            config = {"type": server_type}
            
            if server_type == "stdio" and command:
                config["command"] = command
                if args_str:
                    config["args"] = [arg.strip() for arg in args_str.split(",") if arg.strip()]
            elif server_type == "http" and url:
                config["url"] = url
            
            # Build metadata
            metadata = {}
            if description:
                metadata["description"] = description
            
            self.dismiss({"name": name, "config": config, "metadata": metadata})
        
        elif event.button.id == "add-cancel-btn":
            self.dismiss(None)


class EditServerScreen(ModalScreen):
    """Modal screen for editing an existing MCP server."""
    
    DEFAULT_CSS = AddServerScreen.DEFAULT_CSS
    
    def __init__(self, server_name: str, server_entry):
        super().__init__()
        self.server_name = server_name
        self.server_entry = server_entry
    
    def compose(self) -> ComposeResult:
        """Compose the edit server dialog."""
        with Container(id="add-server-dialog"):
            yield Label(f"Edit Server: {self.server_name}", classes="dialog-title")
            
            yield Label("Server Name:")
            yield Input(value=self.server_name, id="server-name", classes="input-field")
            
            yield Label("Server Type:")
            yield Input(value=self.server_entry.type, id="server-type", classes="input-field")
            
            yield Label("Command (for stdio):")
            yield Input(
                value=self.server_entry.command or "", 
                placeholder="path/to/executable", 
                id="server-command", 
                classes="input-field"
            )
            
            yield Label("Args (comma-separated):")
            args_str = ", ".join(self.server_entry.args or [])
            yield Input(
                value=args_str, 
                placeholder="arg1, arg2, arg3", 
                id="server-args", 
                classes="input-field"
            )
            
            yield Label("URL (for http):")
            yield Input(
                value=self.server_entry.url or "", 
                placeholder="http://localhost:3000", 
                id="server-url", 
                classes="input-field"
            )
            
            yield Label("Description:")
            yield TextArea(
                text=self.server_entry.metadata.description or "", 
                placeholder="Optional description", 
                id="server-description", 
                classes="input-field"
            )
            
            with Horizontal(id="dialog-buttons"):
                yield Button("Update", id="edit-confirm-btn", classes="dialog-button", variant="success")
                yield Button("Cancel", id="edit-cancel-btn", classes="dialog-button")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the dialog."""
        if event.button.id == "edit-confirm-btn":
            # Collect input values
            name = self.query_one("#server-name", Input).value.strip()
            server_type = self.query_one("#server-type", Input).value.strip().lower()
            command = self.query_one("#server-command", Input).value.strip()
            args_str = self.query_one("#server-args", Input).value.strip()
            url = self.query_one("#server-url", Input).value.strip()
            description = self.query_one("#server-description", TextArea).text.strip()
            
            # Build server config
            config = {"type": server_type}
            
            if server_type == "stdio" and command:
                config["command"] = command
                if args_str:
                    config["args"] = [arg.strip() for arg in args_str.split(",") if arg.strip()]
            elif server_type == "http" and url:
                config["url"] = url
            
            # Build metadata
            metadata = {}
            if description:
                metadata["description"] = description
            
            self.dismiss({"name": name, "config": config, "metadata": metadata})
        
        elif event.button.id == "edit-cancel-btn":
            self.dismiss(None)


class ConfirmScreen(ModalScreen):
    """Modal screen for confirmation dialogs."""
    
    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    
    #confirm-dialog {
        width: 60;
        height: 15;
        border: solid $warning;
        background: $surface;
        padding: 1;
    }
    
    #dialog-buttons {
        height: 3;
        dock: bottom;
        margin: 1 0;
    }
    
    .dialog-button {
        margin: 0 1;
    }
    
    #message-container {
        height: auto;
        padding: 1;
        margin: 1 0;
    }
    """
    
    def __init__(self, message: str, title: str = "Confirm"):
        super().__init__()
        self.message = message
        self.title = title
    
    def compose(self) -> ComposeResult:
        """Compose the confirm dialog."""
        with Container(id="confirm-dialog"):
            yield Label(self.title, classes="dialog-title")
            
            with Container(id="message-container"):
                yield Static(self.message)
            
            with Horizontal(id="dialog-buttons"):
                yield Button("Yes", id="confirm-yes-btn", classes="dialog-button", variant="warning")
                yield Button("No", id="confirm-no-btn", classes="dialog-button")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses in the dialog."""
        if event.button.id == "confirm-yes-btn":
            self.dismiss(True)
        elif event.button.id == "confirm-no-btn":
            self.dismiss(False)


class MCPManagerEnhanced(App):
    """Enhanced MCP Manager TUI with full Registry Integration."""
    
    TITLE = "MCP Manager - Registry Integrated"
    
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
        Binding("e", "edit_server", "Edit Server"),
        Binding("delete", "remove_server", "Remove Server"),
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
                    yield Button("Health Check", id="health-btn", classes="action-button")
        
        # Status bar
        yield Static("Ready", id="status-bar")
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize data when app mounts."""
        try:
            # Initialize registry and load data
            self.registry.clear_cache()  # Ensure fresh data
            self.refresh_server_list()
            self.load_deployment_status()
            
            # Set up event handlers for table selection
            server_table = self.query_one("#server-table", DataTable)
            server_table.cursor_type = "row"
            
            stats = self.registry.get_stats()
            self.update_status(f"MCP Manager initialized - {stats['total_servers']} servers registered")
        except Exception as e:
            self.update_status(f"Error initializing: {str(e)}")
    
    def refresh_server_list(self) -> None:
        """Refresh the server registry table with real data from registry."""
        table = self.query_one("#server-table", DataTable)
        table.clear()
        
        # Add columns if they don't exist
        if not table.columns:
            table.add_columns("Server Name", "Type", "Status", "Description")
        
        # Load servers from registry
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
            self.refresh_server_list()
            self.load_deployment_status()
            self.update_status("Data refreshed successfully")
        except Exception as e:
            self.update_status(f"Error refreshing data: {str(e)}")
    
    def action_add_server(self) -> None:
        """Add a new server."""
        self.push_screen(AddServerScreen(), self.on_add_server_complete)
    
    def on_add_server_complete(self, result: Optional[Dict[str, Any]]) -> None:
        """Handle add server completion."""
        if result:
            try:
                success = self.registry.add_server(
                    result["name"],
                    result["config"],
                    result.get("metadata")
                )
                if success:
                    self.refresh_server_list()
                    self.load_deployment_status()
                    self.update_status(f"✅ Added server '{result['name']}' successfully")
                else:
                    self.update_status(f"❌ Failed to add server '{result['name']}'")
            except Exception as e:
                self.update_status(f"❌ Error adding server: {str(e)}")
    
    def action_edit_server(self) -> None:
        """Edit the selected server."""
        server_name = self.get_selected_server()
        if not server_name:
            self.update_status("❌ No server selected")
            return
            
        server = self.registry.get_server(server_name)
        if not server:
            self.update_status(f"❌ Server '{server_name}' not found")
            return
            
        self.push_screen(EditServerScreen(server_name, server), self.on_edit_server_complete)
    
    def on_edit_server_complete(self, result: Optional[Dict[str, Any]]) -> None:
        """Handle edit server completion."""
        if result:
            try:
                success = self.registry.update_server(
                    result["name"],
                    result.get("config"),
                    result.get("metadata")
                )
                if success:
                    self.refresh_server_list()
                    self.load_deployment_status()
                    self.update_status(f"✅ Updated server '{result['name']}' successfully")
                else:
                    self.update_status(f"❌ Failed to update server '{result['name']}'")
            except Exception as e:
                self.update_status(f"❌ Error updating server: {str(e)}")
    
    def action_remove_server(self) -> None:
        """Remove the selected server."""
        server_name = self.get_selected_server()
        if not server_name:
            self.update_status("❌ No server selected")
            return
            
        self.push_screen(ConfirmScreen(
            f"Are you sure you want to remove server '{server_name}'?\\n\\nThis action cannot be undone.",
            "Remove Server"
        ), lambda confirmed: self.on_remove_server_confirmed(confirmed, server_name))
    
    def on_remove_server_confirmed(self, confirmed: bool, server_name: str) -> None:
        """Handle server removal confirmation."""
        if confirmed:
            try:
                success = self.registry.remove_server(server_name)
                if success:
                    self.refresh_server_list()
                    self.load_deployment_status()  # Update deployment status too
                    self.update_status(f"✅ Removed server '{server_name}' successfully")
                else:
                    self.update_status(f"❌ Failed to remove server '{server_name}'")
            except Exception as e:
                self.update_status(f"❌ Error removing server: {str(e)}")
    
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
                self.refresh_server_list()
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
            self.action_edit_server()
        elif button_id == "remove-btn":
            self.action_remove_server()
        elif button_id == "deploy-btn":
            self.action_deploy()
        elif button_id == "health-btn":
            self.action_health_check()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle server table row selection."""
        if event.data_table.id == "server-table":
            row = event.data_table.get_row_at(event.row_index)
            self.selected_server = str(row[0])
            self.update_status(f"Selected server: {self.selected_server}")


def run_enhanced_tui() -> int:
    """Launch the Enhanced Textual TUI interface."""
    app = MCPManagerEnhanced()
    app.run()
    return 0


if __name__ == "__main__":
    run_enhanced_tui()