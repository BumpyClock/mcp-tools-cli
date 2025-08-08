# MCP Manager - TUI Enhancement Sprint Plan

## 🎯 Project Overview

### Objectives
Transform **mcp-tools-cli** into **mcp-manager** with a professional Textual TUI that provides:
- "Configure once, deploy anywhere" workflow
- Intuitive selection patterns (Enter/Spacebar behavior)
- Bidirectional deployment status views
- Real-time health monitoring and feedback
- Professional UI matching RepoMap quality standards

### Success Criteria
- ✅ Seamless project rename with no broken imports
- ✅ Professional Textual TUI with modern design patterns
- ✅ Smart selection UX (Enter = select+advance, Spacebar = multi-select)
- ✅ Bidirectional views (project→servers, server→projects)
- ✅ Real-time status indicators and health monitoring
- ✅ Core functions remain importable for programmatic use
- ✅ Backward CLI compatibility maintained

### Timeline Estimate
- **Total Duration**: 2-3 weeks
- **Phase 1-2**: Foundation & Basic TUI (1 week)
- **Phase 3-4**: Feature Integration & Status Views (1 week)  
- **Phase 5-6**: Polish & Documentation (0.5-1 week)

---

## 🏗️ Phase 1: Project Rename & Foundation
*Estimated: 2-3 days*

### 1.1 Directory Structure Rename
**Priority: High | Complexity: Medium**

- [ ] **Rename root directory**
  - `mcp-tools-cli` → `mcp-manager`
  - Update all path references in scripts and configs

- [ ] **Rename Python package**
  - `src/mcp_tools/` → `src/mcp_manager/`
  - Update all import statements throughout codebase
  - Verify no broken imports remain

- [ ] **Update package configuration**
  - `pyproject.toml`: Change `name = "mcp-manager"`
  - Update entry points: `mcp-manager = "mcp_manager.__main__:main"`
  - Update project URLs, descriptions, and metadata

**Acceptance Criteria:**
- Package installs as `mcp-manager`
- CLI command `mcp-manager` works
- All imports resolve correctly
- No references to old name remain

### 1.2 Core Module Reorganization
**Priority: High | Complexity: Low**

- [ ] **Create clean core structure**
  ```
  src/mcp_manager/
  ├── core/
  │   ├── __init__.py      # Export main functions
  │   ├── registry.py      # MCPServerRegistry
  │   ├── deployment.py    # DeploymentManager  
  │   ├── platforms.py     # PlatformManager
  │   └── projects.py      # ProjectDetector
  ├── tui.py               # New Textual TUI
  ├── cli.py               # Existing CLI
  └── __main__.py          # Entry point
  ```

- [ ] **Update core/__init__.py for clean imports**
  ```python
  # Enable clean programmatic imports
  from .registry import MCPServerRegistry
  from .deployment import DeploymentManager
  from .platforms import PlatformManager
  from .projects import ProjectDetector
  
  __all__ = [
      "MCPServerRegistry",
      "DeploymentManager", 
      "PlatformManager",
      "ProjectDetector"
  ]
  ```

**Acceptance Criteria:**
- Clean imports work: `from mcp_manager.core import registry`
- All existing functionality preserved
- No circular dependencies
- Core modules can be imported independently

### 1.3 Entry Point Refactoring
**Priority: Medium | Complexity: Low**

- [ ] **Update __main__.py with TUI-first approach**
  ```python
  def main():
      if len(sys.argv) == 1:
          # No args → Launch Textual TUI
          try:
              from .tui import run_tui
              run_tui()
          except ImportError:
              print("TUI unavailable. Use 'mcp-manager -h' for CLI help")
              return 1
      else:
          # Args provided → Use CLI
          from .cli import main as cli_main
          cli_main()
  ```

- [ ] **Add help argument detection**
  ```python
  help_args = {'-h', '--help', '-?', 'help'}
  if any(arg in help_args for arg in sys.argv[1:]):
      from .cli import show_help
      show_help()
      return
  ```

