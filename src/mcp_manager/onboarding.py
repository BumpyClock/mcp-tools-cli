"""Onboarding and First-Time User Guidance System."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Static, Button, Checkbox, ProgressBar
from textual.screen import ModalScreen
from textual.binding import Binding
from textual import events
from typing import Dict, List, Optional, Callable, Any
import json
from pathlib import Path
from datetime import datetime

from .help_content import help_content


class OnboardingStep:
    """Represents a single onboarding step."""
    
    def __init__(self, step_id: str, title: str, description: str, action: Optional[str] = None, 
                 completion_check: Optional[Callable[[], bool]] = None, skippable: bool = True):
        """Initialize onboarding step."""
        self.step_id = step_id
        self.title = title
        self.description = description
        self.action = action
        self.completion_check = completion_check
        self.skippable = skippable
        self.completed = False
    
    def is_completed(self) -> bool:
        """Check if step is completed."""
        if self.completion_check:
            self.completed = self.completion_check()
        return self.completed
    
    def mark_completed(self) -> None:
        """Mark step as completed."""
        self.completed = True


class OnboardingProgress(Static):
    """Progress indicator for onboarding."""
    
    def __init__(self, total_steps: int, **kwargs):
        """Initialize progress indicator."""
        super().__init__("", **kwargs)
        self.total_steps = total_steps
        self.current_step = 0
    
    def update_progress(self, current_step: int, step_title: str = "") -> None:
        """Update progress display."""
        self.current_step = current_step
        progress_text = f"Step {current_step + 1} of {self.total_steps}"
        if step_title:
            progress_text += f": {step_title}"
        
        # Create progress bar visual
        filled = int((current_step / self.total_steps) * 20)
        empty = 20 - filled
        bar = "█" * filled + "░" * empty
        
        self.update(f"{progress_text}\n[{bar}] {int((current_step / self.total_steps) * 100)}%")


class OnboardingModal(ModalScreen):
    """Modal screen for onboarding new users."""
    
    BINDINGS = [
        Binding("escape", "skip_onboarding", "Skip", priority=True),
        Binding("enter", "next_step", "Next", priority=True),
        Binding("ctrl+s", "skip_step", "Skip Step", show=False),
    ]
    
    CSS = """
    OnboardingModal {
        align: center middle;
    }
    
    #onboarding-dialog {
        width: 70%;
        height: 80%;
        border: thick $primary;
        background: $surface;
    }
    
    #onboarding-header {
        dock: top;
        height: 5;
        background: $accent;
        border-bottom: solid $primary;
        padding: 1;
    }
    
    #onboarding-progress {
        height: 4;
        text-align: center;
        margin: 1;
    }
    
    #onboarding-content {
        height: auto;
        padding: 2;
        text-align: center;
    }
    
    #step-title {
        text-style: bold;
        color: $accent;
        text-align: center;
        margin-bottom: 2;
    }
    
    #step-description {
        text-align: left;
        margin-bottom: 2;
        height: auto;
    }
    
    #step-action {
        background: $warning;
        text-align: center;
        padding: 1;
        margin: 2;
        border: solid $accent;
    }
    
    #onboarding-footer {
        dock: bottom;
        height: 4;
        border-top: solid $primary;
        padding: 1;
    }
    
    .onboarding-button {
        margin: 0 1;
    }
    
    .completed-step {
        color: $success;
        text-style: bold;
    }
    
    .current-step {
        background: $accent 20%;
        border: solid $accent;
    }
    """
    
    def __init__(self, app_instance, **kwargs):
        """Initialize onboarding modal."""
        super().__init__(**kwargs)
        self.app_instance = app_instance
        self.steps: List[OnboardingStep] = []
        self.current_step_index = 0
        self.progress_widget: Optional[OnboardingProgress] = None
        self.on_complete_callback: Optional[Callable[[], None]] = None
        self._setup_onboarding_steps()
    
    def _setup_onboarding_steps(self) -> None:
        """Set up the onboarding flow steps."""
        self.steps = [
            OnboardingStep(
                step_id="welcome",
                title="Welcome to MCP Manager!",
                description="""
