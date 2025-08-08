"""Validation details and repair dialog for MCP server configurations."""

from typing import Dict, Any, List, Optional
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Static, Button, Label, DataTable, ListView, ListItem, 
    ProgressBar, Collapsible, Rule, Markdown
)
from textual.screen import ModalScreen
from textual.binding import Binding
from textual import events
import structlog

from .config_validator import ValidationResult, ValidationIssue
from .auto_repair import AutoRepair, RepairSuggestion, RepairAction

logger = structlog.get_logger()


class ValidationDetailsDialog(ModalScreen):
    """Modal dialog showing validation details and repair options."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("f", "auto_fix", "Auto Fix", priority=True),
        Binding("r", "revalidate", "Revalidate", priority=True),
    ]
    
    DEFAULT_CSS = """
    ValidationDetailsDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    
    #dialog-container {
        width: 90%;
        max-width: 100;
        height: 80%;
        max-height: 40;
        background: $surface;
        border: solid $primary;
        border-title-color: $primary;
        border-title-style: bold;
    }
    
    #content-area {
        height: 1fr;
        padding: 1;
    }
    
    #button-area {
        height: 4;
        background: $panel;
        border-top: solid $primary;
        padding: 1;
        align: center middle;
    }
    
    .validation-summary {
        background: $panel;
        border: solid $accent;
        padding: 1;
        margin-bottom: 1;
        text-align: center;
    }
    
    .score-excellent {
        color: $success;
        text-style: bold;
    }
    
    .score-good {
        color: $warning;
        text-style: bold;
    }
    
    .score-poor {
        color: $error;
        text-style: bold;
    }
    
    .issue-item {
        padding: 1;
        margin-bottom: 1;
        border: solid $accent;
        border-left-color: $error;
        border-left-size: 3;
        background: $surface;
    }
    
    .issue-error {
        border-left-color: $error;
    }
    
    .issue-warning {
        border-left-color: $warning;
    }
    
    .issue-info {
        border-left-color: $accent;
    }
    
    .issue-severity {
        text-style: bold;
    }
    
    .issue-category {
        color: $text-muted;
        text-style: italic;
    }
    
    .repair-suggestion {
        background: $panel;
        border: solid $success;
        padding: 1;
        margin: 1 0;
        border-radius: 2;
    }
    
    .repair-action {
        background: $surface;
        border-left: solid $accent;
        border-left-size: 2;
        padding: 1;
        margin: 0 1;
    }
    
    .auto-fixable {
        color: $success;
    }
    
    .manual-fix {
        color: $warning;
    }
    
    .dialog-button {
        margin: 0 1;
        min-width: 12;
        background: $accent;
        color: $text;
    }
    
    .primary-button {
        background: $primary;
    }
    
    .success-button {
        background: $success;
    }
    
    .warning-button {
        background: $warning;
    }
    """
    
    def __init__(
        self, 
        server_name: str, 
        validation_result: ValidationResult,
        auto_repair: AutoRepair,
        server_config: Dict[str, Any]
    ):
        """Initialize validation dialog.
        
        Args:
            server_name: Name of the server being validated
            validation_result: Validation result to display
            auto_repair: Auto-repair instance for suggestions
            server_config: Server configuration dictionary
        """
        super().__init__()
        self.server_name = server_name
        self.validation_result = validation_result
        self.auto_repair = auto_repair
        self.server_config = server_config
        
        # Generate repair suggestions
        self.repair_suggestions = self.auto_repair.analyze_issues(
            self.validation_result, 
            self.server_config
        )
        
    def compose(self) -> ComposeResult:
        """Create the dialog layout."""
        with Container(id="dialog-container"):
            # Dialog title
            yield Static(
                f"🔍 Validation Details: {self.server_name}",
                id="dialog-title"
            )
            
            with ScrollableContainer(id="content-area"):
                # Validation summary
                yield self._create_validation_summary()
                
                # Issues section
                if self.validation_result.issues:
                    yield Label("📋 Issues Found:", id="issues-header")
                    for issue in self.validation_result.issues:
                        yield self._create_issue_display(issue)
                else:
                    yield Static("✅ No validation issues found!", classes="success-text")
                
                # Repair suggestions section
                if self.repair_suggestions:
                    yield Rule()
                    yield Label("🔧 Repair Suggestions:", id="repairs-header")
                    for suggestion in self.repair_suggestions:
                        yield self._create_repair_suggestion_display(suggestion)
                else:
                    if self.validation_result.issues:
                        yield Static("ℹ️ No automatic repair suggestions available", classes="info-text")
            
            # Button area
            with Horizontal(id="button-area"):
                if self.repair_suggestions:
                    yield Button("🔧 Auto Fix", id="btn-auto-fix", classes="dialog-button success-button")
                yield Button("🔄 Revalidate", id="btn-revalidate", classes="dialog-button primary-button")
                yield Button("❌ Close", id="btn-close", classes="dialog-button")
    
    def _create_validation_summary(self) -> Container:
        """Create validation summary section."""
        score = self.validation_result.score
        
        # Determine score class and message
        if score >= 90:
            score_class = "score-excellent"
            score_icon = "✅"
            message = "Excellent configuration!"
        elif score >= 70:
            score_class = "score-good" 
            score_icon = "⚠️"
            message = "Good configuration with minor issues"
        else:
            score_class = "score-poor"
            score_icon = "❌"
            message = "Configuration needs attention"
        
        with Container(classes="validation-summary"):
            yield Static(f"{score_icon} Validation Score: {score}%", classes=score_class)
            yield Static(message)
            
            # Health check status
            if self.validation_result.health_checked:
                health_icon = "🟢" if self.validation_result.health_status == "healthy" else "🔴"
                health_text = self.validation_result.health_status or "Unknown"
                yield Static(f"{health_icon} Health: {health_text}")
    
    def _create_issue_display(self, issue: ValidationIssue) -> Container:
        """Create display for a single validation issue."""
        severity_icons = {
            "error": "❌",
            "warning": "⚠️", 
            "info": "ℹ️"
        }
        
        severity_icon = severity_icons.get(issue.severity, "❓")
        issue_class = f"issue-{issue.severity}"
        
        with Container(classes=f"issue-item {issue_class}"):
            # Issue header
            yield Static(
                f"{severity_icon} {issue.severity.upper()}: {issue.message}",
                classes="issue-severity"
            )
            
            # Issue details
            if issue.field:
                yield Static(f"Field: {issue.field}", classes="issue-category")
            
            yield Static(f"Category: {issue.category}", classes="issue-category")
            
            if issue.suggested_value:
                yield Static(f"Suggestion: {issue.suggested_value}")
            
            if issue.auto_fixable:
                yield Static("🔧 Auto-fixable", classes="auto-fixable")
    
    def _create_repair_suggestion_display(self, suggestion: RepairSuggestion) -> Container:
        """Create display for a repair suggestion."""
        with Container(classes="repair-suggestion"):
            # Suggestion header
            confidence = suggestion.get_total_confidence()
            confidence_icon = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🔴"
            
            yield Static(
                f"🔧 {suggestion.title} ({confidence_icon} {confidence:.0%} confidence)",
                classes="repair-title"
            )
            yield Static(suggestion.description)
            
            # Suggestion details
            yield Static(f"📊 Addresses {len(suggestion.issues_addressed)} issue(s)")
            yield Static(f"⏱️ Estimated time: {suggestion.estimated_time}")
            yield Static(f"📈 Success rate: {suggestion.success_rate:.0%}")
            
            # Actions
            if suggestion.actions:
                yield Label("Actions:")
                for action in suggestion.actions:
                    with Container(classes="repair-action"):
                        action_icon = "🔧" if action.auto_applicable else "👤"
                        action_class = "auto-fixable" if action.auto_applicable else "manual-fix"
                        
                        yield Static(
                            f"{action_icon} {action.title}",
                            classes=action_class
                        )
                        yield Static(action.description)
                        
                        if action.preview:
                            yield Static(f"Preview: {action.preview}")
                        
                        if action.destructive:
                            yield Static("⚠️ Destructive action - requires confirmation", classes="warning-text")
    
    def action_dismiss(self) -> None:
        """Close the dialog."""
        self.dismiss()
    
    def action_auto_fix(self) -> None:
        """Apply auto-fixes and close dialog."""
        if not self.repair_suggestions:
            return
        
        # Return repair suggestions for the parent to handle
        self.dismiss({"action": "auto_fix", "suggestions": self.repair_suggestions})
    
    def action_revalidate(self) -> None:
        """Trigger revalidation and close dialog."""
        self.dismiss({"action": "revalidate", "server_name": self.server_name})
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn-close":
            self.action_dismiss()
        elif event.button.id == "btn-auto-fix":
            self.action_auto_fix()
        elif event.button.id == "btn-revalidate":
            self.action_revalidate()


class RepairWizardDialog(ModalScreen):
    """Step-by-step repair wizard dialog."""
    
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", priority=True),
        Binding("enter", "apply_step", "Apply", priority=True),
    ]
    
    DEFAULT_CSS = """
    RepairWizardDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.8);
    }
    
    #wizard-container {
        width: 80%;
        height: 70%;
        background: $surface;
        border: solid $primary;
        border-title-color: $primary;
        border-title-style: bold;
    }
    
    #wizard-header {
        height: 5;
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
    }
    
    #wizard-content {
        height: 1fr;
        padding: 2;
    }
    
    #wizard-footer {
        height: 5;
        background: $panel;
        border-top: solid $primary;
        padding: 1;
    }
    
    .step-indicator {
        text-align: center;
        background: $accent;
        padding: 1;
        margin-bottom: 1;
    }
    
    .repair-preview {
        background: $panel;
        border: solid $accent;
        padding: 1;
        margin: 1 0;
    }
    
    .before-after {
        background: $surface;
        border-left: solid $warning;
        border-left-size: 3;
        padding: 1;
        margin: 1 0;
    }
    """
    
    def __init__(self, repair_suggestions: List[RepairSuggestion], server_name: str):
        """Initialize repair wizard.
        
        Args:
            repair_suggestions: List of repair suggestions to walk through
            server_name: Name of the server being repaired
        """
        super().__init__()
        self.repair_suggestions = repair_suggestions
        self.server_name = server_name
        self.current_step = 0
        self.completed_repairs = []
    
    def compose(self) -> ComposeResult:
        """Create the wizard layout."""
        with Container(id="wizard-container"):
            # Header
            with Container(id="wizard-header"):
                yield Static(f"🧙 Repair Wizard: {self.server_name}")
                yield Static(f"Step {self.current_step + 1} of {len(self.repair_suggestions)}")
            
            # Content area
            with ScrollableContainer(id="wizard-content"):
                if self.repair_suggestions:
                    yield self._create_current_step_display()
            
            # Footer with buttons
            with Horizontal(id="wizard-footer"):
                if self.current_step > 0:
                    yield Button("⬅️ Previous", id="btn-previous", classes="dialog-button")
                
                if self.current_step < len(self.repair_suggestions) - 1:
                    yield Button("Apply & Next ➡️", id="btn-apply-next", classes="dialog-button primary-button")
                else:
                    yield Button("🏁 Apply & Finish", id="btn-apply-finish", classes="dialog-button success-button")
                
                yield Button("⏩ Skip", id="btn-skip", classes="dialog-button")
                yield Button("❌ Cancel", id="btn-cancel", classes="dialog-button")
    
    def _create_current_step_display(self) -> Container:
        """Create display for current repair step."""
        if not self.repair_suggestions:
            return Container()
        
        suggestion = self.repair_suggestions[self.current_step]
        
        with Container():
            # Step indicator
            yield Static(
                f"🔧 {suggestion.title}",
                classes="step-indicator"
            )
            
            # Description
            yield Static(suggestion.description)
            
            # Issues being addressed
            yield Label("Issues being fixed:")
            for issue in suggestion.issues_addressed:
                yield Static(f"• {issue.severity.upper()}: {issue.message}")
            
            # Actions preview
            yield Label("Actions to apply:")
            for action in suggestion.actions:
                with Container(classes="repair-preview"):
                    yield Static(f"🔧 {action.title}")
                    yield Static(action.description)
                    
                    if action.before_value and action.after_value:
                        with Container(classes="before-after"):
                            yield Static(f"Before: {action.before_value}")
                            yield Static(f"After: {action.after_value}")
                    elif action.preview:
                        yield Static(f"Preview: {action.preview}")
                    
                    if action.destructive:
                        yield Static("⚠️ This action modifies system files", classes="warning-text")
    
    def action_dismiss(self) -> None:
        """Cancel the wizard."""
        self.dismiss({"action": "cancel"})
    
    def action_apply_step(self) -> None:
        """Apply current step and advance."""
        if self.current_step < len(self.repair_suggestions) - 1:
            self.current_step += 1
            self.refresh()
        else:
            # Finish wizard
            self.dismiss({
                "action": "complete",
                "applied_suggestions": self.repair_suggestions
            })
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "btn-cancel":
            self.action_dismiss()
        elif event.button.id == "btn-apply-next":
            self.action_apply_step()
        elif event.button.id == "btn-apply-finish":
            self.action_apply_step()
        elif event.button.id == "btn-skip":
            if self.current_step < len(self.repair_suggestions) - 1:
                self.current_step += 1
                self.refresh()
            else:
                self.action_dismiss()
        elif event.button.id == "btn-previous":
            if self.current_step > 0:
                self.current_step -= 1
                self.refresh()