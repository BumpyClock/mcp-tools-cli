"""Smart Deployment Wizard for MCP Manager."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Center
from textual.widgets import (
    Static, Button, Checkbox, Select, ProgressBar,
    RadioButton, RadioSet, Input, Label, Rule, DataTable, 
)
from textual.screen import Screen
from textual import events
from textual.binding import Binding
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime
import logging

from mcp_manager.user_preferences import UserPreferences, PlatformPreference, DeploymentPattern

logger = logging.getLogger(__name__)


class PlatformSelectionWidget(Static):
    """Widget for selecting platform preferences."""
    
    def __init__(self, platforms: List[PlatformPreference], **kwargs):
        super().__init__(**kwargs)
        self.platforms = platforms
        self.checkboxes: Dict[str, Checkbox] = {}
        self.priority_inputs: Dict[str, Input] = {}
    
    def compose(self) -> ComposeResult:
        """Compose the platform selection widget."""
        yield Static("Configure your preferred MCP platforms:", classes="wizard-subtitle")
        yield Static("Check the platforms you use and set their priority (1=highest):", 
                    classes="wizard-help")
        yield Rule()
        
        with Vertical(classes="platform-list"):
            for platform in self.platforms:
                with Horizontal(classes="platform-row"):
                    checkbox = Checkbox(
                        platform.name.replace("-", " ").title(),
                        value=platform.enabled,
                        id=f"platform_{platform.name}"
                    )
                    self.checkboxes[platform.name] = checkbox
                    yield checkbox
                    
                    priority_input = Input(
                        value=str(platform.priority),
                        placeholder="1",
                        classes="priority-input",
                        id=f"priority_{platform.name}"
                    )
                    self.priority_inputs[platform.name] = priority_input
                    yield Label("Priority:")
                    yield priority_input
    
    def get_platform_preferences(self) -> List[PlatformPreference]:
        """Get the current platform preferences from the widget."""
        preferences = []
        
        for platform in self.platforms:
            checkbox = self.checkboxes[platform.name]
            priority_input = self.priority_inputs[platform.name]
            
            try:
                priority = int(priority_input.value) if priority_input.value else platform.priority
            except ValueError:
                priority = platform.priority
            
            preferences.append(PlatformPreference(
                name=platform.name,
                enabled=checkbox.value,
                priority=priority,
                config_path=platform.config_path,
                last_used=platform.last_used
            ))
        
        return preferences


class QuickSetupWidget(Static):
    """Widget for quick setup options."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setup_type = "recommended"
    
    def compose(self) -> ComposeResult:
        """Compose the quick setup widget."""
        yield Static("Choose your setup preference:", classes="wizard-subtitle")
        
        with Vertical(classes="setup-options"):
            with RadioSet(id="setup_type"):
                yield RadioButton("Recommended (Claude Desktop + Code)", value=True)
                yield RadioButton("Developer (All platforms enabled)")
                yield RadioButton("Minimal (Claude Desktop only)")
                yield RadioButton("Custom (Choose manually)")
    
    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle setup type selection."""
        if event.radio_set.id == "setup_type":
            options = ["recommended", "developer", "minimal", "custom"]
            self.setup_type = options[event.index]


class DeploymentSuggestionWidget(Static):
    """Widget showing deployment suggestions."""
    
    def __init__(self, suggestions: List[DeploymentPattern], **kwargs):
        super().__init__(**kwargs)
        self.suggestions = suggestions
        self.selected_suggestions: List[int] = []
    
    def compose(self) -> ComposeResult:
        """Compose the suggestions widget."""
        if not self.suggestions:
            yield Static("No deployment suggestions available yet.", classes="no-suggestions")
            yield Static("Deploy some servers to start building smart suggestions!", 
                        classes="wizard-help")
            return
        
        yield Static("Smart deployment suggestions based on your history:", 
                    classes="wizard-subtitle")
        
        table = DataTable(id="suggestions_table", show_cursor=True)
        table.add_columns("Server", "Platforms", "Used", "Success", "Select")
        
        for i, suggestion in enumerate(self.suggestions):
            platforms_str = ", ".join(suggestion.platforms[:2])
            if len(suggestion.platforms) > 2:
                platforms_str += f" +{len(suggestion.platforms) - 2} more"
            
            success_pct = f"{suggestion.success_rate * 100:.0f}%"
            select_checkbox = "✓" if i in self.selected_suggestions else "○"
            
            table.add_row(
                suggestion.server_name,
                platforms_str,
                str(suggestion.frequency),
                success_pct,
                select_checkbox,
                key=str(i)
            )
        
        yield table
    
    def toggle_suggestion(self, index: int) -> None:
        """Toggle suggestion selection."""
        if index in self.selected_suggestions:
            self.selected_suggestions.remove(index)
        else:
            self.selected_suggestions.append(index)
    
    def get_selected_patterns(self) -> List[DeploymentPattern]:
        """Get selected deployment patterns."""
        return [self.suggestions[i] for i in self.selected_suggestions]


class BatchDeploymentWidget(Static):
    """Widget for batch deployment progress."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_task = ""
        self.progress = 0
        self.total = 0
        self.errors: List[str] = []
    
    def compose(self) -> ComposeResult:
        """Compose the batch deployment widget."""
        yield Static("Batch Deployment Progress", classes="wizard-subtitle")
        
        yield Static("", id="current_task", classes="current-task")
        yield ProgressBar(total=100, show_eta=True, id="batch_progress")
        yield Static("", id="progress_status", classes="progress-status")
        yield Static("", id="error_list", classes="error-list")
    
    def update_progress(self, current: int, total: int, task: str) -> None:
        """Update deployment progress."""
        self.current_task = task
        self.progress = current
        self.total = total
        
        percentage = (current / total * 100) if total > 0 else 0
        
        self.query_one("#current_task", Static).update(f"Current: {task}")
        self.query_one("#batch_progress", ProgressBar).update(progress=percentage)
        self.query_one("#progress_status", Static).update(f"Progress: {current}/{total} ({percentage:.1f}%)")
    
    def add_error(self, error: str) -> None:
        """Add an error to the error list."""
        self.errors.append(error)
        error_text = "Errors:\n" + "\n".join(f"• {error}" for error in self.errors[-5:])  # Show last 5
        self.query_one("#error_list", Static).update(error_text)