Welcome to MCP Manager - your central hub for managing Model Context Protocol (MCP) servers!

MCP servers extend Claude's capabilities by providing access to tools, data sources, and external services. This application helps you:

• Configure and manage multiple MCP servers
• Deploy servers to different platforms (Claude Desktop, VS Code, etc.)  
• Monitor server health and performance
• Resolve configuration conflicts
• Batch operations for efficiency

Let's walk through the key features to get you started quickly.
""",
                skippable=False
            ),
            
            OnboardingStep(
                step_id="interface_overview", 
                title="Interface Overview",
                description="""
The MCP Manager interface has two main sections:

🎯 LEFT PANEL - Server Registry:
• Shows all your configured MCP servers
• Add, edit, or remove servers
• Enable/disable servers for deployment
• Select servers for batch operations

🚀 RIGHT PANEL - Deployment Matrix:
• Interactive grid showing server deployment status
• Each cell represents a server on a platform
• Click cells to toggle deployment state
• Visual indicators show status and conflicts

💡 TIP: Use Tab to switch between panels, and check the status bar for keyboard shortcuts!
""",
                action="Press Tab to switch between panels and explore the interface"
            ),
            
            OnboardingStep(
                step_id="add_first_server",
                title="Add Your First Server",
                description="""
Let's add your first MCP server to get started:

1. In the Server Registry (left panel), press 'A' or click "Add"
2. Enter server details:
   • Name: A unique identifier (e.g., "filesystem-tools")
   • Type: Usually "stdio" for most servers
   • Command: Path to server executable
   • Arguments: Command line arguments if needed

3. Enable the server for deployment
4. Save the configuration

Don't have a server ready? You can skip this step and add servers later.
""",
                action="Press 'A' to add a server, or skip if you don't have one ready",
                completion_check=lambda: len(self.app_instance.registry.list_servers()) > 0
            ),
            
            OnboardingStep(
                step_id="deployment_basics",
                title="Understanding Deployments", 
                description="""
Deployment means configuring a server to work with a specific platform:

📱 PLATFORMS (columns in matrix):
• Claude Desktop - The desktop Claude application
• VS Code Continue - Continue extension for VS Code  
• Custom platforms you've configured

🔄 DEPLOYMENT STATES (cell colors):
• ✅ Green - Server is deployed and working
• ❌ Red - Server is not deployed
• 🔄 Yellow - Deployment in progress  
• ⚠️ Orange - Conflicts need resolution

Click any cell to toggle between deployed/not deployed states.
""",
                action="Try clicking cells in the deployment matrix to see how it works"
            ),
            
            OnboardingStep(
                step_id="keyboard_shortcuts",
                title="Keyboard Shortcuts",
                description="""
MCP Manager is designed for keyboard efficiency. Here are the essential shortcuts:

🎯 GLOBAL SHORTCUTS:
• A - Add server          • E - Edit server
• D - Deploy             • R - Refresh  
• H - Health dashboard   • Q - Quit
• V - Switch view        • Tab - Switch panels

⌨️ CONTEXT SHORTCUTS:
Different shortcuts available based on which panel is focused.
The status bar shows current available shortcuts.

🆘 HELP:
• F1 - Full help system  • ? - Quick shortcuts
• Esc - Cancel operation

Try pressing F1 now to explore the full help system!
""",
                action="Press F1 to open help, or ? to see quick shortcuts"
            ),
            
            OnboardingStep(
                step_id="health_monitoring",
                title="Health Monitoring", 
                description="""
Keep your servers healthy with built-in monitoring:

🔍 HEALTH DASHBOARD (Press 'H'):
• Real-time server status monitoring
• Performance metrics and response times
• Error detection and diagnostics
• Historical trends and alerts

📊 HEALTH STATES:
• 🟢 Healthy - Everything working normally
• 🟡 Warning - Minor issues detected
• 🔴 Critical - Immediate attention needed
• ⚫ Offline - Server not responding

🔄 MONITORING OPTIONS:
• Manual health checks (H key or F5)
• Background monitoring (M to toggle)
• Automatic alerts for critical issues
""",
                action="Press 'H' to explore the health dashboard"
            ),
            
            OnboardingStep(
                step_id="batch_operations",
                title="Batch Operations",
                description="""
