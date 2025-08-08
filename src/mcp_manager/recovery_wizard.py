"""Recovery wizard for step-by-step problem resolution in MCP Manager."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Center
from textual.widgets import Button, Static, Label, ProgressBar, RadioSet, RadioButton, Input, Checkbox
from textual.screen import ModalScreen
from textual.binding import Binding
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from dataclasses import dataclass

from .exceptions import MCPManagerError, RecoveryAction, ErrorSeverity
from .error_handler import RecoveryResult


class WizardStep(Enum):
    """Steps in the recovery wizard."""
    DIAGNOSIS = "diagnosis"
    ACTION_SELECTION = "action_selection"  
    CONFIRMATION = "confirmation"
    EXECUTION = "execution"
    RESULT = "result"


@dataclass
class WizardState:
    """State management for the recovery wizard."""
    current_step: WizardStep = WizardStep.DIAGNOSIS
    selected_action: Optional[RecoveryAction] = None
    user_input: Dict[str, Any] = None
    diagnosis_complete: bool = False
    execution_result: Optional[RecoveryResult] = None
    
    def __post_init__(self):
        if self.user_input is None:
            self.user_input = {}


class RecoveryWizard(ModalScreen):
    """Multi-step wizard for guided problem resolution."""
    
    BINDINGS = [
        Binding("escape", "cancel_wizard", "Cancel", priority=True),
        Binding("enter", "next_step", "Next", priority=True),
        Binding("ctrl+b", "previous_step", "Back"),
        Binding("ctrl+r", "retry_step", "Retry Current Step"),
    ]
    
    CSS = """
    #recovery-wizard {
        width: 85%;
        height: 80%;
        border: solid $accent;
        background: $surface;
        padding: 1;
    }
    
    .wizard-header {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }
    
    .step-indicator {
        text-align: center;
        margin: 1;
        color: $text-muted;
    }
    
    .step-content {
        min-height: 20;
        padding: 1;
        border: solid $secondary;
        margin: 1 0;
    }
    
    .step-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    .diagnosis-item {
        margin: 0 0 0 2;
    }
    
    .action-option {
        margin: 0 0 1 2;
    }
    
    .confirmation-warning {
        color: $warning;
        text-style: bold;
        text-align: center;
        margin: 1;
    }
    
    .execution-status {
        text-align: center;
        margin: 1;
    }
    
    .result-success {
        color: $success;
        text-style: bold;
        text-align: center;
    }
    
    .result-error {
        color: $error;
        text-style: bold;
        text-align: center;
    }
    
    #wizard-navigation {
        justify: center;
        margin: 1;
    }
    
    #wizard-navigation Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, error: MCPManagerError, 
                 recovery_callback: Optional[Callable[[RecoveryAction, Dict[str, Any]], RecoveryResult]] = None):
        super().__init__()
        self.error = error
        self.recovery_callback = recovery_callback
        self.state = WizardState()
        self.step_handlers = {
            WizardStep.DIAGNOSIS: self.create_diagnosis_step,
            WizardStep.ACTION_SELECTION: self.create_action_selection_step,
            WizardStep.CONFIRMATION: self.create_confirmation_step,
            WizardStep.EXECUTION: self.create_execution_step,
            WizardStep.RESULT: self.create_result_step,
        }
    
    def compose(self) -> ComposeResult:
        """Create the recovery wizard layout."""
        with Vertical(id="recovery-wizard"):
            yield Static("🧙‍♂️ Recovery Wizard", classes="wizard-header")
            yield Static(self.get_step_indicator(), id="step-indicator", classes="step-indicator")
            
            # Dynamic content area
            with Vertical(id="step-content", classes="step-content"):
                yield from self.create_current_step()
            
            # Navigation buttons
            with Horizontal(id="wizard-navigation"):
                yield Button("⬅️ Back", id="back-btn", disabled=True)
                yield Button("➡️ Next", id="next-btn")
                yield Button("❌ Cancel", id="cancel-btn", variant="error")
    
    def get_step_indicator(self) -> str:
        """Get step indicator text."""
        steps = list(WizardStep)
        current_index = steps.index(self.state.current_step)
        
        indicator_parts = []
        for i, step in enumerate(steps):
            if i == current_index:
                indicator_parts.append(f"[{i+1}. {step.value.title()} ◀]")
            elif i < current_index:
                indicator_parts.append(f"✓ {i+1}. {step.value.title()}")
            else:
                indicator_parts.append(f"{i+1}. {step.value.title()}")
        
        return " → ".join(indicator_parts)
    
    def create_current_step(self) -> ComposeResult:
        """Create content for the current step."""
        handler = self.step_handlers.get(self.state.current_step)
        if handler:
            yield from handler()
        else:
            yield Static("Unknown step", classes="error-text")
    
    def create_diagnosis_step(self) -> ComposeResult:
        """Create the diagnosis step."""
        yield Static("🔍 Problem Diagnosis", classes="step-title")
        yield Static("Let's identify what went wrong and what we can do about it.", classes="step-description")
        
        # Error details
        yield Static(f"Error Type: {self.error.__class__.__name__}", classes="diagnosis-item")
        yield Static(f"Severity: {self.error.severity.value}", classes="diagnosis-item")
        yield Static(f"Message: {self.error.user_message}", classes="diagnosis-item")
        
        # Context information
        if self.error.context:
            yield Static("Context Information:", classes="diagnosis-header")
            if self.error.context.operation:
                yield Static(f"• Operation: {self.error.context.operation}", classes="diagnosis-item")
            if self.error.context.server_name:
                yield Static(f"• Server: {self.error.context.server_name}", classes="diagnosis-item")
            if self.error.context.platform_key:
                yield Static(f"• Platform: {self.error.context.platform_key}", classes="diagnosis-item")
        
        # Automatic checks
        yield Static("Running automatic diagnostics...", id="diagnosis-status")
        
        # Mark diagnosis as complete (in real implementation, this would run checks)
        self.state.diagnosis_complete = True
        self.query_one("#diagnosis-status", Static).update("✅ Diagnosis complete. Ready to proceed.")
    
    def create_action_selection_step(self) -> ComposeResult:
        """Create the action selection step."""
        yield Static("🎯 Select Recovery Action", classes="step-title")
        yield Static("Choose how you'd like to resolve this issue:", classes="step-description")
        
        if not self.error.suggested_actions:
            yield Static("No automatic recovery actions available.", classes="error-text")
            yield Static("You may need to resolve this issue manually.", classes="warning-text")
            return
        
        # Action selection radio buttons
        with RadioSet(id="action-selection"):
            for action in self.error.suggested_actions:
                yield RadioButton(
                    self.get_detailed_action_description(action),
                    value=action.value,
                    name="recovery_action"
                )
        
        # Additional options based on action type
        if RecoveryAction.MANUAL_FIX in self.error.suggested_actions:
            yield Static("Manual Fix Options:", classes="section-header")
            yield Checkbox("Open configuration files", id="open-config-check")
            yield Checkbox("Show detailed instructions", id="show-instructions-check", value=True)
        
        if RecoveryAction.RETRY in self.error.suggested_actions:
            yield Static("Retry Options:", classes="section-header")
            yield Checkbox("Use exponential backoff", id="backoff-check", value=True)
            with Horizontal():
                yield Static("Max retries: ")
                yield Input(placeholder="3", id="max-retries-input")
    
    def create_confirmation_step(self) -> ComposeResult:
        """Create the confirmation step."""
        yield Static("✅ Confirm Action", classes="step-title")
        
        if not self.state.selected_action:
            yield Static("No action selected. Please go back and select an action.", classes="error-text")
            return
        
        yield Static(f"You have selected: {self.get_detailed_action_description(self.state.selected_action)}", 
                    classes="confirmation-text")
        
        # Show what will happen
        yield Static("What will happen:", classes="section-header")
        consequences = self.get_action_consequences(self.state.selected_action)
        for consequence in consequences:
            yield Static(f"• {consequence}", classes="consequence-item")
        
        # Warnings if applicable
        if self.state.selected_action == RecoveryAction.ROLLBACK:
            yield Static("⚠️ This will undo recent changes and may affect other operations!", 
                        classes="confirmation-warning")
        elif self.state.selected_action == RecoveryAction.ABORT:
            yield Static("⚠️ This will cancel all current operations!", 
                        classes="confirmation-warning")
        
        yield Static("Are you ready to proceed?", classes="confirmation-question")
    
    def create_execution_step(self) -> ComposeResult:
        """Create the execution step."""
        yield Static("⚙️ Executing Recovery", classes="step-title")
        yield Static("Please wait while we execute the selected recovery action...", 
                    classes="execution-status")
        
        # Progress bar
        yield ProgressBar(id="execution-progress", show_percentage=True)
        
        # Status updates
        yield Static("Initializing recovery process...", id="execution-status", classes="execution-status")
        
        # Trigger execution
        self.execute_recovery_action()
    
    def create_result_step(self) -> ComposeResult:
        """Create the result step."""
        yield Static("📊 Recovery Result", classes="step-title")
        
        if not self.state.execution_result:
            yield Static("No execution result available.", classes="error-text")
            return
        
        result = self.state.execution_result
        
        if result.success:
            yield Static("✅ Recovery Successful!", classes="result-success")
            yield Static(f"Action taken: {result.action_taken}", classes="result-detail")
            yield Static(f"Result: {result.message}", classes="result-detail")
        else:
            yield Static("❌ Recovery Failed", classes="result-error")
            yield Static(f"Action attempted: {result.action_taken}", classes="result-detail")
            yield Static(f"Error: {result.message}", classes="result-detail")
            
            if result.manual_intervention_required:
                yield Static("🛠️ Manual intervention is required to resolve this issue.", 
                           classes="manual-required")
            
            if result.retry_suggested:
                yield Static("🔄 You may want to try a different recovery approach.", 
                           classes="retry-suggested")
        
        # Next steps
        yield Static("Next Steps:", classes="section-header")
        next_steps = self.get_next_steps(result)
        for step in next_steps:
            yield Static(f"• {step}", classes="next-step-item")
    
    def get_detailed_action_description(self, action: RecoveryAction) -> str:
        """Get detailed description for a recovery action."""
        descriptions = {
            RecoveryAction.RETRY: "Retry Operation - Attempt the failed operation again with smart backoff",
            RecoveryAction.SKIP: "Skip and Continue - Skip this operation and proceed with others",
            RecoveryAction.ROLLBACK: "Rollback Changes - Undo recent changes to restore previous state",
            RecoveryAction.MANUAL_FIX: "Manual Fix - Get step-by-step instructions to fix the issue",
            RecoveryAction.IGNORE: "Ignore and Continue - Mark as resolved and continue",
            RecoveryAction.ABORT: "Abort Operations - Cancel all current operations safely"
        }
        return descriptions.get(action, f"Unknown action: {action.value}")
    
    def get_action_consequences(self, action: RecoveryAction) -> List[str]:
        """Get list of consequences for an action."""
        consequences = {
            RecoveryAction.RETRY: [
                "The failed operation will be attempted again",
                "May take several attempts with increasing delays",
                "Other operations may be delayed"
            ],
            RecoveryAction.SKIP: [
                "This specific operation will be skipped",
                "Other operations will continue normally",
                "The issue may need to be resolved later"
            ],
            RecoveryAction.ROLLBACK: [
                "Recent configuration changes will be undone",
                "System will be restored to a previous working state",
                "Any unsaved work may be lost"
            ],
            RecoveryAction.MANUAL_FIX: [
                "You will receive detailed fix instructions",
                "The wizard will wait for you to complete the fix",
                "You can test the fix before proceeding"
            ],
            RecoveryAction.IGNORE: [
                "The error will be marked as resolved",
                "Operations will continue as if nothing happened",
                "The underlying issue may persist"
            ],
            RecoveryAction.ABORT: [
                "All current operations will be safely cancelled",
                "Partial changes may be rolled back",
                "You can restart operations later"
            ]
        }
        return consequences.get(action, ["Unknown consequences"])
    
    def get_next_steps(self, result: RecoveryResult) -> List[str]:
        """Get suggested next steps after recovery attempt."""
        if result.success:
            return [
                "The issue has been resolved",
                "You can continue with your operations",
                "Monitor for any recurring issues"
            ]
        else:
            steps = ["Review the error details above"]
            
            if result.manual_intervention_required:
                steps.extend([
                    "Use the Manual Fix option for detailed instructions",
                    "Check system logs for additional information",
                    "Contact support if the issue persists"
                ])
            
            if result.retry_suggested:
                steps.extend([
                    "Try a different recovery approach",
                    "Consider using Rollback to restore previous state",
                    "Check for system-wide issues"
                ])
            
            return steps
    
    def execute_recovery_action(self) -> None:
        """Execute the selected recovery action."""
        if not self.state.selected_action or not self.recovery_callback:
            self.state.execution_result = RecoveryResult(
                success=False,
                action_taken="no_action",
                message="No action selected or callback available"
            )
            return
        
        # Update progress
        progress = self.query_one("#execution-progress", ProgressBar)
        status = self.query_one("#execution-status", Static)
        
        progress.update(progress=25)
        status.update("Preparing recovery action...")
        
        try:
            # Execute the recovery action
            progress.update(progress=50)
            status.update(f"Executing {self.state.selected_action.value}...")
            
            result = self.recovery_callback(self.state.selected_action, self.state.user_input)
            
            progress.update(progress=100)
            status.update("Recovery action completed")
            
            self.state.execution_result = result
            
        except Exception as e:
            progress.update(progress=100)
            status.update(f"Recovery action failed: {str(e)}")
            
            self.state.execution_result = RecoveryResult(
                success=False,
                action_taken="execution_error",
                message=f"Failed to execute recovery: {str(e)}"
            )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "next-btn":
            self.action_next_step()
        elif event.button.id == "back-btn":
            self.action_previous_step()
        elif event.button.id == "cancel-btn":
            self.action_cancel_wizard()
    
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio button selection."""
        if event.radio_set.id == "action-selection":
            self.state.selected_action = RecoveryAction(event.pressed.value)
    
    def action_next_step(self) -> None:
        """Move to the next wizard step."""
        current_steps = list(WizardStep)
        current_index = current_steps.index(self.state.current_step)
        
        # Validate current step before proceeding
        if not self.validate_current_step():
            return
        
        # Move to next step
        if current_index < len(current_steps) - 1:
            self.state.current_step = current_steps[current_index + 1]
            self.refresh_wizard()
        else:
            # Wizard complete
            self.dismiss(self.state.execution_result)
    
    def action_previous_step(self) -> None:
        """Move to the previous wizard step."""
        current_steps = list(WizardStep)
        current_index = current_steps.index(self.state.current_step)
        
        if current_index > 0:
            self.state.current_step = current_steps[current_index - 1]
            self.refresh_wizard()
    
    def action_cancel_wizard(self) -> None:
        """Cancel the wizard."""
        self.dismiss(None)
    
    def action_retry_step(self) -> None:
        """Retry the current step."""
        if self.state.current_step == WizardStep.EXECUTION:
            self.execute_recovery_action()
            self.refresh_wizard()
    
    def validate_current_step(self) -> bool:
        """Validate that the current step is complete."""
        if self.state.current_step == WizardStep.DIAGNOSIS:
            return self.state.diagnosis_complete
        
        elif self.state.current_step == WizardStep.ACTION_SELECTION:
            if not self.state.selected_action:
                self.notify("Please select a recovery action before proceeding", severity="warning")
                return False
            return True
        
        elif self.state.current_step == WizardStep.CONFIRMATION:
            return True  # No validation needed for confirmation
        
        elif self.state.current_step == WizardStep.EXECUTION:
            return self.state.execution_result is not None
        
        return True
    
    def refresh_wizard(self) -> None:
        """Refresh the wizard display for the current step."""
        # Update step indicator
        self.query_one("#step-indicator").update(self.get_step_indicator())
        
        # Update step content
        step_content = self.query_one("#step-content")
        step_content.remove_children()
        step_content.mount(*self.create_current_step())
        
        # Update navigation buttons
        current_steps = list(WizardStep)
        current_index = current_steps.index(self.state.current_step)
        
        back_btn = self.query_one("#back-btn", Button)
        next_btn = self.query_one("#next-btn", Button)
        
        back_btn.disabled = (current_index == 0)
        
        if current_index == len(current_steps) - 1:
            next_btn.label = "Finish"
        else:
            next_btn.label = "Next"