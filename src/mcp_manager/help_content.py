"""Comprehensive Help Content Database for MCP Manager TUI."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class HelpSection:
    """A section of help content with metadata."""
    title: str
    content: str
    keywords: List[str]
    category: str
    shortcuts: Dict[str, str]
    tips: List[str]
    see_also: List[str]


class HelpContentDatabase:
    """Centralized database of all help content for the MCP Manager TUI."""
    
    def __init__(self):
        """Initialize the help content database."""
        self._content = self._load_help_content()
        self._keywords_index = self._build_keywords_index()
    
    def _load_help_content(self) -> Dict[str, HelpSection]:
        """Load all help content sections."""
        return {
            # View-specific help
            "registry_view": HelpSection(
                title="Server Registry",
                content="""
The Server Registry displays all configured MCP servers and their current status.
Each server shows its name, type, and enabled/disabled status.

Use this view to:
• Add new MCP servers to your configuration
• Edit existing server settings and parameters
• Enable/disable servers for deployment
• Remove servers you no longer need
• Select multiple servers for batch operations

Server Status Indicators:
✅ Enabled - Server is active and available for deployment
❌ Disabled - Server is configured but not active
⚠️ Error - Server has configuration or health issues
""",
                keywords=["registry", "servers", "add", "edit", "remove", "enable", "disable", "status"],
                category="views",
                shortcuts={
                    "A": "Add new server",
                    "E": "Edit selected server", 
                    "Delete": "Remove selected server",
                    "Space": "Toggle server selection",
                    "Enter": "Edit server (same as E)",
                    "Tab": "Switch to deployment view"
                },
                tips=[
                    "Use Space to select multiple servers for batch operations",
                    "Disabled servers won't appear in deployment options",
                    "Server names must be unique across your configuration",
                    "Press Tab to switch between registry and deployment views"
                ],
                see_also=["deployment_matrix", "server_configuration", "batch_operations"]
            ),
            
            "deployment_matrix": HelpSection(
                title="Deployment Matrix",
                content="""
The Interactive Deployment Matrix shows which servers are deployed to which platforms.
Each cell represents a server-platform combination with visual status indicators.

Matrix Cell States:
• ✅ Deployed - Server is active on this platform
• ❌ Not Deployed - Server is not configured for this platform
• 🔄 Pending - Deployment operation in progress
• ⚠️ Conflict - Configuration conflicts detected
• ❓ Unknown - Status couldn't be determined

Click or press Enter on cells to toggle deployment state.
Use Spacebar to select multiple cells for batch operations.
""",
                keywords=["deployment", "matrix", "platforms", "toggle", "deploy", "undeploy", "conflicts"],
                category="views", 
                shortcuts={
                    "Enter": "Toggle deployment for current cell",
                    "Space": "Select cell for batch operations",
                    "D": "Deploy selected servers/cells",
                    "U": "Undeploy selected servers/cells", 
                    "C": "Check for conflicts",
                    "I": "Show cell information",
                    "Tab": "Switch to registry view"
                },
                tips=[
                    "Click cells to quickly toggle deployment state",
                    "Red borders indicate configuration conflicts",
                    "Use batch operations to deploy to multiple platforms at once",
                    "Check cell information (I key) for detailed deployment status"
                ],
                see_also=["registry_view", "conflicts", "batch_operations", "platforms"]
            ),
            
            "health_dashboard": HelpSection(
                title="Health Dashboard",
                content="""
The Health Dashboard monitors the status and performance of all your MCP servers.
It provides real-time health metrics, error detection, and performance analysis.

Health Status Levels:
🟢 Healthy - Server is functioning normally
🟡 Warning - Minor issues detected, may need attention  
🔴 Critical - Serious issues requiring immediate action
⚫ Offline - Server is not responding

The dashboard includes:
• Overall health summary with counts
• Detailed server-by-server health information
• Error logs and diagnostic information
• Performance metrics and response times
• Historical health trends
""",
                keywords=["health", "monitoring", "status", "errors", "performance", "diagnostics"],
                category="views",
                shortcuts={
                    "F5": "Refresh health data immediately",
                    "Space": "Select server for detailed view",
                    "Enter": "Show server health details", 
                    "M": "Toggle background monitoring",
                    "H": "Return to main view",
                    "Tab": "Navigate between health sections"
                },
                tips=[
                    "F5 forces immediate health check of all servers",
                    "Background monitoring runs automatic health checks",
                    "Critical issues are highlighted in red",
                    "Click on servers to see detailed diagnostic information"
                ],
                see_also=["monitoring", "troubleshooting", "server_errors", "performance"]
            ),
            
            "project_focus": HelpSection(
                title="Project Focus View",
                content="""