Save time with batch operations on multiple servers:

✅ SELECTION:
• Use Space bar to select/deselect servers or deployments
• Selected items are highlighted and counted
• Mix and match selections as needed

🚀 BATCH ACTIONS:
• Deploy multiple servers at once
• Run health checks on selected servers
• Undeploy from multiple platforms
• Enable/disable multiple servers

The status bar shows your selection count, and operations display progress bars.
""",
                action="Try using Space to select items, then press D to deploy selected"
            ),
            
            OnboardingStep(
                step_id="completion",
                title="You're Ready to Go!",
                description="""
🎉 Congratulations! You've completed the MCP Manager onboarding!

📚 REMEMBER:
• F1 - Opens comprehensive help anytime
• ? - Shows keyboard shortcuts for current context  
• Status bar - Shows available actions and tips
• Tab - Switches between panels

🚀 NEXT STEPS:
• Add your MCP servers to the registry
• Deploy them to your preferred platforms
• Monitor their health and performance
• Explore advanced features as you need them

The interface is designed to be discoverable - keyboard shortcuts and help are always available when you need them.

Happy server managing! 🎯
""",
                skippable=False
            )
        ]
    
    def compose(self) -> ComposeResult:
        """Compose onboarding modal layout."""
        with Vertical(id="onboarding-dialog"):
            # Header
            with Vertical(id="onboarding-header"):
                yield Static("🚀 Welcome to MCP Manager", classes="section-header")
                self.progress_widget = OnboardingProgress(len(self.steps), id="onboarding-progress")
                yield self.progress_widget
            
            # Content area
            with Vertical(id="onboarding-content"):
                yield Static("", id="step-title")
                yield Static("", id="step-description")
                yield Static("", id="step-action", classes="hidden")
            
            # Footer with navigation
            with Horizontal(id="onboarding-footer"):
                yield Button("⬅️ Previous", id="prev-btn", classes="onboarding-button", disabled=True)
                yield Button("Skip Step", id="skip-btn", classes="onboarding-button")
                yield Button("Next ➡️", id="next-btn", classes="onboarding-button")
                yield Button("Skip All", id="skip-all-btn", classes="onboarding-button")
    
    def on_mount(self) -> None:
        """Initialize onboarding when mounted."""
        self._update_step_display()
    
    def _update_step_display(self) -> None:
        """Update the display for current step."""
        if not (0 <= self.current_step_index < len(self.steps)):
            return
        
        step = self.steps[self.current_step_index]
        
        # Update progress
        if self.progress_widget:
            self.progress_widget.update_progress(self.current_step_index, step.title)
        
        # Update content
        title_widget = self.query_one("#step-title", Static)
        title_widget.update(step.title)
        
        description_widget = self.query_one("#step-description", Static) 
        description_widget.update(step.description)
        
        # Update action if present
        action_widget = self.query_one("#step-action", Static)
        if step.action:
            action_widget.update(f"💡 ACTION: {step.action}")
            action_widget.remove_class("hidden")
        else:
            action_widget.add_class("hidden")
        
        # Update navigation buttons
        prev_btn = self.query_one("#prev-btn", Button)
        next_btn = self.query_one("#next-btn", Button)
        skip_btn = self.query_one("#skip-btn", Button)
        
        prev_btn.disabled = self.current_step_index == 0
        next_btn.disabled = False
        skip_btn.disabled = not step.skippable
        
        # Update next button text for last step
        if self.current_step_index == len(self.steps) - 1:
            next_btn.label = "Finish 🎉"
        else:
            next_btn.label = "Next ➡️"
    
    def action_next_step(self) -> None:
        """Move to next onboarding step."""
        # Mark current step as completed
        if self.current_step_index < len(self.steps):
            self.steps[self.current_step_index].mark_completed()
        
        # Check if this was the last step
        if self.current_step_index >= len(self.steps) - 1:
            self._complete_onboarding()
            return
        
        # Move to next step
        self.current_step_index += 1
        self._update_step_display()
    
    def action_prev_step(self) -> None:
        """Move to previous onboarding step."""
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self._update_step_display()
    
    def action_skip_step(self) -> None:
        """Skip current step if skippable."""
        current_step = self.steps[self.current_step_index]
        if current_step.skippable:
            self.action_next_step()
    
    def action_skip_onboarding(self) -> None:
        """Skip entire onboarding process."""
        self._complete_onboarding(skipped=True)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "next-btn":
            self.action_next_step()
        elif event.button.id == "prev-btn":
            self.action_prev_step()
        elif event.button.id == "skip-btn":
            self.action_skip_step()
        elif event.button.id == "skip-all-btn":
            self.action_skip_onboarding()
    
    def _complete_onboarding(self, skipped: bool = False) -> None:
        """Complete onboarding process."""
        # Mark onboarding as completed in user preferences
        self._save_onboarding_completion()
        
        # Call completion callback if provided
        if self.on_complete_callback:
            self.on_complete_callback()
        
        # Show completion message
        completion_message = "Onboarding skipped" if skipped else "Onboarding completed! Welcome to MCP Manager!"
        if hasattr(self.app_instance, 'update_status'):
            self.app_instance.update_status(completion_message)
        
        # Dismiss modal
        self.dismiss()
    
    def _save_onboarding_completion(self) -> None:
        """Save onboarding completion to user preferences."""
        try:
            # Save to a simple preferences file
            prefs_path = Path.home() / ".claude" / "mcp-manager-prefs.json"
            prefs_path.parent.mkdir(exist_ok=True)
            
            prefs = {}
            if prefs_path.exists():
                with open(prefs_path, 'r') as f:
                    prefs = json.load(f)
            
            prefs['onboarding_completed'] = True
            prefs['onboarding_completed_at'] = datetime.now().isoformat()
            prefs['completed_steps'] = [step.step_id for step in self.steps if step.completed]
            
            with open(prefs_path, 'w') as f:
                json.dump(prefs, f, indent=2)
                
        except Exception as e:
            # Don't fail onboarding if we can't save preferences
            pass


class OnboardingSystem:
    """Manages the onboarding experience for new users."""
    
    def __init__(self, app):
        """Initialize onboarding system."""
        self.app = app
        self.onboarding_completed = self._check_onboarding_status()
        self.feature_discovery_enabled = True
    
    def _check_onboarding_status(self) -> bool:
        """Check if user has completed onboarding."""
        try:
            prefs_path = Path.home() / ".claude" / "mcp-manager-prefs.json"
            if not prefs_path.exists():
                return False
            
            with open(prefs_path, 'r') as f:
                prefs = json.load(f)
                return prefs.get('onboarding_completed', False)
        except Exception:
            return False
    
    def should_show_onboarding(self) -> bool:
        """Determine if onboarding should be shown."""
        return not self.onboarding_completed
    
    def start_onboarding(self, on_complete: Optional[Callable[[], None]] = None) -> None:
        """Start the onboarding process."""
        modal = OnboardingModal(self.app)
        if on_complete:
            modal.on_complete_callback = on_complete
        self.app.push_screen(modal)
    
    def mark_onboarding_completed(self) -> None:
        """Mark onboarding as completed."""
        self.onboarding_completed = True
    
    def show_feature_discovery(self, feature: str, description: str, shortcuts: Dict[str, str] = None) -> None:
        """Show progressive feature discovery."""
        if not self.feature_discovery_enabled:
            return
        
        # For now, show as status message
        # In future, could show as tooltip or overlay
        if hasattr(self.app, 'update_status'):
            shortcut_text = ""
            if shortcuts:
                main_shortcut = list(shortcuts.keys())[0]
                shortcut_text = f" (Press {main_shortcut})"
            
            self.app.update_status(f"💡 New feature available: {feature}{shortcut_text}")
    
    def disable_feature_discovery(self) -> None:
        """Disable feature discovery notifications."""
        self.feature_discovery_enabled = False
    
    def enable_feature_discovery(self) -> None:
        """Enable feature discovery notifications."""
        self.feature_discovery_enabled = True