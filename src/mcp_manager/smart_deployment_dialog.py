"""Smart Deployment Dialog with Suggestions and Quick Deploy."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Center, Container
from textual.widgets import (
    Static, Button, Checkbox, Select, ProgressBar,
    DataTable, Label, Rule, ListView, ListItem
)
from textual.screen import ModalScreen
from textual import events
from textual.binding import Binding
from typing import Dict, List, Optional, Any, Callable
from rich.text import Text
import logging

from mcp_manager.user_preferences import UserPreferences
from mcp_manager.smart_wizard import SmartDeploymentWizard

logger = logging.getLogger(__name__)


class SmartSuggestionItem(Static):
    """Widget for displaying a smart suggestion."""
    
    def __init__(self, suggestion: Dict[str, Any], index: int, **kwargs):
        super().__init__(**kwargs)
        self.suggestion = suggestion
        self.index = index
        self.selected = False
    
    def compose(self) -> ComposeResult:
        """Compose the suggestion item."""
        confidence = self.suggestion.get("confidence", 0.0)
        usage = self.suggestion.get("usage", 0)
        
        confidence_bar = "█" * int(confidence * 10)
        confidence_text = f"{confidence * 100:.0f}%"
        
        with Horizontal(classes="suggestion-item"):
            yield Checkbox("", value=self.selected, classes="suggestion-checkbox")
            
            with Vertical(classes="suggestion-content"):
                yield Static(self.suggestion["title"], classes="suggestion-title")
                yield Static(self.suggestion["description"], classes="suggestion-description")
                
                with Horizontal(classes="suggestion-stats"):
                    yield Static(f"Confidence: {confidence_text}", classes="confidence-stat")
                    if usage > 0:
                        yield Static(f"Used {usage} times", classes="usage-stat")
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state change."""
        self.selected = event.value
        self.post_message(SuggestionSelectionChanged(self.index, self.selected))


class SuggestionSelectionChanged(events.Message):
    """Message when suggestion selection changes."""
    
    def __init__(self, index: int, selected: bool) -> None:
        super().__init__()
        self.index = index
        self.selected = selected