Project Focus View shows deployment status for a specific project directory.
It displays which MCP servers are configured and deployed for the selected project.

This view is useful for:
• Managing deployments for a specific project
• Seeing project-specific server configurations
• Understanding which services are available to the project
• Deploying project-specific server setups

The view automatically detects:
• Claude configuration files in the project
• MCP server configurations specific to the project
• Local vs global server deployments
• Project dependencies and requirements
""",
                keywords=["project", "focus", "directory", "configuration", "local", "global"],
                category="views", 
                shortcuts={
                    "Enter": "Select project for management",
                    "D": "Deploy project servers",
                    "V": "Switch view mode",
                    "R": "Refresh project status",
                    "Tab": "Switch panes"
                },
                tips=[
                    "Project view shows only servers relevant to the current project",
                    "Local configurations override global ones",
                    "Use V key to cycle between different view modes",
                    "Projects are auto-detected from Claude config files"
                ],
                see_also=["server_focus", "registry_view", "configuration"]
            ),
            
            "server_focus": HelpSection(
                title="Server Focus View", 
                content="""
Server Focus View shows detailed deployment information for a specific server.
It displays all platforms where the server is deployed and their current status.

This view provides:
• Complete deployment history for the server
• Platform-specific configuration details
• Error logs and diagnostic information for the server
• Performance metrics across all deployments
• Quick actions for server management

Use this view to:
• Troubleshoot server-specific issues
• Manage deployments for a single server
• View server configuration across platforms
• Monitor server performance and health
""",
                keywords=["server", "focus", "deployment", "history", "configuration", "diagnostics"],
                category="views",
                shortcuts={
                    "Enter": "Select server for detailed view",
                    "U": "Undeploy from selected platforms", 
                    "V": "Switch view mode",
                    "R": "Refresh server status",
                    "Tab": "Switch panes"
                },
                tips=[
                    "Server focus shows deployment status across all platforms",
                    "Use this view to troubleshoot server-specific issues",
                    "Configuration differences between platforms are highlighted",
                    "Performance metrics help identify problematic deployments"
                ],
                see_also=["project_focus", "registry_view", "health_dashboard"]
            ),
            
            # Feature explanations
            "keyboard_shortcuts": HelpSection(
                title="Keyboard Shortcuts",
                content="""
MCP Manager is designed for keyboard-first operation with comprehensive shortcuts.
All shortcuts are context-sensitive and shown in the status bar.

Global Shortcuts (Always Available):
A - Add server          E - Edit server         D - Deploy
R - Refresh data        H - Health dashboard    Q - Quit
V - Switch view mode    M - Toggle monitoring   

Navigation:
Tab - Next pane         Shift+Tab - Previous pane
Enter - Default action  Escape - Cancel operation
F5 - Force refresh      ? - Show this help

Context-Sensitive Shortcuts:
Different shortcuts are available depending on which pane is focused
and what view mode you're in. Check the status bar for current options.
""",
                keywords=["keyboard", "shortcuts", "navigation", "keys", "hotkeys"],
                category="features",
                shortcuts={
                    "?": "Show keyboard shortcuts help",
                    "F1": "Open full help system",
                    "Esc": "Close help dialog"
                },
                tips=[
                    "Status bar shows available shortcuts for current context",
                    "Tab switches between server and deployment panes", 
                    "Enter key has different functions based on context",
                    "All destructive actions require confirmation"
                ],
                see_also=["navigation", "context_help", "status_bar"]
            ),
            
            "batch_operations": HelpSection(
                title="Batch Operations",
                content="""
Batch operations allow you to perform actions on multiple servers or deployments
simultaneously, saving time and ensuring consistency.

Selecting Multiple Items:
• Use Space bar to select/deselect servers or deployment cells
• Selected items are highlighted and counted in the status bar
• You can mix and match selections as needed

Available Batch Operations:
• Deploy multiple servers to multiple platforms
• Undeploy servers from selected platforms
• Run health checks on selected servers
• Enable/disable multiple servers at once

The operation progress is shown with a progress bar and detailed status updates.
You can cancel batch operations at any time with the Escape key.
""",
                keywords=["batch", "operations", "multiple", "select", "bulk", "mass"],
                category="features",
                shortcuts={
                    "Space": "Toggle selection",
                    "D": "Deploy selected items",
                    "U": "Undeploy selected items",
                    "H": "Health check selected servers",
                    "Esc": "Cancel batch operation"
                },
                tips=[
                    "Select items with Space before running batch operations",
                    "Status bar shows how many items are selected",
                    "Batch operations can be cancelled while in progress",
                    "Use batch operations to deploy consistent configurations"
                ],
                see_also=["selection", "progress", "deployment_matrix"]
            ),
            
            "conflicts": HelpSection(
                title="Deployment Conflicts",
                content="""
