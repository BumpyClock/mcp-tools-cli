"""Bidirectional status view widgets for MCP Manager TUI."""

from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static, Label
from textual.widget import Widget
import structlog

from .core import MCPServerRegistry, DeploymentManager, ProjectDetector

logger = structlog.get_logger()


class ProjectStatusView(DataTable):
    """Shows what MCP servers are installed in a selected project."""
    
    def __init__(self, deployment_manager: DeploymentManager, **kwargs):
        super().__init__(**kwargs)
        self.deployment_manager = deployment_manager
        self.project_detector = deployment_manager.project_detector
        self.current_project: Optional[Path] = None
        self.setup_columns()
    
    def setup_columns(self) -> None:
        """Initialize table columns."""
        self.add_columns("Server Name", "Type", "Status", "Health")
    
    def show_project_status(self, project_path: Path) -> None:
        """Display installed servers for the selected project."""
        self.current_project = project_path
        self.clear()
        
        try:
            # Get project
            project = self.project_detector.get_project_by_path(project_path)
            if not project:
                self.add_row("No project found", "-", "❌ Error", "-")
                return
            
            # Get installed servers
            installed_servers = project.get_servers()
            
            if not installed_servers:
                self.add_row("No servers installed", "-", "ℹ️ Empty", "-")
                return
            
            # Populate table with server information
            for server_name, server_config in installed_servers.items():
                server_type = server_config.get("command", "unknown")
                if isinstance(server_type, list) and server_type:
                    server_type = server_type[0]  # Take first command element
                
                # Check if server exists in registry
                registry_server = self.deployment_manager.registry.get_server(server_name)
                if registry_server:
                    status = "✅ Registry" if registry_server.metadata.enabled else "⚠️ Disabled"
                    health = "💚 Healthy" if registry_server.metadata.enabled else "🔶 Warning"
                else:
                    status = "🔷 Local Only"
                    health = "🔍 Unknown"
                
                self.add_row(server_name, server_type, status, health)
                
        except Exception as e:
            logger.error("Failed to show project status", project=project_path, error=str(e))
            self.add_row("Error loading project", str(e)[:30], "❌ Error", "-")
    
    def get_selected_server(self) -> Optional[str]:
        """Get the currently selected server name."""
        if self.cursor_row is None:
            return None
        
        try:
            row_data = self.get_row_at(self.cursor_row)
            return str(row_data[0]) if row_data[0] not in ["No servers installed", "No project found", "Error loading project"] else None
        except (IndexError, ValueError):
            return None


