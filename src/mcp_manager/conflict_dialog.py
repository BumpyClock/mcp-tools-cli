"""Conflict Resolution Dialog for Deployment Matrix."""

from typing import List, Optional, Callable
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static, Label, Markdown
from textual.message import Message
from rich.text import Text

from .deployment_matrix import DeploymentConflict


class ConflictResolutionDialog(ModalScreen[Optional[List[str]]]):
    """Modal dialog for resolving deployment conflicts."""
    
    CSS = """
    ConflictResolutionDialog {
        align: center middle;
    }
    
    #dialog {
        width: 80%;
        height: 70%;
        border: thick $background 80%;
        background: $surface;
        padding: 1;
    }
    
    #conflict-table {
        height: 1fr;
        margin: 1 0;
    }
    
    #buttons {
        dock: bottom;
        height: 3;
        text-align: center;
        margin: 1;
    }
    
    #title {
        dock: top;
        height: 3;
        text-align: center;
        margin-bottom: 1;
    }
    
    .conflict-critical {
        background: $error 30%;
    }
    
    .conflict-warning {
        background: $warning 30%;
    }
    
    .conflict-info {
        background: $info 30%;
    }
    """

    class ConflictResolved(Message):
        """Posted when a conflict resolution is applied."""
        def __init__(self, conflict: DeploymentConflict, resolution: str) -> None:
            self.conflict = conflict
            self.resolution = resolution
            super().__init__()

    def __init__(
        self,
        conflicts: List[DeploymentConflict],
        resolution_callback: Optional[Callable[[DeploymentConflict, str], None]] = None
    ) -> None:
        super().__init__()
        self.conflicts = conflicts
        self.resolution_callback = resolution_callback
        self.selected_conflicts: List[DeploymentConflict] = []
        
    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Vertical(id="dialog"):
            yield Static(
                "🔧 Deployment Conflict Resolution",
                id="title",
                classes="dialog-title"
            )
            
            yield Label(
                f"Found {len(self.conflicts)} conflicts requiring attention:",
                classes="dialog-subtitle"
            )
            
            # Conflict details table
            with ScrollableContainer():
                yield DataTable(
                    id="conflict-table",
                    zebra_stripes=True,
                    cursor_type="row"
                )
            
            # Resolution actions
            with Horizontal(id="buttons"):
                yield Button("Auto-Resolve Safe", id="auto-resolve", variant="success")
                yield Button("Manual Review", id="manual-resolve", variant="primary")
                yield Button("Ignore Warnings", id="ignore-warnings", variant="warning")
                yield Button("Cancel", id="cancel", variant="error")
    
    def on_mount(self) -> None:
        """Initialize the dialog when mounted."""
        self._populate_conflict_table()
        
    def _populate_conflict_table(self) -> None:
        """Populate the conflict table with conflict data."""
        table = self.query_one("#conflict-table", DataTable)
        table.clear()
        
        if not table.columns:
            table.add_columns(
                "Severity", "Server", "Platform", "Type", "Description", "Resolution"
            )
        
        for conflict in self.conflicts:
            # Create styled severity indicator
            severity_text = Text(conflict.severity.upper())
            if conflict.severity == "error":
                severity_text.stylize("bold red")
            elif conflict.severity == "warning":
                severity_text.stylize("bold yellow")
            else:
                severity_text.stylize("bold blue")
            
            # Create conflict type with icon
            type_icons = {
                "version_mismatch": "🔄",
                "port_conflict": "🔌",
                "missing_dependency": "📦",
                "configuration_error": "⚙️",
                "resource_conflict": "💾"
            }
            type_icon = type_icons.get(conflict.conflict_type, "⚠️")
            type_text = f"{type_icon} {conflict.conflict_type.replace('_', ' ').title()}"
            
            # Add row with conflict data
            table.add_row(
                severity_text,
                conflict.server_name,
                conflict.platform_key,
                type_text,
                conflict.description,
                conflict.suggested_resolution,
                key=f"{conflict.server_name}:{conflict.platform_key}:{conflict.conflict_type}"
            )
    
    @on(Button.Pressed, "#auto-resolve")
    def auto_resolve_conflicts(self) -> None:
        """Auto-resolve conflicts that can be safely resolved."""
        safe_resolutions = []
        
        for conflict in self.conflicts:
            if self._can_auto_resolve(conflict):
                safe_resolutions.append(conflict.conflict_type)
                if self.resolution_callback:
                    self.resolution_callback(conflict, "auto_resolve")
                self.post_message(self.ConflictResolved(conflict, "auto_resolve"))
        
        if safe_resolutions:
            self.dismiss(safe_resolutions)
        else:
            self._show_no_safe_resolutions()
    
    @on(Button.Pressed, "#manual-resolve")  
    def manual_resolve_conflicts(self) -> None:
        """Open manual resolution interface."""
        # For now, just show selected conflicts
        table = self.query_one("#conflict-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_key_at(table.cursor_row)
            if row_key:
                # Find the corresponding conflict
                conflict = self._find_conflict_by_key(str(row_key))
                if conflict:
                    self._show_manual_resolution_options(conflict)
    
    @on(Button.Pressed, "#ignore-warnings")
    def ignore_warnings(self) -> None:
        """Ignore all warning-level conflicts."""
        ignored_warnings = []
        
        for conflict in self.conflicts:
            if conflict.severity == "warning":
                ignored_warnings.append(conflict.conflict_type)
                if self.resolution_callback:
                    self.resolution_callback(conflict, "ignore")
                self.post_message(self.ConflictResolved(conflict, "ignore"))
        
        if ignored_warnings:
            self.dismiss(ignored_warnings)
        else:
            self._show_no_warnings_to_ignore()
    
    @on(Button.Pressed, "#cancel")
    def cancel_resolution(self) -> None:
        """Cancel conflict resolution."""
        self.dismiss(None)
    
    def _can_auto_resolve(self, conflict: DeploymentConflict) -> bool:
        """Check if a conflict can be safely auto-resolved."""
        auto_resolvable_types = {
            "missing_dependency": conflict.severity != "error",
            "version_mismatch": conflict.severity == "warning",
            "configuration_error": False,  # Always requires manual attention
            "port_conflict": False,  # Always requires manual attention
            "resource_conflict": conflict.severity == "warning"
        }
        
        return auto_resolvable_types.get(conflict.conflict_type, False)
    
    def _find_conflict_by_key(self, key: str) -> Optional[DeploymentConflict]:
        """Find a conflict by its table row key."""
        parts = key.split(":")
        if len(parts) >= 3:
            server_name, platform_key, conflict_type = parts[0], parts[1], parts[2]
            for conflict in self.conflicts:
                if (conflict.server_name == server_name and 
                    conflict.platform_key == platform_key and
                    conflict.conflict_type == conflict_type):
                    return conflict
        return None
    
    def _show_manual_resolution_options(self, conflict: DeploymentConflict) -> None:
        """Show manual resolution options for a specific conflict."""
        # For now, just apply the suggested resolution
        if self.resolution_callback:
            self.resolution_callback(conflict, "manual_resolve")
        self.post_message(self.ConflictResolved(conflict, "manual_resolve"))
        
        # Close dialog with resolution applied
        self.dismiss([conflict.conflict_type])
    
    def _show_no_safe_resolutions(self) -> None:
        """Show message when no conflicts can be safely auto-resolved."""
        title_widget = self.query_one("#title", Static)
        title_widget.update("❌ No conflicts can be safely auto-resolved")
    
    def _show_no_warnings_to_ignore(self) -> None:
        """Show message when there are no warnings to ignore."""
        title_widget = self.query_one("#title", Static)
        title_widget.update("ℹ️ No warning-level conflicts found")


class CellInfoDialog(ModalScreen[None]):
    """Modal dialog showing detailed cell information."""
    
    CSS = """
    CellInfoDialog {
        align: center middle;
    }
    
    #info-dialog {
        width: 60%;
        height: 50%;
        border: thick $background 80%;
        background: $surface;
        padding: 1;
    }
    
    #info-content {
        height: 1fr;
        margin: 1 0;
    }
    
    #info-buttons {
        dock: bottom;
        height: 3;
        text-align: center;
    }
    """
    
    def __init__(
        self,
        server_name: str,
        platform_key: str,
        state_description: str,
        conflicts: List[DeploymentConflict],
        deployment_info: dict = None
    ) -> None:
        super().__init__()
        self.server_name = server_name
        self.platform_key = platform_key
        self.state_description = state_description
        self.conflicts = conflicts
        self.deployment_info = deployment_info or {}
        
    def compose(self) -> ComposeResult:
        """Compose the info dialog."""
        with Vertical(id="info-dialog"):
            yield Static(
                f"📊 Deployment Info: {self.server_name} → {self.platform_key}",
                classes="dialog-title"
            )
            
            with ScrollableContainer(id="info-content"):
                info_md = self._generate_info_markdown()
                yield Markdown(info_md)
            
            with Horizontal(id="info-buttons"):
                yield Button("Close", id="close", variant="primary")
    
    def _generate_info_markdown(self) -> str:
        """Generate markdown content for the cell info."""
        md_lines = [
            f"## {self.server_name} → {self.platform_key}",
            "",
            f"**Current State:** {self.state_description}",
            "",
        ]
        
        # Add deployment info if available
        if self.deployment_info:
            md_lines.extend([
                "### Deployment Details",
                "",
            ])
            for key, value in self.deployment_info.items():
                md_lines.append(f"- **{key.title()}:** {value}")
            md_lines.append("")
        
        # Add conflict information
        if self.conflicts:
            md_lines.extend([
                f"### Conflicts ({len(self.conflicts)})",
                "",
            ])
            for i, conflict in enumerate(self.conflicts, 1):
                severity_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(conflict.severity, "⚪")
                md_lines.extend([
                    f"#### {i}. {severity_icon} {conflict.conflict_type.replace('_', ' ').title()}",
                    f"**Severity:** {conflict.severity.upper()}",
                    f"**Description:** {conflict.description}",
                    f"**Resolution:** {conflict.suggested_resolution}",
                    "",
                ])
        else:
            md_lines.extend([
                "### Conflicts",
                "",
                "✅ No conflicts detected",
                "",
            ])
        
        return "\n".join(md_lines)
    
    @on(Button.Pressed, "#close")
    def close_dialog(self) -> None:
        """Close the info dialog."""
        self.dismiss()