Deployment conflicts occur when there are incompatibilities or issues
with server configurations, platform requirements, or dependencies.

Types of Conflicts:
⚠️  Version Mismatch - Server requires different version than available
🔴 Missing Dependency - Required dependency not found on platform  
⚠️  Configuration Error - Invalid or missing configuration parameters
🔴 Platform Incompatible - Server not supported on target platform
⚠️  Resource Conflict - Multiple servers trying to use same resources

Conflict Resolution:
• Auto-resolve: Let the system fix common issues automatically
• Manual resolve: Choose specific resolution for complex conflicts
• Ignore: Mark conflict as acceptable and proceed anyway
• Cancel: Stop deployment and fix issues manually

Cells with conflicts are highlighted in red in the deployment matrix.
""",
                keywords=["conflicts", "errors", "resolution", "dependencies", "compatibility"],
                category="features", 
                shortcuts={
                    "C": "Check for conflicts", 
                    "Enter": "View conflict details",
                    "R": "Resolve selected conflict",
                    "I": "Ignore conflict",
                    "Esc": "Cancel conflict resolution"
                },
                tips=[
                    "Red borders in the matrix indicate conflicts",
                    "Auto-resolve can fix many common issues",
                    "Some conflicts require manual intervention",
                    "Resolving conflicts before deployment prevents errors"
                ],
                see_also=["deployment_matrix", "troubleshooting", "configuration"]
            ),
            
            # Configuration help
            "server_configuration": HelpSection(
                title="Server Configuration",
                content="""
MCP servers are configured through JSON files that specify how to connect
to and interact with different services and tools.

Basic Server Structure:
{
  "name": "server-name",
  "type": "stdio|sse",
  "command": "path/to/executable",
  "args": ["--arg1", "value1"],
  "env": {"ENV_VAR": "value"}
}

Configuration Options:
• name: Unique identifier for the server
• type: Communication protocol (stdio, sse, websocket)
• command: Executable path or command to run
• args: Command line arguments
• env: Environment variables
• metadata: Additional settings (enabled, description, etc.)

Configuration files are typically stored in:
• Global: ~/.claude/mcp-servers.json
• Project: .claude/mcp-servers.json
""",
                keywords=["configuration", "config", "json", "servers", "setup", "files"],
                category="configuration",
                shortcuts={
                    "E": "Edit server configuration",
                    "A": "Add new server",
                    "V": "View configuration file",
                    "R": "Reload configuration"
                },
                tips=[
                    "Server names must be unique within a configuration",
                    "Use relative paths for project-specific servers", 
                    "Environment variables can contain secrets",
                    "Test configuration with health checks after changes"
                ],
                see_also=["registry_view", "platforms", "troubleshooting"]
            ),
            
            "platforms": HelpSection(
                title="Platform Management",
                content="""
Platforms represent different environments where MCP servers can be deployed.
Each platform has its own configuration, capabilities, and requirements.

Supported Platforms:
• Claude Desktop - Desktop application integration
• Claude Web - Web-based Claude interface  
• Continue - VS Code extension
• Custom - User-defined platform configurations

Platform Status:
✅ Available - Platform is detected and ready
❌ Not Found - Platform is not installed or configured
⚠️  Issues - Platform has configuration or compatibility issues

Platform-Specific Features:
• Different platforms support different server types
• Some platforms require specific configuration formats
• Deployment processes vary between platforms
• Platform capabilities affect server functionality
""",
                keywords=["platforms", "deployment", "targets", "environments", "claude", "continue"],
                category="configuration",
                shortcuts={
                    "P": "Platform management (coming soon)",
                    "D": "Deploy to platforms",
                    "H": "Check platform health",
                    "R": "Refresh platform status"
                },
                tips=[
                    "Not all servers work on all platforms",
                    "Platform detection is automatic but can be overridden",
                    "Check platform requirements before deployment",
                    "Some platforms require additional setup steps"
                ],
                see_also=["deployment_matrix", "server_configuration", "conflicts"]
            ),
            
            # Troubleshooting
            "troubleshooting": HelpSection(
                title="Troubleshooting Guide",
                content="""
Common issues and their solutions for the MCP Manager TUI.

Keyboard Shortcuts Not Working:
• Check which pane has focus (highlighted border)
• Verify shortcut is available in current context
• Look at status bar for available actions

Deployment Failures:
• Check server configuration for errors
• Verify platform is available and compatible
• Review conflict resolution suggestions
• Check server logs for detailed error messages

Health Check Issues:
• Ensure servers are properly configured
• Check network connectivity and permissions
• Verify server executable exists and is runnable
• Review environment variables and dependencies

Configuration Problems:
• Validate JSON syntax in configuration files
• Check file permissions and accessibility
• Ensure server names are unique
• Verify paths and commands are correct