class SetupWizardScreen(Screen):
    """First-time setup wizard screen."""
    
    TITLE = "MCP Manager Setup Wizard"
    
    CSS = """
    SetupWizardScreen {
        align: center middle;
    }
    
    .wizard-container {
        width: 80%;
        max-width: 100;
        border: solid $primary;
        padding: 2;
        background: $surface;
    }
    
    .wizard-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    .wizard-subtitle {
        text-style: bold;
        margin: 1 0;
    }
    
    .wizard-help {
        color: $text-muted;
        margin-bottom: 1;
    }
    
    .platform-row {
        height: 3;
        align: left middle;
        margin: 0 0 1 0;
    }
    
    .platform-row Checkbox {
        width: 30;
    }
    
    .priority-input {
        width: 5;
        margin-left: 2;
    }
    
    .button-row {
        height: 3;
        align: center middle;
        margin-top: 2;
    }
    
    .wizard-button {
        margin: 0 2;
        min-width: 12;
    }
    
    .setup-options {
        margin: 1 0;
    }
    
    .no-suggestions {
        text-align: center;
        color: $text-muted;
        margin: 2 0;
    }
    """
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+c", "cancel", "Cancel", show=False),
    ]
    
    def __init__(self, preferences: UserPreferences, **kwargs):
        super().__init__(**kwargs)
        self.preferences = preferences
        self.current_step = 0
        self.steps = ["welcome", "platforms", "summary"]
        self.platform_widget: Optional[PlatformSelectionWidget] = None
        self.quick_setup_widget: Optional[QuickSetupWidget] = None
        self.selected_platforms: List[PlatformPreference] = []
    
    def compose(self) -> ComposeResult:
        """Compose the setup wizard."""
        with Center():
            with Vertical(classes="wizard-container"):
                yield Static("Welcome to MCP Manager!", classes="wizard-title")
                yield Static("", id="wizard_content")
                
                with Horizontal(classes="button-row"):
                    yield Button("< Back", id="back_btn", classes="wizard-button", disabled=True)
                    yield Button("Next >", id="next_btn", classes="wizard-button")
                    yield Button("Cancel", id="cancel_btn", classes="wizard-button")
    
    def on_mount(self) -> None:
        """Setup wizard when mounted."""
        self.show_current_step()
    
    def show_current_step(self) -> None:
        """Show the current wizard step."""
        step = self.steps[self.current_step]
        content_widget = self.query_one("#wizard_content", Static)
        
        if step == "welcome":
            self.show_welcome_step(content_widget)
        elif step == "platforms":
            self.show_platforms_step(content_widget)
        elif step == "summary":
            self.show_summary_step(content_widget)
        
        # Update button states
        back_btn = self.query_one("#back_btn", Button)
        next_btn = self.query_one("#next_btn", Button)
        
        back_btn.disabled = self.current_step == 0
        
        if self.current_step == len(self.steps) - 1:
            next_btn.label = "Finish"
        else:
            next_btn.label = "Next >"
    
    def show_welcome_step(self, content: Static) -> None:
        """Show welcome step content."""
        welcome_text = """Welcome to MCP Manager!

This setup wizard will help you configure your preferences for managing
MCP (Model Context Protocol) servers across different platforms.

We'll help you:
• Set up your preferred platforms (Claude Desktop, Code, VS Code, etc.)
• Configure smart deployment suggestions
• Enable learning from your usage patterns

This will only take a minute and will make your workflow much more efficient!"""
        
        content.update(welcome_text)
    
    def show_platforms_step(self, content: Static) -> None:
        """Show platform configuration step."""
        if self.platform_widget is None:
            platforms = self.preferences.get_platform_preferences()
            self.platform_widget = PlatformSelectionWidget(platforms)
        
        # Clear and add the platform widget
        content.remove_children()
        content.mount(self.platform_widget)
    
    def show_summary_step(self, content: Static) -> None:
        """Show summary step."""
        if self.platform_widget:
            self.selected_platforms = self.platform_widget.get_platform_preferences()
        
        enabled_platforms = [p for p in self.selected_platforms if p.enabled]
        
        summary_text = f"""Setup Summary

Enabled Platforms ({len(enabled_platforms)}):"""
        
        for platform in sorted(enabled_platforms, key=lambda p: p.priority):
            summary_text += f"\n  {platform.priority}. {platform.name.title()}"
        
        summary_text += f"""

Settings:
• Smart suggestions: Enabled
• Learning from usage: Enabled
• Quick deployment: Enabled

Click 'Finish' to complete the setup and start using MCP Manager!"""
        
        content.update(summary_text)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id
        
        if button_id == "back_btn":
            self.go_back()
        elif button_id == "next_btn":
            self.go_next()
        elif button_id == "cancel_btn":
            self.action_cancel()
    
    def go_back(self) -> None:
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.show_current_step()
    
    def go_next(self) -> None:
        """Go to next step or finish."""
        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.show_current_step()
        else:
            self.finish_setup()
    
    def finish_setup(self) -> None:
        """Finish the setup process."""
        try:
            # Save platform preferences
            if self.platform_widget:
                platforms = self.platform_widget.get_platform_preferences()
                self.preferences.update_platform_preferences(platforms)
            
            # Mark setup as completed
            self.preferences.mark_setup_completed()
            
            self.dismiss({"completed": True})
        except Exception as e:
            logger.error(f"Failed to complete setup: {e}")
            self.dismiss({"completed": False, "error": str(e)})
    
    def action_cancel(self) -> None:
        """Cancel the setup wizard."""
        self.dismiss({"completed": False, "cancelled": True})