**Acceptance Criteria:**
- `mcp-manager` launches TUI
- `mcp-manager -h` shows help
- `mcp-manager command args` uses CLI
- Graceful fallback if Textual unavailable

---

## 🎨 Phase 2: Textual TUI Implementation
*Estimated: 3-4 days*

### 2.1 Main TUI Application Class
**Priority: High | Complexity: High**

- [ ] **Create src/mcp_manager/tui.py with base structure**
  ```python
  from textual.app import App, ComposeResult
  from textual.containers import Vertical, Horizontal
  from textual.widgets import Header, Footer, Tree, Static, DataTable
  
  class MCPManagerTUI(App):
      TITLE = "MCP Manager - Server Registry & Deployment"
      
      BINDINGS = [
          ("a", "add_server", "Add"),
          ("e", "edit_server", "Edit"),
          ("d", "deploy", "Deploy"), 
          ("r", "refresh", "Refresh"),
          ("h", "health_check", "Health"),
          ("q", "quit", "Quit"),
      ]
      
      CSS = """
      # Professional styling matching RepoMap standards
      """
  ```

- [ ] **Implement basic layout structure**
  - Left pane: Server registry tree
  - Right pane: Deployment status/details
  - Bottom: Action buttons and status bar
  - Header with app title and context info

**Acceptance Criteria:**
- App launches and displays correctly
- Basic navigation works with keyboard
- Layout is responsive to terminal resizing
- Matches RepoMap visual quality standards

### 2.2 Core Widgets Implementation
**Priority: High | Complexity: High**

- [ ] **ServerRegistryTree Widget**
  ```python
  class ServerRegistryTree(Tree):
      def __init__(self):
          super().__init__("📦 MCP Servers")
          self.multi_select_mode = False
          self.selected_servers = set()
      
      def on_tree_node_selected(self, event):
          # Handle Enter key behavior
          if self.multi_select_mode:
              self.toggle_selection(event.node)
          else:
              self.single_select(event.node)
              self.advance_to_next_pane()
      
      def on_key(self, event):
          if event.key == "space":
              self.toggle_multi_select()
  ```

- [ ] **DeploymentMatrix Widget** 
  ```python
  class DeploymentMatrix(DataTable):
      def compose_table(self):
          # Columns: Server, Desktop, Code, VS Code, Projects
          # Rows: Each server with status indicators
          # Interactive cells for quick enable/disable
  ```

- [ ] **ServerDetailsPane Widget**
  ```python
  class ServerDetailsPane(Vertical):
      def display_server(self, server_name):
          # Show server configuration
          # Environment variables with masking
          # Health status and connectivity
          # Deployment history
  ```

**Acceptance Criteria:**
- Tree displays servers with status icons
- Multi-select works with spacebar
- Single select + advance works with Enter
- Status matrix shows deployment state
- Details pane updates when server selected

### 2.3 Smart Selection Pattern Implementation
**Priority: High | Complexity: Medium**

- [ ] **Implement Enter/Spacebar behavior**
  - Enter on list item: Single select + advance
  - Spacebar on item: Toggle multi-select  
  - Enter after spacebar: Add to selection + advance
  - Visual feedback for both modes

- [ ] **Add selection state management**
  ```python
  class SelectionManager:
      def __init__(self):
          self.single_selection = None
          self.multi_selections = set()
          self.mode = "single"  # or "multi"
      
      def toggle_mode(self):
          # Switch between single and multi-select
      
      def handle_enter(self, item):
          # Context-aware enter behavior
      
      def handle_spacebar(self, item):
          # Multi-select toggle
  ```

**Acceptance Criteria:**
- Enter selects and advances in single mode
- Spacebar toggles multi-select mode
- Visual indicators show selection state
- Mode switching works intuitively
- Keyboard navigation feels natural

### 2.4 CSS Styling & Visual Design
**Priority: Medium | Complexity: Medium**