Performance Issues:
• Monitor server resource usage
• Check for network latency or timeouts
• Review server logs for performance warnings
• Consider adjusting timeout and retry settings
""",
                keywords=["troubleshooting", "problems", "issues", "errors", "fixes", "solutions"],
                category="troubleshooting",
                shortcuts={
                    "H": "Run health checks",
                    "R": "Refresh data",
                    "F5": "Force refresh",
                    "L": "View logs (coming soon)"
                },
                tips=[
                    "Check the status bar for error messages",
                    "Health dashboard provides detailed diagnostic information",
                    "Many issues can be resolved by refreshing data",
                    "Configuration errors are often syntax-related"
                ],
                see_also=["health_dashboard", "server_configuration", "conflicts"]
            ),
            
            "getting_started": HelpSection(
                title="Getting Started", 
                content="""
Welcome to MCP Manager! This guide will help you get started with managing
your MCP (Model Context Protocol) servers and deployments.

First Steps:
1. Add Your First Server
   • Press 'A' to open the Add Server dialog
   • Enter server name, command, and configuration
   • Enable the server for deployment

2. Explore the Interface
   • Use Tab to switch between server and deployment panes
   • Check the status bar for available keyboard shortcuts
   • Press 'H' to view the health dashboard

3. Deploy Servers
   • Select servers in the registry (Space to multi-select)
   • Press 'D' to deploy to available platforms
   • Monitor progress with the progress bar

4. Monitor Health
   • Use 'H' to open the health dashboard
   • Monitor server status and performance
   • Address any health issues that arise

5. Learn More
   • Press '?' for keyboard shortcuts
   • Press 'F1' for comprehensive help
   • Check status bar for context-sensitive tips
""",
                keywords=["getting", "started", "welcome", "introduction", "first", "steps"],
                category="introduction",
                shortcuts={
                    "A": "Add your first server",
                    "H": "View health dashboard", 
                    "D": "Deploy servers",
                    "?": "Show keyboard shortcuts",
                    "F1": "Open full help"
                },
                tips=[
                    "Start by adding at least one MCP server",
                    "Use the health dashboard to monitor server status",
                    "Keyboard shortcuts make the interface much faster",
                    "Status bar provides context-sensitive guidance"
                ],
                see_also=["server_configuration", "keyboard_shortcuts", "health_dashboard"]
            )
        }
    
    def _build_keywords_index(self) -> Dict[str, List[str]]:
        """Build an index of keywords to help section IDs."""
        index = {}
        for section_id, section in self._content.items():
            for keyword in section.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower not in index:
                    index[keyword_lower] = []
                index[keyword_lower].append(section_id)
        return index
    
    def get_section(self, section_id: str) -> Optional[HelpSection]:
        """Get a specific help section."""
        return self._content.get(section_id)
    
    def search_content(self, query: str) -> List[str]:
        """Search help content by keywords and return matching section IDs."""
        query_lower = query.lower().strip()
        if not query_lower:
            return list(self._content.keys())
        
        matches = set()
        
        # Direct keyword matches
        if query_lower in self._keywords_index:
            matches.update(self._keywords_index[query_lower])
        
        # Partial keyword matches
        for keyword, section_ids in self._keywords_index.items():
            if query_lower in keyword or keyword in query_lower:
                matches.update(section_ids)
        
        # Content text search
        for section_id, section in self._content.items():
            if (query_lower in section.title.lower() or 
                query_lower in section.content.lower()):
                matches.add(section_id)
        
        return list(matches)
    
    def get_sections_by_category(self, category: str) -> List[str]:
        """Get all section IDs in a specific category."""
        return [
            section_id for section_id, section in self._content.items()
            if section.category == category
        ]
    
    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        categories = set()
        for section in self._content.values():
            categories.add(section.category)
        return sorted(list(categories))
    
    def get_contextual_help(self, context: str) -> Optional[HelpSection]:
        """Get help content for a specific context."""
        context_mapping = {
            "server": "registry_view",
            "deployment": "deployment_matrix", 
            "health": "health_dashboard",
            "project_focus": "project_focus",
            "server_focus": "server_focus"
        }
        
        section_id = context_mapping.get(context)
        return self.get_section(section_id) if section_id else None
    
    def get_keyboard_shortcuts_for_context(self, context: str) -> Dict[str, str]:
        """Get keyboard shortcuts for a specific context."""
        section = self.get_contextual_help(context)
        return section.shortcuts if section else {}
    
    def get_tips_for_context(self, context: str) -> List[str]:
        """Get tips for a specific context."""
        section = self.get_contextual_help(context)
        return section.tips if section else []


# Global instance for easy access
help_content = HelpContentDatabase()