class SmartDeploymentWizard:
    """Smart deployment wizard with learning capabilities."""
    
    def __init__(self, preferences: UserPreferences):
        self.preferences = preferences
    
    def should_show_setup_wizard(self) -> bool:
        """Determine if we should show the setup wizard."""
        return not self.preferences.is_setup_completed()
    
    async def run_setup_wizard(self, app) -> Dict[str, Any]:
        """Run the setup wizard."""
        try:
            result = await app.push_screen(SetupWizardScreen(self.preferences))
            return result if result else {"completed": False}
        except Exception as e:
            logger.error(f"Setup wizard failed: {e}")
            return {"completed": False, "error": str(e)}
    
    def get_smart_suggestions(self, server_name: str, available_platforms: List[str]) -> List[Dict[str, Any]]:
        """Get smart deployment suggestions for a server."""
        patterns = self.preferences.get_deployment_suggestions(server_name, limit=5)
        suggestions = []
        
        for pattern in patterns:
            # Filter to only available platforms
            available_pattern_platforms = [p for p in pattern.platforms if p in available_platforms]
            if available_pattern_platforms:
                suggestions.append({
                    "title": f"Deploy to {', '.join(available_pattern_platforms[:2])}" + 
                            (f" +{len(available_pattern_platforms) - 2}" if len(available_pattern_platforms) > 2 else ""),
                    "platforms": available_pattern_platforms,
                    "confidence": pattern.success_rate,
                    "usage": pattern.frequency,
                    "description": f"Used {pattern.frequency} times with {pattern.success_rate*100:.0f}% success rate"
                })
        
        # Add default suggestions if no patterns exist
        if not suggestions and available_platforms:
            enabled_platforms = [p.name for p in self.preferences.get_enabled_platforms()]
            common_platforms = [p for p in enabled_platforms if p in available_platforms][:2]
            
            if common_platforms:
                suggestions.append({
                    "title": f"Deploy to {', '.join(common_platforms)}",
                    "platforms": common_platforms,
                    "confidence": 0.8,
                    "usage": 0,
                    "description": "Your preferred platforms"
                })
        
        return suggestions
    
    def get_quick_deploy_option(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get quick deploy option if available."""
        quick_platforms = self.preferences.get_quick_deploy_targets(server_name)
        if quick_platforms:
            return {
                "title": "Quick Deploy (Usual Places)",
                "platforms": quick_platforms,
                "description": f"Deploy to {', '.join(quick_platforms)} (your usual choice)"
            }
        return None
    
    def record_deployment_choice(self, server_name: str, platforms: List[str], success: bool = True) -> None:
        """Record a deployment choice for learning."""
        self.preferences.record_deployment(server_name, platforms, success)
    
    def get_batch_deployment_plan(self, deployments: List[Tuple[str, List[str]]]) -> List[Dict[str, Any]]:
        """Create an optimized batch deployment plan."""
        plan = []
        
        # Group by platform to minimize context switching
        platform_groups: Dict[str, List[str]] = {}
        
        for server_name, platforms in deployments:
            for platform in platforms:
                if platform not in platform_groups:
                    platform_groups[platform] = []
                platform_groups[platform].append(server_name)
        
        # Create deployment steps
        step_id = 1
        for platform, servers in platform_groups.items():
            for server in servers:
                plan.append({
                    "id": step_id,
                    "server": server,
                    "platform": platform,
                    "description": f"Deploy {server} to {platform}",
                    "estimated_time": 30,  # seconds
                })
                step_id += 1
        
        return plan
    
    def get_deployment_stats(self) -> Dict[str, Any]:
        """Get deployment statistics for the user."""
        return self.preferences.get_stats()
    
    def export_learning_data(self) -> Dict[str, Any]:
        """Export learning data for backup."""
        return {
            "deployment_patterns": self.preferences.preferences.get("deployment_patterns", {}),
            "deployment_history": self.preferences.preferences.get("deployment_history", []),
            "platform_preferences": self.preferences.preferences.get("platforms", {}),
            "exported_at": datetime.now().isoformat(),
        }
    
    def import_learning_data(self, data: Dict[str, Any]) -> None:
        """Import learning data from backup."""
        if "deployment_patterns" in data:
            self.preferences.preferences["deployment_patterns"] = data["deployment_patterns"]
        
        if "deployment_history" in data:
            self.preferences.preferences["deployment_history"] = data["deployment_history"]
        
        if "platform_preferences" in data:
            self.preferences.preferences["platforms"] = data["platform_preferences"]
        
        self.preferences.save_preferences()
    
    def reset_learning_data(self) -> None:
        """Reset all learning data."""
        self.preferences.clear_deployment_history()