- [ ] **Create professional CSS theme**
  ```css
  /* Base application styling */
  Screen {
      background: $surface;
      color: $text;
  }
  
  /* Server registry tree */
  #server_registry {
      width: 40%;
      border: round $primary;
      margin: 1;
  }
  
  /* Status indicators */
  .status-enabled { color: $success; }
  .status-disabled { color: $error; }  
  .status-warning { color: $warning; }
  
  /* Deployment matrix */
  .deployment-matrix {
      border: round $secondary;
  }
  ```

- [ ] **Add status icons and indicators**
  - ✅ Server enabled and healthy
  - ❌ Server disabled or unreachable
  - ⚠️ Server with configuration issues
  - 🔄 Operation in progress
  - 📦 Server category icons

**Acceptance Criteria:**
- Professional appearance matching RepoMap
- Consistent color scheme and typography
- Clear status indicators and icons
- Good contrast and accessibility
- Responsive to different terminal sizes

---

## 🔧 Phase 3: Core Feature Integration
*Estimated: 3-4 days*

### 3.1 Registry Integration
**Priority: High | Complexity: Medium**

- [x] **Connect TUI to existing MCPServerRegistry**
  ```python
  def on_mount(self):
      self.registry = MCPServerRegistry()
      self.deployment_manager = DeploymentManager(self.registry)
      self.refresh_server_list()
  
  def refresh_server_list(self):
      servers = self.registry.list_servers()
      self.server_tree.populate(servers)
  ```

- [x] **Implement server management actions**
  - Add server: Launch configuration wizard
  - Edit server: Open details pane for editing
  - Remove server: Confirmation dialog + removal
  - Enable/disable: Toggle server status

**Acceptance Criteria:**
- TUI displays real servers from registry
- All CRUD operations work correctly
- Changes persist to registry file
- UI updates reflect registry changes

### 3.2 Deployment Integration  
**Priority: High | Complexity: High**

- [x] **Connect to DeploymentManager**
  ```python
  def deploy_servers(self, server_names, target_keys):
      # Use worker thread for non-blocking deployment
      self.run_worker(
          self.deployment_worker, 
          server_names, 
          target_keys,
          thread=True
      )
  
  def deployment_worker(self, server_names, target_keys):
      # Background deployment with progress updates
      results = self.deployment_manager.deploy_servers_bulk(
          server_names, target_keys
      )
      self.call_from_thread(self.update_deployment_status, results)
  ```

- [x] **Add deployment workflow UI**
  - Server selection interface
  - Target selection (platforms/projects) 
  - Confirmation dialog with preview
  - Progress tracking during deployment

**Acceptance Criteria:**
- Deployment operations work from TUI
- Progress feedback during operations
- Results displayed with clear status
- All deployment options accessible

### 3.3 Worker Thread Implementation
**Priority: High | Complexity: Medium**

- [x] **Add non-blocking operations**
  ```python
  def run_deployment(self, servers, targets):
      self.deployment_task = self.run_worker(
          self.deploy_worker,
          servers, targets,
          thread=True,
          exclusive=True
      )
  
  def deploy_worker(self, servers, targets):
      try:
          # Update progress
          self.call_from_thread(self.update_progress, 0)
          
          # Perform deployment
          for i, server in enumerate(servers):
              self.call_from_thread(
                  self.update_status, 
                  f"Deploying {server}..."
              )
              # Deploy server...
              progress = int((i + 1) / len(servers) * 100)
              self.call_from_thread(self.update_progress, progress)
              
      except Exception as e:
          self.call_from_thread(self.show_error, str(e))
      finally:
          self.call_from_thread(self.deployment_complete)
  ```

- [x] **Add operation cancellation**
  - Cancel button during operations
  - Graceful worker thread termination
  - Status cleanup on cancellation

**Acceptance Criteria:**
- Long operations don't block UI
- Progress feedback is smooth and accurate
- Operations can be cancelled gracefully
- Error handling works correctly

### 3.4 Keyboard Shortcuts & Navigation
**Priority: Medium | Complexity: Low**