class ServerStatusView(Vertical):
    """Shows where a selected MCP server is deployed."""
    
    def __init__(self, deployment_manager: DeploymentManager, **kwargs):
        super().__init__(**kwargs)
        self.deployment_manager = deployment_manager
        self.current_server: Optional[str] = None
        self.status_table: Optional[DataTable] = None
    
    def compose(self):
        """Create the server status view layout."""
        yield Static("📍 Server Deployment Locations", classes="section-header")
        yield DataTable(id="server-deployment-table")
    
    def on_mount(self) -> None:
        """Initialize the view after mounting."""
        self.status_table = self.query_one("#server-deployment-table", DataTable)
        self.setup_table()
    
    def setup_table(self) -> None:
        """Initialize deployment table columns."""
        if self.status_table:
            self.status_table.add_columns("Deployment Target", "Type", "Status", "Last Updated")
    
    def show_server_deployments(self, server_name: str) -> None:
        """Display deployment locations for the selected server."""
        self.current_server = server_name
        
        if not self.status_table:
            return
        
        self.status_table.clear()
        
        try:
            # Get server deployment status
            deployment_status = self.deployment_manager.get_server_deployment_status(server_name)
            
            if not deployment_status:
                self.status_table.add_row("No deployments found", "-", "ℹ️ Not deployed", "-")
                return
            
            # Group by type for better organization
            platforms = []
            projects = []
            
            for target_key, is_deployed in deployment_status.items():
                if target_key.startswith("platform:"):
                    platform_name = target_key.split(":", 1)[1]
                    platforms.append((platform_name, is_deployed))
                elif target_key.startswith("project:"):
                    project_path = Path(target_key.split(":", 1)[1])
                    projects.append((project_path.name, is_deployed, project_path))
            
            # Add platform deployments
            for platform_name, is_deployed in platforms:
                status = "✅ Deployed" if is_deployed else "❌ Not deployed"
                icon = "🖥️" if platform_name == "desktop" else "💻" if platform_name == "code" else "🔧"
                self.status_table.add_row(
                    f"{icon} {platform_name.title()}", 
                    "Platform", 
                    status, 
                    "N/A"
                )
            
            # Add project deployments
            for project_name, is_deployed, project_path in projects:
                status = "✅ Deployed" if is_deployed else "❌ Not deployed"
                self.status_table.add_row(
                    f"📁 {project_name}", 
                    "Project", 
                    status, 
                    "N/A"
                )
            
            # If no deployments at all
            if not platforms and not projects:
                self.status_table.add_row("No deployment targets", "-", "ℹ️ Empty", "-")
                
        except Exception as e:
            logger.error("Failed to show server deployments", server=server_name, error=str(e))
            self.status_table.add_row("Error loading deployments", str(e)[:30], "❌ Error", "-")
    
    def get_selected_target(self) -> Optional[str]:
        """Get the currently selected deployment target."""
        if not self.status_table or self.status_table.cursor_row is None:
            return None
        
        try:
            row_data = self.status_table.get_row_at(self.status_table.cursor_row)
            target_name = str(row_data[0])
            if target_name.startswith("🖥️") or target_name.startswith("💻") or target_name.startswith("🔧"):
                # Platform target
                return f"platform:{target_name.split(' ', 1)[1].lower()}"
            elif target_name.startswith("📁"):
                # Project target (would need more context to get full path)
                return f"project:{target_name.split(' ', 1)[1]}"
            return None
        except (IndexError, ValueError):
            return None


class ViewModeManager:
    """Manages switching between different view modes."""
    
    def __init__(self):
        self.current_mode: str = "registry"  # "registry", "project_focus", "server_focus"
        self.view_history: List[str] = ["registry"]
        self.context: Dict[str, Any] = {}
    
    def switch_to_mode(self, mode: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Switch to a specific view mode with optional context."""
        previous_mode = self.current_mode
        
        if mode not in ["registry", "project_focus", "server_focus"]:
            logger.warning("Invalid view mode", mode=mode)
            return previous_mode
        
        self.current_mode = mode
        self.view_history.append(mode)
        
        if context:
            self.context.update(context)
        
        logger.info("Switched view mode", from_mode=previous_mode, to_mode=mode)
        return previous_mode
    
    def toggle_focus_mode(self) -> str:
        """Toggle between project-focus and server-focus modes."""
        if self.current_mode == "project_focus":
            return self.switch_to_mode("server_focus")
        elif self.current_mode == "server_focus":
            return self.switch_to_mode("project_focus")
        else:
            # If in registry mode, switch to project focus
            return self.switch_to_mode("project_focus")
    
    def go_back(self) -> str:
        """Go back to previous view mode."""
        if len(self.view_history) > 1:
            # Remove current mode and get previous
            self.view_history.pop()
            previous_mode = self.view_history[-1]
            self.current_mode = previous_mode
            return previous_mode
        return self.current_mode
    
    def get_mode_description(self) -> str:
        """Get human-readable description of current mode."""
        descriptions = {
            "registry": "📦 Registry View - Browse all servers and deployments",
            "project_focus": "📁 Project Focus - What servers are in this project?",
            "server_focus": "🚀 Server Focus - Where is this server deployed?"
        }
        return descriptions.get(self.current_mode, "Unknown mode")
    
    def get_context_info(self) -> str:
        """Get context information for the current view."""
        if self.current_mode == "project_focus" and "project_path" in self.context:
            project_name = Path(self.context["project_path"]).name
            return f"Project: {project_name}"
        elif self.current_mode == "server_focus" and "server_name" in self.context:
            return f"Server: {self.context['server_name']}"
        return ""