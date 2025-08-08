"""Enhanced Interactive Deployment Matrix with Conflict Detection."""

from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

from textual.widgets import DataTable
from textual.message import Message
from textual.coordinate import Coordinate
from textual import events
from textual.binding import Binding
from textual.reactive import reactive
from rich.text import Text
from rich.console import RenderableType

from .core import MCPServerRegistry, DeploymentManager, PlatformManager


class DeploymentState(Enum):
    """Deployment states with visual indicators."""
    NOT_DEPLOYED = ("❌", "red", "Not Deployed")
    DEPLOYED = ("✅", "green", "Deployed")
    PENDING = ("⏳", "yellow", "Deployment Pending")
    ERROR = ("⚠️", "red", "Deployment Error")
    CONFLICT = ("🔄", "orange3", "Configuration Conflict")
    INCOMPATIBLE = ("🚫", "magenta", "Version Incompatible")

    def __init__(self, icon: str, color: str, description: str):
        self.icon = icon
        self.color = color
        self.description = description


@dataclass
class DeploymentConflict:
    """Represents a deployment conflict."""
    server_name: str
    platform_key: str
    conflict_type: str
    description: str
    severity: str  # "warning", "error", "critical"
    suggested_resolution: str


@dataclass
class CellState:
    """State of a deployment matrix cell."""
    server_name: str
    platform_key: str
    state: DeploymentState
    conflicts: List[DeploymentConflict]
    is_selected: bool = False
    deployment_info: Optional[Dict[str, Any]] = None