- [x] **Implement all planned shortcuts**
  - `A`: Add new server
  - `E`: Edit selected server  
  - `D`: Deploy selected servers
  - `R`: Refresh/reload data
  - `H`: Health check servers
  - `Q`: Quit application
  - `Tab`/`Shift+Tab`: Navigate panes
  - `Escape`: Go back/cancel

- [x] **Add context-sensitive shortcuts**
  - Different shortcuts based on current pane
  - Dynamic help text in footer
  - Conflict resolution for overlapping shortcuts

**Acceptance Criteria:**
- All shortcuts work as designed
- Shortcuts are discoverable (shown in footer)
- No conflicts between different contexts
- Navigation feels intuitive and fast

---

## 📊 Phase 4: Enhanced Status & Monitoring  
*Estimated: 2-3 days*

### 4.1 Bidirectional Status Views
**Priority: High | Complexity: Medium**

- [x] **Project → Servers view**
  ```python
  class ProjectStatusView(DataTable):
      def show_project_status(self, project_path):
          # Display: "What MCPs are installed in this project?"
          installed_servers = self.get_project_servers(project_path)
          self.populate_table(installed_servers)
  ```

- [x] **Server → Projects view**  
  ```python
  class ServerStatusView(Vertical):
      def show_server_deployments(self, server_name):
          # Display: "Where is this server deployed?"
          deployment_status = self.deployment_manager.get_server_deployment_status(server_name)
          self.update_deployment_list(deployment_status)
  ```

- [x] **Add view switching**
  - Toggle between project-focused and server-focused views
  - Maintain context when switching views
  - Quick navigation between related items

**Acceptance Criteria:**
- Project view shows installed servers clearly
- Server view shows deployment locations
- Easy switching between view modes
- Data stays synchronized across views

### 4.2 Health Monitoring Dashboard
**Priority: Medium | Complexity: Medium**

- [x] **Real-time health indicators**
  ```python
  class HealthMonitor:
      def __init__(self):
          self.health_cache = {}
          self.last_check = {}
      
      def check_server_health(self, server_name):
          # Test server connectivity
          # Validate configuration  
          # Check API key validity
          return HealthStatus(healthy=True, message="OK")
      
      def start_background_monitoring(self):
          # Periodic health checks in background
          self.set_interval(self.refresh_health_status, 30.0)
  ```

- [x] **Health status visualization**
  - Color-coded status indicators
  - Last seen timestamps
  - Error messages and diagnostics
  - Health history tracking

**Acceptance Criteria:**
- Health status visible at a glance
- Background monitoring doesn't impact performance
- Clear error messages when issues detected
- Health data refreshes automatically

### 4.3 Deployment Matrix Enhancement
**Priority: Medium | Complexity: High**

- [x] **Interactive deployment grid**
  ```python
  class InteractiveDeploymentMatrix(DataTable):
      def on_cell_selected(self, event):
          # Allow toggling deployment status by clicking cells
          server_name = self.get_server_at_row(event.row)
          target_key = self.get_target_at_column(event.column)
          self.toggle_deployment(server_name, target_key)
      
      def update_cell_status(self, server, target, deployed):
          # Update cell with visual status indicator
          cell_value = "✅" if deployed else "❌"
          self.update_cell(server, target, cell_value)
  ```

- [x] **Deployment conflict detection**
  - Highlight version mismatches
  - Show configuration conflicts
  - Suggest resolution actions

**Acceptance Criteria:**
- Matrix shows all deployment relationships
- Clicking cells toggles deployment status
- Conflicts are clearly highlighted
- Performance remains good with many servers

### 4.4 Configuration Validation
**Priority: Low | Complexity: Medium**

- [x] **Real-time config validation**
  ```python
  class ConfigValidator:
      def validate_server_config(self, server_config):
          issues = []
          
          # Check required fields
          if not server_config.get('command'):
              issues.append("Missing command")
          
          # Validate API keys
          env_vars = server_config.get('env', {})
          for key, value in env_vars.items():
              if self.is_api_key_placeholder(value):
                  issues.append(f"API key placeholder: {key}")
          
          return ValidationResult(valid=len(issues) == 0, issues=issues)
  ```

