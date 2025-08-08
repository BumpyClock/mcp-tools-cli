"""Professional Textual TUI for MCP Manager - Server Registry & Deployment."""

from pathlib import Path
from typing import Optional, Dict, Any
import structlog

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Static, Label, Button, 
    DataTable, ProgressBar, ListView, ListItem
)
from textual.reactive import reactive
from textual import events
from textual.css.query import NoMatches

from mcp_manager.core import MCPServerRegistry, DeploymentManager, PlatformManager, ProjectDetector
from mcp_manager.config_validator import ConfigValidator, ValidationResult
from mcp_manager.auto_repair import AutoRepair, RepairSuggestion
from mcp_manager.validation_dialog import ValidationDetailsDialog, RepairWizardDialog

logger = structlog.get_logger()


class MCPManagerTUI(App[None]):
    """Professional MCP Manager TUI Application with Real-time Validation."""
    
    TITLE = "MCP Manager - Server Registry & Deployment"
    SUB_TITLE = "Professional MCP server management and deployment with smart validation"
    
    CSS = """
    /* Professional theme inspired by RepoMap */
    
    /* Global styles */
    * {
        scrollbar-background: $surface;
        scrollbar-color: $primary;
        scrollbar-corner-color: $surface;
        scrollbar-size: 1 1;
    }
    
    /* Main layout */
    #main-container {
        height: 100%;
        width: 100%;
        layout: horizontal;
        background: $surface;
        border: none;
    }
    
    /* Left pane - Server Registry */
    #left-pane {
        width: 40%;
        height: 100%;
        layout: vertical;
        background: $surface;
        border-right: solid $primary-background;
    }
    
    /* Right pane - Details & Deployment */
    #right-pane {
        width: 60%;
        height: 100%;
        layout: vertical;
        background: $surface;
    }
    
    /* Header styling */
    Header {
        background: $primary;
        color: $text;
        text-align: center;
        height: 3;
        content-align: center middle;
    }
    
    /* Footer styling */
    Footer {
        background: $primary-background;
        color: $text;
        height: 3;
        dock: bottom;
    }
    
    /* Panel headers */
    .panel-header {
        height: 3;
        background: $primary-background;
        color: $text;
        text-align: center;
        content-align: center middle;
        text-style: bold;
        border-bottom: solid $primary;
    }
    
    /* Server registry styles */
    #server-list {
        height: 1fr;
        background: $surface;
        border: none;
    }
    
    /* Validation status indicators */
    .validation-valid {
        color: $success;
        text-style: bold;
    }
    
    .validation-warning {
        color: $warning;
        text-style: bold;
    }
    
    .validation-error {
        color: $error;
        text-style: bold;
    }
    
    .validation-pending {
        color: $accent;
    }
    
    /* Repair dialog styles */
    #repair-dialog {
        width: 80%;
        height: 60%;
        background: $surface;
        border: solid $primary;
        padding: 1;
    }
    
    #validation-progress {
        height: 1;
        margin: 1 0;
    }
    
    /* Fix button styles */
    .fix-button {
        background: $warning;
        color: $text;
    }
    
    .fix-button:hover {
        background: $warning-lighten-2;
    }
    
    .auto-fix-button {
        background: $success;
        color: $text;
    }
    
    .auto-fix-button:hover {
        background: $success-lighten-2;
    }
    
    #server-list > .datatable--header {
        background: $primary-background;
        color: $text;
        text-style: bold;
    }
    
    #server-list > .datatable--cursor {
        background: $primary 20%;
    }
    
    #server-list > .datatable--hover {
        background: $accent 10%;
    }
    
    /* Deployment matrix styles */
    #deployment-matrix {
        height: 1fr;
        background: $surface;
        border: none;
        margin: 1 0;
    }
    
    #deployment-matrix > .datatable--header {
        background: $accent;
        color: $text;
        text-style: bold;
    }
    
    #deployment-matrix > .datatable--cursor {
        background: $accent 20%;
    }
    
    /* Status panel */
    #status-panel {
        height: 8;
        background: $panel;
        border: solid $primary-background;
        border-title-color: $primary;
        border-title-style: bold;
        margin: 1;
        padding: 1;
    }
    
    /* Action buttons */
    .action-buttons {
        height: 4;
        layout: horizontal;
        align: center middle;
        background: $surface;
        padding: 1;
    }
    
    .action-button {
        margin: 0 1;
        min-width: 12;
        background: $accent;
        color: $text;
        border: solid $primary;
        text-align: center;
    }
    
    .action-button:hover {
        background: $accent 80%;
        border: solid $primary 80%;
    }
    
    .action-button.-primary {
        background: $primary;
        border: solid $primary;
    }
    
    .action-button.-primary:hover {
        background: $primary 80%;
    }
    
    /* Info display */
    .info-text {
        color: $text-muted;
        text-align: center;
        margin: 1;
    }
    
    .error-text {
        color: $error;
        text-style: bold;
    }
    
    .success-text {
        color: $success;
        text-style: bold;
    }
    
    .warning-text {
        color: $warning;
        text-style: bold;
    }
    
    /* Enhanced focus indicators */
    *:focus {
        border: solid $primary;
        /* Professional focus indicator */
    }
    
    /* Loading states */
    .loading {
        background: $surface;
        color: $text-muted;
        text-align: center;
        content-align: center middle;
    }
    
    /* Dark theme optimizations */
    App.-dark-mode {
        background: #1a1a1a;
    }
    
    App.-dark-mode .panel-header {
        background: #2d2d2d;
        border-bottom: solid #404040;
    }
    
    App.-dark-mode #server-list > .datatable--header,
    App.-dark-mode #deployment-matrix > .datatable--header {
        background: #2d2d2d;
    }
    """
    
    BINDINGS = [
        Binding("a", "add_server", "Add Server", priority=True),
        Binding("e", "edit_server", "Edit Server", priority=True),
        Binding("d", "deploy", "Deploy", priority=True),
        Binding("v", "validate_servers", "Validate", priority=True),
        Binding("f", "fix_issues", "Auto-Fix", priority=True),
        Binding("i", "show_validation_details", "Details", priority=True),
        Binding("w", "repair_wizard", "Wizard", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("h", "health_check", "Health Check", priority=True),
        Binding("q", "quit", "Quit", priority=True),
        Binding("?", "help", "Help"),
        Binding("f1", "toggle_help", "Help"),
    ]
    
    # Reactive attributes for state management
    current_server: reactive[Optional[str]] = reactive(None)
    deployment_status: reactive[Dict[str, Any]] = reactive({})
    registry_stats: reactive[Dict[str, Any]] = reactive({})
    validation_results: reactive[Dict[str, ValidationResult]] = reactive({})
    validation_running: reactive[bool] = reactive(False)
    
    def __init__(self, registry_file: Optional[Path] = None):
        """Initialize the MCP Manager TUI.
        
        Args:
            registry_file: Path to the MCP servers registry file
        """
        super().__init__()
        self.registry_file = registry_file
        self.registry: Optional[MCPServerRegistry] = None
        self.deployment_manager: Optional[DeploymentManager] = None
        self.platform_manager: Optional[PlatformManager] = None
        self.project_detector: Optional[ProjectDetector] = None
        
        # Initialize validation system
        self.validator = ConfigValidator()
        self.auto_repair = AutoRepair()
        self._validation_cache = {}
        
        # Auto-validation settings
        self.auto_validate = True
        self.validate_on_change = True
    
    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            # Left pane: Server Registry
            with Vertical(id="left-pane"):
                yield Label("📋 Server Registry", classes="panel-header")
                yield DataTable(id="server-list")
                
                # Action buttons for server management
                with Container(classes="action-buttons"):
                    yield Button("➕ Add", id="btn-add", classes="action-button -primary")
                    yield Button("✏️ Edit", id="btn-edit", classes="action-button")
                    yield Button("🔍 Validate", id="btn-validate", classes="action-button")
                    yield Button("🔧 Fix", id="btn-fix", classes="fix-button")
                    yield Button("🗑️ Remove", id="btn-remove", classes="action-button")
            
            # Right pane: Deployment & Details
            with Vertical(id="right-pane"):
                yield Label("🚀 Deployment Matrix", classes="panel-header")
                yield DataTable(id="deployment-matrix")
                
                # Status panel
                with Container(id="status-panel", border_title="📊 Status"):
                    yield Label("Ready to manage MCP servers", id="status-text", classes="info-text")
                    yield Label("", id="stats-text", classes="info-text")
                
                # Deployment action buttons
                with Container(classes="action-buttons"):
                    yield Button("🚀 Deploy", id="btn-deploy", classes="action-button -primary")
                    yield Button("🔄 Refresh", id="btn-refresh", classes="action-button")
                    yield Button("🏥 Health", id="btn-health", classes="action-button")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application on mount."""
        logger.info("Initializing MCP Manager TUI")
        
        try:
            # Initialize core components
            self.registry = MCPServerRegistry(self.registry_file)
            self.deployment_manager = DeploymentManager(self.registry)
            self.platform_manager = PlatformManager()
            self.project_detector = ProjectDetector()
            
            # Setup data tables
            self._setup_server_list()
            self._setup_deployment_matrix()
            
            # Load initial data
            self._refresh_data()
            
            logger.info("MCP Manager TUI initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize TUI", error=str(e))
            self._show_error(f"Initialization failed: {e}")
    
    def _setup_server_list(self) -> None:
        """Setup the server list data table with validation columns."""
        try:
            server_table = self.query_one("#server-list", DataTable)
            server_table.add_columns(
                "Name",
                "Type", 
                "Status",
                "Validation",
                "Score",
                "Issues"
            )
            server_table.cursor_type = "row"
            server_table.zebra_stripes = True
        except NoMatches:
            logger.warning("Server list table not found during setup")
    
    def _setup_deployment_matrix(self) -> None:
        """Setup the deployment matrix data table."""
        try:
            matrix_table = self.query_one("#deployment-matrix", DataTable)
            matrix_table.add_columns(
                "Server",
                "Claude Desktop",
                "Claude Code",
                "Projects",
                "Status"
            )
            matrix_table.cursor_type = "row"
            matrix_table.zebra_stripes = True
        except NoMatches:
            logger.warning("Deployment matrix table not found during setup")
    
    def _refresh_data(self) -> None:
        """Refresh all data in the TUI."""
        if not self.registry:
            return
        
        try:
            # Update server list
            self._update_server_list()
            
            # Update deployment matrix
            self._update_deployment_matrix()
            
            # Update status and stats
            self._update_status()
            
            # Trigger auto-validation if enabled
            if self.auto_validate and not self.validation_running:
                self.call_later(self.action_validate_servers)
            
            logger.info("Data refreshed successfully")
        except Exception as e:
            logger.error("Failed to refresh data", error=str(e))
            self._show_error(f"Refresh failed: {e}")
    
    def _update_server_list(self) -> None:
        """Update the server list table with validation status."""
        if not self.registry:
            return
        
        try:
            server_table = self.query_one("#server-list", DataTable)
            server_table.clear()
            
            servers = self.registry.list_servers()
            for name, entry in servers.items():
                status = "✅ Enabled" if entry.metadata.enabled else "❌ Disabled"
                
                # Get validation status
                validation_result = self.validation_results.get(name)
                if validation_result:
                    validation_icon = self._get_validation_icon(validation_result)
                    score = f"{validation_result.score}%"
                    issues_count = len(validation_result.issues)
                    issues_text = f"{issues_count}" if issues_count > 0 else "-"
                else:
                    validation_icon = "⏳" if self.validation_running else "❓"
                    score = "-"
                    issues_text = "?"
                
                server_table.add_row(
                    name,
                    entry.type.upper(),
                    status,
                    validation_icon,
                    score,
                    issues_text,
                    key=name
                )
        except NoMatches:
            logger.warning("Server list table not found during update")
        except Exception as e:
            logger.error("Failed to update server list", error=str(e))
    
    def _update_deployment_matrix(self) -> None:
        """Update the deployment matrix table."""
        if not self.deployment_manager:
            return
        
        try:
            matrix_table = self.query_one("#deployment-matrix", DataTable)
            matrix_table.clear()
            
            deployment_matrix = self.deployment_manager.get_deployment_matrix()
            
            for server_name, deployments in deployment_matrix.items():
                claude_desktop = "✅" if deployments.get("platform:claude_desktop", False) else "❌"
                claude_code = "✅" if deployments.get("platform:claude_code", False) else "❌"
                
                # Count project deployments
                project_count = sum(1 for k, v in deployments.items() 
                                  if k.startswith("project:") and v)
                projects_str = f"📁 {project_count}" if project_count > 0 else "❌"
                
                # Overall status
                total_deployed = sum(1 for v in deployments.values() if v)
                status = f"🚀 {total_deployed}/{len(deployments)}" if total_deployed > 0 else "❌ None"
                
                matrix_table.add_row(
                    server_name,
                    claude_desktop,
                    claude_code,
                    projects_str,
                    status,
                    key=server_name
                )
        except NoMatches:
            logger.warning("Deployment matrix table not found during update")
        except Exception as e:
            logger.error("Failed to update deployment matrix", error=str(e))
    
    def _update_status(self) -> None:
        """Update status information."""
        if not self.registry:
            return
        
        try:
            stats = self.registry.get_stats()
            self.registry_stats = stats
            
            status_text = self.query_one("#status-text", Label)
            stats_text = self.query_one("#stats-text", Label)
            
            status_text.update("🟢 MCP Manager Ready")
            
            stats_msg = (
                f"📊 Servers: {stats['total_servers']} total, "
                f"{stats['enabled_servers']} enabled | "
                f"🏷️ Tags: {stats['total_tags']}"
            )
            stats_text.update(stats_msg)
            
        except NoMatches:
            logger.warning("Status labels not found during update")
        except Exception as e:
            logger.error("Failed to update status", error=str(e))
    
    def _show_error(self, message: str) -> None:
        """Display an error message."""
        try:
            status_text = self.query_one("#status-text", Label)
            status_text.update(f"🔴 Error: {message}")
            status_text.add_class("error-text")
        except NoMatches:
            logger.error("Could not display error message", message=message)
    
    def _show_success(self, message: str) -> None:
        """Display a success message."""
        try:
            status_text = self.query_one("#status-text", Label)
            status_text.update(f"🟢 {message}")
            status_text.add_class("success-text")
            # Auto-clear after 3 seconds
            self.set_timer(3.0, lambda: status_text.update("🟢 MCP Manager Ready"))
        except NoMatches:
            logger.warning("Could not display success message", message=message)
    
    # Action handlers
    async def action_add_server(self) -> None:
        """Handle add server action."""
        logger.info("Add server action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Add server dialog will be implemented by Agent 2")
    
    async def action_edit_server(self) -> None:
        """Handle edit server action."""
        logger.info("Edit server action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Edit server dialog will be implemented by Agent 2")
    
    async def action_deploy(self) -> None:
        """Handle deploy action."""
        logger.info("Deploy action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Deploy dialog will be implemented by Agent 2")
    
    async def action_refresh(self) -> None:
        """Handle refresh action."""
        logger.info("Refreshing data...")
        self._refresh_data()
        self._show_success("Data refreshed successfully")
    
    async def action_health_check(self) -> None:
        """Handle health check action."""
        logger.info("Health check action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Health check will be implemented by Agent 2")
    
    async def action_help(self) -> None:
        """Show help information."""
        help_text = """
        🔧 MCP Manager - Keyboard Shortcuts:
        
        a - Add new MCP server
        e - Edit selected server
        d - Deploy servers to targets
        r - Refresh all data
        h - Run health checks
        q - Quit application
        ? - Show this help
        
        Use arrow keys to navigate tables.
        """
        self._show_success("Help: See terminal for keyboard shortcuts")
        print(help_text)
    
    async def action_toggle_help(self) -> None:
        """Toggle help display."""
        await self.action_help()
    
    async def action_validate_servers(self) -> None:
        """Validate all server configurations."""
        if not self.registry:
            self._show_error("Registry not initialized")
            return
        
        self._show_info("Starting validation...")
        self.validation_running = True
        
        try:
            servers = self.registry.list_servers()
            if not servers:
                self._show_info("No servers to validate")
                return
            
            # Run validation in background
            self.run_worker(self._validate_all_servers, servers, exclusive=True, thread=True)
            
        except Exception as e:
            logger.error("Validation failed", error=str(e))
            self._show_error(f"Validation failed: {e}")
            self.validation_running = False
    
    async def action_fix_issues(self) -> None:
        """Auto-fix validation issues for the selected server."""
        if not self.current_server:
            self._show_error("No server selected")
            return
        
        validation_result = self.validation_results.get(self.current_server)
        if not validation_result:
            self._show_error("Server not validated yet. Run validation first.")
            return
        
        if not validation_result.issues:
            self._show_success("No issues to fix!")
            return
        
        # Get server config
        server = self.registry.get_server(self.current_server)
        if not server:
            self._show_error("Server configuration not found")
            return
        
        server_config = server.get_config_dict()
        
        # Analyze and apply auto-fixes
        self._show_info("Analyzing issues and applying fixes...")
        self.run_worker(self._auto_fix_server, self.current_server, server_config, validation_result, exclusive=True, thread=True)
    
    def _validate_all_servers(self, servers):
        """Worker function to validate all servers."""
        try:
            results = {}
            total = len(servers)
            
            for i, (server_name, server_entry) in enumerate(servers.items()):
                try:
                    # Update progress
                    progress = int((i / total) * 100)
                    self.call_from_thread(
                        self._update_validation_progress,
                        progress,
                        f"Validating {server_name}..."
                    )
                    
                    # Get server config
                    server_config = server_entry.get_config_dict()
                    
                    # Validate with health check
                    result = self.validator.validate_server_config(
                        server_name, server_config, check_health=True
                    )
                    results[server_name] = result
                    
                except Exception as e:
                    logger.error("Failed to validate server", server=server_name, error=str(e))
                    results[server_name] = ValidationResult(
                        server_name=server_name,
                        valid=False,
                        issues=[],
                        score=0
                    )
            
            # Update UI with results
            self.call_from_thread(self._update_validation_results, results)
            
        except Exception as e:
            logger.error("Validation worker failed", error=str(e))
            self.call_from_thread(self._show_error, f"Validation failed: {e}")
        finally:
            self.call_from_thread(self._finish_validation)
    
    def _auto_fix_server(self, server_name: str, server_config: Dict[str, Any], validation_result: ValidationResult):
        """Worker function to auto-fix server issues."""
        try:
            # Get repair suggestions
            suggestions = self.auto_repair.analyze_issues(validation_result, server_config)
            
            if not suggestions:
                self.call_from_thread(self._show_info, "No automatic fixes available")
                return
            
            applied_fixes = 0
            total_fixes = sum(len(s.actions) for s in suggestions)
            
            for suggestion in suggestions:
                # Apply auto-fixable actions only
                auto_actions = [a for a in suggestion.actions if a.auto_applicable]
                
                for action in auto_actions:
                    try:
                        success, new_config, error = self.auto_repair.apply_repair_action(action, server_config)
                        
                        if success:
                            server_config = new_config
                            applied_fixes += 1
                            self.call_from_thread(
                                self._show_info,
                                f"Applied fix: {action.title}"
                            )
                        else:
                            logger.warning("Fix failed", action=action.title, error=error)
                    
                    except Exception as e:
                        logger.error("Fix application failed", action=action.title, error=str(e))
            
            if applied_fixes > 0:
                # Update server configuration in registry
                try:
                    success = self.registry.update_server(server_name, server_config)
                    if success:
                        self.call_from_thread(
                            self._show_success,
                            f"Applied {applied_fixes}/{total_fixes} fixes to {server_name}"
                        )
                        
                        # Re-validate the server
                        new_result = self.validator.validate_server_config(
                            server_name, server_config, check_health=False
                        )
                        self.call_from_thread(self._update_single_validation, server_name, new_result)
                    else:
                        self.call_from_thread(self._show_error, "Failed to save configuration changes")
                
                except Exception as e:
                    logger.error("Failed to update server config", error=str(e))
                    self.call_from_thread(self._show_error, f"Failed to save changes: {e}")
            else:
                self.call_from_thread(self._show_info, "No automatic fixes could be applied")
        
        except Exception as e:
            logger.error("Auto-fix worker failed", error=str(e))
            self.call_from_thread(self._show_error, f"Auto-fix failed: {e}")
    
    async def action_show_validation_details(self) -> None:
        """Show detailed validation results for selected server."""
        if not self.current_server:
            self._show_error("No server selected")
            return
        
        validation_result = self.validation_results.get(self.current_server)
        if not validation_result:
            self._show_error("Server not validated yet. Run validation first.")
            return
        
        server = self.registry.get_server(self.current_server)
        if not server:
            self._show_error("Server configuration not found")
            return
        
        server_config = server.get_config_dict()
        
        # Show validation details dialog
        dialog = ValidationDetailsDialog(
            server_name=self.current_server,
            validation_result=validation_result,
            auto_repair=self.auto_repair,
            server_config=server_config
        )
        
        result = await self.push_screen(dialog)
        
        # Handle dialog result
        if result:
            if result.get("action") == "auto_fix":
                suggestions = result.get("suggestions", [])
                await self._apply_repair_suggestions(suggestions)
            elif result.get("action") == "revalidate":
                await self.action_validate_servers()
    
    async def action_repair_wizard(self) -> None:
        """Launch repair wizard for selected server."""
        if not self.current_server:
            self._show_error("No server selected")
            return
        
        validation_result = self.validation_results.get(self.current_server)
        if not validation_result or not validation_result.issues:
            self._show_info("No issues found for this server")
            return
        
        server = self.registry.get_server(self.current_server)
        if not server:
            self._show_error("Server configuration not found")
            return
        
        server_config = server.get_config_dict()
        
        # Generate repair suggestions
        suggestions = self.auto_repair.analyze_issues(validation_result, server_config)
        if not suggestions:
            self._show_info("No repair suggestions available")
            return
        
        # Show repair wizard
        wizard = RepairWizardDialog(
            repair_suggestions=suggestions,
            server_name=self.current_server
        )
        
        result = await self.push_screen(wizard)
        
        # Handle wizard result
        if result and result.get("action") == "complete":
            suggestions = result.get("applied_suggestions", [])
            await self._apply_repair_suggestions(suggestions)
    
    async def _apply_repair_suggestions(self, suggestions: List[RepairSuggestion]):
        """Apply a list of repair suggestions."""
        if not suggestions:
            return
        
        server = self.registry.get_server(self.current_server)
        if not server:
            self._show_error("Server configuration not found")
            return
        
        server_config = server.get_config_dict()
        
        self._show_info(f"Applying {len(suggestions)} repair suggestion(s)...")
        
        total_applied = 0
        total_errors = []
        
        for suggestion in suggestions:
            success, new_config, errors = self.auto_repair.apply_repair_suggestion(
                suggestion, server_config, skip_confirmations=True
            )
            
            if success:
                server_config = new_config
                total_applied += 1
            
            total_errors.extend(errors)
        
        if total_applied > 0:
            # Save the updated configuration
            try:
                success = self.registry.update_server(self.current_server, server_config)
                if success:
                    self._show_success(f"Applied {total_applied} repair suggestion(s)")
                    
                    # Re-validate the server
                    await self._revalidate_single_server(self.current_server)
                else:
                    self._show_error("Failed to save configuration changes")
            except Exception as e:
                logger.error("Failed to save repaired config", error=str(e))
                self._show_error(f"Failed to save changes: {e}")
        
        if total_errors:
            self._show_error(f"{len(total_errors)} repair(s) failed: {', '.join(total_errors[:3])}")
    
    async def _revalidate_single_server(self, server_name: str):
        """Revalidate a single server."""
        try:
            server = self.registry.get_server(server_name)
            if not server:
                return
            
            server_config = server.get_config_dict()
            
            # Run validation
            result = self.validator.validate_server_config(
                server_name, server_config, check_health=False
            )
            
            # Update results
            current_results = dict(self.validation_results)
            current_results[server_name] = result
            self.validation_results = current_results
            
            # Refresh display
            self._update_server_list()
            
        except Exception as e:
            logger.error("Failed to revalidate server", server=server_name, error=str(e))
    
    def _update_validation_progress(self, progress: int, message: str):
        """Update validation progress."""
        # Update status message
        self._show_info(f"{message} ({progress}%)")
    
    def _update_validation_results(self, results: Dict[str, ValidationResult]):
        """Update validation results and refresh display."""
        self.validation_results = results
        self._refresh_server_list()
        
        # Show summary
        summary = self.validator.get_validation_summary(results)
        self._show_success(
            f"Validation complete: {summary['valid_servers']}/{summary['total_servers']} servers valid "
            f"(avg score: {summary['average_score']}%)"
        )
    
    def _update_single_validation(self, server_name: str, result: ValidationResult):
        """Update validation result for a single server."""
        current_results = dict(self.validation_results)
        current_results[server_name] = result
        self.validation_results = current_results
        self._refresh_server_list()
    
    def _finish_validation(self):
        """Clean up after validation."""
        self.validation_running = False
    
    def _get_validation_icon(self, result: ValidationResult) -> str:
        """Get validation status icon based on result."""
        if result.score >= 90:
            return "✅"
        elif result.score >= 70:
            return "⚠️"
        else:
            return "❌"
    
    def _refresh_server_list(self):
        """Refresh the server list with validation status."""
        if not self.registry:
            return
        
        try:
            table = self.query_one("#server-list", DataTable)
            table.clear()
            
            # Add columns if needed
            if not hasattr(table, '_columns_added'):
                table.add_columns("Server", "Type", "Status", "Validation", "Score")
                table._columns_added = True
            
            servers = self.registry.list_servers()
            for server_name, server_entry in servers.items():
                # Get validation status
                validation_result = self.validation_results.get(server_name)
                if validation_result:
                    validation_icon = self._get_validation_icon(validation_result)
                    score = f"{validation_result.score}%"
                else:
                    validation_icon = "⏳" if self.validation_running else "-"
                    score = "-"
                
                # Server status
                status = "✅ Enabled" if server_entry.metadata.enabled else "❌ Disabled"
                
                table.add_row(server_name, server_entry.type, status, validation_icon, score)
            
        except Exception as e:
            logger.error("Failed to refresh server list", error=str(e))
    
    # Button event handlers
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_actions = {
            "btn-add": self.action_add_server,
            "btn-edit": self.action_edit_server,
            "btn-validate": self.action_validate_servers,
            "btn-fix": self.action_fix_issues,
            "btn-remove": self._remove_server,
            "btn-deploy": self.action_deploy,
            "btn-refresh": self.action_refresh,
            "btn-health": self.action_health_check,
        }
        
        action = button_actions.get(event.button.id)
        if action:
            self.call_later(action)
    
    async def _remove_server(self) -> None:
        """Handle remove server action."""
        logger.info("Remove server action triggered")
        # Placeholder for Agent 2 to implement
        self._show_error("Remove server confirmation will be implemented by Agent 2")
    
    # Table event handlers
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in data tables."""
        if event.data_table.id == "server-list":
            self.current_server = str(event.row_key)
            logger.info("Selected server", server=self.current_server)
        elif event.data_table.id == "deployment-matrix":
            self.current_server = str(event.row_key)
            logger.info("Selected server from matrix", server=self.current_server)


def run_tui() -> int:
    """Launch the Textual TUI interface."""
    try:
        app = MCPManagerTUI()
        app.run()
        return 0
    except KeyboardInterrupt:
        logger.info("TUI interrupted by user")
        return 0
    except Exception as e:
        logger.error("TUI crashed", error=str(e))
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_tui())