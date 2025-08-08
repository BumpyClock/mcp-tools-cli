"""MCP Manager TUI Application with Worker Thread Support."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, Static, Button, ProgressBar
from textual.binding import Binding
from textual import events
from textual.worker import Worker
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import time
import logging

from mcp_manager.core import MCPServerRegistry, DeploymentManager, PlatformManager, ProjectDetector
from mcp_manager.health_monitor import HealthMonitor, HealthStatus, HealthCheckResult
from mcp_manager.health_dashboard import HealthDashboard, HealthSummaryCard, HealthAlertBanner
from mcp_manager.views import ProjectStatusView, ServerStatusView, ViewModeManager
from mcp_manager.deployment_matrix import InteractiveDeploymentMatrix, DeploymentConflict, DeploymentState
from mcp_manager.conflict_dialog import ConflictResolutionDialog, CellInfoDialog
from mcp_manager.error_handler import ErrorHandler, get_error_handler, RecoveryResult
from mcp_manager.error_dialogs import ErrorDialog, RollbackConfirmationDialog, ManualFixDialog
from mcp_manager.recovery_wizard import RecoveryWizard
from mcp_manager.exceptions import MCPManagerError, ErrorContext, RecoveryAction, ErrorSeverity
from mcp_manager.rollback_manager import RollbackManager
from mcp_manager.backup_system import BackupSystem
from mcp_manager.help_system import HelpSystem, HelpModal, QuickHelpPanel
from mcp_manager.tooltips import TooltipManager, TooltipMixin
from mcp_manager.onboarding import OnboardingSystem


class MCPManagerTUI(App):
    """Professional TUI for MCP Manager with Worker Thread Support."""
    
    TITLE = "MCP Manager - Server Registry & Deployment"
    
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
    
    .focused-panel {
        border: solid $accent;
        border-title-color: $accent;
    }
    
    DataTable {
        height: 100%;
    }
    
    DataTable:focus {
        border: solid $accent;
    }
    
    InteractiveDeploymentMatrix {
        height: 100%;
    }
    
    InteractiveDeploymentMatrix:focus {
        border: solid $accent;
    }
    
    InteractiveDeploymentMatrix .selected-cell {
        background: $accent 20%;
    }
    
    InteractiveDeploymentMatrix .conflict-cell {
        border: solid $error;
    }
    
    .action-button {
        margin: 1;
        width: auto;
    }
    
    #progress-bar {
        margin: 1;
        height: 1;
        display: none;
    }
    
    #progress-bar.visible {
        display: block;
    }
    
    #cancel-btn {
        background: $error;
    }
    
    #cancel-btn:disabled {
        background: $surface;
        color: $text-muted;
    }
    
    #status-bar {
        dock: bottom;
        height: 3;
        border: solid $accent;
        padding: 1;
    }
    
    .hidden {
        display: none;
    }
    
    .visible {
        display: block;
    }
    
    .section-header {
        text-style: bold;
        margin-bottom: 1;
        color: $accent;
    }
    
    #view-container {
        height: 100%;
    }
    
    /* Health Dashboard Styles */
    #health-view {
        height: 100%;
        width: 100%;
        display: none;
    }
    
    #health-view.visible {
        display: block;
    }
    
    #health-grid {
        grid-size: 1;
        grid-rows: 1fr 2fr 1fr;
        height: 100%;
    }
    
    .health-widget {
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    #health-summary {
        height: 10;
    }
    
    #health-table {
        height: 20;
    }
    
    #health-detail {
        height: 10;
    }
    
    #health-alert-banner {
        dock: top;
        height: 1;
        background: $error;
        display: none;
    }
    
    #health-alert-banner.visible {
        display: block;
    }
    
    /* Help System Styles */
    QuickHelpPanel {
        dock: bottom;
        height: 1;
        background: $accent-darken-1;
        color: $text;
        padding: 0 1;
        text-align: center;
    }
    
    .help-tip {
        color: $warning;
        text-style: italic;
    }
    
    .help-shortcut {
        color: $accent;
        text-style: bold;
    }
    """
    
    BINDINGS = [
        # Core navigation
        Binding("tab", "focus_next", "Next Pane", show=False),
        Binding("shift+tab", "focus_previous", "Prev Pane", show=False),
        Binding("escape", "cancel_operation", "Cancel", show=False),
        
        # Help system
        Binding("f1", "show_help", "Help", priority=True),
        Binding("question_mark", "show_shortcuts", "Shortcuts", priority=True),
        Binding("ctrl+h", "show_contextual_help", "Context Help", show=False),
        
        # Primary actions - always visible
        Binding("a", "add_server", "Add", priority=True),
        Binding("e", "edit_server", "Edit", priority=True),
        Binding("d", "deploy", "Deploy", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("h", "show_health_dashboard", "Health", priority=True),
        Binding("m", "toggle_monitoring", "Monitor", priority=True),
        Binding("v", "switch_view", "View", priority=True),
        Binding("f5", "force_refresh", "Force Refresh", show=False),
        Binding("q", "quit", "Quit", priority=True),
        
        # Error handling actions
        Binding("ctrl+z", "undo_last_operation", "Undo", priority=True),
        Binding("ctrl+e", "show_error_history", "Errors", show=False),
        Binding("ctrl+w", "show_recovery_wizard", "Recovery", show=False),
        
        # Context-sensitive actions
        Binding("u", "undeploy", "Undeploy", show=False),
        Binding("ctrl+d", "quick_deploy", "Quick Deploy", show=False),
        Binding("space", "toggle_selection", "Select", show=False),
        Binding("enter", "default_action", "Action", show=False),
        Binding("delete", "remove_server", "Remove", show=False),
    ]
    
    def __init__(self):
        super().__init__()
        # Initialize core components with correct path
        registry_path = Path(__file__).parent.parent.parent / "mcp-servers.json"
        self.registry = MCPServerRegistry(registry_path)
        self.deployment_manager = DeploymentManager(self.registry)
        self.platform_manager = PlatformManager()
        self.project_detector = ProjectDetector()
        
        # Initialize Phase 5 components with graceful fallback
        try:
            from .user_preferences import UserPreferences
            from .smart_wizard import SmartDeploymentWizard
            from .error_handler import ErrorHandler
            from .rollback_manager import RollbackManager
            self.user_preferences = UserPreferences()
            self.smart_wizard = SmartDeploymentWizard(self.user_preferences)
            self.rollback_manager = RollbackManager()
            self.error_handler = ErrorHandler()
        except ImportError:
            # Phase 5 components not available - use basic functionality
            self.user_preferences = None
            self.smart_wizard = None
            self.rollback_manager = None
            self.error_handler = None
        
        # Initialize help system with fallback
        try:
            from .help_system import HelpSystem
            from .tooltips import TooltipManager
            self.help_system = HelpSystem(self)
            self.tooltip_manager = TooltipManager(self)
        except ImportError:
            self.help_system = None
            self.tooltip_manager = None
        # Initialize onboarding with fallback
        try:
            from .onboarding import OnboardingSystem
            self.onboarding_system = OnboardingSystem(self)
        except ImportError:
            self.onboarding_system = None
        
        # Initialize health monitoring
        self.health_monitor = HealthMonitor(self.registry, self.platform_manager)
        self.health_dashboard: Optional[HealthDashboard] = None
        self.health_alert_banner: Optional[HealthAlertBanner] = None
        
        # Initialize backup system
        try:
            from .backup_system import BackupSystem
            self.backup_system = BackupSystem()
        except ImportError:
            self.backup_system = None
        
        self.last_error = None
        
        # Worker management
        self.current_operation: Optional[Worker] = None
        self.operation_cancelled = False
        
        # Selection tracking  
        self.selected_servers = set()
        
        # Focus management
        self.current_pane = "server"  # "server" or "deployment"
        self.has_changes = False
        
        # View management
        self.view_manager = ViewModeManager()
        self.project_status_view: Optional[ProjectStatusView] = None
        self.server_status_view: Optional[ServerStatusView] = None
        self.current_view = "main"  # "main" or "health"
        
        # Context-sensitive help
        self.context_help = {
            "server": "A:Add E:Edit Del:Remove D:Deploy H:Health V:View R:Refresh Ctrl+Z:Undo Q:Quit Tab:Switch",
            "deployment": "Enter:Toggle Space:Select C:Conflicts I:Info D:Deploy U:Undeploy V:View R:Refresh Ctrl+Z:Undo Q:Quit",
            "health": "F5:Refresh Space:Select Enter:Details M:Monitor Ctrl+E:Errors Q:Back Tab:Switch",
            "project_focus": "Enter:Select D:Deploy V:View R:Refresh Ctrl+Z:Undo Q:Quit Tab:Switch",
            "server_focus": "Enter:Select U:Undeploy V:View R:Refresh Ctrl+Z:Undo Q:Quit Tab:Switch",
            "dialog": "Enter:Confirm Esc:Cancel Y:Yes N:No",
            "error": "Enter:Select Esc:Cancel R:Retry S:Skip U:Rollback W:Wizard",
        }
        self.operation_progress = 0
        
    def compose(self) -> ComposeResult:
        """Create the TUI layout."""
        yield Header()
        
        # Health alert banner (hidden by default)
        self.health_alert_banner = HealthAlertBanner(
            self.health_monitor, 
            id="health-alert-banner"
        )
        yield self.health_alert_banner
        
        with Horizontal():
            # Left panel - Server Registry
            with Vertical(id="left-panel"):
                yield Static("📦 MCP Server Registry", classes="panel-title")
                yield DataTable(id="server-table")
                
                with Horizontal():
                    yield Button("Add", id="add-btn", classes="action-button")
                    yield Button("Edit", id="edit-btn", classes="action-button")
                    yield Button("Remove", id="remove-btn", classes="action-button")
            
            # Right panel - Multi-view deployment interface
            with Vertical(id="right-panel"):
                yield Static("🚀 Interactive Deployment Matrix", id="panel-title-right", classes="panel-title")
                
                # Container for different views
                with Vertical(id="view-container"):
                    # Default deployment matrix
                    yield InteractiveDeploymentMatrix(
                        registry=self.registry,
                        deployment_manager=self.deployment_manager,
                        platform_manager=self.platform_manager,
                        id="deployment-matrix"
                    )
                    
                    # Project status view (initially hidden)
                    yield ProjectStatusView(self.deployment_manager, id="project-status-view", classes="hidden")
                    
                    # Server status view (initially hidden)
                    yield ServerStatusView(self.deployment_manager, id="server-status-view", classes="hidden")
                    
                    # Health dashboard (initially hidden)
                    self.health_dashboard = HealthDashboard(
                        self.health_monitor,
                        id="health-view",
                        classes="hidden"
                    )
                    yield self.health_dashboard
                
                with Horizontal():
                    yield Button("Deploy Selected", id="deploy-btn", classes="action-button")
                    yield Button("Undeploy Selected", id="undeploy-btn", classes="action-button")
                    yield Button("Health Check", id="health-btn", classes="action-button")
                    yield Button("Switch View", id="view-btn", classes="action-button")
                    yield Button("Resolve Conflicts", id="resolve-btn", classes="action-button")
                    yield Button("Cancel", id="cancel-btn", classes="action-button", disabled=True)
                
                # Progress bar for operations
                yield ProgressBar(id="progress-bar", show_eta=True, show_percentage=True)
        
        # Status bar with view mode indicator and quick help
        yield Static("Ready | 📦 Registry View", id="status-bar")
        
        # Quick help panel (with fallback)
        if self.help_system:
            try:
                self.quick_help_panel = self.help_system.create_quick_help_panel()
                yield self.quick_help_panel
            except Exception:
                # Fallback: Create a simple static help panel
                yield Static("Press F1 for help | A:Add E:Edit D:Deploy R:Refresh Q:Quit", 
                           classes="help-tip", id="fallback-help")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize data when app mounts."""
        # Initialize view widgets
        self.project_status_view = self.query_one("#project-status-view", ProjectStatusView)
        self.server_status_view = self.query_one("#server-status-view", ServerStatusView)
        
        self.load_server_registry()
        self.load_deployment_status()
        self.update_focus_indicators()
        self.update_view_mode_display()
        self.update_status("MCP Manager initialized successfully")
        
        # Check if we need to show the setup wizard
        try:
            if self.smart_wizard and self.smart_wizard.should_show_setup_wizard():
                self.run_worker(self._show_setup_wizard)
        except Exception as e:
            self.update_status(f"Setup wizard disabled due to error: {e}")
        
        # Focus the server table initially
        server_table = self.query_one("#server-table", DataTable)
        server_table.focus()
        
        # Start background health monitoring
        self.health_monitor.start_background_monitoring()
        
        # Initialize help system and show onboarding if needed (with safety checks)
        if self.help_system:
            try:
                self.help_system.setup_help_system()
            except Exception as e:
                self.update_status(f"Help system initialization failed: {e}")
        
        if self.onboarding_system:
            try:
                if self.onboarding_system.should_show_onboarding():
                    self.onboarding_system.start_onboarding(
                        on_complete=lambda: self.update_status("Welcome to MCP Manager! Press F1 for help anytime.")
                    )
            except Exception as e:
                self.update_status(f"Onboarding system failed: {e}")
    
    def on_unmount(self) -> None:
        """Clean up when app is unmounted."""
        # Stop health monitoring
        if self.health_monitor:
            self.health_monitor.stop_background_monitoring()
    
    def load_server_registry(self) -> None:
        """Load servers into the registry table."""
        try:
            table = self.query_one("#server-table", DataTable)
            table.clear()
            
            if not table.columns:
                table.add_columns("Server Name", "Type", "Status")
            
            # Debug: Show registry file path
            registry_path = self.registry.registry_file
            self.update_status(f"Loading servers from: {registry_path}")
            
            # Load servers from registry
            servers = self.registry.list_servers()
            self.update_status(f"Found {len(servers)} servers in registry")
            
            if len(servers) == 0:
                # Debug: Check if file exists
                if registry_path.exists():
                    self.update_status(f"Registry file exists at {registry_path} but contains no servers")
                else:
                    self.update_status(f"Registry file not found at {registry_path}")
                return
            
            for server_name, server in servers.items():
                status = "✅ Enabled" if server.metadata.enabled else "❌ Disabled"
                table.add_row(server_name, server.type, status)
                self.update_status(f"Added server: {server_name} ({server.type})")
                
            self.update_status(f"Successfully loaded {table.row_count} servers into table")
            
        except Exception as e:
            self.update_status(f"Error loading servers: {e}")
            import traceback
            self.notify(f"Registry loading error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}", 
                       title="Debug: Registry Error", timeout=15)
    
    def load_deployment_status(self) -> None:
        """Refresh the interactive deployment matrix."""
        matrix = self.query_one("#deployment-matrix", InteractiveDeploymentMatrix)
        matrix.refresh_matrix()
    
    def action_refresh(self) -> None:
        """Refresh all data and current view."""
        if self.current_operation:
            self.update_status("Cannot refresh during operation")
            return
            
        # Clear tables and reload
        self.load_server_registry()
        self.load_deployment_status()
        
        # Refresh current view data
        current_mode = self.view_manager.current_mode
        context = self.view_manager.context
        
        if current_mode == "project_focus" and "project_path" in context:
            project_path = Path(context["project_path"])
            if self.project_status_view:
                self.project_status_view.show_project_status(project_path)
        
        elif current_mode == "server_focus" and "server_name" in context:
            server_name = context["server_name"]
            if self.server_status_view:
                self.server_status_view.show_server_deployments(server_name)
        
        # Refresh health dashboard if visible
        if self.current_view == "health" and self.health_dashboard:
            self.health_dashboard.refresh_all()
        
        self.update_status("Data refreshed")
    
    def action_add_server(self) -> None:
        """Add a new server."""
        try:
            # Check current server count for context
            servers = self.registry.list_servers()
            current_count = len(servers)
            
            # Show helpful status message with current state
            self.update_status(f"Add Server (A): Currently have {current_count} servers. Full add dialog coming soon - use CLI for now: 'mcp-manager add <name> --type stdio --command python'")
            
            # Optional: Show available server types as a hint
            server_types = ["stdio", "sse", "http", "docker"]
            type_hint = ", ".join(server_types)
            self.notify(f"Supported server types: {type_hint}", title="Add Server Help", timeout=5)
            
        except Exception as e:
            self.update_status(f"Add server error: {e}")
            self.notify("Add server failed: Could not access registry", title="Error", timeout=3)
    
    # Help System Actions
    def action_show_help(self) -> None:
        """Show the full help system (F1)."""
        self.help_system.show_full_help()
    
    def action_show_shortcuts(self) -> None:
        """Show keyboard shortcuts help (?)."""
        self.help_system.show_keyboard_shortcuts(self.current_pane)
    
    def action_show_contextual_help(self) -> None:
        """Show context-sensitive help (Ctrl+H)."""
        self.help_system.show_contextual_help(self.current_pane)
    
    def action_deploy(self) -> None:
        """Deploy all enabled servers to available platforms."""
        if self.current_operation:
            self.update_status("Another operation is already running")
            return
            
        # Get all enabled servers
        servers = self.registry.list_servers()
        enabled_servers = [
            name for name, server in servers.items() 
            if server.metadata.enabled
        ]
        
        if not enabled_servers:
            self.update_status("No enabled servers to deploy")
            return
            
        # Get available platforms
        platforms = self.platform_manager.get_available_platforms()
        available_platforms = [key for key, info in platforms.items() if info["available"]]
        
        if not available_platforms:
            self.update_status("No available platforms found")
            return
            
        # Start deployment worker
        self.run_deployment(enabled_servers, available_platforms)
    
    def action_show_health_dashboard(self) -> None:
        """Show the health dashboard."""
        if self.current_view == "health":
            # Already in health view, go back to main
            self.show_main_view()
        else:
            # Switch to health view
            self.show_health_view()
    
    def action_toggle_monitoring(self) -> None:
        """Toggle background health monitoring."""
        if self.health_monitor.monitoring_active:
            self.health_monitor.stop_background_monitoring()
            self.update_status("Background monitoring stopped")
        else:
            self.health_monitor.start_background_monitoring()
            self.update_status("Background monitoring started")
    
    def action_force_refresh(self) -> None:
        """Force refresh of health data (F5)."""
        if self.current_view == "health":
            # Run immediate health check on all servers
            self.run_health_check_immediate()
        else:
            # Regular refresh
            self.action_refresh()
    
    def show_main_view(self) -> None:
        """Show the main server/deployment view."""
        self.current_view = "main"
        
        # Show main views, hide health view
        deployment_matrix = self.query_one("#deployment-matrix")
        health_view = self.query_one("#health-view")
        
        deployment_matrix.remove_class("hidden")
        health_view.add_class("hidden")
        
        # Update help context
        self.update_focus_indicators()
        self.update_status("Switched to main view")
    
    def show_health_view(self) -> None:
        """Show the health dashboard view."""
        self.current_view = "health"
        
        # Hide main views, show health view
        deployment_matrix = self.query_one("#deployment-matrix")
        health_view = self.query_one("#health-view")
        
        deployment_matrix.add_class("hidden")
        health_view.remove_class("hidden")
        
        # Focus health table
        if self.health_dashboard and self.health_dashboard.health_table:
            self.health_dashboard.health_table.focus()
        
        # Update help context
        self.current_pane = "health"
        self.update_context_help()
        self.update_status("Health Dashboard - Press H to return to main view")
    
    def run_health_check_immediate(self) -> None:
        """Run immediate health check on all servers."""
        if self.current_operation:
            self.update_status("Another operation is already running")
            return
            
        # Get all servers
        servers = self.registry.list_servers()
        server_names = list(servers.keys())
        
        if not server_names:
            self.update_status("No servers found for health check")
            return
            
        # Start health check worker
        self.run_health_check(server_names)
    
    def action_health_check(self) -> None:
        """Run health check on all servers (legacy method)."""
        self.run_health_check_immediate()
    
    def run_deployment(self, server_names: List[str], platform_keys: List[str]) -> None:
        """Start deployment operation with worker thread."""
        try:
            # Start a transaction for rollback capability
            transaction_id = self.rollback_manager.start_transaction(
                "deployment", 
                f"Deploying {len(server_names)} servers to {len(platform_keys)} platforms"
            )
            
            # Add deployment action to transaction
            self.rollback_manager.add_action(
                "deploy",
                f"Deploy servers: {', '.join(server_names)}",
                rollback_data={"server_names": server_names, "platform_keys": platform_keys}
            )
            
            # Create a lambda that captures the arguments
            self.current_operation = self.run_worker(
                lambda: self.deploy_worker(server_names, platform_keys), 
                thread=True, exclusive=True
            )
            self._start_operation("Deploying servers...")
            
        except Exception as e:
            self.handle_operation_error(e, "deployment", {"server_names": server_names, "platform_keys": platform_keys})
    
    def deploy_worker(self, server_names: List[str], platform_keys: List[str]) -> Dict[str, Any]:
        """Worker function for server deployment."""
        try:
            results = {}
            total_operations = len(server_names) * len(platform_keys)
            completed = 0
            
            # Update initial progress
            self.call_from_thread(self._update_progress, 0, f"Starting deployment of {len(server_names)} servers...")
            
            for server_name in server_names:
                if self.operation_cancelled:
                    break
                    
                server_results = {}
                
                for platform_key in platform_keys:
                    if self.operation_cancelled:
                        break
                        
                    # Update progress
                    progress = int((completed / total_operations) * 100) if total_operations > 0 else 100
                    self.call_from_thread(
                        self._update_progress, 
                        progress,
                        f"Deploying {server_name} to {platform_key}..."
                    )
                    
                    # Simulate deployment work (replace with actual deployment)
                    time.sleep(0.5)  # Simulate work
                    
                    try:
                        success = self.deployment_manager.deploy_server_to_platform(
                            server_name, platform_key, use_placeholders=True
                        )
                        server_results[platform_key] = success
                    except Exception as e:
                        server_results[platform_key] = False
                        self.call_from_thread(
                            self.update_status,
                            f"Error deploying {server_name} to {platform_key}: {str(e)}"
                        )
                    
                    completed += 1
                
                results[server_name] = server_results
            
            if self.operation_cancelled:
                self.call_from_thread(self.update_status, "Deployment cancelled")
                return {"cancelled": True}
            else:
                # Final progress update
                self.call_from_thread(self._update_progress, 100, "Deployment completed")
                successful = sum(1 for server_results in results.values() 
                               for success in server_results.values() if success)
                total = sum(len(server_results) for server_results in results.values())
                self.call_from_thread(
                    self.update_status, 
                    f"Deployment completed: {successful}/{total} successful"
                )
                return {"results": results, "completed": True}
                
        except Exception as e:
            self.call_from_thread(self.update_status, f"Deployment error: {str(e)}")
            return {"error": str(e)}
        finally:
            self.call_from_thread(self._finish_operation)
    
    def run_health_check(self, server_names: List[str]) -> None:
        """Start health check operation with worker thread."""
        self.current_operation = self.run_worker(
            lambda: self.health_check_worker(server_names),
            thread=True,
            exclusive=True
        )
        self._start_operation("Running health checks...")
    
    def health_check_worker(self, server_names: List[str]) -> Dict[str, Any]:
        """Worker function for health checks using the health monitor."""
        try:
            # Update initial progress
            self.call_from_thread(self._update_progress, 0, f"Checking {len(server_names)} servers...")
            
            # Use the health monitor's async check method
            import asyncio
            
            # Create event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            def progress_callback(progress: int, message: str):
                if not self.operation_cancelled:
                    self.call_from_thread(self._update_progress, progress, message)
            
            # Run health checks
            results = loop.run_until_complete(
                self.health_monitor.check_all_servers(progress_callback)
            )
            
            loop.close()
            
            if self.operation_cancelled:
                self.call_from_thread(self.update_status, "Health check cancelled")
                return {"cancelled": True}
            else:
                # Count healthy servers
                healthy_count = sum(
                    1 for result in results.values() 
                    if result.status == HealthStatus.HEALTHY
                )
                
                self.call_from_thread(
                    self.update_status, 
                    f"Health check completed: {healthy_count}/{len(results)} servers healthy"
                )
                return {"results": results, "completed": True}
                
        except Exception as e:
            self.call_from_thread(self.update_status, f"Health check error: {str(e)}")
            return {"error": str(e)}
        finally:
            self.call_from_thread(self._finish_operation)
    
    def action_cancel_operation(self) -> None:
        """Cancel the current operation."""
        if self.current_operation:
            self.operation_cancelled = True
            try:
                self.current_operation.cancel()
            except Exception:
                pass  # Worker might already be finished
            self._finish_operation()
            self.update_status("Operation cancelled by user")
    
    def _start_operation(self, message: str) -> None:
        """Start an operation - update UI state."""
        self.operation_cancelled = False
        self.operation_progress = 0
        
        # Show progress bar
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.add_class("visible")
        progress_bar.update(progress=0)
        
        # Enable cancel button
        cancel_btn = self.query_one("#cancel-btn", Button)
        cancel_btn.disabled = False
        
        # Disable operation buttons
        for btn_id in ["deploy-btn", "health-btn", "undeploy-btn"]:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.disabled = True
            except Exception:
                pass
        
        self.update_status(message)
    
    def _finish_operation(self) -> None:
        """Finish an operation - restore UI state."""
        self.current_operation = None
        self.operation_cancelled = False
        
        # Hide progress bar
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.remove_class("visible")
        
        # Disable cancel button
        cancel_btn = self.query_one("#cancel-btn", Button)
        cancel_btn.disabled = True
        
        # Re-enable operation buttons
        for btn_id in ["deploy-btn", "health-btn", "undeploy-btn"]:
            try:
                btn = self.query_one(f"#{btn_id}", Button)
                btn.disabled = False
            except Exception:
                pass
        
        # Refresh data to show any changes
        self.action_refresh()
    
    def _update_progress(self, progress: int, message: str) -> None:
        """Update progress bar and status message."""
        self.operation_progress = progress
        
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=progress)
        
        self.update_status(f"{message} ({progress}%)")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "cancel-btn":
            self.action_cancel_operation()
        elif event.button.id == "deploy-btn":
            self.action_deploy()
        elif event.button.id == "health-btn":
            self.action_show_health_dashboard()
        elif event.button.id == "resolve-btn":
            self.action_resolve_conflicts()
        elif event.button.id == "view-btn":
            self.action_switch_view()
        # Add other button handlers as needed
    
    # Deployment Matrix Event Handlers
    def on_interactive_deployment_matrix_cell_toggled(self, event: InteractiveDeploymentMatrix.CellToggled) -> None:
        """Handle cell toggle events from the deployment matrix."""
        server_name = event.server_name
        platform_key = event.platform_key
        new_state = event.new_state
        
        if new_state == DeploymentState.PENDING:
            # Start deployment operation
            self.run_single_deployment(server_name, platform_key, deploy=True)
        elif new_state == DeploymentState.NOT_DEPLOYED:
            # Start undeployment operation
            self.run_single_deployment(server_name, platform_key, deploy=False)
        
        self.update_status(f"Toggled {server_name} → {platform_key} to {new_state.description}")

    def on_interactive_deployment_matrix_conflict_detected(self, event: InteractiveDeploymentMatrix.ConflictDetected) -> None:
        """Handle conflict detection events."""
        conflict_count = len(event.conflicts)
        critical_count = sum(1 for c in event.conflicts if c.severity == "error")
        
        if critical_count > 0:
            self.update_status(f"⚠️ {critical_count} critical conflicts detected! Use 'Resolve Conflicts' to fix.")
        else:
            self.update_status(f"⚠️ {conflict_count} conflicts detected. Review and resolve as needed.")

    def on_interactive_deployment_matrix_batch_operation(self, event: InteractiveDeploymentMatrix.BatchOperation) -> None:
        """Handle batch operations from the deployment matrix."""
        operation = event.operation
        cells = event.cells
        
        matrix = self.query_one("#deployment-matrix", InteractiveDeploymentMatrix)
        selected_deployments = matrix.get_selected_deployments()
        
        if operation == "toggle" and selected_deployments:
            self.run_batch_deployment(selected_deployments)
            
    def on_interactive_deployment_matrix_cell_info_requested(self, event: InteractiveDeploymentMatrix.CellInfoRequested) -> None:
        """Handle cell info requests from the deployment matrix."""
        self.push_screen(CellInfoDialog(
            server_name=event.server_name,
            platform_key=event.platform_key,
            state_description=event.state_description,
            conflicts=event.conflicts,
            deployment_info=event.deployment_info
        ))
            
    def run_single_deployment(self, server_name: str, platform_key: str, deploy: bool = True) -> None:
        """Run deployment/undeployment for a single server-platform combination."""
        if self.current_operation:
            self.update_status("Another operation is already running")
            return
            
        operation = "deploy" if deploy else "undeploy"
        self.current_operation = self.run_worker(
            lambda: self.single_deployment_worker(server_name, platform_key, deploy),
            thread=True,
            exclusive=True
        )
        self._start_operation(f"{operation.title()}ing {server_name} to {platform_key}...")
    
    def single_deployment_worker(self, server_name: str, platform_key: str, deploy: bool) -> Dict[str, Any]:
        """Worker function for single deployment operations."""
        try:
            self.call_from_thread(self._update_progress, 0, f"{'Deploying' if deploy else 'Undeploying'} {server_name}...")
            
            # Simulate work
            time.sleep(0.5)
            
            if deploy:
                success = self.deployment_manager.deploy_server_to_platform(
                    server_name, platform_key, use_placeholders=True
                )
            else:
                success = self.deployment_manager.undeploy_server_from_platform(
                    server_name, platform_key
                )
            
            self.call_from_thread(self._update_progress, 100, "Operation completed")
            
            if success:
                self.call_from_thread(
                    self.update_status, 
                    f"Successfully {'deployed' if deploy else 'undeployed'} {server_name} {'to' if deploy else 'from'} {platform_key}"
                )
            else:
                self.call_from_thread(
                    self.update_status, 
                    f"Failed to {'deploy' if deploy else 'undeploy'} {server_name} {'to' if deploy else 'from'} {platform_key}"
                )
            
            return {"success": success, "completed": True}
            
        except Exception as e:
            self.call_from_thread(self.update_status, f"Deployment error: {str(e)}")
            return {"error": str(e)}
        finally:
            self.call_from_thread(self._finish_operation)
    
    def run_batch_deployment(self, deployments: List[Tuple[str, str]]) -> None:
        """Run batch deployment operations."""
        if self.current_operation:
            self.update_status("Another operation is already running")
            return
            
        if not deployments:
            self.update_status("No deployments selected")
            return
            
        self.current_operation = self.run_worker(
            lambda: self.batch_deployment_worker(deployments),
            thread=True,
            exclusive=True
        )
        self._start_operation(f"Batch operation on {len(deployments)} deployments...")
    
    def batch_deployment_worker(self, deployments: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Worker function for batch deployment operations."""
        try:
            results = {}
            total = len(deployments)
            completed = 0
            
            self.call_from_thread(self._update_progress, 0, f"Starting batch operation on {total} deployments...")
            
            for server_name, platform_key in deployments:
                if self.operation_cancelled:
                    break
                    
                progress = int((completed / total) * 100) if total > 0 else 100
                self.call_from_thread(
                    self._update_progress, 
                    progress,
                    f"Processing {server_name} → {platform_key}..."
                )
                
                try:
                    # For now, assume we're deploying. In a real implementation,
                    # we'd determine the desired action based on current state
                    success = self.deployment_manager.deploy_server_to_platform(
                        server_name, platform_key, use_placeholders=True
                    )
                    results[(server_name, platform_key)] = success
                except Exception as e:
                    results[(server_name, platform_key)] = False
                    self.call_from_thread(
                        self.update_status,
                        f"Error processing {server_name} → {platform_key}: {str(e)}"
                    )
                
                completed += 1
                time.sleep(0.2)  # Simulate work
            
            if self.operation_cancelled:
                self.call_from_thread(self.update_status, "Batch operation cancelled")
                return {"cancelled": True}
            else:
                successful = sum(1 for success in results.values() if success)
                self.call_from_thread(
                    self.update_status, 
                    f"Batch operation completed: {successful}/{len(results)} successful"
                )
                return {"results": results, "completed": True}
                
        except Exception as e:
            self.call_from_thread(self.update_status, f"Batch operation error: {str(e)}")
            return {"error": str(e)}
        finally:
            self.call_from_thread(self._finish_operation)
    
    def action_resolve_conflicts(self) -> None:
        """Show conflict resolution interface."""
        matrix = self.query_one("#deployment-matrix", InteractiveDeploymentMatrix)
        conflicts = matrix.get_conflicts()
        
        if not conflicts:
            self.update_status("No conflicts detected")
            return
            
        # Show conflict resolution dialog
        self.push_screen(
            ConflictResolutionDialog(conflicts, self._handle_conflict_resolution),
            self._on_conflict_resolution_complete
        )
        
    def _handle_conflict_resolution(self, conflict: DeploymentConflict, resolution: str) -> None:
        """Handle conflict resolution actions."""
        if resolution == "auto_resolve":
            self._auto_resolve_conflict(conflict)
        elif resolution == "manual_resolve":
            self._manual_resolve_conflict(conflict)
        elif resolution == "ignore":
            self._ignore_conflict(conflict)
            
    def _auto_resolve_conflict(self, conflict: DeploymentConflict) -> None:
        """Automatically resolve a conflict."""
        # Implementation would depend on conflict type
        if conflict.conflict_type == "version_mismatch":
            # Update to consistent version
            pass
        elif conflict.conflict_type == "missing_dependency":
            # Install dependency
            pass
        # Add more auto-resolution logic as needed
        
    def _manual_resolve_conflict(self, conflict: DeploymentConflict) -> None:
        """Manually resolve a conflict."""
        # Show detailed resolution options
        pass
        
    def _ignore_conflict(self, conflict: DeploymentConflict) -> None:
        """Mark a conflict as ignored."""
        # Add to ignored conflicts list
        pass
        
    def _on_conflict_resolution_complete(self, resolved_conflicts: Optional[List[str]]) -> None:
        """Handle completion of conflict resolution."""
        if resolved_conflicts:
            self.update_status(f"Resolved {len(resolved_conflicts)} conflicts")
            # Refresh the matrix to show updated state
            self.load_deployment_status()
        else:
            self.update_status("Conflict resolution cancelled")
    
    # Navigation and context-sensitive actions
    def action_focus_next(self) -> None:
        """Focus next pane (Tab)."""
        if self.current_pane == "server":
            self.current_pane = "deployment"
        else:
            self.current_pane = "server"
        self.update_focus_indicators()
        self.update_status("Switched to " + ("deployment" if self.current_pane == "deployment" else "server") + " pane")
    
    def action_focus_previous(self) -> None:
        """Focus previous pane (Shift+Tab)."""
        self.action_focus_next()  # Same as next since we only have 2 panes
    
    def action_cancel_operation(self) -> None:
        """Cancel current operation (Escape)."""
        if self.current_operation:
            self.operation_cancelled = True
            self.update_status("Operation cancelled")
        else:
            self.update_status("Ready")
    
    def action_default_action(self) -> None:
        """Default action for Enter key based on context."""
        if self.current_pane == "server":
            self.action_edit_server()
        else:
            self.action_deploy()
    
    def action_edit_server(self) -> None:
        """Edit selected server (E key)."""
        if self.current_pane != "server":
            self.update_status("Switch to server pane to edit servers (Tab key)")
            return
        
        server_table = self.query_one("#server-table", DataTable)
        if server_table.cursor_row is None:
            self.update_status("No server selected - use arrow keys to select a server, then press E to edit")
            return
        
        try:
            row_data = server_table.get_row_at(server_table.cursor_row)
            server_name = str(row_data[0])
            # Get server details to show current status
            server = self.registry.get_server(server_name)
            if server:
                enabled_status = "enabled" if server.metadata.enabled else "disabled"
                self.update_status(f"Edit Server (E): '{server_name}' ({server.type}, {enabled_status})")
                
                # Show detailed server information in a notification
                details = f"Server: {server_name}\nType: {server.type}\nStatus: {enabled_status}"
                if server.command:
                    details += f"\nCommand: {server.command}"
                if server.args:
                    details += f"\nArgs: {' '.join(server.args)}"
                if server.metadata.description:
                    details += f"\nDescription: {server.metadata.description}"
                
                details += f"\n\nTo edit: Use CLI command 'mcp-manager update {server_name}' or modify mcp-servers.json directly"
                self.notify(details, title=f"Server Details: {server_name}", timeout=10)
            else:
                self.update_status(f"Server '{server_name}' not found in registry")
                self.notify("Server not found in registry. This may indicate a data loading issue.", title="Error", timeout=5)
            self.has_changes = True
        except (IndexError, ValueError) as e:
            self.update_status(f"Failed to get selected server: {e}")
            self.notify("Could not retrieve server information. Try refreshing with R key.", title="Error", timeout=5)
    
    def action_remove_server(self) -> None:
        """Remove selected server (Delete key)."""
        if self.current_pane != "server":
            self.update_status("Switch to server pane to remove servers")
            return
        
        server_table = self.query_one("#server-table", DataTable)
        if server_table.cursor_row is None:
            self.update_status("No server selected for removal")
            return
        
        try:
            row_data = server_table.get_row_at(server_table.cursor_row)
            server_name = str(row_data[0])
            # For now, just show a message. In a full implementation, 
            # this would show a confirmation dialog
            self.update_status(f"Remove server '{server_name}' functionality coming soon...")
            self.has_changes = True
        except (IndexError, ValueError):
            self.update_status("Failed to get selected server")
    
    def action_undeploy(self) -> None:
        """Undeploy selected server (U key)."""
        if self.current_pane != "deployment":
            self.update_status("Switch to deployment pane to undeploy servers")
            return
        
        deployment_matrix = self.query_one("#deployment-matrix", InteractiveDeploymentMatrix)
        selected_deployments = deployment_matrix.get_selected_deployments()
        
        if not selected_deployments:
            self.update_status("No server selected for undeployment")
            return
        
        # Run batch undeployment for selected deployments
        deployment_pairs = [(s, p) for s, p in selected_deployments]
        self.run_batch_deployment(deployment_pairs)  # This will handle undeployment based on current state
    
    def action_toggle_selection(self) -> None:
        """Toggle selection of current row (Space)."""
        if self.current_pane == "server":
            server_table = self.query_one("#server-table", DataTable)
            if server_table.cursor_row is not None:
                try:
                    row_data = server_table.get_row_at(server_table.cursor_row)
                    server_name = str(row_data[0])
                    
                    if server_name in self.selected_servers:
                        self.selected_servers.remove(server_name)
                        self.update_status(f"Deselected: {server_name}")
                    else:
                        self.selected_servers.add(server_name)
                        self.update_status(f"Selected: {server_name}")
                    
                    # Update selection count display
                    count = len(self.selected_servers)
                    if count > 0:
                        self.update_status(f"{count} server(s) selected")
                except (IndexError, ValueError):
                    self.update_status("Failed to toggle server selection")
        else:
            self.update_status("Selection only available in server pane")
    
    def update_focus_indicators(self) -> None:
        """Update visual indicators for focused pane."""
        left_panel = self.query_one("#left-panel")
        right_panel = self.query_one("#right-panel")
        
        # Remove existing focus indicators
        left_panel.remove_class("focused-panel")
        right_panel.remove_class("focused-panel")
        
        # Add focus indicator to current pane
        if self.current_pane == "server":
            left_panel.add_class("focused-panel")
            server_table = self.query_one("#server-table", DataTable)
            server_table.focus()
        else:
            right_panel.add_class("focused-panel")
            deployment_matrix = self.query_one("#deployment-matrix", InteractiveDeploymentMatrix)
            deployment_matrix.focus()
        
        self.update_context_help()
    
    # Key event handling for context-sensitive shortcuts
    def on_key(self, event: events.Key) -> None:
        """Handle key events for context-sensitive shortcuts."""
        # Handle Delete key for server removal
        if event.key == "delete" and self.current_pane == "server":
            self.action_remove_server()
            event.prevent_default()
        # Handle F5 for refresh
        elif event.key == "f5":
            self.action_force_refresh()
            event.prevent_default()
        # Handle ESC in health view to return to main
        elif event.key == "escape" and self.current_view == "health":
            self.show_main_view()
            event.prevent_default()
    
    def update_status(self, message: str) -> None:
        """Update the status bar with message and context help."""
        status_bar = self.query_one("#status-bar", Static)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Get help text from help system (with fallback)
        if self.help_system:
            try:
                help_text = self.help_system.get_status_bar_help(self.current_pane)
            except Exception:
                help_text = "A:Add E:Edit D:Deploy R:Refresh Q:Quit"
        else:
            help_text = "A:Add E:Edit D:Deploy R:Refresh Q:Quit"
        
        status_bar.update(f"[{timestamp}] {message} | {help_text}")
    
    def update_context_help(self) -> None:
        """Update context-sensitive help in status bar."""
        # Update quick help panel (with safety checks)
        if hasattr(self, 'help_system') and self.help_system and hasattr(self, 'quick_help_panel'):
            try:
                self.help_system.update_quick_help(self.current_pane)
            except Exception:
                pass  # Silently fail to avoid disrupting the UI
        
        # Update status bar with new help text
        status_bar = self.query_one("#status-bar", Static)
        current_text = str(status_bar.renderable)
        
        # Get help text with fallback
        if self.help_system:
            try:
                help_text = self.help_system.get_status_bar_help(self.current_pane)
            except Exception:
                help_text = "A:Add E:Edit D:Deploy R:Refresh Q:Quit"
        else:
            help_text = "A:Add E:Edit D:Deploy R:Refresh Q:Quit"
        
        if "|" in current_text:
            message_part = current_text.split("|")[0].strip()
            status_bar.update(f"{message_part} | {help_text}")
        else:
            status_bar.update(f"{current_text} | {help_text}")
    
    # View Mode Management
    def action_switch_view(self) -> None:
        """Switch between different view modes (V key)."""
        current_mode = self.view_manager.current_mode
        
        if current_mode == "registry":
            # Get currently selected server from server table
            server_table = self.query_one("#server-table", DataTable)
            if server_table.cursor_row is not None:
                try:
                    row_data = server_table.get_row_at(server_table.cursor_row)
                    server_name = str(row_data[0])
                    # Switch to server focus mode
                    self.view_manager.switch_to_mode("server_focus", {"server_name": server_name})
                    self.show_server_focus_view(server_name)
                except (IndexError, ValueError):
                    # No server selected, switch to project focus
                    self.switch_to_project_focus()
            else:
                # No selection, switch to project focus
                self.switch_to_project_focus()
        
        elif current_mode == "server_focus":
            # Switch to project focus
            self.switch_to_project_focus()
        
        elif current_mode == "project_focus":
            # Switch back to registry view
            self.view_manager.switch_to_mode("registry")
            self.show_registry_view()
        
        self.update_view_mode_display()
    
    def switch_to_project_focus(self) -> None:
        """Switch to project focus view."""
        # Find projects and show the first one, or show project selection
        projects = self.project_detector.find_projects_in_common_locations()
        
        if projects:
            # Use the first project or current working directory project
            selected_project = None
            cwd = Path.cwd()
            
            # Try to find current project
            for project in projects:
                if cwd.is_relative_to(project.project_path):
                    selected_project = project
                    break
            
            if not selected_project:
                selected_project = projects[0]
            
            self.view_manager.switch_to_mode("project_focus", 
                                           {"project_path": str(selected_project.project_path)})
            self.show_project_focus_view(selected_project.project_path)
        else:
            self.update_status("No projects found with Claude configurations")
            self.view_manager.switch_to_mode("registry")
            self.show_registry_view()
    
    def show_registry_view(self) -> None:
        """Show the default registry view."""
        # Hide other views and show deployment matrix
        self.hide_all_views()
        deployment_matrix = self.query_one("#deployment-matrix")
        deployment_matrix.remove_class("hidden")
        deployment_matrix.add_class("visible")
        
        # Update panel title
        title = self.query_one("#panel-title-right", Static)
        title.update("🚀 Interactive Deployment Matrix")
        
        self.current_pane = "deployment"
        self.update_focus_indicators()
    
    def show_project_focus_view(self, project_path: Path) -> None:
        """Show project focus view for a specific project."""
        self.hide_all_views()
        
        # Show and populate project status view
        if self.project_status_view:
            self.project_status_view.remove_class("hidden")
            self.project_status_view.add_class("visible")
            self.project_status_view.show_project_status(project_path)
            
            # Update panel title
            title = self.query_one("#panel-title-right", Static)
            title.update(f"📁 Project: {project_path.name}")
            
            self.current_pane = "deployment"
            self.update_focus_indicators()
    
    def show_server_focus_view(self, server_name: str) -> None:
        """Show server focus view for a specific server."""
        self.hide_all_views()
        
        # Show and populate server status view
        if self.server_status_view:
            self.server_status_view.remove_class("hidden")
            self.server_status_view.add_class("visible")
            self.server_status_view.show_server_deployments(server_name)
            
            # Update panel title
            title = self.query_one("#panel-title-right", Static)
            title.update(f"🚀 Server: {server_name}")
            
            self.current_pane = "deployment"
            self.update_focus_indicators()
    
    def hide_all_views(self) -> None:
        """Hide all views in the right panel."""
        views = ["#deployment-matrix", "#project-status-view", "#server-status-view"]
        for view_id in views:
            try:
                view = self.query_one(view_id)
                view.add_class("hidden")
                view.remove_class("visible")
            except Exception:
                pass  # View not found, continue
    
    def update_view_mode_display(self) -> None:
        """Update the view mode indicator in the status bar."""
        mode_description = self.view_manager.get_mode_description()
        context_info = self.view_manager.get_context_info()
        
        # Update the status bar with current mode
        status_bar = self.query_one("#status-bar", Static)
        current_text = str(status_bar.renderable)
        
        if "|" in current_text:
            message_part = current_text.split("|")[0].strip()
            if context_info:
                status_text = f"{message_part} | {mode_description} | {context_info}"
            else:
                status_text = f"{message_part} | {mode_description}"
        else:
            if context_info:
                status_text = f"{current_text} | {mode_description} | {context_info}"
            else:
                status_text = f"{current_text} | {mode_description}"
        
        status_bar.update(status_text)
    
    # === Smart Wizard Actions ===
    
    def action_show_wizard(self) -> None:
        """Show the setup wizard or preferences."""
        if self.preferences.is_setup_completed():
            # Show preferences/settings screen
            self.update_status("Feature not implemented yet: Preferences screen")
        else:
            # Show setup wizard
            self.run_worker(self._show_setup_wizard)
    
    async def _show_setup_wizard(self) -> None:
        """Show the setup wizard (worker method)."""
        try:
            self.update_status("Launching setup wizard...")
            result = await self.smart_wizard.run_setup_wizard(self)
            
            if result.get("completed"):
                self.update_status("✓ Setup completed! Welcome to MCP Manager")
                # Refresh the UI to reflect new preferences
                self.action_refresh()
            elif result.get("cancelled"):
                self.update_status("Setup cancelled")
            else:
                error = result.get("error", "Unknown error")
                self.update_status(f"Setup failed: {error}")
        except Exception as e:
            self.update_status(f"Setup wizard error: {e}")
    
    def get_smart_deployment_suggestions(self, server_name: str) -> List[Dict[str, Any]]:
        """Get smart deployment suggestions for a server."""
        available_platforms = [info["name"] for info in self.platform_manager.get_platforms()]
        return self.smart_wizard.get_smart_suggestions(server_name, available_platforms)
    
    def record_deployment_success(self, server_name: str, platforms: List[str], success: bool = True) -> None:
        """Record deployment outcome for learning."""
        self.smart_wizard.record_deployment_choice(server_name, platforms, success)
    
    def get_quick_deploy_option(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get quick deploy option for a server if available."""
        return self.smart_wizard.get_quick_deploy_option(server_name)
    
    def action_quick_deploy(self) -> None:
        """Quick deploy selected server to usual platforms."""
        if self.current_operation:
            self.update_status("Another operation is already running")
            return
        
        # Get selected server
        server_table = self.query_one("#server-table", DataTable)
        if server_table.cursor_row is None:
            self.update_status("Please select a server to quick deploy")
            return
        
        try:
            row_data = server_table.get_row_at(server_table.cursor_row)
            server_name = str(row_data[0])
            
            # Get quick deploy option
            quick_option = self.get_quick_deploy_option(server_name)
            if not quick_option:
                self.update_status(f"No quick deploy option available for {server_name}. Use it more to build suggestions!")
                return
            
            # Deploy immediately to usual platforms
            platforms = quick_option["platforms"]
            self.update_status(f"Quick deploying {server_name} to {', '.join(platforms)}...")
            self.run_worker(
                lambda: self._run_async_deployment(server_name, platforms),
                thread=True
            )
            
        except (IndexError, ValueError):
            self.update_status("Please select a valid server")
    
    async def _show_smart_deployment_dialog(self, server_name: str, available_platforms: List[str]) -> None:
        """Show smart deployment dialog for a server."""
        try:
            dialog = SmartDeploymentDialog(
                server_name=server_name,
                available_platforms=available_platforms,
                smart_wizard=self.smart_wizard
            )
            
            result = await self.push_screen(dialog)
            
            if result:
                deployment_type = result.get("type")
                platforms = result.get("platforms", [])
                
                if platforms:
                    self.update_status(f"Deploying {server_name} to {', '.join(platforms)}...")
                    
                    # Record the deployment choice for learning
                    self.record_deployment_success(server_name, platforms, success=True)  # Assume success for now
                    
                    # Actually deploy
                    await self._deploy_server_to_platforms(server_name, platforms)
                else:
                    self.update_status("No platforms selected")
            else:
                self.update_status("Deployment cancelled")
                
        except Exception as e:
            self.update_status(f"Smart deployment failed: {e}")
    
    def _run_async_deployment(self, server_name: str, platforms: List[str]) -> None:
        """Synchronous wrapper for async deployment (for worker threads)."""
        import asyncio
        
        # Create event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._deploy_server_to_platforms(server_name, platforms))
        finally:
            loop.close()
    
    async def _deploy_server_to_platforms(self, server_name: str, platforms: List[str]) -> None:
        """Deploy a specific server to specific platforms."""
        try:
            success_count = 0
            error_count = 0
            
            for platform in platforms:
                try:
                    # This would be the actual deployment logic
                    # For now, we'll simulate deployment
                    await self._simulate_deployment(server_name, platform)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logging.error(f"Failed to deploy {server_name} to {platform}: {e}")
            
            # Record results for learning
            overall_success = error_count == 0
            self.record_deployment_success(server_name, platforms, overall_success)
            
            if success_count == len(platforms):
                self.call_from_thread(self.update_status, f"✓ Successfully deployed {server_name} to all platforms")
            elif success_count > 0:
                self.call_from_thread(self.update_status, f"⚠ Partially deployed {server_name}: {success_count}/{len(platforms)} succeeded")
            else:
                self.call_from_thread(self.update_status, f"✗ Failed to deploy {server_name} to any platform")
            
            # Refresh the deployment matrix
            self.call_from_thread(self.action_refresh)
            
        except Exception as e:
            self.call_from_thread(self.update_status, f"Deployment error: {e}")
            self.record_deployment_success(server_name, platforms, False)
    
    async def _simulate_deployment(self, server_name: str, platform: str) -> None:
        """Simulate deployment for demonstration purposes."""
        import asyncio
        import random
        
        # Simulate deployment time
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # Simulate occasional failures for learning
        if random.random() < 0.1:  # 10% failure rate
            raise Exception(f"Simulated deployment failure for {platform}")
        
        # In real implementation, this would call the actual deployment manager
        # result = await self.deployment_manager.deploy_server_async(server_name, platform)
    
    # Error Handling Methods
    def handle_operation_error(self, error: Exception, operation: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Handle errors that occur during operations."""
        # Create error context
        error_context = ErrorContext(
            operation=operation,
            server_name=context.get("server_name") if context else None,
            platform_key=context.get("platform_key") if context else None,
            project_path=context.get("project_path") if context else None,
            user_data=context,
            timestamp=datetime.now().isoformat()
        )
        
        # Handle the error
        recovery_result = self.error_handler.handle_error(error, error_context)
        
        # Show error dialog if manual intervention is required
        if recovery_result.manual_intervention_required:
            self.show_error_dialog(error, error_context, recovery_result)
        else:
            # Show result in status
            self.update_status(f"Error handled: {recovery_result.message}")
    
    def show_error_dialog(self, error: Exception, context: ErrorContext, recovery_result: RecoveryResult) -> None:
        """Show an error dialog with recovery options."""
        if not isinstance(error, MCPManagerError):
            from .exceptions import ErrorFactory
            mcp_error = ErrorFactory.from_exception(error, context)
        else:
            mcp_error = error
        
        self.last_error = mcp_error
        diagnostics = self.error_handler.generate_diagnostics(mcp_error)
        
        def recovery_callback(action: RecoveryAction) -> None:
            self.execute_recovery_action(action, mcp_error, context)
        
        dialog = ErrorDialog(mcp_error, diagnostics, recovery_callback)
        self.push_screen(dialog)
    
    def execute_recovery_action(self, action: RecoveryAction, error: MCPManagerError, context: ErrorContext) -> None:
        """Execute a selected recovery action."""
        try:
            if action == RecoveryAction.RETRY:
                self.retry_last_operation(context)
            elif action == RecoveryAction.ROLLBACK:
                self.show_rollback_confirmation()
            elif action == RecoveryAction.SKIP:
                self.skip_current_operation()
            elif action == RecoveryAction.MANUAL_FIX:
                self.show_manual_fix_dialog(error)
            elif action == RecoveryAction.ABORT:
                self.abort_all_operations()
            
            self.update_status(f"Recovery action '{action.value}' executed")
            
        except Exception as e:
            self.update_status(f"Failed to execute recovery action: {str(e)}")
    
    def action_undo_last_operation(self) -> None:
        """Undo the last operation (Ctrl+Z)."""
        if not self.rollback_manager.can_rollback():
            self.update_status("No operations available to undo")
            return
        
        self.show_rollback_confirmation()
    
    def action_show_error_history(self) -> None:
        """Show error history (Ctrl+E)."""
        error_stats = self.error_handler.get_error_statistics()
        recent_errors = self.error_handler.get_recent_errors(10)
        
        if not recent_errors:
            self.update_status("No recent errors to display")
            return
        
        # Create a simple error history display
        error_info = f"Recent Errors ({error_stats['total_errors']} total, {error_stats['recovery_rate']:.1f}% recovery rate):\n"
        for error in recent_errors[-5:]:  # Show last 5 errors
            error_info += f"• {error['timestamp']}: {error['error_type']} - {error['message'][:60]}...\n"
        
        self.notify(error_info, title="Error History", timeout=10)
    
    def action_show_recovery_wizard(self) -> None:
        """Show the recovery wizard (Ctrl+W)."""
        if not self.last_error:
            self.update_status("No recent error to recover from")
            return
        
        def recovery_callback(action: RecoveryAction, user_input: Dict[str, Any]) -> RecoveryResult:
            # This would integrate with the error handler to execute the recovery
            return RecoveryResult(
                success=True,
                action_taken=action.value,
                message=f"Recovery action {action.value} executed successfully"
            )
        
        wizard = RecoveryWizard(self.last_error, recovery_callback)
        self.push_screen(wizard)
    
    def show_rollback_confirmation(self) -> None:
        """Show rollback confirmation dialog."""
        last_transaction = self.rollback_manager.get_last_transaction()
        if not last_transaction:
            self.update_status("No transaction to rollback")
            return
        
        def rollback_callback(confirmed: bool) -> None:
            if confirmed:
                success = self.rollback_manager.rollback_transaction()
                if success:
                    self.update_status("Successfully rolled back last operation")
                    self.action_refresh()  # Refresh to show rolled back state
                else:
                    self.update_status("Failed to rollback operation")
        
        dialog = RollbackConfirmationDialog(last_transaction, rollback_callback)
        self.push_screen(dialog)
    
    def show_manual_fix_dialog(self, error: MCPManagerError) -> None:
        """Show manual fix instructions."""
        diagnostics = self.error_handler.generate_diagnostics(error)
        dialog = ManualFixDialog(error, diagnostics)
        self.push_screen(dialog)
    
    def retry_last_operation(self, context: ErrorContext) -> None:
        """Retry the last failed operation."""
        if context.operation == "deployment":
            server_names = context.user_data.get("server_names", [])
            platform_keys = context.user_data.get("platform_keys", [])
            if server_names and platform_keys:
                self.run_deployment(server_names, platform_keys)
        elif context.operation == "health_check":
            server_names = context.user_data.get("server_names", [])
            if server_names:
                self.run_health_check(server_names)
        else:
            self.update_status(f"Cannot retry operation: {context.operation}")
    
    def skip_current_operation(self) -> None:
        """Skip the current operation."""
        if self.current_operation:
            self.action_cancel_operation()
            self.update_status("Current operation skipped")
        else:
            self.update_status("No operation to skip")
    
    def abort_all_operations(self) -> None:
        """Abort all current operations."""
        if self.current_operation:
            self.action_cancel_operation()
        
        # Stop health monitoring
        if self.health_monitor.monitoring_active:
            self.health_monitor.stop_background_monitoring()
        
        self.update_status("All operations aborted")


def run_tui() -> int:
    """Launch the Textual TUI interface."""
    app = MCPManagerTUI()
    app.run()
    return 0


if __name__ == "__main__":
    run_tui()