- [x] **Auto-repair suggestions**
  - Detect common configuration problems
  - Offer one-click fixes where possible
  - Guide users through manual fixes

**Acceptance Criteria:**
- Configuration issues are detected automatically
- Clear guidance provided for fixing issues
- Auto-repair works for common problems
- Validation doesn't slow down the UI

---

## ⚡ Phase 5: UX Polish & Testing
*Estimated: 2-3 days*

### 5.1 "Configure Once, Deploy Anywhere" Workflow
**Priority: High | Complexity: Medium**

- [ ] **User preferences system**
  ```python
  class UserPreferences:
      def __init__(self):
          self.config_file = Path.home() / ".mcp-manager" / "preferences.json"
          self.preferences = self.load_preferences()
      
      def save_platform_preferences(self, platforms):
          # Remember which platforms user typically uses
          self.preferences['default_platforms'] = platforms
          self.save_preferences()
      
      def get_deployment_suggestions(self, server_name):
          # Suggest targets based on user history
          return self.preferences.get('deployment_patterns', {}).get(server_name, [])
  ```

- [ ] **Smart deployment wizard**
  - Remember user's preferred platforms
  - Suggest deployment targets based on history
  - One-click deployment to "usual" targets
  - Batch deployment with progress tracking

**Acceptance Criteria:**
- Setup wizard runs on first launch
- User preferences are remembered
- Deployment becomes faster over time
- Smart suggestions improve workflow efficiency

### 5.2 Error Handling & Recovery
**Priority: High | Complexity: Medium**

- [ ] **Comprehensive error handling**
  ```python
  class ErrorHandler:
      def handle_deployment_error(self, error, context):
          if isinstance(error, ConfigurationError):
              self.show_config_fix_dialog(error)
          elif isinstance(error, NetworkError):
              self.show_retry_dialog(error)
          else:
              self.show_generic_error(error, context)
      
      def offer_recovery_actions(self, error):
          # Suggest specific recovery steps
          # Provide one-click fixes where possible
  ```

- [ ] **Rollback capabilities**
  - Backup configurations before changes
  - Quick rollback on deployment failures
  - Transaction-like deployment operations

**Acceptance Criteria:**
- Errors are handled gracefully with clear messages
- Recovery suggestions are helpful and actionable
- Rollback works reliably when needed
- Users are never left in broken states

### 5.3 Context-Sensitive Help
**Priority: Medium | Complexity: Low**

- [ ] **Help system implementation**
  ```python
  class HelpSystem:
      def show_contextual_help(self, current_screen):
          help_content = self.get_help_for_screen(current_screen)
          self.display_help_panel(help_content)
      
      def show_keyboard_shortcuts(self):
          # Show all available shortcuts for current context
  ```

- [ ] **Tooltips and guidance**
  - Status bar tips for current actions
  - First-time user guidance
  - Keyboard shortcut reminders

**Acceptance Criteria:**
- Help is always accessible and contextual
- New users can discover features easily
- Keyboard shortcuts are discoverable
- Documentation is integrated into the app

### 5.4 Integration Testing
**Priority: High | Complexity: Medium**

- [x] **End-to-end workflow testing**
  - Test complete user journeys
  - Verify all keyboard shortcuts work
  - Test error conditions and recovery
  - Performance testing with large datasets

- [x] **Cross-platform compatibility**
  - Windows terminal compatibility
  - Different terminal emulators
  - Color scheme variations
  - Font rendering differences

**Acceptance Criteria:**
- All major workflows work end-to-end
- Performance is acceptable on target hardware
- UI renders correctly across different terminals
- No critical bugs or crashes

---

## 🚀 Phase 6: Documentation & Deployment
*Estimated: 1-2 days*

### 6.1 Documentation Updates
**Priority: Medium | Complexity: Low**

- [ ] **Update README.md**
  - New project name and description
  - Installation instructions for mcp-manager
  - Quick start guide with screenshots
  - Feature highlights and comparisons