class InteractiveDeploymentMatrix(DataTable):
    """Enhanced interactive deployment matrix with conflict detection."""
    
    # Reactive attributes
    selected_cells: reactive[Set[Coordinate]] = reactive(set(), init=False)
    multi_select_mode: reactive[bool] = reactive(False, init=False)
    show_conflicts: reactive[bool] = reactive(True, init=False)
    
    # Key bindings for matrix interaction
    BINDINGS = [
        Binding("enter", "toggle_cell", "Toggle Deployment", show=False),
        Binding("space", "select_cell", "Select Cell", show=False),
        Binding("ctrl+a", "select_all", "Select All", show=False),
        Binding("escape", "clear_selection", "Clear Selection", show=False),
        Binding("shift+enter", "batch_toggle", "Batch Toggle", show=False),
        Binding("c", "check_conflicts", "Check Conflicts", show=False),
        Binding("r", "resolve_conflicts", "Resolve Conflicts", show=False),
        Binding("i", "show_cell_info", "Cell Info", show=False),
    ]

    class CellToggled(Message):
        """Posted when a cell's deployment status is toggled."""
        def __init__(self, server_name: str, platform_key: str, new_state: DeploymentState) -> None:
            self.server_name = server_name
            self.platform_key = platform_key
            self.new_state = new_state
            super().__init__()

    class ConflictDetected(Message):
        """Posted when conflicts are detected."""
        def __init__(self, conflicts: List[DeploymentConflict]) -> None:
            self.conflicts = conflicts
            super().__init__()

    class BatchOperation(Message):
        """Posted when batch operations are requested."""
        def __init__(self, operation: str, cells: Set[Coordinate]) -> None:
            self.operation = operation
            self.cells = cells
            super().__init__()

    def __init__(
        self,
        registry: MCPServerRegistry,
        deployment_manager: DeploymentManager,
        platform_manager: PlatformManager,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.registry = registry
        self.deployment_manager = deployment_manager
        self.platform_manager = platform_manager
        
        # Internal state tracking
        self._cell_states: Dict[Tuple[str, str], CellState] = {}
        self._server_names: List[str] = []
        self._platform_keys: List[str] = []
        self._conflicts: List[DeploymentConflict] = []
        
        # Configuration
        self.cursor_type = "cell"  # Enable cell-level cursor
        self.zebra_stripes = True  # Improve readability

    def on_mount(self) -> None:
        """Initialize the matrix when mounted."""
        self.refresh_matrix()
        self.detect_conflicts()

    def refresh_matrix(self) -> None:
        """Refresh the entire deployment matrix."""
        self.clear()
        self._load_data()
        self._populate_table()
        self._update_visual_state()

    def _load_data(self) -> None:
        """Load servers and platforms data."""
        # Get all servers
        servers = self.registry.list_servers()
        self._server_names = list(servers.keys())
        
        # Get available platforms
        platforms = self.platform_manager.get_available_platforms()
        self._platform_keys = [key for key, info in platforms.items() if info["available"]]
        
        # Initialize cell states
        self._cell_states = {}
        for server_name in self._server_names:
            for platform_key in self._platform_keys:
                state = self._determine_deployment_state(server_name, platform_key)
                self._cell_states[(server_name, platform_key)] = CellState(
                    server_name=server_name,
                    platform_key=platform_key,
                    state=state,
                    conflicts=[]
                )

    def _populate_table(self) -> None:
        """Populate the table with data."""
        if not self.columns:
            # Add columns with platform names
            columns = ["Server"] + [self._format_platform_name(key) for key in self._platform_keys]
            self.add_columns(*columns)
        
        # Add rows for each server
        for server_name in self._server_names:
            row_data = [Text(server_name, style="bold")]
            for platform_key in self._platform_keys:
                cell_state = self._cell_states[(server_name, platform_key)]
                cell_renderable = self._create_cell_renderable(cell_state)
                row_data.append(cell_renderable)
            self.add_row(*row_data, key=server_name)

    def _determine_deployment_state(self, server_name: str, platform_key: str) -> DeploymentState:
        """Determine the current deployment state for a server-platform combination."""
        try:
            platforms = self.platform_manager.get_available_platforms()
            platform_info = platforms.get(platform_key)
            
            if not platform_info or not platform_info.config_path.exists():
                return DeploymentState.NOT_DEPLOYED
                
            # Load platform configuration
            try:
                config = json.loads(platform_info.config_path.read_text())
                mcp_servers = config.get("mcpServers", {})
                
                if server_name in mcp_servers:
                    # Check for conflicts or issues
                    server_config = mcp_servers[server_name]
                    if self._has_configuration_issues(server_config):
                        return DeploymentState.ERROR
                    return DeploymentState.DEPLOYED
                else:
                    return DeploymentState.NOT_DEPLOYED
                    
            except json.JSONDecodeError:
                return DeploymentState.ERROR
                
        except Exception:
            return DeploymentState.ERROR

    def _has_configuration_issues(self, server_config: Dict[str, Any]) -> bool:
        """Check if server configuration has issues."""
        # Basic validation - extend as needed
        required_fields = ["command"]
        return not all(field in server_config for field in required_fields)

    def _create_cell_renderable(self, cell_state: CellState) -> RenderableType:
        """Create a renderable for a cell based on its state."""
        state = cell_state.state
        icon = state.icon
        
        # Add conflict indicator if conflicts exist
        if cell_state.conflicts:
            icon += "⚠️"
        
        # Add selection indicator
        if cell_state.is_selected:
            icon = f"[reverse]{icon}[/reverse]"
            
        # Create colored text
        text = Text(icon, style=state.color)
        
        # Add tooltip-like information in style
        if cell_state.conflicts:
            text.stylize("underline")
            
        return text

    def _format_platform_name(self, platform_key: str) -> str:
        """Format platform key for display."""
        return platform_key.replace("_", " ").title()

    def detect_conflicts(self) -> None:
        """Detect deployment conflicts across the matrix."""
        conflicts = []
        
        # Check for version conflicts
        conflicts.extend(self._detect_version_conflicts())
        
        # Check for resource conflicts  
        conflicts.extend(self._detect_resource_conflicts())
        
        # Check for dependency conflicts
        conflicts.extend(self._detect_dependency_conflicts())
        
        # Update cell states with conflicts
        self._apply_conflicts_to_cells(conflicts)
        
        # Store conflicts
        self._conflicts = conflicts
        
        # Post message if conflicts found
        if conflicts:
            self.post_message(self.ConflictDetected(conflicts))

    def _detect_version_conflicts(self) -> List[DeploymentConflict]:
        """Detect version conflicts between deployments."""
        conflicts = []
        
        # Group deployments by server
        server_deployments: Dict[str, List[Tuple[str, Dict]]] = {}
        
        for (server_name, platform_key), cell_state in self._cell_states.items():
            if cell_state.state == DeploymentState.DEPLOYED:
                if server_name not in server_deployments:
                    server_deployments[server_name] = []
                    
                # Get deployment info (mock for now)
                deployment_info = {"version": "1.0.0"}  # Would be loaded from actual config
                server_deployments[server_name].append((platform_key, deployment_info))
        
        # Check for version mismatches
        for server_name, deployments in server_deployments.items():
            if len(deployments) > 1:
                versions = {dep[1].get("version") for dep in deployments}
                if len(versions) > 1:
                    for platform_key, deployment_info in deployments:
                        conflicts.append(DeploymentConflict(
                            server_name=server_name,
                            platform_key=platform_key,
                            conflict_type="version_mismatch",
                            description=f"Version mismatch: {versions}",
                            severity="warning",
                            suggested_resolution="Standardize version across platforms"
                        ))
        
        return conflicts

    def _detect_resource_conflicts(self) -> List[DeploymentConflict]:
        """Detect resource conflicts (ports, files, etc.)."""
        conflicts = []
        
        # Track used ports
        used_ports: Dict[int, List[Tuple[str, str]]] = {}
        
        for (server_name, platform_key), cell_state in self._cell_states.items():
            if cell_state.state == DeploymentState.DEPLOYED:
                # Mock port detection - would parse actual config
                server = self.registry.get_server(server_name)
                if server and hasattr(server, 'port'):
                    port = getattr(server, 'port', None)
                    if port:
                        if port not in used_ports:
                            used_ports[port] = []
                        used_ports[port].append((server_name, platform_key))
        
        # Check for port conflicts
        for port, users in used_ports.items():
            if len(users) > 1:
                for server_name, platform_key in users:
                    conflicts.append(DeploymentConflict(
                        server_name=server_name,
                        platform_key=platform_key,
                        conflict_type="port_conflict",
                        description=f"Port {port} used by multiple servers",
                        severity="error",
                        suggested_resolution="Assign unique ports to each server"
                    ))
        
        return conflicts

    def _detect_dependency_conflicts(self) -> List[DeploymentConflict]:
        """Detect dependency conflicts."""
        conflicts = []
        
        # Check for missing dependencies
        for (server_name, platform_key), cell_state in self._cell_states.items():
            if cell_state.state == DeploymentState.DEPLOYED:
                server = self.registry.get_server(server_name)
                if server:
                    # Mock dependency check
                    dependencies = getattr(server, 'dependencies', [])
                    for dep in dependencies:
                        if not self._is_dependency_available(dep, platform_key):
                            conflicts.append(DeploymentConflict(
                                server_name=server_name,
                                platform_key=platform_key,
                                conflict_type="missing_dependency",
                                description=f"Missing dependency: {dep}",
                                severity="error",
                                suggested_resolution=f"Install {dep} on {platform_key}"
                            ))
        
        return conflicts

    def _is_dependency_available(self, dependency: str, platform_key: str) -> bool:
        """Check if a dependency is available on a platform."""
        # Mock implementation - would check actual system
        return True  # Assume available for now

    def _apply_conflicts_to_cells(self, conflicts: List[DeploymentConflict]) -> None:
        """Apply detected conflicts to cell states."""
        # Group conflicts by cell
        conflict_map: Dict[Tuple[str, str], List[DeploymentConflict]] = {}
        for conflict in conflicts:
            key = (conflict.server_name, conflict.platform_key)
            if key not in conflict_map:
                conflict_map[key] = []
            conflict_map[key].append(conflict)
        
        # Update cell states
        for (server_name, platform_key), cell_conflicts in conflict_map.items():
            if (server_name, platform_key) in self._cell_states:
                cell_state = self._cell_states[(server_name, platform_key)]
                cell_state.conflicts = cell_conflicts
                
                # Update state if there are critical conflicts
                if any(c.severity == "error" for c in cell_conflicts):
                    cell_state.state = DeploymentState.CONFLICT

    def _update_visual_state(self) -> None:
        """Update the visual appearance of the table."""
        for row_index, server_name in enumerate(self._server_names):
            for col_index, platform_key in enumerate(self._platform_keys):
                cell_state = self._cell_states[(server_name, platform_key)]
                cell_renderable = self._create_cell_renderable(cell_state)
                # Skip cell updates for now - just populate the table structure
                # TODO: Implement proper cell updating after table is populated

    # Event handlers
    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection for toggling deployment."""
        coordinate = event.coordinate
        if coordinate.column == 0:  # Skip server name column
            return
            
        server_name = self._server_names[coordinate.row]
        platform_key = self._platform_keys[coordinate.column - 1]
        
        # Toggle deployment state
        self._toggle_deployment(server_name, platform_key)

    def on_key(self, event: events.Key) -> None:
        """Handle keyboard navigation and commands."""
        if event.key == "enter":
            self.action_toggle_cell()
        elif event.key == "space":
            self.action_select_cell()
        elif event.key == "c":
            self.action_check_conflicts()
        elif event.key == "i":
            self.action_show_cell_info()

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """Handle cell highlighting for hover effects."""
        # Update status or show preview information
        coordinate = event.coordinate
        if coordinate.column > 0:
            server_name = self._server_names[coordinate.row]
            platform_key = self._platform_keys[coordinate.column - 1]
            cell_state = self._cell_states[(server_name, platform_key)]
            
            # Show tooltip-like information in status
            status = f"{server_name} → {platform_key}: {cell_state.state.description}"
            if cell_state.conflicts:
                status += f" ({len(cell_state.conflicts)} conflicts)"
            
            # This would be handled by the parent app to update status
            # self.app.update_status(status)

    # Actions
    def action_toggle_cell(self) -> None:
        """Toggle deployment for current cell."""
        coordinate = self.cursor_coordinate
        if coordinate.column == 0:
            return
            
        server_name = self._server_names[coordinate.row]
        platform_key = self._platform_keys[coordinate.column - 1]
        self._toggle_deployment(server_name, platform_key)

    def action_select_cell(self) -> None:
        """Toggle selection for current cell."""
        coordinate = self.cursor_coordinate
        if coordinate.column == 0:
            return
            
        if coordinate in self.selected_cells:
            new_selected = self.selected_cells.copy()
            new_selected.remove(coordinate)
            self.selected_cells = new_selected
        else:
            new_selected = self.selected_cells.copy()
            new_selected.add(coordinate)
            self.selected_cells = new_selected
        
        # Update visual state
        self._update_selection_display()

    def action_select_all(self) -> None:
        """Select all deployment cells."""
        all_cells = set()
        for row in range(len(self._server_names)):
            for col in range(1, len(self._platform_keys) + 1):  # Skip server name column
                all_cells.add(Coordinate(row, col))
        self.selected_cells = all_cells
        self._update_selection_display()

    def action_clear_selection(self) -> None:
        """Clear all selections."""
        self.selected_cells = set()
        self._update_selection_display()

    def action_batch_toggle(self) -> None:
        """Toggle deployment for all selected cells."""
        if not self.selected_cells:
            return
            
        self.post_message(self.BatchOperation("toggle", self.selected_cells))

    def action_check_conflicts(self) -> None:
        """Re-run conflict detection."""
        self.detect_conflicts()
        self._update_visual_state()

    def action_resolve_conflicts(self) -> None:
        """Show conflict resolution options."""
        if self._conflicts:
            # This would show a dialog or detailed view
            pass

    def action_show_cell_info(self) -> None:
        """Show detailed information about current cell."""
        coordinate = self.cursor_coordinate
        if coordinate.column == 0:
            return
            
        server_name = self._server_names[coordinate.row]
        platform_key = self._platform_keys[coordinate.column - 1]
        cell_state = self._cell_states[(server_name, platform_key)]
        
        # Post message to parent to show cell info dialog
        self.post_message(self.CellInfoRequested(
            server_name=server_name,
            platform_key=platform_key,
            state_description=cell_state.state.description,
            conflicts=cell_state.conflicts.copy(),
            deployment_info=cell_state.deployment_info or {}
        ))

    class CellInfoRequested(Message):
        """Posted when cell info is requested."""
        def __init__(
            self,
            server_name: str,
            platform_key: str,
            state_description: str,
            conflicts: List[DeploymentConflict],
            deployment_info: dict
        ) -> None:
            self.server_name = server_name
            self.platform_key = platform_key
            self.state_description = state_description
            self.conflicts = conflicts
            self.deployment_info = deployment_info
            super().__init__()

    def _toggle_deployment(self, server_name: str, platform_key: str) -> None:
        """Toggle deployment state for a specific server-platform combination."""
        cell_state = self._cell_states[(server_name, platform_key)]
        
        # Determine new state
        if cell_state.state == DeploymentState.DEPLOYED:
            new_state = DeploymentState.NOT_DEPLOYED
        elif cell_state.state == DeploymentState.NOT_DEPLOYED:
            new_state = DeploymentState.PENDING  # Would become DEPLOYED after operation
        else:
            new_state = DeploymentState.NOT_DEPLOYED  # Reset from error states
        
        # Update cell state
        cell_state.state = new_state
        
        # Post message for parent to handle actual deployment
        self.post_message(self.CellToggled(server_name, platform_key, new_state))
        
        # Update visual
        self._update_visual_state()

    def _update_selection_display(self) -> None:
        """Update visual display of selected cells."""
        # Update cell states with selection info
        for row in range(len(self._server_names)):
            for col in range(1, len(self._platform_keys) + 1):
                coordinate = Coordinate(row, col)
                server_name = self._server_names[row]
                platform_key = self._platform_keys[col - 1]
                cell_state = self._cell_states[(server_name, platform_key)]
                cell_state.is_selected = coordinate in self.selected_cells
        
        # Refresh visual state
        self._update_visual_state()

    def get_selected_deployments(self) -> List[Tuple[str, str]]:
        """Get list of selected server-platform combinations."""
        deployments = []
        for coordinate in self.selected_cells:
            if coordinate.column > 0:
                server_name = self._server_names[coordinate.row]
                platform_key = self._platform_keys[coordinate.column - 1]
                deployments.append((server_name, platform_key))
        return deployments

    def get_conflicts(self) -> List[DeploymentConflict]:
        """Get all detected conflicts."""
        return self._conflicts.copy()

    def get_cell_info(self, server_name: str, platform_key: str) -> Optional[CellState]:
        """Get detailed information about a specific cell."""
        return self._cell_states.get((server_name, platform_key))