class QuickDeployCard(Static):
    """Card for quick deploy option."""
    
    def __init__(self, quick_option: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.quick_option = quick_option
    
    def compose(self) -> ComposeResult:
        """Compose the quick deploy card."""
        with Container(classes="quick-deploy-card"):
            yield Static("⚡ Quick Deploy", classes="quick-deploy-title")
            yield Static(self.quick_option["title"], classes="quick-deploy-subtitle")
            yield Static(self.quick_option["description"], classes="quick-deploy-description")
            yield Button("Deploy Now", id="quick_deploy_btn", classes="quick-deploy-button")


class SmartDeploymentDialog(ModalScreen):
    """Smart deployment dialog with suggestions and learning."""
    
    CSS = """
    SmartDeploymentDialog {
        align: center middle;
    }
    
    .dialog-container {
        width: 90%;
        max-width: 100;
        height: 80%;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    
    .dialog-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .section-title {
        text-style: bold;
        margin: 1 0;
        color: $secondary;
    }
    
    .quick-deploy-card {
        border: solid $success;
        padding: 1;
        margin: 1 0;
        background: $success 10%;
    }
    
    .quick-deploy-title {
        text-style: bold;
        color: $success;
    }
    
    .quick-deploy-subtitle {
        color: $text;
        margin: 0 0 1 0;
    }
    
    .quick-deploy-description {
        color: $text-muted;
        margin: 0 0 1 0;
    }
    
    .quick-deploy-button {
        background: $success;
        color: $text;
    }
    
    .suggestion-item {
        border: solid $muted;
        padding: 1;
        margin: 1 0;
    }
    
    .suggestion-item:hover {
        border: solid $accent;
    }
    
    .suggestion-title {
        text-style: bold;
        color: $text;
    }
    
    .suggestion-description {
        color: $text-muted;
        margin: 0 0 1 0;
    }
    
    .suggestion-stats {
        height: 1;
    }
    
    .confidence-stat {
        color: $secondary;
        width: 20;
    }
    
    .usage-stat {
        color: $text-muted;
    }
    
    .platform-selection {
        margin: 1 0;
        height: 15;
        border: solid $muted;
        padding: 1;
    }
    
    .button-row {
        height: 3;
        align: center middle;
        margin-top: 2;
    }
    
    .dialog-button {
        margin: 0 1;
        min-width: 12;
    }
    
    .no-suggestions {
        text-align: center;
        color: $text-muted;
        margin: 2 0;
        padding: 2;
        border: dashed $muted;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "deploy", "Deploy"),
    ]
    
    def __init__(
        self,
        server_name: str,
        available_platforms: List[str],
        smart_wizard: SmartDeploymentWizard,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.server_name = server_name
        self.available_platforms = available_platforms
        self.smart_wizard = smart_wizard
        
        # Get suggestions and quick deploy option
        self.suggestions = smart_wizard.get_smart_suggestions(server_name, available_platforms)
        self.quick_option = smart_wizard.get_quick_deploy_option(server_name)
        
        # Selection state
        self.selected_suggestions: List[int] = []
        self.manual_selections: Set[str] = set()
        
        # Result
        self.result: Optional[Dict[str, Any]] = None
    
    def compose(self) -> ComposeResult:
        """Compose the smart deployment dialog."""
        with Center():
            with Vertical(classes="dialog-container"):
                yield Static(f"Deploy {self.server_name}", classes="dialog-title")
                
                # Quick deploy section
                if self.quick_option:
                    yield Static("⚡ Quick Deploy", classes="section-title")
                    yield QuickDeployCard(self.quick_option)
                    yield Rule()
                
                # Smart suggestions section
                if self.suggestions:
                    yield Static("🎯 Smart Suggestions", classes="section-title")
                    yield Static("Based on your deployment history:", classes="help-text")
                    
                    with Vertical(classes="suggestions-list"):
                        for i, suggestion in enumerate(self.suggestions):
                            yield SmartSuggestionItem(suggestion, i)
                    
                    yield Rule()
                else:
                    yield Static("🎯 Smart Suggestions", classes="section-title")
                    yield Static(
                        "No suggestions yet. Deploy this server a few times to build smart suggestions!",
                        classes="no-suggestions"
                    )
                    yield Rule()
                
                # Manual platform selection
                yield Static("🔧 Manual Selection", classes="section-title")
                yield Static("Select specific platforms:", classes="help-text")
                
                with Vertical(classes="platform-selection"):
                    for platform in self.available_platforms:
                        yield Checkbox(
                            platform.replace("-", " ").title(),
                            id=f"platform_{platform}",
                            classes="platform-checkbox"
                        )
                
                # Action buttons
                with Horizontal(classes="button-row"):
                    yield Button("Deploy", id="deploy_btn", classes="dialog-button", variant="primary")
                    yield Button("Cancel", id="cancel_btn", classes="dialog-button")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "quick_deploy_btn":
            self.deploy_quick()
        elif button_id == "deploy_btn":
            self.deploy_selected()
        elif button_id == "cancel_btn":
            self.action_cancel()
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        checkbox_id = event.checkbox.id
        if checkbox_id and checkbox_id.startswith("platform_"):
            platform = checkbox_id.replace("platform_", "")
            if event.value:
                self.manual_selections.add(platform)
            else:
                self.manual_selections.discard(platform)
    
    def on_suggestion_selection_changed(self, event: SuggestionSelectionChanged) -> None:
        """Handle suggestion selection changes."""
        if event.selected:
            if event.index not in self.selected_suggestions:
                self.selected_suggestions.append(event.index)
        else:
            if event.index in self.selected_suggestions:
                self.selected_suggestions.remove(event.index)
    
    def deploy_quick(self) -> None:
        """Deploy using quick deploy option."""
        if self.quick_option:
            self.result = {
                "type": "quick",
                "platforms": self.quick_option["platforms"],
                "server_name": self.server_name
            }
            self.dismiss(self.result)
    
    def deploy_selected(self) -> None:
        """Deploy using selected suggestions and manual selections."""
        # Collect all selected platforms
        all_platforms = set(self.manual_selections)
        
        # Add platforms from selected suggestions
        for suggestion_index in self.selected_suggestions:
            suggestion = self.suggestions[suggestion_index]
            all_platforms.update(suggestion["platforms"])
        
        if not all_platforms:
            # No platforms selected, show error
            self.update_status("Please select at least one platform or suggestion")
            return
        
        self.result = {
            "type": "manual",
            "platforms": list(all_platforms),
            "server_name": self.server_name,
            "used_suggestions": len(self.selected_suggestions) > 0
        }
        self.dismiss(self.result)
    
    def action_cancel(self) -> None:
        """Cancel the deployment dialog."""
        self.result = None
        self.dismiss(self.result)
    
    def action_deploy(self) -> None:
        """Deploy with current selections."""
        self.deploy_selected()
    
    def update_status(self, message: str) -> None:
        """Update status message (placeholder)."""
        # This would be implemented to show status messages
        logger.info(f"Dialog status: {message}")


class BatchDeploymentPlan:
    """Plan for batch deployment with progress tracking."""
    
    def __init__(self, deployments: List[Tuple[str, List[str]]]):
        self.deployments = deployments
        self.total_steps = len(deployments)
        self.current_step = 0
        self.errors: List[str] = []
        self.successes: List[str] = []
    
    def get_progress(self) -> float:
        """Get current progress as percentage."""
        return (self.current_step / self.total_steps * 100) if self.total_steps > 0 else 0
    
    def next_deployment(self) -> Optional[Tuple[str, List[str]]]:
        """Get next deployment in the plan."""
        if self.current_step < len(self.deployments):
            deployment = self.deployments[self.current_step]
            self.current_step += 1
            return deployment
        return None
    
    def record_success(self, server_name: str, platforms: List[str]) -> None:
        """Record successful deployment."""
        self.successes.append(f"{server_name} → {', '.join(platforms)}")
    
    def record_error(self, server_name: str, platforms: List[str], error: str) -> None:
        """Record deployment error."""
        self.errors.append(f"{server_name} → {', '.join(platforms)}: {error}")
    
    def is_complete(self) -> bool:
        """Check if all deployments are complete."""
        return self.current_step >= self.total_steps
    
    def get_summary(self) -> Dict[str, Any]:
        """Get deployment summary."""
        return {
            "total": self.total_steps,
            "completed": self.current_step,
            "successes": len(self.successes),
            "errors": len(self.errors),
            "success_rate": len(self.successes) / self.current_step if self.current_step > 0 else 0,
            "error_details": self.errors,
        }