- [ ] **Create user guide**
  - Step-by-step tutorials
  - Advanced usage scenarios
  - Troubleshooting guide
  - FAQ section

**Acceptance Criteria:**
- Documentation is comprehensive and accurate
- New users can get started quickly
- Advanced features are well explained
- Common issues are addressed

### 6.2 Migration Guide
**Priority: Low | Complexity: Low**

- [ ] **Migration documentation**
  - How to upgrade from mcp-tools-cli
  - Configuration file migration
  - Feature mapping (old vs new)
  - Breaking changes notice

- [ ] **Backward compatibility notes**
  - Which CLI commands still work
  - API changes for programmatic users
  - Deprecation timeline if applicable

**Acceptance Criteria:**
- Existing users can migrate smoothly
- Clear communication about changes
- Migration path is well documented

### 6.3 Package Testing & Distribution
**Priority: High | Complexity: Low**

- [ ] **Package validation**
  - Test installation from PyPI
  - Verify all dependencies resolve
  - Test on clean environments
  - Cross-platform installation testing

- [ ] **Release preparation**
  - Version numbering scheme
  - Changelog preparation
  - Release notes
  - Distribution testing

**Acceptance Criteria:**
- Package installs cleanly on target platforms
- All dependencies are correctly specified
- Installation process is smooth
- Package metadata is accurate

---

## 📈 Success Metrics

### User Experience Metrics
- **Setup Time**: First-time users can deploy their first server in < 5 minutes
- **Daily Usage**: Regular deployment tasks complete in < 30 seconds
- **Error Recovery**: Users can resolve common issues in < 2 minutes
- **Feature Discovery**: New features are discoverable within the UI

### Technical Metrics  
- **Performance**: UI remains responsive with 50+ servers
- **Reliability**: Zero data corruption or loss during operations
- **Compatibility**: Works on Windows, macOS, Linux terminals
- **Maintainability**: Clean code structure supports future enhancements

### Quality Standards
- **Visual Design**: Matches RepoMap professional standards
- **User Interface**: Intuitive keyboard navigation and shortcuts
- **Error Messages**: Clear, actionable, and helpful
- **Documentation**: Comprehensive and up-to-date

---

## 🔄 Risk Mitigation

### Technical Risks
- **Textual Dependency**: Fallback to CLI if TUI unavailable
- **Performance**: Profile and optimize for large server counts
- **Cross-platform**: Test thoroughly on target operating systems
- **Data Loss**: Implement robust backup and recovery mechanisms

### User Experience Risks
- **Learning Curve**: Provide comprehensive onboarding and help
- **Workflow Disruption**: Maintain CLI compatibility during transition
- **Feature Gaps**: Ensure TUI has all CLI functionality
- **Migration Issues**: Test upgrade path extensively

### Project Risks
- **Timeline**: Break work into smaller deliverable chunks
- **Scope Creep**: Focus on core requirements first
- **Quality**: Implement testing at each phase
- **Maintenance**: Document architecture and design decisions

---

## 📝 Implementation Notes

### Development Environment Setup
```bash
# Clone and setup
git clone <repo> mcp-manager
cd mcp-manager
pip install -e ".[dev]"

# Install Textual development tools
pip install textual-dev

# Run TUI in development mode
textual run --dev mcp_manager.tui:MCPManagerTUI
```

### Code Quality Standards
- Type hints for all public functions
- Comprehensive docstrings
- Unit tests for core functionality
- Integration tests for TUI workflows
- Code formatting with black
- Linting with ruff

### Testing Strategy
- Unit tests for business logic
- Widget testing for TUI components
- Integration tests for complete workflows
- Performance tests for large datasets
- Cross-platform compatibility testing
- User acceptance testing with real workflows

This sprint plan provides a comprehensive roadmap for transforming mcp-tools-cli into mcp-manager with a professional Textual TUI. Each phase builds upon the previous work while maintaining deliverable milestones throughout the development process.