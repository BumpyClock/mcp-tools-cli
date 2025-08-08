"""Error dialog components for MCP Manager TUI."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Button, Static, Label, Markdown, DataTable, ProgressBar, RadioSet, RadioButton
from textual.screen import ModalScreen
from textual.binding import Binding
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from .exceptions import MCPManagerError, RecoveryAction, ErrorSeverity
from .error_handler import RecoveryResult, ErrorDiagnostics
from .rollback_manager import RollbackTransaction


class ErrorDialog(ModalScreen):
    """Modal dialog for displaying errors with recovery options."""
    
    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("enter", "confirm_action", "Confirm", priority=True),
        Binding("1", "select_action(0)", "Action 1", show=False),
        Binding("2", "select_action(1)", "Action 2", show=False),
        Binding("3", "select_action(2)", "Action 3", show=False),
        Binding("4", "select_action(3)", "Action 4", show=False),
        Binding("r", "retry", "Retry", show=False),
        Binding("s", "skip", "Skip", show=False),
        Binding("u", "rollback", "Rollback", show=False),
    ]
    
    CSS = """
    #error-dialog {
        width: 80%;
        height: 70%;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    .error-severity {
        text-style: bold;
        margin-right: 1;
    }
    
    .error-severity.critical {
        color: $error;
        text-style: bold blink;
    }
    
    .error-severity.error {
        color: $error;
    }
    
    .error-severity.warning {
        color: $warning;
    }
    
    .error-severity.info {
        color: $info;
    }
    
    .error-text {
        margin: 1 0;
        padding: 1;
        background: $surface-lighten-1;
    }
    
    .section {
        margin: 1 0;
        padding: 1;
        border: solid $secondary;
    }
    
    .section-header {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .context-item, .fix-item, .instruction-item, .resource-item {
        margin: 0 0 0 2;
    }
    
    .technical-text, .stack-trace {
        background: $surface-darken-1;
        padding: 1;
        color: $text-muted;
    }
    
    #action-buttons {
        justify: center;
        margin: 1;
    }
    
    #action-buttons Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, error: MCPManagerError, diagnostics: ErrorDiagnostics,
                 recovery_callback: Optional[Callable] = None):
        super().__init__()
        self.error = error
        self.diagnostics = diagnostics
        self.recovery_callback = recovery_callback
        self.selected_action: Optional[RecoveryAction] = None
    
    def compose(self) -> ComposeResult:
        """Create the error dialog layout."""
        severity_color = self.get_severity_color(self.error.severity)
        severity_icon = self.get_severity_icon(self.error.severity)
        
        with Vertical(id="error-dialog"):
            # Header with error severity and type
            with Horizontal(id="error-header"):
                yield Static(f"{severity_icon} {self.error.severity.value.upper()}", 
                           classes=f"error-severity {severity_color}")
                yield Static(self.error.__class__.__name__, classes="error-type")
                yield Static(f"[{self.diagnostics.error_code}]", classes="error-code")
            
            # Error message
            yield Static(self.error.user_message, id="error-message", classes="error-text")
            
            # Context information if available
            if self.error.context:
                with Vertical(id="error-context", classes="section"):
                    yield Static("📍 Context", classes="section-header")
                    
                    context_info = []
                    if self.error.context.operation:
                        context_info.append(f"Operation: {self.error.context.operation}")
                    if self.error.context.server_name:
                        context_info.append(f"Server: {self.error.context.server_name}")
                    if self.error.context.platform_key:
                        context_info.append(f"Platform: {self.error.context.platform_key}")
                    if self.error.context.project_path:
                        context_info.append(f"Project: {self.error.context.project_path}")
                    
                    for info in context_info:
                        yield Static(f"• {info}", classes="context-item")
            
            # Suggested fixes
            if self.diagnostics.suggested_fixes:
                with Vertical(id="suggested-fixes", classes="section"):
                    yield Static("💡 Suggested Fixes", classes="section-header")
                    
                    for i, fix in enumerate(self.diagnostics.suggested_fixes, 1):
                        yield Static(f"{i}. {fix}", classes="fix-item")
            
            # Recovery actions
            if self.error.suggested_actions:
                with Vertical(id="recovery-actions", classes="section"):
                    yield Static("🔄 Recovery Options", classes="section-header")
                    
                    with RadioSet(id="action-radio-set"):
                        for action in self.error.suggested_actions:
                            yield RadioButton(
                                self.get_action_description(action),
                                value=action.value,
                                name="recovery_action"
                            )
            
            # Action buttons
            with Horizontal(id="action-buttons"):
                if RecoveryAction.RETRY in self.error.suggested_actions:
                    yield Button("🔄 Retry", id="retry-btn", variant="primary")
                
                if RecoveryAction.ROLLBACK in self.error.suggested_actions:
                    yield Button("↩️ Rollback", id="rollback-btn", variant="warning")
                
                if RecoveryAction.SKIP in self.error.suggested_actions:
                    yield Button("⏭️ Skip", id="skip-btn", variant="default")
                
                if RecoveryAction.MANUAL_FIX in self.error.suggested_actions:
                    yield Button("🛠️ Manual Fix", id="manual-btn", variant="default")
                
                yield Button("❌ Close", id="close-btn", variant="error")
    
    def get_severity_color(self, severity: ErrorSeverity) -> str:
        """Get CSS class for severity color."""
        colors = {
            ErrorSeverity.INFO: "info",
            ErrorSeverity.WARNING: "warning", 
            ErrorSeverity.ERROR: "error",
            ErrorSeverity.CRITICAL: "critical"
        }
        return colors.get(severity, "error")
    
    def get_severity_icon(self, severity: ErrorSeverity) -> str:
        """Get icon for error severity."""
        icons = {
            ErrorSeverity.INFO: "ℹ️",
            ErrorSeverity.WARNING: "⚠️",
            ErrorSeverity.ERROR: "❌",
            ErrorSeverity.CRITICAL: "🚨"
        }
        return icons.get(severity, "❌")
    
    def get_action_description(self, action: RecoveryAction) -> str:
        """Get user-friendly description for recovery action."""
        descriptions = {
            RecoveryAction.RETRY: "Try the operation again",
            RecoveryAction.SKIP: "Skip this operation and continue",
            RecoveryAction.ROLLBACK: "Undo recent changes",
            RecoveryAction.MANUAL_FIX: "Fix the issue manually",
            RecoveryAction.IGNORE: "Ignore and continue",
            RecoveryAction.ABORT: "Cancel all operations"
        }
        return descriptions.get(action, action.value)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "retry-btn":
            self.selected_action = RecoveryAction.RETRY
            self.confirm_action()
        elif event.button.id == "rollback-btn":
            self.selected_action = RecoveryAction.ROLLBACK
            self.confirm_action()
        elif event.button.id == "skip-btn":
            self.selected_action = RecoveryAction.SKIP
            self.confirm_action()
        elif event.button.id == "manual-btn":
            self.selected_action = RecoveryAction.MANUAL_FIX
            self.show_manual_fix_dialog()
        elif event.button.id == "close-btn":
            self.action_close()
    
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio button selection."""
        if event.radio_set.id == "action-radio-set":
            self.selected_action = RecoveryAction(event.pressed.value)
    
    def action_close(self) -> None:
        """Close the dialog without action."""
        self.dismiss(None)
    
    def action_confirm_action(self) -> None:
        """Confirm the selected action."""
        if self.selected_action:
            self.confirm_action()
        else:
            self.action_close()
    
    def action_select_action(self, index: int) -> None:
        """Select action by number key."""
        if 0 <= index < len(self.error.suggested_actions):
            self.selected_action = self.error.suggested_actions[index]
            self.confirm_action()
    
    def action_retry(self) -> None:
        """Quick retry action."""
        if RecoveryAction.RETRY in self.error.suggested_actions:
            self.selected_action = RecoveryAction.RETRY
            self.confirm_action()
    
    def action_skip(self) -> None:
        """Quick skip action."""
        if RecoveryAction.SKIP in self.error.suggested_actions:
            self.selected_action = RecoveryAction.SKIP
            self.confirm_action()
    
    def action_rollback(self) -> None:
        """Quick rollback action."""
        if RecoveryAction.ROLLBACK in self.error.suggested_actions:
            self.selected_action = RecoveryAction.ROLLBACK
            self.confirm_action()
    
    def confirm_action(self) -> None:
        """Confirm and execute the selected action."""
        if self.selected_action and self.recovery_callback:
            self.recovery_callback(self.selected_action)
        self.dismiss(self.selected_action)
    
    def show_manual_fix_dialog(self) -> None:
        """Show detailed manual fix instructions."""
        self.app.push_screen(ManualFixDialog(self.error, self.diagnostics))


class RollbackConfirmationDialog(ModalScreen):
    """Dialog for confirming rollback operations."""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("enter", "confirm", "Confirm"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]
    
    CSS = """
    #rollback-dialog {
        width: 70%;
        height: 60%;
        border: solid $warning;
        background: $surface;
        padding: 1;
    }
    
    .dialog-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
        color: $accent;
    }
    
    .confirmation-text {
        text-align: center;
        margin: 1;
        color: $warning;
    }
    
    .warning-text {
        text-align: center;
        margin: 1;
        color: $error;
        text-style: bold;
    }
    """
    
    def __init__(self, transaction: RollbackTransaction, 
                 callback: Optional[Callable[[bool], None]] = None):
        super().__init__()
        self.transaction = transaction
        self.callback = callback
    
    def compose(self) -> ComposeResult:
        """Create the rollback confirmation dialog."""
        with Vertical(id="rollback-dialog"):
            yield Static("↩️ Confirm Rollback", classes="dialog-title")
            
            yield Static("Are you sure you want to rollback the following operation?", 
                        classes="confirmation-text")
            
            # Transaction details
            with Vertical(id="transaction-details", classes="section"):
                yield Static("📋 Transaction Details", classes="section-header")
                yield Static(f"Operation: {self.transaction.operation}", classes="detail-item")
                yield Static(f"Description: {self.transaction.description}", classes="detail-item")
                yield Static(f"Actions: {len(self.transaction.actions)}", classes="detail-item")
                yield Static(f"Created: {self.transaction.created_at}", classes="detail-item")
            
            # Warning message
            yield Static("⚠️ This action cannot be undone. Make sure you want to proceed.", 
                        classes="warning-text")
            
            # Action buttons
            with Horizontal(id="rollback-action-buttons"):
                yield Button("✅ Confirm Rollback", id="confirm-btn", variant="warning")
                yield Button("❌ Cancel", id="cancel-btn", variant="default")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm-btn":
            self.action_confirm()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
    
    def action_confirm(self) -> None:
        """Confirm the rollback."""
        if self.callback:
            self.callback(True)
        self.dismiss(True)
    
    def action_cancel(self) -> None:
        """Cancel the rollback."""
        if self.callback:
            self.callback(False)
        self.dismiss(False)


class ManualFixDialog(ModalScreen):
    """Dialog showing detailed manual fix instructions."""
    
    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("enter", "mark_fixed", "Mark as Fixed"),
    ]
    
    CSS = """
    #manual-fix-dialog {
        width: 80%;
        height: 80%;
        border: solid $accent;
        background: $surface;
        padding: 1;
    }
    """
    
    def __init__(self, error: MCPManagerError, diagnostics: ErrorDiagnostics):
        super().__init__()
        self.error = error
        self.diagnostics = diagnostics
    
    def compose(self) -> ComposeResult:
        """Create the manual fix dialog layout."""
        with Vertical(id="manual-fix-dialog"):
            yield Static("🛠️ Manual Fix Instructions", classes="dialog-title")
            
            # Problem description
            with Vertical(id="problem-description", classes="section"):
                yield Static("❗ Problem", classes="section-header")
                yield Static(self.error.user_message, classes="problem-text")
            
            # Step-by-step instructions
            with Vertical(id="fix-instructions", classes="section"):
                yield Static("📋 Fix Instructions", classes="section-header")
                
                instructions = self.generate_fix_instructions()
                for i, instruction in enumerate(instructions, 1):
                    yield Static(f"{i}. {instruction}", classes="instruction-item")
            
            # Action buttons
            with Horizontal(id="manual-action-buttons"):
                yield Button("✅ Mark as Fixed", id="fixed-btn", variant="success")
                yield Button("❌ Still Having Issues", id="issues-btn", variant="warning")
                yield Button("🔙 Back", id="back-btn", variant="default")
    
    def generate_fix_instructions(self) -> List[str]:
        """Generate step-by-step fix instructions based on error type."""
        instructions = []
        
        if hasattr(self.error, 'config_path') and self.error.config_path:
            instructions.extend([
                f"Open the configuration file: {self.error.config_path}",
                "Check the file syntax and formatting",
                "Verify all required fields are present and correctly formatted"
            ])
        
        if hasattr(self.error, 'field_name') and self.error.field_name:
            instructions.append(f"Pay special attention to the '{self.error.field_name}' field")
        
        # Add error-specific instructions
        instructions.extend(self.diagnostics.suggested_fixes)
        
        instructions.extend([
            "Save any changes to the configuration",
            "Test the configuration to ensure it works",
            "Return here and click 'Mark as Fixed' if resolved"
        ])
        
        return instructions
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "fixed-btn":
            self.action_mark_fixed()
        elif event.button.id == "issues-btn":
            self.notify("For additional support, check the documentation or contact support")
        elif event.button.id == "back-btn":
            self.action_close()
    
    def action_close(self) -> None:
        """Close the dialog."""
        self.dismiss(False)
    
    def action_mark_fixed(self) -> None:
        """Mark the issue as fixed."""
        self.dismiss(True)